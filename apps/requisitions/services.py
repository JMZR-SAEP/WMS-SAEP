import hashlib
import json
from dataclasses import dataclass, replace
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.core.api.exceptions import DomainConflict
from apps.core.events import (
    REQUISICAO_ATENDIDA,
    REQUISICAO_AUTORIZADA,
    REQUISICAO_CANCELADA,
    REQUISICAO_ENVIADA_AUTORIZACAO,
    REQUISICAO_RECUSADA,
    publish_on_commit,
)
from apps.materials.models import Material
from apps.requisitions.models import (
    EventoTimeline,
    ItemRequisicao,
    Requisicao,
    RequisicaoIdempotencyKey,
    SequenciaNumeroRequisicao,
    StatusIdempotencia,
    StatusRequisicao,
    TipoEvento,
)
from apps.requisitions.policies import (
    pode_atender_requisicao,
    pode_autorizar_requisicao,
    pode_cancelar_autorizada,
    pode_manipular_pre_autorizacao,
    pode_visualizar_requisicao,
    queryset_fila_atendimento,
    queryset_fila_autorizacao,
)
from apps.stock.models import EstoqueMaterial
from apps.stock.services import (
    registrar_liberacao_reserva_por_atendimento,
    registrar_reserva_por_autorizacao,
    registrar_saida_por_atendimento,
)
from apps.users.models import PapelChoices, Setor
from apps.users.policies import (
    pode_criar_requisicao_para,
    pode_ver_fila_atendimento,
)

User = get_user_model()
IDEMPOTENCY_ENDPOINT_FULFILL = "requisitions_fulfill"


@dataclass(frozen=True)
class ItemRascunhoData:
    material_id: int
    quantidade_solicitada: Decimal
    observacao: str = ""


@dataclass(frozen=True)
class ItemAutorizacaoData:
    item_id: int
    quantidade_autorizada: Decimal
    justificativa_autorizacao_parcial: str = ""


@dataclass(frozen=True)
class ItemAtendimentoData:
    item_id: int
    quantidade_entregue: Decimal
    justificativa_atendimento_parcial: str = ""


ItemAtendimentoPayload = ItemAtendimentoData | dict[str, object]


def _decimal_canonico(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _hash_payload_atendimento(
    *,
    itens: list[ItemAtendimentoData] | None,
    retirante_fisico: str,
    observacao_atendimento: str,
) -> str:
    payload: dict[str, object] = {
        "itens": None,
        "observacao_atendimento": observacao_atendimento.strip(),
        "retirante_fisico": retirante_fisico.strip(),
    }
    if itens is not None:
        payload["itens"] = [
            {
                "item_id": item.item_id,
                "justificativa_atendimento_parcial": (
                    item.justificativa_atendimento_parcial.strip()
                ),
                "quantidade_entregue": _decimal_canonico(item.quantidade_entregue),
            }
            for item in sorted(itens, key=lambda item: item.item_id)
        ]
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload_json.encode()).hexdigest()


def _normalizar_itens_atendimento(
    itens: list[ItemAtendimentoPayload] | None,
) -> list[ItemAtendimentoData] | None:
    if itens is None:
        return None
    return [
        item if isinstance(item, ItemAtendimentoData) else ItemAtendimentoData(**item)
        for item in itens
    ]


def _validacao_payload_atendimento(message: str, *, item_ids: list[int] | None = None):
    details: dict[str, object] = {"itens": [message]}
    if item_ids is not None:
        details["item_ids"] = item_ids
    return ValidationError(details)


def _side_effect_reservar_itens_autorizados(
    requisicao: Requisicao, payload: dict[str, object]
) -> None:
    # CONTRATO: payload precisa conter "itens_requisicao": list[ItemRequisicao]
    # quando este side effect for registrado em TRANSICOES_REQUISICAO.
    for item_requisicao in payload["itens_requisicao"]:
        quantidade_autorizada = item_requisicao.quantidade_autorizada
        if quantidade_autorizada <= 0:
            continue
        registrar_reserva_por_autorizacao(
            requisicao=requisicao,
            item=item_requisicao,
            quantidade=quantidade_autorizada,
        )


def _side_effect_liberar_reservas_cancelamento(
    requisicao: Requisicao, payload: dict[str, object]
) -> None:
    estoques_por_material_id = payload["estoques_por_material_id"]
    for item_requisicao in payload["itens_requisicao"]:
        quantidade_liberada = item_requisicao.quantidade_autorizada
        if quantidade_liberada <= 0:
            continue
        registrar_liberacao_reserva_por_atendimento(
            requisicao=requisicao,
            item=item_requisicao,
            quantidade=quantidade_liberada,
            estoque_travado=estoques_por_material_id[item_requisicao.material_id],
        )


