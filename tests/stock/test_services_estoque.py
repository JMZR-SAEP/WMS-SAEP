from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.stock.models import EstoqueMaterial, MovimentacaoEstoque, TipoMovimentacao
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

    def test_movimentacao_nao_pode_ser_atualizada_por_save(self):
        material = self._criar_material()
        _, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=Decimal("75.500"),
        )

        movimentacao.quantidade = Decimal("80.000")

        with pytest.raises(ValueError, match="imutáveis"):
            movimentacao.save()

    def test_movimentacao_nao_pode_ser_removida_por_delete(self):
        material = self._criar_material()
        _, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=Decimal("75.500"),
        )

        with pytest.raises(ValueError, match="não podem ser removidas"):
            movimentacao.delete()

    def test_movimentacao_nao_pode_ser_atualizada_por_queryset_update(self):
        material = self._criar_material()
        _, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=Decimal("75.500"),
        )

        with pytest.raises(ValueError, match="imutáveis"):
            MovimentacaoEstoque.objects.filter(pk=movimentacao.pk).update(
                quantidade=Decimal("80.000")
            )

    def test_movimentacao_nao_pode_ser_atualizada_por_bulk_update(self):
        material = self._criar_material()
        _, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=Decimal("75.500"),
        )

        movimentacao.quantidade = Decimal("80.000")

        with pytest.raises(ValueError, match="imutáveis"):
            MovimentacaoEstoque.objects.bulk_update([movimentacao], ["quantidade"])

    def test_movimentacao_nao_pode_ser_removida_por_queryset_delete(self):
        material = self._criar_material()
        _, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=Decimal("75.500"),
        )

        with pytest.raises(ValueError, match="não podem ser removidas"):
            MovimentacaoEstoque.objects.filter(pk=movimentacao.pk).delete()

    def test_movimentacao_saldo_inicial_precisa_ser_coerente_no_banco(self):
        material = self._criar_material()

        with pytest.raises(IntegrityError):
            MovimentacaoEstoque.objects.create(
                material=material,
                tipo=TipoMovimentacao.SALDO_INICIAL,
                quantidade=Decimal("75.500"),
                saldo_anterior=Decimal("10.000"),
                saldo_posterior=Decimal("85.500"),
            )
