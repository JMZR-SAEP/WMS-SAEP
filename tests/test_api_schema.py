"""Smoke tests for DRF/OpenAPI configuration."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import Setor, User


@pytest.mark.django_db
class TestOpenAPISchema:
    """Test OpenAPI schema generation and accessibility."""

    @staticmethod
    def _criar_staff():
        usuario = User.objects.create(
            matricula_funcional="990001",
            nome_completo="Staff Schema",
            is_active=True,
            is_staff=True,
        )
        setor = Setor.objects.create(nome="Tecnologia", chefe_responsavel=usuario)
        usuario.setor = setor
        usuario.save()
        return usuario

    def test_schema_endpoint_requires_staff(self):
        """Verify /api/v1/schema/ requires staff outside DEBUG override."""
        client = APIClient()
        response = client.get(reverse("schema"))
        assert response.status_code == 403

    def test_schema_endpoint_staff_can_access(self):
        """Verify staff users can access /api/v1/schema/."""
        usuario = self._criar_staff()
        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("schema"))
        assert response.status_code == 200

    def test_swagger_ui_requires_staff(self):
        """Verify Swagger UI endpoint requires staff outside DEBUG override."""
        client = APIClient()
        response = client.get(reverse("swagger-ui"))
        assert response.status_code == 403

    def test_swagger_ui_returns_html_for_staff(self):
        """Verify Swagger UI returns HTML content for staff users."""
        usuario = self._criar_staff()
        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("swagger-ui"))
        assert response.status_code == 200
        assert b"<!DOCTYPE html>" in response.content or b"<!DOCTYPE" in response.content

    def test_drf_is_properly_configured(self):
        """Verify DRF is properly configured with custom pagination."""
        from django.conf import settings

        assert "DEFAULT_PAGINATION_CLASS" in settings.REST_FRAMEWORK
        assert (
            settings.REST_FRAMEWORK["DEFAULT_PAGINATION_CLASS"]
            == "apps.core.api.pagination.StandardPagination"
        )

    def test_exception_handler_is_configured(self):
        """Verify custom exception handler is configured."""
        from django.conf import settings

        assert "EXCEPTION_HANDLER" in settings.REST_FRAMEWORK
        assert (
            settings.REST_FRAMEWORK["EXCEPTION_HANDLER"]
            == "apps.core.api.exceptions.api_exception_handler"
        )

    def test_core_app_is_installed(self):
        """Verify apps.core is in INSTALLED_APPS."""
        from django.conf import settings

        assert "apps.core" in settings.INSTALLED_APPS

    def test_schema_contem_rotas_de_requisicoes(self):
        """Verify requisitions routes are exposed in OpenAPI."""
        usuario = self._criar_staff()
        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("schema"))

        assert response.status_code == 200
        content = response.content.decode()
        assert "/api/v1/materials/{id}/" in content
        assert "/api/v1/requisitions/" in content
        assert "/api/v1/requisitions/{id}/submit/" in content
        assert "/api/v1/requisitions/{id}/return-to-draft/" in content
        assert "/api/v1/requisitions/{id}/discard/" in content
        assert "/api/v1/requisitions/{id}/cancel/" in content
        assert "/api/v1/requisitions/{id}/authorize/" in content
        assert "/api/v1/requisitions/{id}/refuse/" in content
        assert "/api/v1/requisitions/{id}/fulfill/" in content
        assert "/api/v1/requisitions/pending-approvals/" in content
        assert "/api/v1/requisitions/pending-fulfillments/" in content
        assert "materials_retrieve" in content
        assert "RequisicaoItemFulfillInput" in content
        assert "quantidade_entregue" in content
        assert "justificativa_atendimento_parcial" in content
