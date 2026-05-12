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


class PushClientEventType(models.TextChoices):
    PERMISSION_DENIED = "push_permission_denied", "Push negado"
    UNAVAILABLE = "push_unavailable", "Push indisponível"
    REQUIRES_PWA = "push_requires_pwa", "Push requer PWA instalado"
    BADGE_UNAVAILABLE = "push_badge_unavailable", "Badge indisponível"


class PushDiagnosticStatus(models.TextChoices):
    ACTIVE = "ativo", "Ativo"
    BLOCKED = "bloqueado", "Bloqueado"
    UNSUPPORTED = "sem_suporte", "Sem suporte"
    REQUIRES_PWA = "requer_instalacao_pwa", "Requer instalação PWA"
    REQUIRES_ACTIVATION = "requer_ativacao", "Requer ativação"


class PushReminderType(models.TextChoices):
    OVERDUE_APPROVALS = "autorizacoes_atrasadas", "Autorizações atrasadas"


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


class PushClientEvent(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_client_events",
        help_text="Usuário autenticado associado ao evento técnico de push.",
    )
    papel = models.CharField(
        max_length=30,
        choices=PapelChoices.choices,
        help_text="Snapshot do papel operacional no momento do evento.",
    )
    event_type = models.CharField(max_length=40, choices=PushClientEventType.choices)
    diagnostic_status = models.CharField(max_length=30, choices=PushDiagnosticStatus.choices)
    notification_supported = models.BooleanField(default=False)
    service_worker_supported = models.BooleanField(default=False)
    push_manager_supported = models.BooleanField(default=False)
    badging_supported = models.BooleanField(default=False)
    standalone_display = models.BooleanField(default=False)
    event_date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Evento técnico de push"
        verbose_name_plural = "Eventos técnicos de push"
        ordering = ["-event_date", "-updated_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "event_type", "event_date"],
                name="push_client_event_usuario_tipo_dia_unico",
            ),
        ]
        indexes = [
            models.Index(fields=["usuario", "event_type", "-event_date"]),
        ]

    def __str__(self):
        return f"{self.event_type}:{self.usuario_id}:{self.event_date}"


class PushReminderState(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_reminder_states",
        help_text="Usuário destinatário do lembrete agregado.",
    )
    reminder_type = models.CharField(max_length=40, choices=PushReminderType.choices)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    last_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estado de lembrete push"
        verbose_name_plural = "Estados de lembrete push"
        ordering = ["-updated_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "reminder_type"],
                name="push_reminder_state_usuario_tipo_unico",
            ),
        ]

    def __str__(self):
        return f"{self.reminder_type}:{self.usuario_id}"
