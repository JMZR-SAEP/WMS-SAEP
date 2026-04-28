from decimal import Decimal

import pytest
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.utils import IntegrityError

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.stock.models import EstoqueMaterial


@pytest.mark.django_db
class TestEstoqueMaterialModel:
    @staticmethod
    def _criar_material(codigo_completo="013.001.001", **kwargs):
        grupo = GrupoMaterial.objects.create(codigo_grupo="013", nome="Hidráulico")
        subgrupo = SubgrupoMaterial.objects.create(
            grupo=grupo, codigo_subgrupo="001", nome="Tubulação"
        )
        defaults = dict(
            subgrupo=subgrupo,
            codigo_completo=codigo_completo,
            sequencial="001",
            nome="Tubo PVC 50mm",
            unidade_medida="UN",
        )
        defaults.update(kwargs)
        return Material.objects.create(**defaults)

    @staticmethod
    def _criar_estoque(material=None, **kwargs):
        if material is None:
            material = TestEstoqueMaterialModel._criar_material()
        defaults = dict(
            saldo_fisico=Decimal("10.000"),
            saldo_reservado=Decimal("3.000"),
        )
        defaults.update(kwargs)
        return EstoqueMaterial.objects.create(material=material, **defaults)

    def test_criar_estoque_com_material(self):
        material = self._criar_material()
        estoque = self._criar_estoque(material)
        assert estoque.id
        assert estoque.material == material
        assert estoque.saldo_fisico == Decimal("10.000")
        assert estoque.saldo_reservado == Decimal("3.000")
        assert estoque.created_at
        assert estoque.updated_at

    def test_str_representation(self):
        material = self._criar_material()
        estoque = self._criar_estoque(material)
        assert str(estoque) == "Estoque: 013.001.001"

    def test_saldo_disponivel_calculado_corretamente(self):
        material = self._criar_material()
        estoque = self._criar_estoque(
            material,
            saldo_fisico=Decimal("10.000"),
            saldo_reservado=Decimal("3.000"),
        )
        assert estoque.saldo_disponivel == Decimal("7.000")

    def test_saldo_disponivel_com_valor_zero(self):
        material = self._criar_material()
        estoque = self._criar_estoque(
            material,
            saldo_fisico=Decimal("5.000"),
            saldo_reservado=Decimal("5.000"),
        )
        assert estoque.saldo_disponivel == Decimal("0.000")

    def test_saldo_disponivel_negativo_em_divergencia(self):
        material = self._criar_material()
        estoque = self._criar_estoque(
            material,
            saldo_fisico=Decimal("3.000"),
            saldo_reservado=Decimal("5.000"),
        )
        assert estoque.saldo_disponivel == Decimal("-2.000")

    def test_protected_error_ao_deletar_material_com_estoque(self):
        material = self._criar_material()
        self._criar_estoque(material)
        with pytest.raises(ProtectedError):
            material.delete()

    def test_estoque_duplicado_por_material_levanta_integrityerror(self):
        material = self._criar_material()
        self._criar_estoque(material)
        with pytest.raises(IntegrityError):
            self._criar_estoque(material)

    def test_saldo_fisico_negativo_levanta_integrityerror(self):
        material = self._criar_material()
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                EstoqueMaterial.objects.create(
                    material=material,
                    saldo_fisico=Decimal("-1.000"),
                    saldo_reservado=Decimal("0.000"),
                )

    def test_saldo_reservado_negativo_levanta_integrityerror(self):
        material = self._criar_material()
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                EstoqueMaterial.objects.create(
                    material=material,
                    saldo_fisico=Decimal("10.000"),
                    saldo_reservado=Decimal("-1.000"),
                )

    def test_acesso_reverso_material_estoque(self):
        material = self._criar_material()
        estoque = self._criar_estoque(material)
        assert material.estoque == estoque
        assert material.estoque.saldo_disponivel == Decimal("7.000")

    def test_ordering_por_codigo_completo_material(self):
        # O ordering é por material__codigo_completo, então a ordem segue os materiais criados
        mat1 = self._criar_material(codigo_completo="013.001.001")
        self._criar_estoque(mat1)

        grupo = GrupoMaterial.objects.create(codigo_grupo="014", nome="Elétrico")
        subgrupo = SubgrupoMaterial.objects.create(grupo=grupo, codigo_subgrupo="001", nome="Fios")
        mat2 = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="014.001.001",
            sequencial="001",
            nome="Fio de cobre",
            unidade_medida="M",
        )
        self._criar_estoque(mat2)

        # Verificar que os estoques estão em ordem correta
        estoques = list(EstoqueMaterial.objects.all())
        assert estoques[0].material.codigo_completo == "013.001.001"
        assert estoques[1].material.codigo_completo == "014.001.001"
