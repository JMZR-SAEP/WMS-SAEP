import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.requisitions.admin import EventoTimelineAdmin, ItemRequisicaoAdmin, RequisicaoAdmin
from apps.requisitions.models import EventoTimeline, ItemRequisicao, Requisicao
from apps.users.models import User


@pytest.mark.django_db
class TestRequisitionsAdmin:
    @staticmethod
    def _staff_request():
        request = RequestFactory().get("/admin/")
        request.user = User.objects.create_superuser(
            matricula_funcional="99020",
            password="testpass123",
            nome_completo="Super Admin Requisitions",
        )
        return request

    def test_requisicao_admin_eh_somente_leitura(self):
        request = self._staff_request()
        model_admin = RequisicaoAdmin(Requisicao, admin.site)

        assert model_admin.has_view_permission(request) is True
        assert model_admin.has_add_permission(request) is False
        assert model_admin.has_change_permission(request) is False
        assert model_admin.has_delete_permission(request) is False
        assert tuple(model_admin.get_readonly_fields(request)) == (
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "data_criacao",
            "created_at",
            "updated_at",
        )

    def test_item_requisicao_admin_eh_somente_leitura(self):
        request = self._staff_request()
        model_admin = ItemRequisicaoAdmin(ItemRequisicao, admin.site)

        assert model_admin.has_view_permission(request) is True
        assert model_admin.has_add_permission(request) is False
        assert model_admin.has_change_permission(request) is False
        assert model_admin.has_delete_permission(request) is False

    def test_evento_timeline_admin_eh_somente_leitura(self):
        request = self._staff_request()
        model_admin = EventoTimelineAdmin(EventoTimeline, admin.site)

        assert model_admin.has_view_permission(request) is True
        assert model_admin.has_add_permission(request) is False
        assert model_admin.has_change_permission(request) is False
        assert model_admin.has_delete_permission(request) is False
