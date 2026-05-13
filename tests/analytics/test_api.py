import pytest
from django.core.cache import cache
from django.db import connection
from django.urls import reverse
from rest_framework.test import APIClient

from apps.analytics.models import FrontendAnalyticsEvent
from apps.analytics.views import FrontendAnalyticsEventThrottle
from apps.users.models import PapelChoices, Setor, User


@pytest.fixture(autouse=True)
def ensure_analytics_table(db):
    existing_tables = connection.introspection.table_names()
    if FrontendAnalyticsEvent._meta.db_table not in existing_tables:
        pytest.fail(
            "Tabela de analytics ausente; rode rtk make setup para recriar migrations efêmeras."
        )


@pytest.mark.django_db
class TestFrontendAnalyticsAPI:
    @staticmethod
    def _criar_usuario() -> User:
        usuario = User.objects.create(
            matricula_funcional="69001",
            nome_completo="Usuario Analytics",
            papel=PapelChoices.CHEFE_SETOR,
            is_active=True,
        )
        setor = Setor.objects.create(nome="Analytics", chefe_responsavel=usuario)
        usuario.setor = setor
        usuario.save(update_fields=["setor"])
        return usuario

    def test_events_exige_autenticacao(self):
        client = APIClient()

        response = client.post(reverse("analytics-event-list"), data={}, format="json")

        assert response.status_code == 403
        assert response.data["error"]["code"] == "not_authenticated"

    def test_events_exige_csrf_com_sessao_django(self):
        usuario = self._criar_usuario()
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(usuario)

        response = client.post(
            reverse("analytics-event-list"),
            data={"event_type": "draft_started", "screen": "nova_requisicao"},
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_events_com_sessao_e_csrf_valido_retorna_201(self):
        usuario = self._criar_usuario()
        usuario.set_password("senha-valida")
        usuario.save(update_fields=["password"])
        client = APIClient(enforce_csrf_checks=True)

        assert client.login(username=usuario.matricula_funcional, password="senha-valida")
        csrf_response = client.get(reverse("auth-csrf"))
        assert csrf_response.status_code == 200
        assert "csrf_token" in csrf_response.data
        csrf_token = csrf_response.data["csrf_token"]

        response = client.post(
            reverse("analytics-event-list"),
            data={"event_type": "draft_started", "screen": "nova_requisicao"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert response.status_code == 201
        assert response.data["event_type"] == "draft_started"
        assert response.data["screen"] == "nova_requisicao"
        event = FrontendAnalyticsEvent.objects.get()
        assert event.usuario == usuario
        assert event.papel == PapelChoices.CHEFE_SETOR

    def test_events_rejeita_usuario_nao_operacional_no_service(self):
        usuario = self._criar_usuario()
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.post(
            reverse("analytics-event-list"),
            data={"event_type": "draft_started", "screen": "nova_requisicao"},
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"
        assert FrontendAnalyticsEvent.objects.count() == 0

    def test_events_registra_evento_sem_pii_com_usuario_e_papel_da_sessao(self):
        usuario = self._criar_usuario()
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.post(
            reverse("analytics-event-list"),
            data={
                "event_type": "draft_saved",
                "screen": "nova_requisicao",
                "draft_step": "itens",
                "action": "save_draft",
            },
            format="json",
            HTTP_USER_AGENT="Mozilla/5.0 deve ser ignorado",
            REMOTE_ADDR="192.0.2.20",
        )

        assert response.status_code == 201
        assert response.data["event_type"] == "draft_saved"
        assert response.data["screen"] == "nova_requisicao"
        assert response.data["draft_step"] == "itens"
        assert "usuario" not in response.data
        assert "user_agent" not in response.data
        assert "ip" not in response.data

        event = FrontendAnalyticsEvent.objects.get()
        assert event.usuario == usuario
        assert event.papel == PapelChoices.CHEFE_SETOR

    def test_events_rejeita_campos_sensiveis(self):
        usuario = self._criar_usuario()
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.post(
            reverse("analytics-event-list"),
            data={
                "event_type": "draft_saved",
                "screen": "nova_requisicao",
                "nome": "Fulano",
                "material_id": 123,
                "numero_publico": "REQ-2026-000001",
            },
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert set(response.data["error"]["details"]["campos_extras"]) == {
            "material_id",
            "nome",
            "numero_publico",
        }
        assert set(response.data["error"]["details"]["campos_sensiveis"]) == {
            "material_id",
            "nome",
            "numero_publico",
        }
        assert FrontendAnalyticsEvent.objects.count() == 0

    def test_events_rejeita_campos_extras_nao_sensiveis(self):
        usuario = self._criar_usuario()
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.post(
            reverse("analytics-event-list"),
            data={
                "event_type": "draft_saved",
                "screen": "nova_requisicao",
                "ignored": "x",
            },
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert response.data["error"]["details"]["campos_extras"] == ["ignored"]
        assert response.data["error"]["details"]["campos_sensiveis"] == []
        assert FrontendAnalyticsEvent.objects.count() == 0

    def test_events_rejeita_endpoint_com_id_cru(self):
        usuario = self._criar_usuario()
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.post(
            reverse("analytics-event-list"),
            data={
                "event_type": "api_error",
                "screen": "requisicao_detalhe",
                "endpoint_key": "/api/v1/requisitions/123/",
                "http_status": 500,
                "error_code": "internal_error",
                "trace_id": "trace-abc",
            },
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"

    @pytest.mark.parametrize(
        "endpoint_key",
        [
            "/api/v1/requisitions/550e8400-e29b-41d4-a716-446655440000/",
            "/api/v1/requisitions/deadbeef/",
        ],
    )
    def test_events_rejeita_endpoint_com_uuid_ou_hash(self, endpoint_key):
        usuario = self._criar_usuario()
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.post(
            reverse("analytics-event-list"),
            data={
                "event_type": "api_error",
                "screen": "requisicao_detalhe",
                "endpoint_key": endpoint_key,
                "http_status": 500,
            },
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"

    def test_events_registra_erro_por_endpoint_status_e_trace_sem_details(self):
        usuario = self._criar_usuario()
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.post(
            reverse("analytics-event-list"),
            data={
                "event_type": "api_error",
                "screen": "autorizacoes",
                "endpoint_key": "/api/v1/requisitions/{id}/authorize/",
                "http_status": 409,
                "error_code": "domain_conflict",
                "trace_id": "trace-domain",
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["endpoint_key"] == "/api/v1/requisitions/{id}/authorize/"
        assert response.data["http_status"] == 409
        assert response.data["error_code"] == "domain_conflict"
        assert response.data["trace_id"] == "trace-domain"
        assert "details" not in response.data

    def test_events_aplica_throttle_por_usuario(self, monkeypatch):
        cache.clear()
        monkeypatch.setattr(FrontendAnalyticsEventThrottle, "rate", "1/min")
        usuario = self._criar_usuario()
        client = APIClient()
        client.force_authenticate(user=usuario)

        payload = {
            "event_type": "draft_started",
            "screen": "nova_requisicao",
            "draft_step": "beneficiario",
        }

        first_response = client.post(reverse("analytics-event-list"), data=payload, format="json")
        second_response = client.post(reverse("analytics-event-list"), data=payload, format="json")

        assert first_response.status_code == 201
        assert second_response.status_code == 429

    def test_papel_snapshot_e_imutavel(self):
        usuario = self._criar_usuario()
        event = FrontendAnalyticsEvent.objects.create(
            usuario=usuario,
            papel=usuario.papel,
            event_type="login_success",
            screen="login",
        )

        event.papel = PapelChoices.CHEFE_ALMOXARIFADO
        with pytest.raises(ValueError, match="papel snapshot"):
            event.save(update_fields=["papel"])

    def test_papel_snapshot_e_imutavel_em_queryset_update(self):
        usuario = self._criar_usuario()
        event = FrontendAnalyticsEvent.objects.create(
            usuario=usuario,
            papel=usuario.papel,
            event_type="login_success",
            screen="login",
        )

        with pytest.raises(ValueError, match="papel snapshot"):
            FrontendAnalyticsEvent.objects.filter(pk=event.pk).update(
                papel=PapelChoices.CHEFE_ALMOXARIFADO
            )

        event.refresh_from_db()
        assert event.papel == PapelChoices.CHEFE_SETOR