TRANSICOES_REQUISICAO: dict[str, dict[str, object]] = {
    "autorizar_total": {
        "from_status": (StatusRequisicao.AGUARDANDO_AUTORIZACAO,),
        "to_status": StatusRequisicao.AUTORIZADA,
        "timeline_event_type": TipoEvento.AUTORIZACAO_TOTAL,
        "audit_fields_to_set": (
            "chefe_autorizador",
            "data_autorizacao_ou_recusa",
            "status",
        ),
        "side_effects": (_side_effect_reservar_itens_autorizados,),
        "notification_event": REQUISICAO_AUTORIZADA,
    },
    "autorizar_parcial": {
        "from_status": (StatusRequisicao.AGUARDANDO_AUTORIZACAO,),
        "to_status": StatusRequisicao.AUTORIZADA,
        "timeline_event_type": TipoEvento.AUTORIZACAO_PARCIAL,
        "audit_fields_to_set": (
            "chefe_autorizador",
            "data_autorizacao_ou_recusa",
            "status",
        ),
        "side_effects": (_side_effect_reservar_itens_autorizados,),
        "notification_event": REQUISICAO_AUTORIZADA,
    },
    "recusar": {
        "from_status": (StatusRequisicao.AGUARDANDO_AUTORIZACAO,),
        "to_status": StatusRequisicao.RECUSADA,
        "timeline_event_type": TipoEvento.RECUSA,
        "audit_fields_to_set": (
            "chefe_autorizador",
            "data_autorizacao_ou_recusa",
            "motivo_recusa",
            "status",
        ),
        "side_effects": (),
        "notification_event": REQUISICAO_RECUSADA,
    },
    "atender_total": {
        "from_status": (StatusRequisicao.AUTORIZADA,),
        "to_status": StatusRequisicao.ATENDIDA,
        "timeline_event_type": TipoEvento.ATENDIMENTO,
        "audit_fields_to_set": (
            "responsavel_atendimento",
            "data_finalizacao",
            "retirante_fisico",
            "observacao_atendimento",
            "status",
        ),
        "side_effects": (),
        "notification_event": REQUISICAO_ATENDIDA,
    },
    "atender_parcial": {
        "from_status": (StatusRequisicao.AUTORIZADA,),
        "to_status": StatusRequisicao.ATENDIDA_PARCIALMENTE,
        "timeline_event_type": TipoEvento.ATENDIMENTO_PARCIAL,
        "audit_fields_to_set": (
            "responsavel_atendimento",
            "data_finalizacao",
            "retirante_fisico",
            "observacao_atendimento",
            "status",
        ),
        "side_effects": (),
        "notification_event": REQUISICAO_ATENDIDA,
    },
    "cancelar_pos_autorizacao_sem_saldo": {
        "from_status": (StatusRequisicao.AUTORIZADA,),
        "to_status": StatusRequisicao.CANCELADA,
        "timeline_event_type": TipoEvento.CANCELAMENTO,
        "audit_fields_to_set": (
            "responsavel_atendimento",
            "data_finalizacao",
            "motivo_cancelamento",
            "status",
        ),
        "side_effects": (_side_effect_liberar_reservas_cancelamento,),
        "notification_event": REQUISICAO_CANCELADA,
    },
    "cancelar_pre_autorizacao": {
        "from_status": (
            StatusRequisicao.RASCUNHO,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        ),
        "to_status": StatusRequisicao.CANCELADA,
        "timeline_event_type": TipoEvento.CANCELAMENTO,
        "audit_fields_to_set": (
            "data_finalizacao",
            "status",
        ),
        "side_effects": (),
        "notification_event": REQUISICAO_CANCELADA,
    },
}


def _apply_requisicao_transition(
    requisicao: Requisicao,
    transition_name: str,
    actor: User,
    *,
    payload: dict[str, object],
) -> Requisicao:
    config = TRANSICOES_REQUISICAO[transition_name]

    if requisicao.status not in config["from_status"]:
        raise DomainConflict(
            "Transição inválida para o status atual da requisição.",
            details={"status_atual": requisicao.status, "transicao": transition_name},
        )

    for field_name in config["audit_fields_to_set"]:
        if field_name == "status":
            setattr(requisicao, field_name, config["to_status"])
            continue
        setattr(requisicao, field_name, payload[field_name])

    requisicao.full_clean()
    requisicao.save(
        update_fields=[
            *config["audit_fields_to_set"],
            "updated_at",
        ]
    )
    EventoTimeline.objects.create(
        requisicao=requisicao,
        tipo_evento=config["timeline_event_type"],
        usuario=actor,
    )

    for side_effect in config["side_effects"]:
        side_effect(requisicao, payload)

    notification_event = config.get("notification_event")
    if notification_event:
        _publish_notification_event_on_commit(notification_event, requisicao)

    return requisicao


def _publish_notification_event_on_commit(event_name: str, requisicao: Requisicao) -> None:
    if not transaction.get_connection().in_atomic_block:
        raise DomainConflict(
            "Publicação de notificação de requisição exige transação ativa.",
            details={"requisicao_id": requisicao.pk, "event_name": event_name},
        )
    publish_on_commit(event_name, {"requisicao_id": requisicao.pk})


def _material_e_estoque_validos_autorizacao(
    *, material: Material, quantidade_autorizada: Decimal
) -> None:
    errors = {}
    estoque = getattr(material, "estoque", None)

    if not material.is_active:
        errors["material_id"] = f"Material {material.codigo_completo} está inativo."
    elif estoque is None:
        errors["material_id"] = f"Material {material.codigo_completo} está sem estoque disponível."
    else:
        saldo_disponivel = estoque.saldo_disponivel
        if quantidade_autorizada > saldo_disponivel:
            errors["quantidade_autorizada"] = (
                f"Quantidade autorizada ({quantidade_autorizada}) excede o saldo disponível "
                f"({saldo_disponivel}) para o material {material.codigo_completo}."
            )

    if errors:
        raise DomainConflict(
            "Requisição em conflito com o estado atual do estoque.", details=errors
        )


