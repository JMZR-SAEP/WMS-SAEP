from decimal import Decimal

import pytest

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.stock.models import EstoqueMaterial, TipoMovimentacao
from apps.stock.services import registrar_saldo_inicial


@pytest.mark.django_db
class TestRegistrarSaldoInicial:
    @staticmethod
    def _criar_material():
        grupo = GrupoMaterial.objects.create(
            codigo_grupo="001",
            nome="Grupo Teste",
        )
        subgrupo = SubgrupoMaterial.objects.create(
            grupo=grupo,
            codigo_subgrupo="002",
            nome="Subgrupo Teste",
        )
        material = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="001.002.003",
            sequencial="003",
            nome="Material Teste",
            unidade_medida="UN",
        )
        return material

    def test_registrar_saldo_inicial_cria_estoque_com_quantidade_correta(self):
        material = self._criar_material()
        quantidade = Decimal("100.000")

        estoque, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=quantidade,
        )

        assert estoque.id is not None
        assert estoque.material == material
        assert estoque.saldo_fisico == quantidade
        assert estoque.saldo_reservado == Decimal("0")

        estoque_recuperado = EstoqueMaterial.objects.get(material=material)
        assert estoque_recuperado.saldo_fisico == quantidade

    def test_registrar_saldo_inicial_cria_movimentacao_tipo_saldo_inicial(self):
        material = self._criar_material()
        quantidade = Decimal("100.000")

        estoque, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=quantidade,
        )

        assert movimentacao.id is not None
        assert movimentacao.material == material
        assert movimentacao.tipo == TipoMovimentacao.SALDO_INICIAL
        assert movimentacao.quantidade == quantidade
        assert movimentacao.saldo_anterior == Decimal("0")
        assert movimentacao.saldo_posterior == quantidade

    def test_registrar_saldo_inicial_saldo_reservado_zero(self):
        material = self._criar_material()

        estoque, _ = registrar_saldo_inicial(
            material=material,
            quantidade=Decimal("50.000"),
        )

        assert estoque.saldo_disponivel == Decimal("50.000")
        assert estoque.saldo_reservado == Decimal("0")

    def test_registrar_saldo_inicial_levanta_se_estoque_ja_existe(self):
        material = self._criar_material()
        EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=Decimal("50"),
            saldo_reservado=Decimal("0"),
        )

        with pytest.raises(ValueError, match="já existe"):
            registrar_saldo_inicial(
                material=material,
                quantidade=Decimal("100"),
            )

    def test_registrar_saldo_inicial_levanta_se_quantidade_negativa(self):
        material = self._criar_material()

        with pytest.raises(ValueError, match="não pode ser negativa"):
            registrar_saldo_inicial(
                material=material,
                quantidade=Decimal("-10"),
            )

    def test_registrar_saldo_inicial_quantidade_zero_permitida(self):
        material = self._criar_material()

        estoque, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=Decimal("0"),
        )

        assert estoque.saldo_fisico == Decimal("0")
        assert movimentacao.quantidade == Decimal("0")

    def test_movimentacao_tem_saldo_anterior_zero_e_posterior_igual_quantidade(self):
        material = self._criar_material()
        quantidade = Decimal("75.500")

        _, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=quantidade,
        )

        assert movimentacao.saldo_anterior == Decimal("0")
        assert movimentacao.saldo_posterior == quantidade
        assert movimentacao.observacao == ""
