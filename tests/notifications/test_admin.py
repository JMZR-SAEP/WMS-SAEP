import pytest
from django.contrib import admin, messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from apps.notifications.admin import NotificacaoAdmin
from apps.notifications.models import Notificacao, TipoNotificacao
from apps.notifications.services import criar_notificacao_usuario
from apps.users.models import User


@pytest.mark.django_db
class TestNotificacaoAdmin:
    @staticmethod
    def _criar_usuario(matricula: str, nome: str) -> User:
        return User.objects.create(
            matricula_funcional=matricula,
            nome_completo=nome,
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )

    @staticmethod
    def _request_admin(usuario: User):
        request = RequestFactory().post("/admin/notifications/notificacao/")
        request.user = usuario
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))
        return request

    def test_lida_e_lida_em_sao_readonly_no_admin(self):
        model_admin = NotificacaoAdmin(Notificacao, admin.site)

        assert "lida" in model_admin.readonly_fields
        assert "lida_em" in model_admin.readonly_fields

    def test_action_marcar_como_lida_usa_service_para_destinatario(self):
        usuario = self._criar_usuario("30100", "Destinatario Admin")
        notificacao = criar_notificacao_usuario(
            destinatario=usuario,
            tipo=TipoNotificacao.REQUISICAO_CANCELADA,
            titulo="Teste",
            mensagem="Teste.",
        )
        model_admin = NotificacaoAdmin(Notificacao, admin.site)
        request = self._request_admin(usuario)

        model_admin.marcar_como_lida_action(request, Notificacao.objects.filter(pk=notificacao.pk))

        notificacao.refresh_from_db()
        assert notificacao.lida is True
        assert notificacao.lida_em is not None

    def test_action_marcar_como_lida_exibe_warning_para_nao_destinatario(self):
        destinatario = self._criar_usuario("30101", "Destinatario")
        outro = self._criar_usuario("30102", "Outro Admin")
        notificacao = criar_notificacao_usuario(
            destinatario=destinatario,
            tipo=TipoNotificacao.REQUISICAO_CANCELADA,
            titulo="Teste",
            mensagem="Teste.",
        )
        model_admin = NotificacaoAdmin(Notificacao, admin.site)
        request = self._request_admin(outro)

        model_admin.marcar_como_lida_action(request, Notificacao.objects.filter(pk=notificacao.pk))

        notificacao.refresh_from_db()
        stored_messages = list(request._messages)
        assert notificacao.lida is False
        assert any(message.level == messages.WARNING for message in stored_messages)
