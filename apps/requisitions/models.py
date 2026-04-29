from django.db import models
from django.db.models import Q


class StatusRequisicao(models.TextChoices):
    RASCUNHO = "rascunho", "Rascunho"
    AGUARDANDO_AUTORIZACAO = "aguardando_autorizacao", "Aguardando Autorização"
    RECUSADA = "recusada", "Recusada"
    AUTORIZADA = "autorizada", "Autorizada"
    ATENDIDA_PARCIALMENTE = "atendida_parcialmente", "Atendida Parcialmente"
    ATENDIDA = "atendida", "Atendida"
    CANCELADA = "cancelada", "Cancelada"
    ESTORNADA = "estornada", "Estornada"

    @classmethod
    def estados_finais(cls):
        return [cls.ATENDIDA_PARCIALMENTE, cls.ATENDIDA, cls.CANCELADA, cls.ESTORNADA]


class Requisicao(models.Model):
    numero_publico = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Número público da requisição (formato REQ-AAAA-NNNNNN), atribuído no primeiro envio",
    )
    criador = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="requisicoes_criadas",
        help_text="Usuário que criou a requisição",
    )
    beneficiario = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="requisicoes_beneficiadas",
        help_text="Usuário beneficiário dos materiais",
    )
    setor_beneficiario = models.ForeignKey(
        "users.Setor",
        on_delete=models.PROTECT,
        related_name="requisicoes",
        help_text="Setor do beneficiário (snapshot histórico, nunca recalculado)",
    )
    status = models.CharField(
        max_length=30,
        choices=StatusRequisicao.choices,
        default=StatusRequisicao.RASCUNHO,
        help_text="Status atual da requisição",
    )
    data_criacao = models.DateTimeField(
        auto_now_add=True,
        help_text="Data e hora de criação da requisição",
    )
    data_envio_autorizacao = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data do primeiro envio para autorização",
    )
    data_autorizacao_ou_recusa = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data da autorização ou recusa",
    )
    chefe_autorizador = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="requisicoes_autorizadas",
        help_text="Chefe que autorizou ou recusou a requisição",
    )
    motivo_recusa = models.TextField(
        blank=True,
        default="",
        help_text="Motivo da recusa (obrigatório quando status=recusada)",
    )
    data_finalizacao = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data de finalização ou cancelamento",
    )
    responsavel_atendimento = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="requisicoes_atendidas",
        help_text="Responsável do Almoxarifado que atendeu a requisição",
    )
    retirante_fisico = models.TextField(
        blank=True,
        default="",
        help_text="Nome de quem retirou (diferente do beneficiário)",
    )
    motivo_cancelamento = models.TextField(
        blank=True,
        default="",
        help_text="Motivo do cancelamento (obrigatório quando cancelada)",
    )
    observacao = models.TextField(
        blank=True,
        default="",
        help_text="Observações gerais",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Requisição"
        verbose_name_plural = "Requisições"
        ordering = ["-data_criacao"]
        constraints = [
            models.UniqueConstraint(
                fields=["numero_publico"],
                condition=Q(numero_publico__isnull=False) & ~Q(numero_publico=""),
                name="req_numero_publico_unico_quando_preenchido",
            ),
            models.CheckConstraint(
                condition=~Q(status=StatusRequisicao.RECUSADA) | Q(motivo_recusa__gt=""),
                name="req_motivo_recusa_obrigatorio_quando_recusada",
            ),
            models.CheckConstraint(
                condition=~Q(status=StatusRequisicao.CANCELADA) | Q(motivo_cancelamento__gt=""),
                name="req_motivo_cancelamento_obrigatorio_quando_cancelada",
            ),
        ]

    def __str__(self):
        return (
            f"REQ {self.numero_publico or f'(rascunho {self.id})'}"
            f" — {self.beneficiario.nome_completo}"
        )
