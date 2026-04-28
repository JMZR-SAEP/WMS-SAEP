import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.materials.models import GrupoMaterial, SubgrupoMaterial


@pytest.mark.django_db
class TestSubgrupoMaterial:
    @staticmethod
    def _criar_grupo(codigo_grupo="013", nome="Material Hidráulico"):
        return GrupoMaterial.objects.create(codigo_grupo=codigo_grupo, nome=nome)

    def test_criar_subgrupo_com_campos_validos(self):
        grupo = self._criar_grupo()
        subgrupo = SubgrupoMaterial.objects.create(
            grupo=grupo, codigo_subgrupo="024", nome="Tubos e Conexões"
        )
        assert subgrupo.grupo == grupo
        assert subgrupo.codigo_subgrupo == "024"
        assert subgrupo.nome == "Tubos e Conexões"
        assert subgrupo.created_at is not None
        assert subgrupo.updated_at is not None

    def test_str_representation(self):
        grupo = self._criar_grupo()
        subgrupo = SubgrupoMaterial.objects.create(
            grupo=grupo, codigo_subgrupo="024", nome="Tubos e Conexões"
        )
        assert str(subgrupo) == "013.024 — Tubos e Conexões"

    def test_codigo_subgrupo_deve_ser_unico_por_grupo(self):
        grupo1 = self._criar_grupo(codigo_grupo="013", nome="Grupo 1")
        grupo2 = self._criar_grupo(codigo_grupo="015", nome="Grupo 2")

        SubgrupoMaterial.objects.create(grupo=grupo1, codigo_subgrupo="024", nome="Subgrupo A")

        # Mesmo código pode existir em outro grupo
        SubgrupoMaterial.objects.create(grupo=grupo2, codigo_subgrupo="024", nome="Subgrupo B")

        # Mas não pode haver duplicata no mesmo grupo
        with pytest.raises(IntegrityError):
            SubgrupoMaterial.objects.create(
                grupo=grupo1, codigo_subgrupo="024", nome="Subgrupo Duplicado"
            )

    def test_subgrupo_sem_grupo_nao_permitido(self):
        with pytest.raises(IntegrityError):
            SubgrupoMaterial.objects.create(
                grupo=None, codigo_subgrupo="024", nome="Tubos e Conexões"
            )

    def test_deletar_grupo_com_subgrupos_vinculados_levanta_protected_error(self):
        grupo = self._criar_grupo()
        SubgrupoMaterial.objects.create(grupo=grupo, codigo_subgrupo="024", nome="Tubos e Conexões")

        with pytest.raises(ProtectedError):
            grupo.delete()

    def test_ordering_por_grupo_e_codigo_subgrupo(self):
        grupo1 = self._criar_grupo(codigo_grupo="013", nome="Grupo 1")
        grupo2 = self._criar_grupo(codigo_grupo="015", nome="Grupo 2")

        SubgrupoMaterial.objects.create(grupo=grupo1, codigo_subgrupo="025", nome="B")
        SubgrupoMaterial.objects.create(grupo=grupo1, codigo_subgrupo="024", nome="A")
        SubgrupoMaterial.objects.create(grupo=grupo2, codigo_subgrupo="024", nome="C")

        subgrupos = list(SubgrupoMaterial.objects.all())
        expected = [
            (grupo1, "024"),
            (grupo1, "025"),
            (grupo2, "024"),
        ]
        assert [(s.grupo, s.codigo_subgrupo) for s in subgrupos] == expected

    def test_subgrupos_relacionados_ao_grupo(self):
        grupo = self._criar_grupo()
        sub1 = SubgrupoMaterial.objects.create(
            grupo=grupo, codigo_subgrupo="024", nome="Subgrupo 1"
        )
        sub2 = SubgrupoMaterial.objects.create(
            grupo=grupo, codigo_subgrupo="025", nome="Subgrupo 2"
        )

        assert grupo.subgrupos.count() == 2
        assert set(grupo.subgrupos.all()) == {sub1, sub2}

    @pytest.mark.parametrize("codigo_invalido", ["24", "0240", "A24", "02A", "ABC"])
    def test_codigo_subgrupo_deve_ter_exatamente_tres_digitos(self, codigo_invalido):
        grupo = self._criar_grupo()
        subgrupo = SubgrupoMaterial(
            grupo=grupo,
            codigo_subgrupo=codigo_invalido,
            nome="Tubos e Conexões",
        )

        with pytest.raises(ValidationError):
            subgrupo.full_clean()
