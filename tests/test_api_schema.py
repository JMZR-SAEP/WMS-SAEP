"""Smoke tests for DRF/OpenAPI configuration."""

from django.urls import reverse
from rest_framework.test import APIClient


class TestOpenAPISchema:
    """Test OpenAPI schema generation and accessibility."""

    def test_schema_endpoint_is_accessible(self):
        """Verify /api/v1/schema/ endpoint is accessible."""
        client = APIClient()
        response = client.get(reverse("schema"))
        assert response.status_code == 200

    def test_swagger_ui_is_accessible(self):
        """Verify Swagger UI endpoint is accessible."""
        client = APIClient()
        response = client.get(reverse("swagger-ui"))
        assert response.status_code == 200

    def test_swagger_ui_returns_html(self):
        """Verify Swagger UI returns HTML content."""
        client = APIClient()
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
