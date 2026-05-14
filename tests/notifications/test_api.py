import pytest
from django.core.cache import cache
from django.db import IntegrityError
from django.urls import reverse
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.notifications.models import PushClientEvent, PushSubscription, TipoNotificacao
from apps.notifications.services import (
    criar_notificacao_papel,
    criar_notificacao_usuario,
    marcar_notificacao_como_lida,
    registrar_push_subscription,
)
from apps.notifications.views import PushClientEventThrottle
from apps.requisitions.models import Requisicao
from apps.users.models import PapelChoices, Setor, User


@pytest.mark.django_db
class TestNotificacoesAPI:
    @staticmethod
    def _criar_setor(nome: str, chefe_matricula: str, papel=PapelChoices.CHEFE_SETOR) -> Setor:
        chefe = User.objects.create(
            matricula_funcional=chefe_matricula,
            nome_completo=f"Chefe {nome}",
            papel=papel,
            is_active=True,
        )
        setor = Setor.objects.create(nome=nome, chefe_responsavel=chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        return setor

    @staticmethod
    def _criar_usuario(
        matricula: str,
        nome: str,
        *,
        papel=PapelChoices.SOLICITANTE,
        setor: Setor | None = None,
    ) -> User:
        return User.objects.create(
            matricula_funcional=matricula,
            nome_completo=nome,
            papel=papel,
            setor=setor,
            is_active=True,
        )

    def test_lista_exige_autenticacao(self):
        client = APIClient()
        response = client.get(reverse("notification-list"))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "not_authenticated"

    def test_lista_retorna_individuais_do_usuario_e_coletivas_do_papel(self):
        setor = self._criar_setor("API Notificacoes", "41001")
        usuario = self._criar_usuario(
            "41002",
            "Usuario API",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        outro_usuario = self._criar_usuario(
            "41003",
            "Outro Usuario",
            papel=PapelChoices.CHEFE_SETOR,
            setor=setor,
        )
        requisicao = Requisicao.objects.create(criador=usuario, beneficiario=usuario)

        notificacao_individual = criar_notificacao_usuario(
            destinatario=usuario,
            tipo=TipoNotificacao.REQUISICAO_CANCELADA,
            titulo="Cancelada",
            mensagem="Sua requisição foi cancelada.",
            objeto_relacionado=requisicao,
        )
        notificacao_coletiva = criar_notificacao_papel(
            papel_destinatario=PapelChoices.AUXILIAR_ALMOXARIFADO,
            tipo=TipoNotificacao.REQUISICAO_AUTORIZADA,
            titulo="Autorizada",
            mensagem="Existe requisição para atendimento.",
            objeto_relacionado=requisicao,
        )
        criar_notificacao_usuario(
            destinatario=outro_usuario,
            tipo=TipoNotificacao.REQUISICAO_RECUSADA,
            titulo="Recusada",
            mensagem="Não deve aparecer para outro usuário.",
        )
        criar_notificacao_papel(
            papel_destinatario=PapelChoices.CHEFE_SETOR,
            tipo=TipoNotificacao.REQUISICAO_ENVIADA_AUTORIZACAO,
            titulo="Fila de autorização",
            mensagem="Não deve aparecer para outro papel.",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("notification-list"))

        assert response.status_code == 200
        assert response.data["count"] == 2
        ids = [item["id"] for item in response.data["results"]]
        assert ids == [notificacao_coletiva.id, notificacao_individual.id]
        assert response.data["results"][0]["leitura_suportada"] is False
        assert response.data["results"][0]["destino"]["tipo"] == "papel"
        assert response.data["results"][1]["leitura_suportada"] is True
        assert response.data["results"][1]["destino"]["tipo"] == "usuario"
        assert response.data["results"][1]["objeto_relacionado"] == {
            "tipo": "requisicao",
            "id": requisicao.id,
            "numero_publico": None,
            "status": "rascunho",
        }

    def test_unread_count_conta_so_individual_nao_lida_do_usuario(self):
        setor = self._criar_setor("Unread Count", "41004")
        usuario = self._criar_usuario("41005", "Usuario Count", setor=setor)
        outro = self._criar_usuario("41006", "Outro Count", setor=setor)

        lida = criar_notificacao_usuario(
            destinatario=usuario,
            tipo=TipoNotificacao.REQUISICAO_CANCELADA,
            titulo="Lida",
            mensagem="Já lida.",
        )
        marcar_notificacao_como_lida(notificacao=lida, usuario=usuario)
        criar_notificacao_usuario(
            destinatario=usuario,
            tipo=TipoNotificacao.REQUISICAO_AUTORIZADA,
            titulo="Não lida 1",
            mensagem="Ainda não lida.",
        )
        criar_notificacao_usuario(
            destinatario=usuario,
            tipo=TipoNotificacao.REQUISICAO_RECUSADA,
            titulo="Não lida 2",
            mensagem="Ainda não lida.",
        )
        criar_notificacao_usuario(
            destinatario=outro,
            tipo=TipoNotificacao.REQUISICAO_RECUSADA,
            titulo="Outro usuário",
            mensagem="Não entra no contador.",
        )
        criar_notificacao_papel(
            papel_destinatario=usuario.papel,
            tipo=TipoNotificacao.REQUISICAO_AUTORIZADA,
            titulo="Coletiva",
            mensagem="Não entra no contador.",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("notification-unread-count"))

        assert response.status_code == 200
        assert response.data == {"unread_count": 2}

    def test_unread_count_exige_autenticacao(self):
        client = APIClient()
        response = client.get(reverse("notification-unread-count"))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "not_authenticated"

    def test_mark_read_marca_individual_e_retorna_estado_atualizado(self):
        setor = self._criar_setor("Mark Read", "41007")
        usuario = self._criar_usuario("41008", "Usuario Mark Read", setor=setor)
        notificacao = criar_notificacao_usuario(
            destinatario=usuario,
            tipo=TipoNotificacao.REQUISICAO_PRONTA_PARA_RETIRADA,
            titulo="Atendida",
            mensagem="Requisição atendida.",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(
            reverse("notification-mark-read", kwargs={"pk": notificacao.id}),
            data={},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["lida"] is True
        assert response.data["lida_em"] is not None

        notificacao.refresh_from_db()
        assert notificacao.lida is True
        primeiro_lida_em = notificacao.lida_em

        second_response = client.post(
            reverse("notification-mark-read", kwargs={"pk": notificacao.id}),
            data={},
            format="json",
        )
        assert second_response.status_code == 200
        assert second_response.data["lida"] is True

        notificacao.refresh_from_db()
        assert notificacao.lida_em == primeiro_lida_em

    def test_mark_read_rejeita_notificacao_coletiva_visivel(self):
        setor = self._criar_setor("Mark Read Coletiva", "41009")
        usuario = self._criar_usuario(
            "41010",
            "Usuario Coletivo",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
            setor=setor,
        )
        notificacao = criar_notificacao_papel(
            papel_destinatario=PapelChoices.CHEFE_ALMOXARIFADO,
            tipo=TipoNotificacao.REQUISICAO_AUTORIZADA,
            titulo="Ação coletiva",
            mensagem="Visível mas sem leitura individual.",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(
            reverse("notification-mark-read", kwargs={"pk": notificacao.id}),
            data={},
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_mark_read_exige_autenticacao(self):
        setor = self._criar_setor("Mark Read Auth", "41011")
        usuario = self._criar_usuario("41012", "Usuario Auth", setor=setor)
        notificacao = criar_notificacao_usuario(
            destinatario=usuario,
            tipo=TipoNotificacao.REQUISICAO_PRONTA_PARA_RETIRADA,
            titulo="Atendida",
            mensagem="Requisição atendida.",
        )

        client = APIClient()
        response = client.post(
            reverse("notification-mark-read", kwargs={"pk": notificacao.id}),
            data={},
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "not_authenticated"

    def test_mark_read_de_outro_usuario_retorna_not_found(self):
        setor = self._criar_setor("Mark Read Outros", "41013")
        destinatario = self._criar_usuario("41014", "Destinatário", setor=setor)
        outro_usuario = self._criar_usuario("41015", "Outro Usuário", setor=setor)
        notificacao = criar_notificacao_usuario(
            destinatario=destinatario,
            tipo=TipoNotificacao.REQUISICAO_PRONTA_PARA_RETIRADA,
            titulo="Atendida",
            mensagem="Requisição atendida.",
        )

        client = APIClient()
        client.force_authenticate(user=outro_usuario)
        response = client.post(
            reverse("notification-mark-read", kwargs={"pk": notificacao.id}),
            data={},
            format="json",
        )

        assert response.status_code == 404
        assert response.data["error"]["code"] == "not_found"

    def test_push_config_retorna_chave_publica_quando_configurado(self, settings):
        settings.WEB_PUSH_VAPID_PUBLIC_KEY = "BPublicKey"

        setor = self._criar_setor("Push Config", "41016")
        usuario = setor.chefe_responsavel
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.get(reverse("notification-push-config"))

        assert response.status_code == 200
        assert response.data == {
            "enabled": True,
            "vapid_public_key": "BPublicKey",
        }

    def test_push_config_exige_autenticacao(self):
        client = APIClient()

        response = client.get(reverse("notification-push-config"))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "not_authenticated"

    def test_push_config_rejeita_usuario_sem_permissao(self):
        usuario = self._criar_usuario("41017", "Usuario Push Sem Permissao")
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.get(reverse("notification-push-config"))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_push_subscriptions_registra_assinatura_do_usuario_autenticado(self, settings):
        settings.WEB_PUSH_VAPID_PUBLIC_KEY = "BPublicKey"

        setor = self._criar_setor("Push Subscription", "41018")
        usuario = setor.chefe_responsavel
        client = APIClient()
        client.force_authenticate(user=usuario)

        payload = {
            "endpoint": "https://push.example.test/subscription/abc",
            "keys": {
                "p256dh": "cDI1NmRoLWtleQ",
                "auth": "YXV0aC1rZXk",
            },
        }
        response = client.post(
            reverse("notification-push-subscriptions"),
            data=payload,
            format="json",
        )

        assert response.status_code == 200
        assert response.data == {
            "endpoint": "https://push.example.test/subscription/abc",
            "active": True,
        }

        second_response = client.post(
            reverse("notification-push-subscriptions"),
            data=payload,
            format="json",
        )

        assert second_response.status_code == 200
        assert second_response.data["endpoint"] == "https://push.example.test/subscription/abc"
        assert (
            PushSubscription.objects.filter(
                usuario=usuario,
                endpoint="https://push.example.test/subscription/abc",
            ).count()
            == 1
        )
        subscription = PushSubscription.objects.get(
            usuario=usuario,
            endpoint="https://push.example.test/subscription/abc",
        )
        assert subscription.active is True

    def test_push_subscriptions_exige_autenticacao(self):
        client = APIClient()

        response = client.post(
            reverse("notification-push-subscriptions"),
            data={},
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "not_authenticated"

    def test_push_subscriptions_rejeita_usuario_sem_permissao(self):
        usuario = self._criar_usuario("41019", "Usuario Push Sem Permissao")
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.post(
            reverse("notification-push-subscriptions"),
            data={
                "endpoint": "https://push.example.test/subscription/sem-permissao",
                "keys": {
                    "p256dh": "cDI1NmRoLWtleQ",
                    "auth": "YXV0aC1rZXk",
                },
            },
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_push_subscriptions_rejeita_payload_invalido_com_envelope(self):
        setor = self._criar_setor("Push Payload Invalido", "41020")
        usuario = setor.chefe_responsavel
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.post(
            reverse("notification-push-subscriptions"),
            data={
                "keys": {
                    "p256dh": "cDI1NmRoLWtleQ",
                    "auth": "$valor-invalido",
                },
            },
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert response.data["error"]["details"]["endpoint"][0].code == "required"
        assert response.data["error"]["details"]["keys"]["auth"][0].code == "invalid"

    def test_push_subscriptions_rejeita_endpoint_de_outro_usuario(self):
        setor_original = self._criar_setor("Push Dono Original", "41021")
        setor_outro = self._criar_setor("Push Outro Chefe", "41022")
        subscription = PushSubscription.objects.create(
            usuario=setor_original.chefe_responsavel,
            endpoint="https://push.example.test/subscription/outro-usuario",
            p256dh="p256dh-original",
            auth="auth-original",
        )
        original_endpoint = subscription.endpoint
        original_p256dh = subscription.p256dh
        original_auth = subscription.auth
        original_active = subscription.active
        client = APIClient()
        client.force_authenticate(user=setor_outro.chefe_responsavel)

        response = client.post(
            reverse("notification-push-subscriptions"),
            data={
                "endpoint": "https://push.example.test/subscription/outro-usuario",
                "keys": {
                    "p256dh": "cDI1NmRoLWtleQ",
                    "auth": "YXV0aC1rZXk",
                },
            },
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"
        subscription.refresh_from_db()
        assert subscription.usuario == setor_original.chefe_responsavel
        assert subscription.endpoint == original_endpoint
        assert subscription.p256dh == original_p256dh
        assert subscription.auth == original_auth
        assert subscription.active == original_active

    def test_registrar_push_subscription_revalida_dono_apos_integrity_error(self, monkeypatch):
        setor_original = self._criar_setor("Push Race Dono Original", "41030")
        setor_outro = self._criar_setor("Push Race Outro Chefe", "41031")
        PushSubscription.objects.create(
            usuario=setor_original.chefe_responsavel,
            endpoint="https://push.example.test/subscription/race-outro",
            p256dh="p256dh-original",
            auth="auth-original",
        )
        monkeypatch.setattr(
            PushSubscription.objects,
            "create",
            lambda **kwargs: (_ for _ in ()).throw(IntegrityError("duplicate endpoint")),
        )

        with pytest.raises(PermissionDenied, match="Endpoint de push"):
            registrar_push_subscription(
                usuario=setor_outro.chefe_responsavel,
                endpoint="https://push.example.test/subscription/race-outro",
                p256dh="p256dh-novo",
                auth="auth-novo",
            )

    def test_push_subscriptions_deactivate_desativa_assinatura_do_usuario(self):
        setor = self._criar_setor("Push Deactivate", "41023")
        usuario = setor.chefe_responsavel
        subscription = PushSubscription.objects.create(
            usuario=usuario,
            endpoint="https://push.example.test/subscription/deactivate",
            p256dh="p256dh-original",
            auth="auth-original",
        )
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.post(
            reverse("notification-push-subscriptions-deactivate"),
            data={
                "endpoint": "https://push.example.test/subscription/deactivate",
            },
            format="json",
        )

        assert response.status_code == 204
        subscription.refresh_from_db()
        assert subscription.active is False

    def test_push_subscriptions_deactivate_exige_autenticacao(self):
        client = APIClient()

        response = client.post(
            reverse("notification-push-subscriptions-deactivate"),
            data={
                "endpoint": "https://push.example.test/subscription/deactivate-auth",
            },
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "not_authenticated"

    def test_push_subscriptions_deactivate_rejeita_usuario_sem_permissao(self):
        usuario = self._criar_usuario("41024", "Usuario Push Deactivate Sem Permissao")
        subscription = PushSubscription.objects.create(
            usuario=usuario,
            endpoint="https://push.example.test/subscription/deactivate-sem-permissao",
            p256dh="p256dh-original",
            auth="auth-original",
        )
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.post(
            reverse("notification-push-subscriptions-deactivate"),
            data={
                "endpoint": "https://push.example.test/subscription/deactivate-sem-permissao",
            },
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"
        subscription.refresh_from_db()
        assert subscription.active is True

    def test_push_subscriptions_deactivate_rejeita_endpoint_de_outro_usuario(self):
        setor_original = self._criar_setor("Push Deactivate Dono Original", "41025")
        setor_outro = self._criar_setor("Push Deactivate Outro Chefe", "41026")
        subscription = PushSubscription.objects.create(
            usuario=setor_original.chefe_responsavel,
            endpoint="https://push.example.test/subscription/deactivate-outro-usuario",
            p256dh="p256dh-original",
            auth="auth-original",
        )
        client = APIClient()
        client.force_authenticate(user=setor_outro.chefe_responsavel)

        response = client.post(
            reverse("notification-push-subscriptions-deactivate"),
            data={
                "endpoint": "https://push.example.test/subscription/deactivate-outro-usuario",
            },
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"
        subscription.refresh_from_db()
        assert subscription.active is True

    def test_push_events_registra_evento_sem_pii_e_deduplica_por_dia(self):
        setor = self._criar_setor("Push Events", "41027")
        usuario = setor.chefe_responsavel
        client = APIClient()
        client.force_authenticate(user=usuario)

        payload = {
            "event_type": "push_permission_denied",
            "diagnostic_status": "bloqueado",
            "notification_supported": True,
            "service_worker_supported": True,
            "push_manager_supported": True,
            "badging_supported": False,
            "standalone_display": False,
        }
        response = client.post(
            reverse("notification-push-events"),
            data=payload,
            format="json",
            HTTP_USER_AGENT="Mozilla/5.0 deve ser ignorado",
            REMOTE_ADDR="192.0.2.10",
        )

        assert response.status_code == 200
        assert response.data["event_type"] == "push_permission_denied"
        assert response.data["diagnostic_status"] == "bloqueado"
        assert "user_agent" not in response.data
        assert "ip" not in response.data
        assert "beneficiario" not in response.data
        assert PushClientEvent.objects.count() == 1

        second_response = client.post(
            reverse("notification-push-events"),
            data={
                **payload,
                "badging_supported": True,
            },
            format="json",
        )

        assert second_response.status_code == 200
        assert PushClientEvent.objects.count() == 1
        event = PushClientEvent.objects.get()
        assert event.usuario == usuario
        assert event.papel == PapelChoices.CHEFE_SETOR
        assert event.badging_supported is True

        usuario.papel = PapelChoices.CHEFE_ALMOXARIFADO
        usuario.save(update_fields=["papel"])
        third_response = client.post(
            reverse("notification-push-events"),
            data={
                **payload,
                "push_manager_supported": False,
            },
            format="json",
        )

        assert third_response.status_code == 200
        event.refresh_from_db()
        assert event.papel == PapelChoices.CHEFE_SETOR
        assert event.push_manager_supported is False

        event.papel = PapelChoices.SOLICITANTE
        with pytest.raises(ValueError, match="papel snapshot"):
            event.save(update_fields=["papel", "updated_at"])

    def test_push_events_rejeita_campos_sensiveis(self):
        setor = self._criar_setor("Push Events Sem PII", "41030")
        client = APIClient()
        client.force_authenticate(user=setor.chefe_responsavel)

        response = client.post(
            reverse("notification-push-events"),
            data={
                "event_type": "push_unavailable",
                "diagnostic_status": "sem_suporte",
                "notification_supported": False,
                "service_worker_supported": False,
                "push_manager_supported": False,
                "badging_supported": False,
                "standalone_display": False,
                "nome": "Fulano",
                "numero_publico": "REQ-2026-000001",
            },
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert set(response.data["error"]["details"]["campos_sensiveis"]) == {
            "nome",
            "numero_publico",
        }
        assert PushClientEvent.objects.count() == 0

    def test_push_events_rejeita_usuario_sem_permissao(self):
        usuario = self._criar_usuario("41028", "Usuario Push Event Sem Permissao")
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.post(
            reverse("notification-push-events"),
            data={
                "event_type": "push_unavailable",
                "diagnostic_status": "sem_suporte",
                "notification_supported": False,
                "service_worker_supported": False,
                "push_manager_supported": False,
                "badging_supported": False,
                "standalone_display": False,
            },
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_push_events_aplica_throttle_por_usuario(self, monkeypatch):
        cache.clear()
        monkeypatch.setattr(PushClientEventThrottle, "rate", "1/min")
        setor = self._criar_setor("Push Events Throttle", "41029")
        usuario = setor.chefe_responsavel
        client = APIClient()
        client.force_authenticate(user=usuario)

        payload = {
            "event_type": "push_unavailable",
            "diagnostic_status": "sem_suporte",
            "notification_supported": False,
            "service_worker_supported": False,
            "push_manager_supported": False,
            "badging_supported": False,
            "standalone_display": False,
        }

        first_response = client.post(
            reverse("notification-push-events"),
            data=payload,
            format="json",
        )
        second_response = client.post(
            reverse("notification-push-events"),
            data=payload,
            format="json",
        )

        assert first_response.status_code == 200
        assert second_response.status_code == 429
