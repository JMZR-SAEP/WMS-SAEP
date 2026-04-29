from decimal import Decimal

from apps.materials.models import Material
from apps.stock.models import EstoqueMaterial, MovimentacaoEstoque, TipoMovimentacao


def registrar_saldo_inicial(
    *,
    material: Material,
    quantidade: Decimal,
) -> tuple[EstoqueMaterial, MovimentacaoEstoque]:
    """Cria EstoqueMaterial com saldo_fisico = quantidade.
    Registra MovimentacaoEstoque tipo SALDO_INICIAL.

    Deve ser chamado dentro de transaction.atomic() (responsabilidade do chamador).
    Levanta ValueError se EstoqueMaterial já existir para o material (piloto: carga inicial única).
    Levanta ValueError se quantidade < 0.

    Retorna (estoque, movimentacao).
    """
    if quantidade < 0:
        raise ValueError(f"Quantidade não pode ser negativa: {quantidade}")

    if EstoqueMaterial.objects.filter(material=material).exists():
        raise ValueError(f"EstoqueMaterial já existe para {material.codigo_completo}")

    estoque = EstoqueMaterial.objects.create(
        material=material,
        saldo_fisico=quantidade,
        saldo_reservado=Decimal(0),
    )

    movimentacao = MovimentacaoEstoque.objects.create(
        material=material,
        tipo=TipoMovimentacao.SALDO_INICIAL,
        quantidade=quantidade,
        saldo_anterior=Decimal(0),
        saldo_posterior=quantidade,
        observacao="",
    )

    return estoque, movimentacao
