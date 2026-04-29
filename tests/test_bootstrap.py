"""Smoke tests for Django bootstrap and basic configuration."""

from django.apps import apps
from django.conf import settings
from django.urls import reverse


class TestSettingsLoading:
    """Test that Django settings load correctly without domain apps."""

    def test_settings_module_is_test(self):
        """Verify settings module is config.settings.test."""
        assert settings.SETTINGS_MODULE == "config.settings.test"

    def test_secret_key_is_set(self):
        """Verify SECRET_KEY is loaded from environment."""
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 0

    def test_database_is_configured(self):
        """Verify PostgreSQL database is configured."""
        assert "default" in settings.DATABASES
        assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"

    def test_installed_apps_contains_core_apps(self):
        """Verify core Django apps are installed."""
        installed = [app.name for app in apps.get_app_configs()]
        assert "django.contrib.admin" in installed or "admin" in installed
        assert "django.contrib.auth" in installed or "auth" in installed
        assert "rest_framework" in installed or "rest_framework" in installed

    def test_only_released_domain_apps_are_installed(self):
        """Verify only the domain apps already released in the current milestone are installed."""
        installed = [app.name for app in apps.get_app_configs()]
        released_domain_apps = [
            "users",
            "materials",
            "stock",
            "requisitions",
        ]
        for app in released_domain_apps:
            assert any(app in name for name in installed), (
                f"Released domain app '{app}' should already be installed"
            )
        # users is installed after PIL-BE-ACE-001 (complete)
        # materials is installed after PIL-BE-MAT-001 (complete)
        # stock is installed after PIL-BE-EST-001 (complete)
        # requisitions is installed after PIL-BE-REQ-001 (current)
        # Other domain apps should not be installed yet
        domain_apps = [
            "organizational",
            "approvals",
            "warehouse",
            "notifications",
            "imports",
            "audit",
            "reports",
        ]
        for app in domain_apps:
            assert not any(app in name for name in installed), (
                f"Domain app '{app}' should not be installed yet"
            )

    def test_drf_is_configured(self):
        """Verify Django REST Framework is configured."""
        assert "rest_framework" in settings.INSTALLED_APPS or any(
            "rest_framework" in str(app) for app in settings.INSTALLED_APPS
        )
        assert settings.REST_FRAMEWORK is not None


class TestURLLoading:
    """Test that URL configuration loads correctly."""

    def test_admin_url_is_accessible(self):
        """Verify admin URL is accessible."""
        admin_url = reverse("admin:index")
        assert admin_url == "/admin/"

    def test_root_urls_load(self):
        """Verify root URLconf loads without errors."""
        from config import urls

        assert urls.urlpatterns is not None
        assert len(urls.urlpatterns) > 0


class TestDjangoCheck:
    """Test that Django check command passes."""

    def test_django_setup_succeeds(self):
        """Verify Django setup completes without errors."""
        from django.core.management import call_command

        call_command("check", verbosity=0)