def _validar_itens_autorizacao(
    *, itens_requisicao: list[ItemRequisicao], itens: list[ItemAutorizacaoData]
) -> dict[int, ItemAutorizacaoData]:
    if not itens:
        raise ValidationError({"itens": ["Informe ao menos um item para autorizar."]})

    itens_por_id = {item.item_id: item for item in itens}
    if len(itens_por_id) != len(itens):
        raise ValidationError(
            {"itens": ["Não informe o mesmo item mais de uma vez na mesma autorização."]}
        )

    itens_requisicao_por_id = {item.id: item for item in itens_requisicao}

    missing_ids = [item.id for item in itens_requisicao if item.id not in itens_por_id]
    if missing_ids:
        raise ValidationError({"itens": [f"Itens ausentes na autorização: {missing_ids}."]})

    extra_ids = [item_id for item_id in itens_por_id if item_id not in itens_requisicao_por_id]
    if extra_ids:
        raise ValidationError({"itens": [f"Itens inválidos na autorização: {extra_ids}."]})

    houve_quantidade_maior_que_zero = False
    erros_itens: list[dict[str, list[str]]] = [{} for _ in itens]
    for index, item_autorizacao in enumerate(itens):
        item_requisicao = itens_requisicao_por_id[item_autorizacao.item_id]
        item_erros: dict[str, list[str]] = {}
        justificativa_autorizacao_parcial = (
            item_autorizacao.justificativa_autorizacao_parcial or ""
        ).strip()

        if item_autorizacao.quantidade_autorizada < 0:
            item_erros["quantidade_autorizada"] = ["Não pode ser negativa."]
        if item_autorizacao.quantidade_autorizada > item_requisicao.quantidade_solicitada:
            item_erros["quantidade_autorizada"] = [
                "Não pode ser maior que a quantidade solicitada."
            ]
        if (
            item_autorizacao.quantidade_autorizada < item_requisicao.quantidade_solicitada
            and not justificativa_autorizacao_parcial
        ):
            item_erros["justificativa_autorizacao_parcial"] = [
                "Justificativa é obrigatória quando a autorização é parcial ou zero."
            ]

        if item_erros:
            erros_itens[index] = item_erros
            continue

        if item_autorizacao.quantidade_autorizada > 0:
            houve_quantidade_maior_que_zero = True
        itens_por_id[item_autorizacao.item_id] = replace(
            item_autorizacao,
            justificativa_autorizacao_parcial=justificativa_autorizacao_parcial,
        )

    if any(erros_itens):
        raise ValidationError({"itens": erros_itens})

    if not houve_quantidade_maior_que_zero:
        raise DomainConflict(
            "Autorização deve manter ao menos um item com quantidade maior que zero.",
            details={"itens": "Autorize pelo menos um item com quantidade maior que zero."},
        )

    return itens_por_id


def _material_e_estoque_validos(*, material: Material, quantidade_solicitada: Decimal) -> None:
    errors = {}
    estoque = getattr(material, "estoque", None)

    if not material.is_active:
        errors["material_id"] = f"Material {material.codigo_completo} está inativo."

    if estoque is None:
        errors["material_id"] = f"Material {material.codigo_completo} está sem estoque disponível."
    else:
        saldo_disponivel = estoque.saldo_disponivel
        if saldo_disponivel <= 0:
            errors["material_id"] = (
                f"Material {material.codigo_completo} está sem saldo disponível para requisição."
            )
        elif quantidade_solicitada > saldo_disponivel:
            errors["quantidade_solicitada"] = (
                f"Quantidade solicitada ({quantidade_solicitada}) excede o saldo disponível "
                f"({saldo_disponivel}) para o material {material.codigo_completo}."
            )

    if errors:
        raise DomainConflict(
            "Requisição em conflito com o estado atual do estoque.", details=errors
        )


def _recarregar_requisicao_para_autorizacao(requisicao: Requisicao) -> Requisicao:
    return (
        Requisicao.objects.select_for_update()
        .select_related("criador", "beneficiario", "setor_beneficiario")
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=requisicao.pk)
    )


def _recarregar_requisicao_para_atendimento(requisicao: Requisicao) -> Requisicao:
    return (
        Requisicao.objects.select_for_update()
        .select_related("criador", "beneficiario", "setor_beneficiario")
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=requisicao.pk)
    )


def _recarregar_requisicao_detalhe(requisicao_id: int) -> Requisicao:
    return (
        Requisicao.objects.select_related(
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "chefe_autorizador",
            "responsavel_atendimento",
        )
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=requisicao_id)
    )


def _obter_registro_idempotencia_atendimento(
    *,
    requisicao: Requisicao,
    ator: User,
    idempotency_key: str,
    payload_hash: str,
) -> tuple[RequisicaoIdempotencyKey, bool]:
    lookup = {
        "usuario": ator,
        "requisicao": requisicao,
        "endpoint": IDEMPOTENCY_ENDPOINT_FULFILL,
        "key": idempotency_key,
    }
    try:
        with transaction.atomic():
            return RequisicaoIdempotencyKey.objects.select_for_update().get_or_create(
                **lookup,
                defaults={
                    "payload_hash": payload_hash,
                    "status": StatusIdempotencia.IN_PROGRESS,
                },
            )
    except IntegrityError:
        return RequisicaoIdempotencyKey.objects.select_for_update().get(**lookup), False


def _travar_estoques_dos_itens(
    itens_requisicao: list[ItemRequisicao],
) -> dict[int, EstoqueMaterial]:
    material_ids = sorted({item.material_id for item in itens_requisicao})
    estoques = list(
        EstoqueMaterial.objects.select_for_update()
        .select_related("material")
        .filter(material_id__in=material_ids)
        .order_by("material_id")
    )
    estoques_por_material_id = {estoque.material_id: estoque for estoque in estoques}
    material_ids_sem_estoque = set(material_ids) - set(estoques_por_material_id)
    if material_ids_sem_estoque:
        raise DomainConflict(
            "Material autorizado não possui estoque cadastrado.",
            details={"material_ids": sorted(material_ids_sem_estoque)},
        )
    return estoques_por_material_id


def _validar_itens_rascunho(itens: list[ItemRascunhoData]) -> list[Material]:
    if not itens:
        raise ValidationError({"itens": ["Informe ao menos um item para criar a requisição."]})

    material_ids = [item.material_id for item in itens]
    if len(set(material_ids)) != len(material_ids):
        raise ValidationError(
            {"itens": ["Não informe o mesmo material mais de uma vez na mesma requisição."]}
        )

    materiais = list(
        Material.objects.select_related("subgrupo__grupo", "estoque")
        .filter(pk__in=material_ids)
        .order_by("codigo_completo")
    )
    materiais_por_id = {material.pk: material for material in materiais}

    missing_ids = [
        material_id for material_id in material_ids if material_id not in materiais_por_id
    ]
    if missing_ids:
        raise ValidationError({"itens": [f"Materiais inexistentes: {missing_ids}."]})

    for item in itens:
        if item.quantidade_solicitada <= 0:
            raise ValidationError(
                {"itens": ["Quantidade solicitada deve ser maior que zero para todos os itens."]}
            )
        _material_e_estoque_validos(
            material=materiais_por_id[item.material_id],
            quantidade_solicitada=item.quantidade_solicitada,
        )

    return [materiais_por_id[item.material_id] for item in itens]


