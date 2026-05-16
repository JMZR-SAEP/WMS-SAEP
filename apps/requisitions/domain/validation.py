from dataclasses import replace
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from apps.core.api.exceptions import DomainConflict
from apps.materials.models import Material
from apps.requisitions.domain.types import (
    ItemAtendimentoData,
    ItemAutorizacaoData,
    ItemRascunhoData,
)
from apps.requisitions.models import ItemRequisicao, StatusRequisicao


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


def validacao_payload_atendimento(message: str, *, item_ids: list[int] | None = None):
    from rest_framework.exceptions import ValidationError

    details: dict[str, object] = {"itens": [message]}
    if item_ids is not None:
        details["item_ids"] = item_ids
    return ValidationError(details)


def validar_beneficiario_setor(beneficiario) -> None:
    if beneficiario.setor_id is None:
        raise ValidationError(
            {"beneficiario_id": ["Beneficiário deve possuir setor para criar a requisição."]}
        )
    if not beneficiario.setor.is_active:
        raise DomainConflict(
            "Setor do beneficiário está inativo.",
            details={"beneficiario_id": f"Setor '{beneficiario.setor.nome}' está inativo."},
        )


def validar_beneficiario_setor_ativo(beneficiario, setor) -> None:
    if beneficiario.setor_id is None:
        raise ValidationError({"beneficiario_id": ["Beneficiário deve possuir setor válido."]})
    if not setor.is_active:
        raise DomainConflict(
            "Setor do beneficiário está inativo.",
            details={"beneficiario_id": f"Setor '{setor.nome}' está inativo."},
        )


def validar_status_rascunho_para_edicao(requisicao) -> None:
    if requisicao.status != StatusRequisicao.RASCUNHO:
        raise DomainConflict(
            "Somente requisições em rascunho podem ser editadas.",
            details={"status_atual": requisicao.status},
        )


def validar_descarte_rascunho(requisicao) -> None:
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


def validar_status_cancelamento_pre(requisicao) -> None:
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


def validar_motivo(motivo: str, campo: str, mensagem: str) -> str:
    motivo = motivo.strip()
    if not motivo:
        raise ValidationError({campo: [mensagem]})
    return motivo


def validar_itens_autorizados_existem(itens_autorizados, requisicao) -> None:
    if not itens_autorizados:
        raise DomainConflict(
            "Requisição autorizada não possui itens com quantidade autorizada.",
            details={"requisicao_id": requisicao.id},
        )


def validar_itens_atendimento(
    itens: list[ItemAtendimentoData],
    itens_autorizados: list,
) -> tuple[dict, bool]:
    """Valida payload de atendimento. Retorna (dados_por_item_id, atendimento_parcial)."""
    item_ids_recebidos = [item.item_id for item in itens]
    item_ids_unicos = set(item_ids_recebidos)
    if len(item_ids_unicos) != len(item_ids_recebidos):
        item_ids_repetidos = sorted(
            {item_id for item_id in item_ids_recebidos if item_ids_recebidos.count(item_id) > 1}
        )
        raise validacao_payload_atendimento(
            "Payload de atendimento não pode repetir item_id.",
            item_ids=item_ids_repetidos,
        )

    item_ids_esperados = {item.id for item in itens_autorizados}
    item_ids_desconhecidos = item_ids_unicos - item_ids_esperados
    if item_ids_desconhecidos:
        raise validacao_payload_atendimento(
            "Payload de atendimento contém item inválido para esta requisição.",
            item_ids=sorted(item_ids_desconhecidos),
        )

    item_ids_omitidos = item_ids_esperados - item_ids_unicos
    if item_ids_omitidos:
        raise validacao_payload_atendimento(
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

    return dados_por_item_id, atendimento_parcial


def validar_retirante(retirante_fisico: str) -> str:
    normalizado = retirante_fisico.strip()
    if not normalizado:
        raise ValidationError({"retirante_fisico": ["Nome do retirante é obrigatório."]})
    return normalizado


def validar_consistencia_itens_retirada(itens_requisicao) -> None:
    for item in itens_requisicao:
        if (
            item.quantidade_entregue < 0
            or item.quantidade_entregue > item.quantidade_autorizada
            or item.quantidade_autorizada > item.quantidade_solicitada
        ):
            raise DomainConflict(
                "Item em estado inconsistente para retirada.",
                details={
                    "item_id": item.id,
                    "quantidade_entregue": str(item.quantidade_entregue),
                    "quantidade_autorizada": str(item.quantidade_autorizada),
                    "quantidade_solicitada": str(item.quantidade_solicitada),
                },
            )


def validar_envio_para_autorizacao(itens) -> None:
    if not itens:
        raise DomainConflict(
            "Requisição sem itens não pode ser enviada.",
            details={"itens": "Adicione ao menos um item válido antes do envio."},
        )
    for item in itens:
        _material_e_estoque_validos(
            material=item.material, quantidade_solicitada=item.quantidade_solicitada
        )
