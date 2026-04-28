import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.materials.admin import GrupoMaterialAdmin, SubgrupoMaterialAdmin
from apps.materials.models import GrupoMaterial, SubgrupoMaterial
from apps.users.models import User


@pytest.mark.django_db
class TestMaterialsAdmin:
    @staticmethod
    def _staff_request():
        request = RequestFactory().get("/admin/")
        request.user = User.objects.create_superuser(
            matricula_funcional="99010",
            password="testpass123",
            nome_completo="Super Admin Materials",
        )
        return request

    def test_grupo_material_admin_bloqueia_mutacao_manual_de_dados_scpi(self):
        request = self._staff_request()
        model_admin = GrupoMaterialAdmin(GrupoMaterial, admin.site)

        assert model_admin.has_view_permission(request) is True
        assert model_admin.has_add_permission(request) is False
        assert model_admin.has_change_permission(request) is False
        assert model_admin.has_delete_permission(request) is False
        assert model_admin.get_readonly_fields(request) == (
            "codigo_grupo",
            "nome",
            "created_at",
            "updated_at",
        )

    def test_subgrupo_material_admin_bloqueia_mutacao_manual_de_dados_scpi(self):
        request = self._staff_request()
        model_admin = SubgrupoMaterialAdmin(SubgrupoMaterial, admin.site)

        assert model_admin.has_view_permission(request) is True
        assert model_admin.has_add_permission(request) is False
        assert model_admin.has_change_permission(request) is False
        assert model_admin.has_delete_permission(request) is False
        assert model_admin.get_readonly_fields(request) == (
            "grupo",
            "codigo_subgrupo",
            "nome",
            "created_at",
            "updated_at",
        )

    def test_material_admin_permite_criacao_bloqueia_edicao_campos_scpi(self):
        from apps.materials.admin import MaterialAdmin
        from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial

        request = self._staff_request()
        model_admin = MaterialAdmin(Material, admin.site)

        grupo = GrupoMaterial.objects.create(codigo_grupo="013", nome="Grupo Test")
        subgrupo = SubgrupoMaterial.objects.create(
            grupo=grupo, codigo_subgrupo="001", nome="Subgrupo Test"
        )
        material = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="013.001.001",
            sequencial="001",
            nome="Material Test",
            unidade_medida="UN",
        )

        assert model_admin.has_view_permission(request) is True
        assert model_admin.has_add_permission(request) is True
        assert model_admin.has_change_permission(request) is False
        assert model_admin.has_delete_permission(request) is False

        assert model_admin.get_readonly_fields(request, None) == (
            "created_at",
            "updated_at",
        )

        assert model_admin.get_readonly_fields(request, material) == (
            "subgrupo",
            "codigo_completo",
            "sequencial",
            "nome",
            "descricao",
            "unidade_medida",
            "created_at",
            "updated_at",
        )
