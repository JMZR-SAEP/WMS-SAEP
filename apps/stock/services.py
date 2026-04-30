from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.core.api.exceptions import DomainConflict
from apps.materials.models import Material
from apps.requisitions.models import ItemRequisicao, Requisicao
from apps.stock.models import (
    EstoqueMaterial,
    MovimentacaoEstoque,
    TipoMovimentacao,
)


def registrar_saldo_inicial(
    *,
    material: Material,
    quantidade: Decimal,
) -> tuple[EstoqueMaterial, MovimentacaoEstoque]:
    """Cria EstoqueMaterial com saldo_fisico = quantidade.
    Registra MovimentacaoEstoque tipo SALDO_INICIAL.

    Executa em transaction.atomic() e trava o material para serializar a criação.
    Levanta ValueError se EstoqueMaterial já existir para o material (piloto: carga inicial única).
    Levanta ValueError se quantidade < 0.

    Retorna (estoque, movimentacao).
    """
    if quantidade < 0:
        raise ValueError(f"Quantidade não pode ser negativa: {quantidade}")

    with transaction.atomic():
        material_travado = Material.objects.select_for_update().only("id").get(pk=material.pk)

        if EstoqueMaterial.objects.filter(material=material_travado).exists():
            raise ValueError(f"EstoqueMaterial já existe para {material.codigo_completo}")

        try:
            estoque = EstoqueMaterial.objects.create(
                material=material_travado,
                saldo_fisico=quantidade,
                saldo_reservado=Decimal(0),
            )

            movimentacao = MovimentacaoEstoque.objects.create(
                material=material_travado,
                tipo=TipoMovimentacao.SALDO_INICIAL,
                quantidade=quantidade,
                saldo_anterior=Decimal(0),
                saldo_posterior=quantidade,
                observacao="",
            )
        except IntegrityError as e:
            raise ValueError(
                f"Conflito concorrente ao registrar saldo para {material.codigo_completo}"
            ) from e

    return estoque, movimentacao


def registrar_reserva_por_autorizacao(
    *,
    requisicao: Requisicao,
    item: ItemRequisicao,
    quantidade: Decimal,
) -> tuple[EstoqueMaterial, MovimentacaoEstoque]:
    """Registra reserva por autorização sem alterar saldo físico.

    Retorna `(estoque, movimentacao)`.
    """
    with transaction.atomic():
        estoque = (
            EstoqueMaterial.objects.select_for_update()
            .select_related("material")
            .get(material_id=item.material_id)
        )

        if quantidade > estoque.saldo_disponivel:
            raise DomainConflict(
                "Quantidade reservada excede o saldo disponível.",
                details={
                    "quantidade": str(quantidade),
                    "saldo_disponivel": str(estoque.saldo_disponivel),
                    "material_id": item.material_id,
                },
            )

        saldo_reservado_anterior = estoque.saldo_reservado
        saldo_reservado_posterior = saldo_reservado_anterior + quantidade

        estoque.saldo_reservado = saldo_reservado_posterior
        estoque.save(update_fields=["saldo_reservado", "updated_at"])

        movimentacao = MovimentacaoEstoque.objects.create(
            requisicao=requisicao,
            item_requisicao=item,
            material=item.material,
            tipo=TipoMovimentacao.RESERVA_POR_AUTORIZACAO,
            quantidade=quantidade,
            saldo_anterior=estoque.saldo_fisico,
            saldo_posterior=estoque.saldo_fisico,
            saldo_reservado_anterior=saldo_reservado_anterior,
            saldo_reservado_posterior=saldo_reservado_posterior,
            observacao="Reserva por autorização",
        )

    return estoque, movimentacao
