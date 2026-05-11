import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.notifications.models import TipoNotificacao
from apps.notifications.services import (
    criar_notificacao_papel,
    criar_notificacao_usuario,
    marcar_notificacao_como_lida,
)
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
            tipo=TipoNotificacao.REQUISICAO_ATENDIDA,
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
            tipo=TipoNotificacao.REQUISICAO_ATENDIDA,
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
            tipo=TipoNotificacao.REQUISICAO_ATENDIDA,
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

        usuario = self._criar_usuario("41016", "Usuario Push Config")
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.get(reverse("notification-push-config"))

        assert response.status_code == 200
        assert response.data == {
            "enabled": True,
            "vapid_public_key": "BPublicKey",
        }

    def test_push_subscriptions_registra_assinatura_do_usuario_autenticado(self, settings):
        settings.WEB_PUSH_VAPID_PUBLIC_KEY = "BPublicKey"

        usuario = self._criar_usuario("41017", "Usuario Push Subscription")
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.post(
            reverse("notification-push-subscriptions"),
            data={
                "endpoint": "https://push.example.test/subscription/abc",
                "keys": {
                    "p256dh": "p256dh-key",
                    "auth": "auth-key",
                },
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data == {
            "endpoint": "https://push.example.test/subscription/abc",
            "active": True,
        }