def _gerar_numero_publico(*, ano: int | None = None) -> str:
    ano = ano or timezone.localdate().year

    with transaction.atomic():
        try:
            sequencia = SequenciaNumeroRequisicao.objects.select_for_update().get(ano=ano)
        except SequenciaNumeroRequisicao.DoesNotExist:
            try:
                with transaction.atomic():
                    sequencia = SequenciaNumeroRequisicao.objects.create(
                        ano=ano,
                        ultimo_numero=0,
                    )
            except IntegrityError:
                sequencia = SequenciaNumeroRequisicao.objects.select_for_update().get(ano=ano)

        sequencia.ultimo_numero += 1
        sequencia.save(update_fields=["ultimo_numero", "updated_at"])
        return f"REQ-{ano}-{sequencia.ultimo_numero:06d}"


def criar_rascunho_requisicao(
    *,
    criador: User,
    beneficiario: User,
    observacao: str,
    itens: list[ItemRascunhoData],
) -> Requisicao:
    if not pode_criar_requisicao_para(criador, beneficiario):
        raise PermissionDenied(
            "Usuário sem permissão para criar requisição para este beneficiário."
        )

    if beneficiario.setor_id is None:
        raise ValidationError(
            {"beneficiario_id": ["Beneficiário deve possuir setor para criar a requisição."]}
        )

    if not beneficiario.setor.is_active:
        raise DomainConflict(
            "Setor do beneficiário está inativo.",
            details={"beneficiario_id": f"Setor '{beneficiario.setor.nome}' está inativo."},
        )

    materiais = _validar_itens_rascunho(itens)

    with transaction.atomic():
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario,
            observacao=observacao,
        )
        materiais_por_id = {material.pk: material for material in materiais}
        ItemRequisicao.objects.bulk_create(
            [
                ItemRequisicao(
                    requisicao=requisicao,
                    material=materiais_por_id[item.material_id],
                    unidade_medida=materiais_por_id[item.material_id].unidade_medida,
                    quantidade_solicitada=item.quantidade_solicitada,
                    observacao=item.observacao,
                )
                for item in itens
            ]
        )

    return (
        Requisicao.objects.select_related(
            "criador",
            "beneficiario",
            "setor_beneficiario",
        )
        .prefetch_related("itens__material", "eventos__usuario")
        .get(pk=requisicao.pk)
    )


def atualizar_rascunho_requisicao(
    *,
    requisicao_id: int,
    ator: User,
    beneficiario_id: int,
    observacao: str,
    itens: list[ItemRascunhoData],
) -> Requisicao:
    with transaction.atomic():
        try:
            requisicao_locked = (
                Requisicao.objects.select_related(
                    "criador",
                    "beneficiario",
                    "setor_beneficiario",
                )
                .select_for_update()
                .prefetch_related("itens__material", "eventos__usuario")
                .get(pk=requisicao_id)
            )
        except Requisicao.DoesNotExist as exc:
            raise NotFound("Requisição não encontrada.") from exc

        if not pode_visualizar_requisicao(ator, requisicao_locked):
            raise NotFound("Requisição não encontrada.")

        if not pode_manipular_pre_autorizacao(ator, requisicao_locked):
            raise PermissionDenied("Apenas criador pode editar a requisição.")

        if requisicao_locked.status != StatusRequisicao.RASCUNHO:
            raise DomainConflict(
                "Somente requisições em rascunho podem ser editadas.",
                details={"status_atual": requisicao_locked.status},
            )

        try:
            beneficiario_locked = User.objects.select_for_update().get(pk=beneficiario_id)
        except User.DoesNotExist as exc:
            raise NotFound("Beneficiário não encontrado.") from exc

        if beneficiario_locked.setor_id is None:
            raise ValidationError({"beneficiario_id": ["Beneficiário deve possuir setor válido."]})

        setor_beneficiario_locked = Setor.objects.select_for_update().get(
            pk=beneficiario_locked.setor_id
        )

        if not setor_beneficiario_locked.is_active:
            raise DomainConflict(
                "Setor do beneficiário está inativo.",
                details={
                    "beneficiario_id": f"Setor '{setor_beneficiario_locked.nome}' está inativo."
                },
            )

        if not pode_criar_requisicao_para(ator, beneficiario_locked):
            raise PermissionDenied(
                "Usuário sem permissão para criar requisição para este beneficiário."
            )

        materiais = _validar_itens_rascunho(itens)

        requisicao_locked.beneficiario = beneficiario_locked
        requisicao_locked.setor_beneficiario = setor_beneficiario_locked
        requisicao_locked.observacao = observacao
        requisicao_locked.full_clean()
        requisicao_locked.save(
            update_fields=[
                "beneficiario",
                "setor_beneficiario",
                "observacao",
                "updated_at",
            ]
        )

        requisicao_locked.itens.all().delete()
        materiais_por_id = {material.pk: material for material in materiais}
        ItemRequisicao.objects.bulk_create(
            [
                ItemRequisicao(
                    requisicao=requisicao_locked,
                    material=materiais_por_id[item.material_id],
                    unidade_medida=materiais_por_id[item.material_id].unidade_medida,
                    quantidade_solicitada=item.quantidade_solicitada,
                    observacao=item.observacao,
                )
                for item in itens
            ]
        )

    return (
        Requisicao.objects.select_related(
            "criador",
            "beneficiario",
            "setor_beneficiario",
        )
        .prefetch_related("itens__material", "eventos__usuario")
        .get(pk=requisicao_id)
    )


