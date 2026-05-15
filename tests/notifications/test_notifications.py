import json
from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.notifications.models import (
    Notificacao,
    PushReminderState,
    PushSubscription,
    TipoNotificacao,
)
from apps.notifications.services import (
    criar_notificacao_papel,
    criar_notificacao_usuario,
    enviar_push_lembretes_autorizacoes_atrasadas,
    enviar_push_payload_usuario,
    marcar_notificacao_como_lida,
)
from apps.requisitions.models import StatusRequisicao
from apps.requisitions.services import (
    ItemAutorizacaoData,
    ItemRascunhoData,
    atender_requisicao_completa,
    autorizar_requisicao,
    cancelar_requisicao,
    criar_rascunho_requisicao,
    enviar_para_autorizacao,
    recusar_requisicao,
)
from apps.stock.models import EstoqueMaterial
from apps.users.models import PapelChoices, Setor, User


@pytest.mark.django_db(transaction=True)
class TestNotificacoes:
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

    @staticmethod
    def _criar_material_com_estoque(codigo: str, saldo_fisico: Decimal) -> Material:
        grupo_codigo, subgrupo_codigo, sequencial = codigo.split(".")
        grupo, _ = GrupoMaterial.objects.get_or_create(
            codigo_grupo=grupo_codigo,
            defaults={"nome": f"Grupo {grupo_codigo}"},
        )
        subgrupo, _ = SubgrupoMaterial.objects.get_or_create(
            grupo=grupo,
            codigo_subgrupo=subgrupo_codigo,
            defaults={"nome": f"Subgrupo {subgrupo_codigo}"},
        )
        material = Material.objects.create(
            codigo_completo=codigo,
            sequencial=sequencial,
            subgrupo=subgrupo,
            nome=f"Material {codigo}",
            unidade_medida="UN",
        )
        EstoqueMaterial.objects.create(material=material, saldo_fisico=saldo_fisico)
        return material

    def test_cria_notificacao_individual_e_marca_como_lida(self):
        usuario = self._criar_usuario("30001", "Usuario Notificado")
        notificacao = criar_notificacao_usuario(
            destinatario=usuario,
            tipo=TipoNotificacao.REQUISICAO_CANCELADA,
            titulo="Requisição cancelada",
            mensagem="A requisição foi cancelada.",
        )

        assert notificacao.destinatario == usuario
        assert notificacao.papel_destinatario is None
        assert notificacao.lida is False

        marcar_notificacao_como_lida(notificacao=notificacao, usuario=usuario)

        notificacao.refresh_from_db()
        assert notificacao.lida is True
        assert notificacao.lida_em is not None

    def test_marcar_como_lida_rejeita_usuario_nao_destinatario(self):
        destinatario = self._criar_usuario("30099", "Destinatario")
        outro = self._criar_usuario("30098", "Outro")
        notificacao = criar_notificacao_usuario(
            destinatario=destinatario,
            tipo=TipoNotificacao.REQUISICAO_CANCELADA,
            titulo="Teste",
            mensagem="Teste.",
        )

        with pytest.raises(PermissionDenied):
            marcar_notificacao_como_lida(notificacao=notificacao, usuario=outro)

    def test_marcar_como_lida_rejeita_notificacao_por_papel(self):
        usuario = self._criar_usuario(
            "30097",
            "Auxiliar",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
        )
        notificacao = criar_notificacao_papel(
            papel_destinatario=PapelChoices.AUXILIAR_ALMOXARIFADO,
            tipo=TipoNotificacao.REQUISICAO_AUTORIZADA,
            titulo="Teste",
            mensagem="Teste.",
        )

        with pytest.raises(PermissionDenied):
            marcar_notificacao_como_lida(notificacao=notificacao, usuario=usuario)

    def test_cria_notificacao_para_papel_operacional(self):
        notificacao = criar_notificacao_papel(
            papel_destinatario=PapelChoices.AUXILIAR_ALMOXARIFADO,
            tipo=TipoNotificacao.REQUISICAO_AUTORIZADA,
            titulo="Requisição autorizada",
            mensagem="Há requisição pronta para atendimento.",
        )

        assert notificacao.destinatario is None
        assert notificacao.papel_destinatario == PapelChoices.AUXILIAR_ALMOXARIFADO
        assert notificacao.lida is False

    def test_envio_para_autorizacao_notifica_chefe_do_setor(self):
        setor = self._criar_setor("Notificacao Envio", "30002")
        solicitante = self._criar_usuario("30003", "Solicitante", setor=setor)
        material = self._criar_material_com_estoque("001.001.301", Decimal("5"))
        requisicao = criar_rascunho_requisicao(
            criador=solicitante,
            beneficiario=solicitante,
            observacao="",
            itens=[
                ItemRascunhoData(
                    material_id=material.id,
                    quantidade_solicitada=Decimal("2"),
                )
            ],
        )

        enviar_para_autorizacao(requisicao=requisicao, ator=solicitante)

        notificacao = Notificacao.objects.get(
            destinatario=setor.chefe_responsavel,
            tipo=TipoNotificacao.REQUISICAO_ENVIADA_AUTORIZACAO,
        )
        assert notificacao.objeto_relacionado.status == StatusRequisicao.AGUARDANDO_AUTORIZACAO

    def test_envio_para_autorizacao_dispara_push_para_chefe_do_setor(
        self,
        monkeypatch,
        settings,
    ):
        settings.WEB_PUSH_VAPID_PRIVATE_KEY = "private-key"
        settings.WEB_PUSH_VAPID_SUBJECT = "mailto:suporte@saep.test"
        chamadas = []

        def fake_webpush(**kwargs):
            chamadas.append(kwargs)

        monkeypatch.setattr("apps.notifications.services._webpush", fake_webpush)

        setor = self._criar_setor("Push Envio", "30016")
        PushSubscription.objects.create(
            usuario=setor.chefe_responsavel,
            endpoint="https://push.example.test/subscription/chefe",
            p256dh="p256dh-key",
            auth="auth-key",
        )
        solicitante = self._criar_usuario("30017", "Solicitante Push", setor=setor)
        material = self._criar_material_com_estoque("001.001.306", Decimal("5"))
        requisicao = criar_rascunho_requisicao(
            criador=solicitante,
            beneficiario=solicitante,
            observacao="",
            itens=[
                ItemRascunhoData(
                    material_id=material.id,
                    quantidade_solicitada=Decimal("2"),
                )
            ],
        )

        enviada = enviar_para_autorizacao(requisicao=requisicao, ator=solicitante)

        assert len(chamadas) == 1
        chamada = chamadas[0]
        assert chamada["subscription_info"] == {
            "endpoint": "https://push.example.test/subscription/chefe",
            "keys": {
                "p256dh": "p256dh-key",
                "auth": "auth-key",
            },
        }
        assert chamada["vapid_private_key"] == "private-key"
        assert chamada["vapid_claims"] == {"sub": "mailto:suporte@saep.test"}
        payload = json.loads(chamada["data"])
        assert payload["url"] == f"/requisicoes/{enviada.id}?contexto=autorizacao"
        assert "Solicitante Push" in payload["body"]
        assert "Material" not in payload["body"]
        assert "Push Envio" not in payload["body"]

    def test_falha_410_de_push_desativa_assinatura_sem_bloquear_requisicao(
        self,
        monkeypatch,
        settings,
    ):
        settings.WEB_PUSH_VAPID_PRIVATE_KEY = "private-key"
        settings.WEB_PUSH_VAPID_SUBJECT = "mailto:suporte@saep.test"

        class FakeResponse:
            status_code = 410

        class FakePushError(Exception):
            response = FakeResponse()

        def fake_webpush(**kwargs):
            raise FakePushError("push gone")

        monkeypatch.setattr("apps.notifications.services._webpush", fake_webpush)

        setor = self._criar_setor("Push Falha", "30018")
        subscription = PushSubscription.objects.create(
            usuario=setor.chefe_responsavel,
            endpoint="https://push.example.test/subscription/gone",
            p256dh="p256dh-key",
            auth="auth-key",
        )
        solicitante = self._criar_usuario("30019", "Solicitante Push Falha", setor=setor)
        material = self._criar_material_com_estoque("001.001.307", Decimal("5"))
        requisicao = criar_rascunho_requisicao(
            criador=solicitante,
            beneficiario=solicitante,
            observacao="",
            itens=[
                ItemRascunhoData(
                    material_id=material.id,
                    quantidade_solicitada=Decimal("2"),
                )
            ],
        )

        enviada = enviar_para_autorizacao(requisicao=requisicao, ator=solicitante)

        assert enviada.status == StatusRequisicao.AGUARDANDO_AUTORIZACAO
        subscription.refresh_from_db()
        assert subscription.active is False
        assert subscription.last_failure_status == 410

    def test_lembrete_agregado_envia_um_push_por_chefe_para_autorizacoes_atrasadas(
        self,
        monkeypatch,
        settings,
    ):
        settings.WEB_PUSH_VAPID_PRIVATE_KEY = "private-key"
        settings.WEB_PUSH_VAPID_SUBJECT = "mailto:suporte@saep.test"
        chamadas = []

        def fake_webpush(**kwargs):
            chamadas.append(kwargs)

        monkeypatch.setattr("apps.notifications.services._webpush", fake_webpush)

        now = timezone.now()
        setor_a = self._criar_setor("Setor Sigiloso A", "30020")
        setor_b = self._criar_setor("Setor Sigiloso B", "30021")
        PushSubscription.objects.create(
            usuario=setor_a.chefe_responsavel,
            endpoint="https://push.example.test/subscription/chefe-a",
            p256dh="p256dh-key-a",
            auth="auth-key-a",
        )
        PushSubscription.objects.create(
            usuario=setor_b.chefe_responsavel,
            endpoint="https://push.example.test/subscription/chefe-b",
            p256dh="p256dh-key-b",
            auth="auth-key-b",
        )
        material = self._criar_material_com_estoque("001.001.308", Decimal("10"))

        for index, setor in enumerate((setor_a, setor_b), start=1):
            solicitante = self._criar_usuario(
                f"3003{index}",
                f"Beneficiario Sigiloso {index}",
                setor=setor,
            )
            requisicao = criar_rascunho_requisicao(
                criador=solicitante,
                beneficiario=solicitante,
                observacao="",
                itens=[
                    ItemRascunhoData(
                        material_id=material.id,
                        quantidade_solicitada=Decimal("2"),
                    )
                ],
            )
            enviada = enviar_para_autorizacao(requisicao=requisicao, ator=solicitante)
            enviada.data_envio_autorizacao = now - timedelta(hours=5)
            enviada.save(update_fields=["data_envio_autorizacao", "updated_at"])

        chamadas.clear()
        sent = enviar_push_lembretes_autorizacoes_atrasadas(now=now)

        assert sent == 2
        assert len(chamadas) == 2
        payloads = [json.loads(chamada["data"]) for chamada in chamadas]
        assert {payload["url"] for payload in payloads} == {"/autorizacoes"}
        assert {payload["tag"] for payload in payloads} == {"autorizacoes-atrasadas"}
        for payload in payloads:
            assert "autorização" in payload["body"]
            assert "Beneficiario Sigiloso" not in payload["body"]
            assert "Setor Sigiloso" not in payload["body"]
            assert "Material" not in payload["body"]

    def test_lembrete_agregado_respeita_cooldown_por_chefe(self, monkeypatch, settings):
        settings.WEB_PUSH_VAPID_PRIVATE_KEY = "private-key"
        settings.WEB_PUSH_VAPID_SUBJECT = "mailto:suporte@saep.test"
        chamadas = []

        def fake_webpush(**kwargs):
            chamadas.append(kwargs)

        monkeypatch.setattr("apps.notifications.services._webpush", fake_webpush)

        now = timezone.now()
        setor = self._criar_setor("Cooldown", "30022")
        PushSubscription.objects.create(
            usuario=setor.chefe_responsavel,
            endpoint="https://push.example.test/subscription/cooldown",
            p256dh="p256dh-key",
            auth="auth-key",
        )
        solicitante = self._criar_usuario("30023", "Solicitante Cooldown", setor=setor)
        material = self._criar_material_com_estoque("001.001.309", Decimal("5"))
        requisicao = criar_rascunho_requisicao(
            criador=solicitante,
            beneficiario=solicitante,
            observacao="",
            itens=[
                ItemRascunhoData(
                    material_id=material.id,
                    quantidade_solicitada=Decimal("2"),
                )
            ],
        )
        enviada = enviar_para_autorizacao(requisicao=requisicao, ator=solicitante)
        enviada.data_envio_autorizacao = now - timedelta(hours=5)
        enviada.save(update_fields=["data_envio_autorizacao", "updated_at"])

        chamadas.clear()
        first_sent = enviar_push_lembretes_autorizacoes_atrasadas(now=now)
        second_sent = enviar_push_lembretes_autorizacoes_atrasadas(now=now + timedelta(hours=1))

        assert first_sent == 1
        assert second_sent == 0
        assert len(chamadas) == 1
        state = PushReminderState.objects.get(usuario=setor.chefe_responsavel)
        assert state.last_count == 1

    def test_push_payload_nao_envia_para_usuario_inelegivel(self, monkeypatch, settings):
        settings.WEB_PUSH_VAPID_PRIVATE_KEY = "private-key"
        settings.WEB_PUSH_VAPID_SUBJECT = "mailto:suporte@saep.test"
        chamadas = []

        def fake_webpush(**kwargs):
            chamadas.append(kwargs)

        monkeypatch.setattr("apps.notifications.services._webpush", fake_webpush)
        usuario = self._criar_usuario("30024", "Solicitante Inelegivel")
        subscription = PushSubscription.objects.create(
            usuario=usuario,
            endpoint="https://push.example.test/subscription/inelegivel",
            p256dh="p256dh-key",
            auth="auth-key",
        )

        sent = enviar_push_payload_usuario(
            usuario_id=usuario.pk,
            payload={"title": "Teste", "body": "Teste", "url": "/autorizacoes"},
        )

        assert sent == 0
        assert chamadas == []
        subscription.refresh_from_db()
        assert subscription.last_success_at is None
        assert subscription.last_failure_status is None

    def test_send_push_reminders_command_reporta_falha(self, monkeypatch):
        def falha_servico():
            raise RuntimeError("serviço indisponível")

        monkeypatch.setattr(
            "apps.notifications.management.commands.send_push_reminders."
            "enviar_push_lembretes_autorizacoes_atrasadas",
            falha_servico,
        )
        stderr = StringIO()

        with pytest.raises(CommandError, match="Falha ao enviar lembretes push agregados"):
            call_command("send_push_reminders", stderr=stderr)

        assert "serviço indisponível" in stderr.getvalue()

    def test_autorizacao_notifica_solicitante_e_almoxarifado(self):
        setor = self._criar_setor("Notificacao Autorizacao", "30004")
        solicitante = self._criar_usuario("30005", "Solicitante", setor=setor)
        material = self._criar_material_com_estoque("001.001.302", Decimal("5"))
        requisicao = criar_rascunho_requisicao(
            criador=solicitante,
            beneficiario=solicitante,
            observacao="",
            itens=[
                ItemRascunhoData(
                    material_id=material.id,
                    quantidade_solicitada=Decimal("2"),
                )
            ],
        )
        enviada = enviar_para_autorizacao(requisicao=requisicao, ator=solicitante)
        item = enviada.itens.get()

        autorizar_requisicao(
            requisicao=enviada,
            ator=setor.chefe_responsavel,
            itens=[
                ItemAutorizacaoData(
                    item_id=item.id,
                    quantidade_autorizada=Decimal("2"),
                )
            ],
        )

        assert (
            Notificacao.objects.filter(
                destinatario=solicitante,
                tipo=TipoNotificacao.REQUISICAO_AUTORIZADA,
            ).count()
            == 1
        )
        assert Notificacao.objects.filter(
            papel_destinatario=PapelChoices.AUXILIAR_ALMOXARIFADO,
            tipo=TipoNotificacao.REQUISICAO_AUTORIZADA,
        ).exists()
        assert Notificacao.objects.filter(
            papel_destinatario=PapelChoices.CHEFE_ALMOXARIFADO,
            tipo=TipoNotificacao.REQUISICAO_AUTORIZADA,
        ).exists()

    def test_recusa_notifica_criador_e_beneficiario(self):
        setor = self._criar_setor("Notificacao Recusa", "30006")
        criador = self._criar_usuario(
            "30007",
            "Criador",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor,
        )
        beneficiario = self._criar_usuario("30008", "Beneficiario", setor=setor)
        material = self._criar_material_com_estoque("001.001.303", Decimal("5"))
        requisicao = criar_rascunho_requisicao(
            criador=criador,
            beneficiario=beneficiario,
            observacao="",
            itens=[
                ItemRascunhoData(
                    material_id=material.id,
                    quantidade_solicitada=Decimal("2"),
                )
            ],
        )
        enviada = enviar_para_autorizacao(requisicao=requisicao, ator=criador)

        recusar_requisicao(
            requisicao=enviada,
            ator=setor.chefe_responsavel,
            motivo_recusa="Sem necessidade operacional.",
        )

        assert Notificacao.objects.filter(
            destinatario=criador,
            tipo=TipoNotificacao.REQUISICAO_RECUSADA,
        ).exists()
        assert Notificacao.objects.filter(
            destinatario=beneficiario,
            tipo=TipoNotificacao.REQUISICAO_RECUSADA,
        ).exists()

    def test_cancelamento_notifica_criador_e_beneficiario(self):
        setor = self._criar_setor("Notificacao Cancelamento", "30009")
        criador = self._criar_usuario(
            "30010",
            "Criador",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor,
        )
        beneficiario = self._criar_usuario("30011", "Beneficiario", setor=setor)
        material = self._criar_material_com_estoque("001.001.304", Decimal("5"))
        requisicao = criar_rascunho_requisicao(
            criador=criador,
            beneficiario=beneficiario,
            observacao="",
            itens=[
                ItemRascunhoData(
                    material_id=material.id,
                    quantidade_solicitada=Decimal("2"),
                )
            ],
        )
        enviada = enviar_para_autorizacao(requisicao=requisicao, ator=criador)

        cancelar_requisicao(requisicao=enviada, ator=criador, motivo_cancelamento="")

        assert Notificacao.objects.filter(
            destinatario=criador,
            tipo=TipoNotificacao.REQUISICAO_CANCELADA,
        ).exists()
        assert Notificacao.objects.filter(
            destinatario=beneficiario,
            tipo=TipoNotificacao.REQUISICAO_CANCELADA,
        ).exists()

    def test_atendimento_notifica_criador_e_beneficiario(self):
        setor = self._criar_setor("Notificacao Atendimento", "30012")
        criador = self._criar_usuario(
            "30013",
            "Criador",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor,
        )
        beneficiario = self._criar_usuario("30014", "Beneficiario", setor=setor)
        almoxarife = self._criar_usuario(
            "30015",
            "Almoxarife",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque("001.001.305", Decimal("5"))
        requisicao = criar_rascunho_requisicao(
            criador=criador,
            beneficiario=beneficiario,
            observacao="",
            itens=[
                ItemRascunhoData(
                    material_id=material.id,
                    quantidade_solicitada=Decimal("2"),
                )
            ],
        )
        enviada = enviar_para_autorizacao(requisicao=requisicao, ator=criador)
        item = enviada.itens.get()
        autorizada = autorizar_requisicao(
            requisicao=enviada,
            ator=setor.chefe_responsavel,
            itens=[
                ItemAutorizacaoData(
                    item_id=item.id,
                    quantidade_autorizada=Decimal("2"),
                )
            ],
        )

        atender_requisicao_completa(
            requisicao=autorizada,
            ator=almoxarife,
            observacao_atendimento="",
        )

        assert Notificacao.objects.filter(
            destinatario=criador,
            tipo=TipoNotificacao.REQUISICAO_PRONTA_PARA_RETIRADA,
        ).exists()
        assert Notificacao.objects.filter(
            destinatario=beneficiario,
            tipo=TipoNotificacao.REQUISICAO_PRONTA_PARA_RETIRADA,
        ).exists()
