from dataclasses import replace
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from apps.core.api.exceptions import DomainConflict
from apps.materials.models import Material
from apps.requisitions.domain.types import ItemAutorizacaoData, ItemRascunhoData
from apps.requisitions.models import ItemRequisicao


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