def enviar_para_autorizacao(*, requisicao: Requisicao, ator: User) -> Requisicao:
    with transaction.atomic():
        requisicao = (
            Requisicao.objects.select_for_update()
            .select_related("criador", "beneficiario", "setor_beneficiario")
            .prefetch_related("itens__material__estoque", "eventos__usuario")
            .get(pk=requisicao.pk)
        )

        if not pode_manipular_pre_autorizacao(ator, requisicao):
            raise PermissionDenied("Apenas criador pode enviar a requisição.")

        if requisicao.status != StatusRequisicao.RASCUNHO:
            raise DomainConflict(
                "Somente requisições em rascunho podem ser enviadas para autorização.",
                details={"status_atual": requisicao.status},
            )

        itens = list(requisicao.itens.all())
        if not itens:
            raise DomainConflict(
                "Requisição sem itens não pode ser enviada.",
                details={"itens": "Adicione ao menos um item válido antes do envio."},
            )

        for item in itens:
            _material_e_estoque_validos(
                material=item.material,
                quantidade_solicitada=item.quantidade_solicitada,
            )

        is_primeiro_envio = not requisicao.numero_publico
        if is_primeiro_envio:
            numero_publico = _gerar_numero_publico()
            requisicao.numero_publico = numero_publico
            requisicao.data_envio_autorizacao = timezone.now()

        requisicao.status = StatusRequisicao.AGUARDANDO_AUTORIZACAO
        requisicao.full_clean()
        requisicao.save(
            update_fields=[
                "numero_publico",
                "status",
                "data_envio_autorizacao",
                "updated_at",
            ]
        )
        EventoTimeline.objects.create(
            requisicao=requisicao,
            tipo_evento=(
                TipoEvento.ENVIO_AUTORIZACAO
                if is_primeiro_envio
                else TipoEvento.REENVIO_AUTORIZACAO
            ),
            usuario=ator,
        )
        _publish_notification_event_on_commit(REQUISICAO_ENVIADA_AUTORIZACAO, requisicao)

    return (
        Requisicao.objects.select_related(
            "criador",
            "beneficiario",
            "setor_beneficiario",
        )
        .prefetch_related("itens__material", "eventos__usuario")
        .get(pk=requisicao.pk)
    )


def retornar_para_rascunho(*, requisicao: Requisicao, ator: User) -> Requisicao:
    with transaction.atomic():
        requisicao = (
            Requisicao.objects.select_for_update()
            .select_related("criador", "beneficiario", "setor_beneficiario")
            .prefetch_related("itens__material", "eventos__usuario")
            .get(pk=requisicao.pk)
        )

        if not pode_manipular_pre_autorizacao(ator, requisicao):
            raise PermissionDenied("Apenas criador ou beneficiário podem retornar a requisição.")

        if requisicao.status != StatusRequisicao.AGUARDANDO_AUTORIZACAO:
            raise DomainConflict(
                "Somente requisições aguardando autorização podem retornar para rascunho.",
                details={"status_atual": requisicao.status},
            )

        requisicao.status = StatusRequisicao.RASCUNHO
        requisicao.save(update_fields=["status", "updated_at"])
        EventoTimeline.objects.create(
            requisicao=requisicao,
            tipo_evento=TipoEvento.RETORNO_RASCUNHO,
            usuario=ator,
        )

    return (
        Requisicao.objects.select_related(
            "criador",
            "beneficiario",
            "setor_beneficiario",
        )
        .prefetch_related("itens__material", "eventos__usuario")
        .get(pk=requisicao.pk)
    )


def descartar_rascunho_nunca_enviado(*, requisicao: Requisicao, ator: User) -> None:
    with transaction.atomic():
        requisicao = (
            Requisicao.objects.select_for_update().prefetch_related("itens").get(pk=requisicao.pk)
        )

        if not pode_manipular_pre_autorizacao(ator, requisicao):
            raise PermissionDenied("Apenas criador pode descartar a requisição.")

        if requisicao.status != StatusRequisicao.RASCUNHO:
            raise DomainConflict(
                "Somente requisições em rascunho podem ser descartadas.",
                details={"status_atual": requisicao.status},
            )
        if requisicao.numero_publico or requisicao.data_envio_autorizacao is not None:
            raise DomainConflict(
                "Rascunho já formalizado deve ser cancelado logicamente, não descartado.",
                details={"numero_publico": requisicao.numero_publico},
            )

        requisicao.itens.all().delete()
        requisicao.delete()


def _cancelar_pre_autorizacao(*, requisicao: Requisicao, ator: User) -> Requisicao:
    if not pode_manipular_pre_autorizacao(ator, requisicao):
        if requisicao.status == StatusRequisicao.RASCUNHO:
            raise PermissionDenied("Apenas criador pode cancelar a requisição.")
        raise PermissionDenied("Apenas criador ou beneficiário podem cancelar a requisição.")

    if requisicao.status == StatusRequisicao.RASCUNHO:
        if not requisicao.numero_publico:
            raise DomainConflict(
                "Rascunho nunca enviado deve ser descartado, não cancelado logicamente.",
                details={"status_atual": requisicao.status},
            )
    elif requisicao.status != StatusRequisicao.AGUARDANDO_AUTORIZACAO:
        raise DomainConflict(
            "Somente rascunhos já formalizados ou requisições aguardando autorização podem ser cancelados.",
            details={"status_atual": requisicao.status},
        )

    return _apply_requisicao_transition(
        requisicao=requisicao,
        transition_name="cancelar_pre_autorizacao",
        actor=ator,
        payload={
            "data_finalizacao": timezone.now(),
        },
    )


