from dataclasses import dataclass
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.api.exceptions import DomainConflict
from apps.materials.models import Material
from apps.requisitions.models import (
    EventoTimeline,
    ItemRequisicao,
    Requisicao,
    SequenciaNumeroRequisicao,
    StatusRequisicao,
    TipoEvento,
)
from apps.requisitions.policies import pode_manipular_pre_autorizacao, queryset_fila_autorizacao
from apps.users.models import PapelChoices
from apps.users.policies import pode_criar_requisicao_para

User = get_user_model()


@dataclass(frozen=True)
class ItemRascunhoData:
    material_id: int
    quantidade_solicitada: Decimal
    observacao: str = ""


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
        raise DomainConflict("Requisição em conflito com o estado atual do estoque.", details=errors)


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

    missing_ids = [material_id for material_id in material_ids if material_id not in materiais_por_id]
    if missing_ids:
        raise ValidationError({"itens": [f"Materiais inexistentes: {missing_ids}."]})

    for item in itens:
        if item.quantidade_solicitada <= 0:
            raise ValidationError(
                {
                    "itens": [
                        "Quantidade solicitada deve ser maior que zero para todos os itens."
                    ]
                }
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
            sequencia = (
                SequenciaNumeroRequisicao.objects.select_for_update().get(ano=ano)
            )
        except SequenciaNumeroRequisicao.DoesNotExist:
            try:
                sequencia = SequenciaNumeroRequisicao.objects.create(ano=ano, ultimo_numero=0)
            except IntegrityError:
                sequencia = (
                    SequenciaNumeroRequisicao.objects.select_for_update().get(ano=ano)
                )

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
        raise PermissionDenied("Usuário sem permissão para criar requisição para este beneficiário.")

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


def enviar_para_autorizacao(*, requisicao: Requisicao, ator: User) -> Requisicao:
    if not pode_manipular_pre_autorizacao(ator, requisicao):
        raise PermissionDenied("Apenas criador ou beneficiário podem enviar a requisição.")

    with transaction.atomic():
        requisicao = (
            Requisicao.objects.select_for_update()
            .select_related("criador", "beneficiario", "setor_beneficiario")
            .prefetch_related("itens__material__estoque", "eventos__usuario")
            .get(pk=requisicao.pk)
        )

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
                TipoEvento.ENVIO_AUTORIZACAO if is_primeiro_envio else TipoEvento.REENVIO_AUTORIZACAO
            ),
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


def retornar_para_rascunho(*, requisicao: Requisicao, ator: User) -> Requisicao:
    if not pode_manipular_pre_autorizacao(ator, requisicao):
        raise PermissionDenied("Apenas criador ou beneficiário podem retornar a requisição.")

    with transaction.atomic():
        requisicao = (
            Requisicao.objects.select_for_update()
            .select_related("criador", "beneficiario", "setor_beneficiario")
            .prefetch_related("itens__material", "eventos__usuario")
            .get(pk=requisicao.pk)
        )

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
    if not pode_manipular_pre_autorizacao(ator, requisicao):
        raise PermissionDenied("Apenas criador ou beneficiário podem descartar a requisição.")

    with transaction.atomic():
        requisicao = (
            Requisicao.objects.select_for_update()
            .prefetch_related("itens")
            .get(pk=requisicao.pk)
        )

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


def cancelar_pre_autorizacao(*, requisicao: Requisicao, ator: User) -> Requisicao:
    if not pode_manipular_pre_autorizacao(ator, requisicao):
        raise PermissionDenied("Apenas criador ou beneficiário podem cancelar a requisição.")

    with transaction.atomic():
        requisicao = (
            Requisicao.objects.select_for_update()
            .select_related("criador", "beneficiario", "setor_beneficiario")
            .prefetch_related("itens__material", "eventos__usuario")
            .get(pk=requisicao.pk)
        )

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

        requisicao.status = StatusRequisicao.CANCELADA
        requisicao.data_finalizacao = timezone.now()
        requisicao.save(update_fields=["status", "data_finalizacao", "updated_at"])
        EventoTimeline.objects.create(
            requisicao=requisicao,
            tipo_evento=TipoEvento.CANCELAMENTO,
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
