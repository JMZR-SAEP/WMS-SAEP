from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.users.models import PapelChoices


class TipoNotificacao(models.TextChoices):
    REQUISICAO_ENVIADA_AUTORIZACAO = (
        "requisicao_enviada_autorizacao",
        "Requisição enviada para autorização",
    )
    REQUISICAO_AUTORIZADA = "requisicao_autorizada", "Requisição autorizada"
    REQUISICAO_RECUSADA = "requisicao_recusada", "Requisição recusada"
    REQUISICAO_CANCELADA = "requisicao_cancelada", "Requisição cancelada"
    REQUISICAO_ATENDIDA = "requisicao_atendida", "Requisição atendida"


class Notificacao(models.Model):
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notificacoes",
        help_text="Usuário destinatário da notificação.",
    )
    papel_destinatario = models.CharField(
        max_length=30,
        choices=PapelChoices.choices,
        null=True,
        blank=True,
        db_index=True,
        help_text="Papel operacional destinatário quando a notificação for coletiva.",
    )
    tipo = models.CharField(
        max_length=40,
        choices=TipoNotificacao.choices,
        db_index=True,
        help_text="Tipo de notificação.",
    )
    titulo = models.CharField(max_length=120)
    mensagem = models.TextField()
    lida = models.BooleanField(default=False, db_index=True)
    lida_em = models.DateTimeField(null=True, blank=True)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    objeto_relacionado = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["destinatario", "lida", "-created_at"]),
            models.Index(fields=["papel_destinatario", "lida", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        models.Q(destinatario__isnull=False)
                        & models.Q(papel_destinatario__isnull=True)
                    )
                    | (
                        models.Q(destinatario__isnull=True)
                        & models.Q(papel_destinatario__isnull=False)
                    )
                ),
                name="notif_destinatario_usuario_ou_papel",
            ),
            models.CheckConstraint(
                condition=(
                    (models.Q(content_type__isnull=True) & models.Q(object_id__isnull=True))
                    | (models.Q(content_type__isnull=False) & models.Q(object_id__isnull=False))
                ),
                name="notif_objeto_relacionado_coerente",
            ),
            models.CheckConstraint(
                condition=(
                    (models.Q(lida=False) & models.Q(lida_em__isnull=True))
                    | (models.Q(lida=True) & models.Q(lida_em__isnull=False))
                ),
                name="notif_lida_lida_em_coerentes",
            ),
        ]

    def __str__(self):
        destino = self.destinatario_id or self.papel_destinatario
        return f"{self.tipo} -> {destino}"


class PushSubscription(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        help_text="Usuário autenticado dono da assinatura Web Push.",
    )
    endpoint = models.URLField(
        max_length=500,
        unique=True,
        help_text="Endpoint retornado pelo PushManager do navegador.",
    )
    p256dh = models.TextField(help_text="Chave pública p256dh da assinatura.")
    auth = models.TextField(help_text="Segredo auth da assinatura.")
    active = models.BooleanField(default=True, db_index=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    last_failure_status = models.PositiveSmallIntegerField(null=True, blank=True)
    last_failure_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Assinatura push"
        verbose_name_plural = "Assinaturas push"
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["usuario", "active", "-updated_at"]),
        ]

    def __str__(self):
        return f"push:{self.usuario_id}:{self.endpoint}"