def _cancelar_autorizada_sem_saldo(
    *, requisicao: Requisicao, ator: User, motivo_cancelamento: str
) -> Requisicao:
    motivo_cancelamento = motivo_cancelamento.strip()
    if not motivo_cancelamento:
        raise ValidationError({"motivo_cancelamento": ["Motivo do cancelamento é obrigatório."]})

    if not pode_cancelar_autorizada(ator, requisicao):
        raise PermissionDenied("Usuário sem permissão para cancelar esta requisição.")

    if requisicao.status != StatusRequisicao.AUTORIZADA:
        raise DomainConflict(
            "Somente requisições autorizadas podem ser canceladas no atendimento.",
            details={"status_atual": requisicao.status},
        )

    itens_requisicao = list(
        ItemRequisicao.objects.select_for_update()
        .select_related("material")
        .filter(requisicao=requisicao)
        .order_by("material_id", "id")
    )
    itens_autorizados = [item for item in itens_requisicao if item.quantidade_autorizada > 0]
    if not itens_autorizados:
        raise DomainConflict(
            "Requisição autorizada não possui itens com quantidade autorizada.",
            details={"requisicao_id": requisicao.id},
        )

    estoques_por_material_id = _travar_estoques_dos_itens(itens_autorizados)
    itens_com_saldo_fisico = [
        item.id
        for item in itens_autorizados
        if estoques_por_material_id[item.material_id].saldo_fisico > 0
    ]
    if itens_com_saldo_fisico:
        raise DomainConflict(
            "Ainda há saldo físico para atendimento parcial da requisição.",
            details={"item_ids": itens_com_saldo_fisico},
        )

    return _apply_requisicao_transition(
        requisicao=requisicao,
        transition_name="cancelar_pos_autorizacao_sem_saldo",
        actor=ator,
        payload={
            "responsavel_atendimento": ator,
            "data_finalizacao": timezone.now(),
            "motivo_cancelamento": motivo_cancelamento,
            "itens_requisicao": itens_autorizados,
            "estoques_por_material_id": estoques_por_material_id,
        },
    )


def cancelar_requisicao(
    *, requisicao: Requisicao, ator: User, motivo_cancelamento: str
) -> Requisicao:
    with transaction.atomic():
        requisicao = _recarregar_requisicao_para_atendimento(requisicao)
        if requisicao.status == StatusRequisicao.AUTORIZADA:
            requisicao = _cancelar_autorizada_sem_saldo(
                requisicao=requisicao,
                ator=ator,
                motivo_cancelamento=motivo_cancelamento,
            )
        else:
            requisicao = _cancelar_pre_autorizacao(requisicao=requisicao, ator=ator)

    return (
        Requisicao.objects.select_related(
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "chefe_autorizador",
            "responsavel_atendimento",
        )
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=requisicao.pk)
    )


def autorizar_requisicao(
    *, requisicao: Requisicao, ator: User, itens: list[ItemAutorizacaoData]
) -> Requisicao:
    with transaction.atomic():
        requisicao = _recarregar_requisicao_para_autorizacao(requisicao)
        if not pode_autorizar_requisicao(ator, requisicao):
            raise PermissionDenied("Usuário sem permissão para autorizar esta requisição.")

        if requisicao.status != StatusRequisicao.AGUARDANDO_AUTORIZACAO:
            raise DomainConflict(
                "Somente requisições aguardando autorização podem ser autorizadas.",
                details={"status_atual": requisicao.status},
            )

        itens_requisicao = list(
            ItemRequisicao.objects.select_for_update()
            .select_related("material")
            .filter(requisicao=requisicao)
            .order_by("material_id", "id")
        )
        itens_por_id = _validar_itens_autorizacao(itens_requisicao=itens_requisicao, itens=itens)
        estoque_por_material_id = {
            estoque.material_id: estoque
            for estoque in (
                EstoqueMaterial.objects.select_for_update()
                .select_related("material")
                .filter(material_id__in=[item.material_id for item in itens_requisicao])
                .order_by("material_id")
            )
        }

        for item_requisicao in itens_requisicao:
            item_autorizacao = itens_por_id[item_requisicao.id]
            quantidade_autorizada = item_autorizacao.quantidade_autorizada

            if quantidade_autorizada > 0:
                estoque = estoque_por_material_id.get(item_requisicao.material_id)
                if estoque is None:
                    raise DomainConflict(
                        "Material da requisição está sem estoque disponível.",
                        details={"material_id": item_requisicao.material_id},
                    )
                if quantidade_autorizada > estoque.saldo_disponivel:
                    raise DomainConflict(
                        "Saldo disponível insuficiente no momento da autorização.",
                        details={
                            "item_id": item_requisicao.id,
                            "saldo_disponivel": str(estoque.saldo_disponivel),
                            "quantidade_autorizada": str(quantidade_autorizada),
                        },
                    )

            item_requisicao.quantidade_autorizada = quantidade_autorizada
            item_requisicao.justificativa_autorizacao_parcial = (
                item_autorizacao.justificativa_autorizacao_parcial
            )
            item_requisicao.full_clean()
            item_requisicao.save(
                update_fields=[
                    "quantidade_autorizada",
                    "justificativa_autorizacao_parcial",
                    "updated_at",
                ]
            )

        transicao = "autorizar_total"
        if any(
            item.quantidade_autorizada < item.quantidade_solicitada for item in itens_requisicao
        ):
            transicao = "autorizar_parcial"

        _apply_requisicao_transition(
            requisicao=requisicao,
            transition_name=transicao,
            actor=ator,
            payload={
                "chefe_autorizador": ator,
                "data_autorizacao_ou_recusa": timezone.now(),
                "itens_requisicao": itens_requisicao,
            },
        )

    return (
        Requisicao.objects.select_related(
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "chefe_autorizador",
        )
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=requisicao.pk)
    )


def recusar_requisicao(*, requisicao: Requisicao, ator: User, motivo_recusa: str) -> Requisicao:
    motivo_recusa = motivo_recusa.strip()
    if not motivo_recusa:
        raise ValidationError({"motivo_recusa": ["Motivo da recusa é obrigatório."]})

    with transaction.atomic():
        requisicao = _recarregar_requisicao_para_autorizacao(requisicao)
        if not pode_autorizar_requisicao(ator, requisicao):
            raise PermissionDenied("Usuário sem permissão para recusar esta requisição.")

        if requisicao.status != StatusRequisicao.AGUARDANDO_AUTORIZACAO:
            raise DomainConflict(
                "Somente requisições aguardando autorização podem ser recusadas.",
                details={"status_atual": requisicao.status},
            )

        _apply_requisicao_transition(
            requisicao=requisicao,
            transition_name="recusar",
            actor=ator,
            payload={
                "chefe_autorizador": ator,
                "motivo_recusa": motivo_recusa,
                "data_autorizacao_ou_recusa": timezone.now(),
            },
        )

    return (
        Requisicao.objects.select_related(
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "chefe_autorizador",
        )
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=requisicao.pk)
    )


