import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.materials.models import GrupoMaterial


@pytest.mark.django_db
class TestGrupoMaterial:
    def test_criar_grupo_com_campos_validos(self):
        grupo = GrupoMaterial.objects.create(codigo_grupo="013", nome="Material Hidráulico")
        assert grupo.codigo_grupo == "013"
        assert grupo.nome == "Material Hidráulico"
        assert grupo.created_at is not None
        assert grupo.updated_at is not None

    def test_str_representation(self):
        grupo = GrupoMaterial.objects.create(codigo_grupo="013", nome="Material Hidráulico")
        assert str(grupo) == "013 — Material Hidráulico"

    def test_codigo_grupo_deve_ser_unico(self):
        GrupoMaterial.objects.create(codigo_grupo="013", nome="Material Hidráulico")
        with pytest.raises(IntegrityError):
            GrupoMaterial.objects.create(codigo_grupo="013", nome="Outro Nome")

    def test_ordering_por_codigo_grupo(self):
        GrupoMaterial.objects.create(codigo_grupo="015", nome="B")
        GrupoMaterial.objects.create(codigo_grupo="013", nome="A")
        GrupoMaterial.objects.create(codigo_grupo="014", nome="C")

        grupos = list(GrupoMaterial.objects.all())
        assert [g.codigo_grupo for g in grupos] == ["013", "014", "015"]

    @pytest.mark.parametrize("codigo_invalido", ["13", "0134", "A13", "01A", "ABC"])
    def test_codigo_grupo_deve_ter_exatamente_tres_digitos(self, codigo_invalido):
        grupo = GrupoMaterial(codigo_grupo=codigo_invalido, nome="Material Hidráulico")

        with pytest.raises(ValidationError):
            grupo.full_clean()
