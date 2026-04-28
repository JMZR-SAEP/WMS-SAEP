import pytest
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.utils import IntegrityError

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial


@pytest.mark.django_db
class TestMaterialModel:
    @staticmethod
    def _criar_subgrupo():
        grupo = GrupoMaterial.objects.create(codigo_grupo="013", nome="Hidráulico")
        return SubgrupoMaterial.objects.create(grupo=grupo, codigo_subgrupo="001", nome="Tubulação")

    @staticmethod
    def _criar_material(subgrupo, **kwargs):
        defaults = dict(
            codigo_completo="013.001.001",
            sequencial="001",
            nome="Tubo PVC 50mm",
            unidade_medida="UN",
        )
        defaults.update(kwargs)
        return Material.objects.create(subgrupo=subgrupo, **defaults)

    def test_criar_material_com_campos_validos(self):
        subgrupo = self._criar_subgrupo()
        material = self._criar_material(subgrupo)
        assert material.id
        assert material.codigo_completo == "013.001.001"
        assert material.sequencial == "001"
        assert material.nome == "Tubo PVC 50mm"
        assert material.unidade_medida == "UN"
        assert material.is_active is True
        assert material.observacoes_internas == ""
        assert material.created_at
        assert material.updated_at

    def test_str_representation(self):
        subgrupo = self._criar_subgrupo()
        material = self._criar_material(subgrupo)
        assert str(material) == "013.001.001 — Tubo PVC 50mm"

    def test_codigo_duplicado_levanta_integrityerror(self):
        subgrupo = self._criar_subgrupo()
        self._criar_material(subgrupo)
        with pytest.raises(IntegrityError):
            self._criar_material(subgrupo, codigo_completo="013.001.001")

    def test_subgrupo_nulo_levanta_integrityerror(self):
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                Material.objects.create(
                    subgrupo=None,
                    codigo_completo="013.001.001",
                    sequencial="001",
                    nome="Tubo PVC 50mm",
                    unidade_medida="UN",
                )

    def test_protected_error_ao_deletar_subgrupo_com_materiais(self):
        subgrupo = self._criar_subgrupo()
        self._criar_material(subgrupo)
        with pytest.raises(ProtectedError):
            subgrupo.delete()

    @pytest.mark.parametrize(
        "codigo_invalido",
        ["013001001", "013.001", "13.001.001", "ABC.DEF.GHI", "013.001.0012"],
    )
    def test_codigo_completo_com_formato_invalido_levanta_validationerror(self, codigo_invalido):
        subgrupo = self._criar_subgrupo()
        material = Material(
            subgrupo=subgrupo,
            codigo_completo=codigo_invalido,
            sequencial="001",
            nome="Tubo PVC 50mm",
            unidade_medida="UN",
        )
        with pytest.raises(ValidationError):
            material.full_clean()

    def test_sequencial_e_unidade_podem_ser_criados(self):
        subgrupo = self._criar_subgrupo()
        material = self._criar_material(
            subgrupo,
            sequencial="099",
            unidade_medida="KG",
        )
        assert material.sequencial == "099"
        assert material.unidade_medida == "KG"

    def test_ordering_por_codigo_completo(self):
        subgrupo = self._criar_subgrupo()
        mat2 = self._criar_material(subgrupo, codigo_completo="013.001.002")
        mat1 = self._criar_material(subgrupo, codigo_completo="013.001.001", nome="Outro")
        mat3 = self._criar_material(subgrupo, codigo_completo="013.001.003")
        assert list(Material.objects.all()) == [mat1, mat2, mat3]

    def test_related_name_materiais_funciona(self):
        subgrupo = self._criar_subgrupo()
        self._criar_material(subgrupo)
        assert subgrupo.materiais.count() == 1

    def test_material_inativado(self):
        subgrupo = self._criar_subgrupo()
        material = self._criar_material(subgrupo)
        material.is_active = False
        material.save()
        assert material.is_active is False
        reloaded = Material.objects.get(id=material.id)
        assert reloaded.is_active is False