def listar_fila_autorizacao(*, ator: User):
    if not ator.is_authenticated:
        raise PermissionDenied("Usuário precisa estar autenticado para ver a fila de autorizações.")
    if ator.is_superuser or not ator.is_active:
        raise PermissionDenied("Usuário sem permissão para acessar a fila de autorizações.")
    if ator.papel not in (PapelChoices.CHEFE_SETOR, PapelChoices.CHEFE_ALMOXARIFADO):
        raise PermissionDenied("Usuário sem permissão para acessar a fila de autorizações.")

    queryset = queryset_fila_autorizacao(ator)
    return (
        queryset.filter(status=StatusRequisicao.AGUARDANDO_AUTORIZACAO)
        .select_related("criador", "beneficiario", "setor_beneficiario")
        .prefetch_related("itens__material")
        .order_by("data_envio_autorizacao", "id")
    )


def listar_fila_atendimento(*, ator: User):
    if not ator.is_authenticated:
        raise PermissionDenied("Usuário precisa estar autenticado para ver a fila de atendimento.")
    if not pode_ver_fila_atendimento(ator):
        raise PermissionDenied("Usuário sem permissão para acessar a fila de atendimento.")

    return (
        queryset_fila_atendimento(ator)
        .select_related(
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "chefe_autorizador",
        )
        .prefetch_related("itens__material")
        .order_by("data_autorizacao_ou_recusa", "id")
    )


def atender_requisicao(
    *,
    requisicao: Requisicao,
    ator: User,
    itens: list[ItemAtendimentoPayload] | None = None,
    retirante_fisico: str = "",
    observacao_atendimento: str = "",
) -> Requisicao:
    itens_normalizados = _normalizar_itens_atendimento(itens)
    if itens_normalizados is None:
        return atender_requisicao_completa(
            requisicao=requisicao,
            ator=ator,
            retirante_fisico=retirante_fisico,
            observacao_atendimento=observacao_atendimento,
        )

    return atender_requisicao_com_itens(
        requisicao=requisicao,
        ator=ator,
        itens=itens_normalizados,
        retirante_fisico=retirante_fisico,
        observacao_atendimento=observacao_atendimento,
    )


def atender_requisicao_idempotente(
    *,
    requisicao: Requisicao,
    ator: User,
    idempotency_key: str,
    itens: list[ItemAtendimentoPayload] | None = None,
    retirante_fisico: str = "",
    observacao_atendimento: str = "",
) -> Requisicao:
    itens_normalizados = _normalizar_itens_atendimento(itens)
    payload_hash = _hash_payload_atendimento(
        itens=itens_normalizados,
        retirante_fisico=retirante_fisico,
        observacao_atendimento=observacao_atendimento,
    )

    with transaction.atomic():
        registro, criado = _obter_registro_idempotencia_atendimento(
            requisicao=requisicao,
            ator=ator,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
        )

        if not criado:
            if registro.payload_hash != payload_hash:
                raise DomainConflict(
                    "Chave de idempotência já usada com payload diferente.",
                    details={
                        "idempotency_key": idempotency_key,
                        "endpoint": IDEMPOTENCY_ENDPOINT_FULFILL,
                    },
                )
            if registro.status == StatusIdempotencia.COMPLETED:
                return _recarregar_requisicao_detalhe(requisicao.id)
            raise DomainConflict(
                "Atendimento com esta chave de idempotência ainda está em processamento.",
                details={
                    "idempotency_key": idempotency_key,
                    "endpoint": IDEMPOTENCY_ENDPOINT_FULFILL,
                },
            )

        requisicao_atendida = atender_requisicao(
            requisicao=requisicao,
            ator=ator,
            itens=itens_normalizados,
            retirante_fisico=retirante_fisico,
            observacao_atendimento=observacao_atendimento,
        )
        registro.status = StatusIdempotencia.COMPLETED
        registro.save(update_fields=["status", "updated_at"])
        return requisicao_atendida


def atender_requisicao_completa(
    *,
    requisicao: Requisicao,
    ator: User,
    retirante_fisico: str = "",
    observacao_atendimento: str = "",
) -> Requisicao:
    with transaction.atomic():
        requisicao = _recarregar_requisicao_para_atendimento(requisicao)
        if not pode_atender_requisicao(ator, requisicao):
            raise PermissionDenied("Usuário sem permissão para atender esta requisição.")

        if requisicao.status != StatusRequisicao.AUTORIZADA:
            raise DomainConflict(
                "Somente requisições autorizadas podem ser atendidas.",
                details={"status_atual": requisicao.status},
            )

        itens_requisicao = list(
            ItemRequisicao.objects.select_for_update()
            .select_related("material")
            .filter(requisicao=requisicao)
            .order_by("material_id", "id")
        )
        itens_autorizados = [item for item in itens_requisicao if item.quantidade_autorizada > 0]
        if not itens_autorizados:
            raise DomainConflict(
                "Requisição autorizada não possui itens com quantidade autorizada.",
                details={"requisicao_id": requisicao.id},
            )
        estoques_por_material_id = _travar_estoques_dos_itens(itens_autorizados)

        for item in itens_autorizados:
            quantidade_entregue = item.quantidade_autorizada
            registrar_saida_por_atendimento(
                requisicao=requisicao,
                item=item,
                quantidade=quantidade_entregue,
                estoque_travado=estoques_por_material_id[item.material_id],
            )
            item.quantidade_entregue = quantidade_entregue
            item.justificativa_atendimento_parcial = ""
            item.full_clean()
            item.save(
                update_fields=[
                    "quantidade_entregue",
                    "justificativa_atendimento_parcial",
                    "updated_at",
                ]
            )

        _apply_requisicao_transition(
            requisicao=requisicao,
            transition_name="atender_total",
            actor=ator,
            payload={
                "responsavel_atendimento": ator,
                "data_finalizacao": timezone.now(),
                "retirante_fisico": retirante_fisico.strip(),
                "observacao_atendimento": observacao_atendimento.strip(),
            },
        )

    return (
        Requisicao.objects.select_related(
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "chefe_autorizador",
            "responsavel_atendimento",
        )
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=requisicao.pk)
    )


