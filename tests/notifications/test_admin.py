import pytest
from django.contrib import admin, messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from apps.notifications.admin import NotificacaoAdmin
from apps.notifications.models import Notificacao, TipoNotificacao
from apps.notifications.services import criar_notificacao_papel, criar_notificacao_usuario
from apps.users.models import PapelChoices, User


@pytest.mark.django_db
class TestNotificacaoAdmin:
    @staticmethod
    def _criar_usuario(
        matricula: str,
        nome: str,
        *,
        papel=PapelChoices.SOLICITANTE,
        is_superuser=False,
    ) -> User:
        return User.objects.create(
            matricula_funcional=matricula,
            nome_completo=nome,
            papel=papel,
            is_active=True,
            is_staff=True,
            is_superuser=is_superuser,
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
        assert model_admin.list_select_related == ("destinatario",)

    def test_queryset_restringe_notificacoes_para_staff_nao_superuser(self):
        usuario = self._criar_usuario(
            "30110",
            "Auxiliar Admin",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
        )
        outro = self._criar_usuario(
            "30111",
            "Outro Admin",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
        )
        notificacao_usuario = criar_notificacao_usuario(
            destinatario=usuario,
            tipo=TipoNotificacao.REQUISICAO_CANCELADA,
            titulo="Individual",
            mensagem="Individual.",
        )
        notificacao_outro = criar_notificacao_usuario(
            destinatario=outro,
            tipo=TipoNotificacao.REQUISICAO_CANCELADA,
            titulo="Outro",
            mensagem="Outro.",
        )
        notificacao_papel_usuario = criar_notificacao_papel(
            papel_destinatario=PapelChoices.AUXILIAR_ALMOXARIFADO,
            tipo=TipoNotificacao.REQUISICAO_AUTORIZADA,
            titulo="Papel",
            mensagem="Papel.",
        )
        notificacao_papel_outro = criar_notificacao_papel(
            papel_destinatario=PapelChoices.CHEFE_ALMOXARIFADO,
            tipo=TipoNotificacao.REQUISICAO_AUTORIZADA,
            titulo="Outro papel",
            mensagem="Outro papel.",
        )
        model_admin = NotificacaoAdmin(Notificacao, admin.site)
        request = self._request_admin(usuario)

        queryset = model_admin.get_queryset(request)

        assert notificacao_usuario in queryset
        assert notificacao_papel_usuario in queryset
        assert notificacao_outro not in queryset
        assert notificacao_papel_outro not in queryset

    def test_queryset_superuser_ve_todas_as_notificacoes(self):
        superuser = self._criar_usuario("30112", "Superuser", is_superuser=True)
        destinatario = self._criar_usuario("30113", "Destinatario")
        notificacao = criar_notificacao_usuario(
            destinatario=destinatario,
            tipo=TipoNotificacao.REQUISICAO_CANCELADA,
            titulo="Teste",
            mensagem="Teste.",
        )
        model_admin = NotificacaoAdmin(Notificacao, admin.site)
        request = self._request_admin(superuser)

        assert notificacao in model_admin.get_queryset(request)

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

    def test_action_marcar_como_lida_exibe_warning_para_notificacao_por_papel(self):
        usuario = self._criar_usuario(
            "30103",
            "Auxiliar Admin",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
        )
        notificacao = criar_notificacao_papel(
            papel_destinatario=PapelChoices.AUXILIAR_ALMOXARIFADO,
            tipo=TipoNotificacao.REQUISICAO_AUTORIZADA,
            titulo="Papel",
            mensagem="Papel.",
        )
        model_admin = NotificacaoAdmin(Notificacao, admin.site)
        request = self._request_admin(usuario)

        model_admin.marcar_como_lida_action(request, Notificacao.objects.filter(pk=notificacao.pk))

        notificacao.refresh_from_db()
        stored_messages = list(request._messages)
        assert notificacao.lida is False
        assert any(message.level == messages.WARNING for message in stored_messages)
