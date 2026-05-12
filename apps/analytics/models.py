from django.conf import settings
from django.db import models

from apps.users.models import PapelChoices


class FrontendAnalyticsEventType(models.TextChoices):
    LOGIN_SUCCESS = "login_success", "Login realizado"
    DRAFT_STARTED = "draft_started", "Criação iniciada"
    DRAFT_SAVED = "draft_saved", "Rascunho salvo"
    DRAFT_SUBMITTED = "draft_submitted", "Rascunho enviado"
    DRAFT_ABANDONED = "draft_abandoned", "Rascunho abandonado"
    AUTHORIZATION_TOTAL = "authorization_total", "Autorização total"
    AUTHORIZATION_PARTIAL = "authorization_partial", "Autorização parcial"
    AUTHORIZATION_REFUSED = "authorization_refused", "Autorização recusada"
    API_ERROR = "api_error", "Erro de API"


class FrontendAnalyticsScreen(models.TextChoices):
    LOGIN = "login", "Login"
    MINHAS_REQUISICOES = "minhas_requisicoes", "Minhas requisições"
    NOVA_REQUISICAO = "nova_requisicao", "Nova requisição"
    REQUISICAO_DETALHE = "requisicao_detalhe", "Detalhe da requisição"
    AUTORIZACOES = "autorizacoes", "Autorizações"
    ATENDIMENTOS = "atendimentos", "Atendimentos"
    ALERTAS = "alertas", "Alertas"
    SHELL = "shell", "Shell"


class FrontendAnalyticsDraftStep(models.TextChoices):
    BENEFICIARIO = "beneficiario", "Beneficiário"
    ITENS = "itens", "Itens"
    REVISAO = "revisao", "Revisão"
    ENVIO = "envio", "Envio"


class FrontendAnalyticsEvent(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="frontend_analytics_events",
        help_text="Usuário autenticado associado ao evento.",
    )
    papel = models.CharField(
        max_length=30,
        choices=PapelChoices.choices,
        help_text="Snapshot do papel operacional no momento do evento.",
    )
    event_type = models.CharField(max_length=40, choices=FrontendAnalyticsEventType.choices)
    screen = models.CharField(
        max_length=40,
        choices=FrontendAnalyticsScreen.choices,
        blank=True,
    )
    draft_step = models.CharField(
        max_length=30,
        choices=FrontendAnalyticsDraftStep.choices,
        blank=True,
    )
    action = models.CharField(max_length=60, blank=True)
    endpoint_key = models.CharField(max_length=120, blank=True)
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    trace_id = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento de analytics frontend"
        verbose_name_plural = "Eventos de analytics frontend"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["usuario", "event_type", "-created_at"]),
            models.Index(fields=["event_type", "-created_at"]),
            models.Index(fields=["endpoint_key", "http_status", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type}:{self.usuario_id}:{self.created_at}"

    def save(self, *args, **kwargs):
        if self.pk:
            persisted_papel = (
                type(self).objects.filter(pk=self.pk).values_list("papel", flat=True).first()
            )
            if persisted_papel is not None and self.papel != persisted_papel:
                raise ValueError("O papel snapshot do evento de analytics é imutável.")

        super().save(*args, **kwargs)
