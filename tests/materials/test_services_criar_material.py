import pytest
from django.core.exceptions import ValidationError

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.materials.services import criar_material


@pytest.mark.django_db
class TestCriarMaterial:
    @staticmethod
    def _criar_grupo_subgrupo():
        grupo = GrupoMaterial.objects.create(
            codigo_grupo="001",
            nome="Grupo Teste",
        )
        subgrupo = SubgrupoMaterial.objects.create(
            grupo=grupo,
            codigo_subgrupo="002",
            nome="Subgrupo Teste",
        )
        return grupo, subgrupo

    def test_criar_material_valido_persiste_e_retorna_instancia(self):
        _, subgrupo = self._criar_grupo_subgrupo()

        material = criar_material(
            codigo_completo="001.002.003",
            nome="Material Teste",
            unidade_medida="UN",
            subgrupo=subgrupo,
            sequencial="003",
            descricao="Descrição teste",
        )

        assert material.id is not None
        assert material.codigo_completo == "001.002.003"
        assert material.nome == "Material Teste"
        assert material.unidade_medida == "UN"
        assert material.sequencial == "003"
        assert material.descricao == "Descrição teste"
        assert material.is_active is True

        material_recuperado = Material.objects.get(codigo_completo="001.002.003")
        assert material_recuperado.id == material.id

    def test_criar_material_valida_coerencia_codigo_scpi(self):
        _, subgrupo = self._criar_grupo_subgrupo()

        with pytest.raises(ValidationError):
            criar_material(
                codigo_completo="999.999.999",
                nome="Material Incoerente",
                unidade_medida="UN",
                subgrupo=subgrupo,
                sequencial="003",
            )

    def test_criar_material_sem_descricao(self):
        _, subgrupo = self._criar_grupo_subgrupo()

        material = criar_material(
            codigo_completo="001.002.003",
            nome="Material Sem Descrição",
            unidade_medida="UN",
            subgrupo=subgrupo,
            sequencial="003",
        )

        assert material.descricao == ""

    def test_criar_material_codigo_duplicado_levanta_erro(self):
        _, subgrupo = self._criar_grupo_subgrupo()

        criar_material(
            codigo_completo="001.002.003",
            nome="Material 1",
            unidade_medida="UN",
            subgrupo=subgrupo,
            sequencial="003",
        )

        with pytest.raises(ValidationError, match="codigo_completo"):
            criar_material(
                codigo_completo="001.002.003",
                nome="Material 2",
                unidade_medida="UN",
                subgrupo=subgrupo,
                sequencial="003",
            )