def atender_requisicao_com_itens(
    *,
    requisicao: Requisicao,
    ator: User,
    itens: list[ItemAtendimentoData],
    retirante_fisico: str = "",
    observacao_atendimento: str = "",
) -> Requisicao:
    with transaction.atomic():
        requisicao = _recarregar_requisicao_para_atendimento(requisicao)
        if not pode_atender_requisicao(ator, requisicao):
            raise PermissionDenied("Usuário sem permissão para atender esta requisição.")

        if requisicao.status != StatusRequisicao.AUTORIZADA:
            raise DomainConflict(
                "Somente requisições autorizadas podem ser atendidas.",
                details={"status_atual": requisicao.status},
            )

        itens_requisicao = list(
            ItemRequisicao.objects.select_for_update()
            .select_related("material")
            .filter(requisicao=requisicao)
            .order_by("material_id", "id")
        )
        itens_autorizados = [item for item in itens_requisicao if item.quantidade_autorizada > 0]
        if not itens_autorizados:
            raise DomainConflict(
                "Requisição autorizada não possui itens com quantidade autorizada.",
                details={"requisicao_id": requisicao.id},
            )

        item_ids_recebidos = [item.item_id for item in itens]
        item_ids_unicos = set(item_ids_recebidos)
        if len(item_ids_unicos) != len(item_ids_recebidos):
            item_ids_repetidos = sorted(
                {item_id for item_id in item_ids_recebidos if item_ids_recebidos.count(item_id) > 1}
            )
            raise _validacao_payload_atendimento(
                "Payload de atendimento não pode repetir item_id.",
                item_ids=item_ids_repetidos,
            )

        item_ids_esperados = {item.id for item in itens_autorizados}
        item_ids_desconhecidos = item_ids_unicos - item_ids_esperados
        if item_ids_desconhecidos:
            raise _validacao_payload_atendimento(
                "Payload de atendimento contém item inválido para esta requisição.",
                item_ids=sorted(item_ids_desconhecidos),
            )

        item_ids_omitidos = item_ids_esperados - item_ids_unicos
        if item_ids_omitidos:
            raise _validacao_payload_atendimento(
                "Payload de atendimento deve informar todos os itens autorizados.",
                item_ids=sorted(item_ids_omitidos),
            )

        dados_por_item_id = {item.item_id: item for item in itens}
        possui_entrega = False
        atendimento_parcial = False

        for item in itens_autorizados:
            item_data = dados_por_item_id[item.id]
            quantidade_entregue = item_data.quantidade_entregue
            quantidade_autorizada = item.quantidade_autorizada
            justificativa = item_data.justificativa_atendimento_parcial.strip()

            if quantidade_entregue < 0:
                raise DomainConflict(
                    "Quantidade entregue não pode ser negativa.",
                    details={"item_id": item.id, "quantidade_entregue": str(quantidade_entregue)},
                )
            if quantidade_entregue > quantidade_autorizada:
                raise DomainConflict(
                    "Quantidade entregue não pode ser maior que a autorizada.",
                    details={
                        "item_id": item.id,
                        "quantidade_entregue": str(quantidade_entregue),
                        "quantidade_autorizada": str(quantidade_autorizada),
                    },
                )
            if quantidade_entregue < quantidade_autorizada and not justificativa:
                raise DomainConflict(
                    "Justificativa é obrigatória para atendimento parcial ou zero.",
                    details={"item_id": item.id},
                )

            possui_entrega = possui_entrega or quantidade_entregue > 0
            atendimento_parcial = atendimento_parcial or quantidade_entregue < quantidade_autorizada

        if not possui_entrega:
            raise DomainConflict("Atendimento parcial deve entregar ao menos um item.")

        estoques_por_material_id = _travar_estoques_dos_itens(itens_autorizados)

        for item in itens_autorizados:
            item_data = dados_por_item_id[item.id]
            quantidade_entregue = item_data.quantidade_entregue
            quantidade_nao_entregue = item.quantidade_autorizada - quantidade_entregue

            if quantidade_entregue > 0:
                registrar_saida_por_atendimento(
                    requisicao=requisicao,
                    item=item,
                    quantidade=quantidade_entregue,
                    estoque_travado=estoques_por_material_id[item.material_id],
                )
            if quantidade_nao_entregue > 0:
                registrar_liberacao_reserva_por_atendimento(
                    requisicao=requisicao,
                    item=item,
                    quantidade=quantidade_nao_entregue,
                    estoque_travado=estoques_por_material_id[item.material_id],
                )

            item.quantidade_entregue = quantidade_entregue
            item.justificativa_atendimento_parcial = (
                item_data.justificativa_atendimento_parcial.strip()
                if quantidade_nao_entregue > 0
                else ""
            )
            item.full_clean()
            item.save(
                update_fields=[
                    "quantidade_entregue",
                    "justificativa_atendimento_parcial",
                    "updated_at",
                ]
            )

        _apply_requisicao_transition(
            requisicao=requisicao,
            transition_name="atender_parcial" if atendimento_parcial else "atender_total",
            actor=ator,
            payload={
                "responsavel_atendimento": ator,
                "data_finalizacao": timezone.now(),
                "retirante_fisico": retirante_fisico.strip(),
                "observacao_atendimento": observacao_atendimento.strip(),
            },
        )

    return (
        Requisicao.objects.select_related(
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "chefe_autorizador",
            "responsavel_atendimento",
        )
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=requisicao.pk)
    )
