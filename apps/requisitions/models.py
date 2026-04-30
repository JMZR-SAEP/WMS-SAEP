from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F, Q


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
        return [
            cls.ATENDIDA_PARCIALMENTE,
            cls.ATENDIDA,
            cls.CANCELADA,
            cls.ESTORNADA,
            cls.RECUSADA,
        ]


class TipoEvento(models.TextChoices):
    CRIACAO = "criacao", "Criação"
    ENVIO_AUTORIZACAO = "envio_autorizacao", "Envio para Autorização"
    RETORNO_RASCUNHO = "retorno_rascunho", "Retorno para Rascunho"
    REENVIO_AUTORIZACAO = "reenvio_autorizacao", "Reenvio para Autorização"
    AUTORIZACAO = "autorizacao", "Autorização"
    RECUSA = "recusa", "Recusa"
    ATENDIMENTO_PARCIAL = "atendimento_parcial", "Atendimento Parcial"
    ATENDIMENTO = "atendimento", "Atendimento"
    CANCELAMENTO = "cancelamento", "Cancelamento"
    ESTORNO = "estorno", "Estorno"


class SequenciaNumeroRequisicao(models.Model):
    ano = models.PositiveIntegerField(unique=True)
    ultimo_numero = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sequência Anual de Requisição"
        verbose_name_plural = "Sequências Anuais de Requisição"
        ordering = ["-ano"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ultimo_numero__gte=0),
                name="req_seq_ultimo_numero_nao_negativo",
            ),
        ]

    def __str__(self):
        return f"{self.ano}: {self.ultimo_numero}"


class Requisicao(models.Model):
    numero_publico = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^REQ-\d{4}-\d{6}$",
                message="numero_publico deve seguir o formato REQ-AAAA-NNNNNN.",
            )
        ],
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
        editable=False,
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
                condition=Q(numero_publico__isnull=True)
                | Q(numero_publico="")
                | Q(numero_publico__regex=r"^REQ-\d{4}-\d{6}$"),
                name="req_numero_publico_formato_valido_ou_vazio",
            ),
            models.CheckConstraint(
                condition=Q(numero_publico__isnull=True)
                | Q(numero_publico="")
                | ~Q(status=StatusRequisicao.RASCUNHO)
                | Q(data_envio_autorizacao__isnull=False),
                name="req_numero_publico_nao_pode_ser_preenchido_em_rascunho_nunca_enviado",
            ),
            models.CheckConstraint(
                condition=~Q(status=StatusRequisicao.RECUSADA) | Q(motivo_recusa__gt=""),
                name="req_motivo_recusa_obrigatorio_quando_recusada",
            ),
            models.CheckConstraint(
                condition=~Q(status=StatusRequisicao.CANCELADA)
                | Q(motivo_cancelamento__gt="")
                | Q(data_autorizacao_ou_recusa__isnull=True),
                name="req_motivo_cancelamento_obrigatorio_quando_cancelada_pos_autorizacao",
            ),
        ]

    def __str__(self):
        return (
            f"REQ {self.numero_publico or f'(rascunho {self.id})'}"
            f" — {self.beneficiario.nome_completo}"
        )

    def save(self, *args, **kwargs):
        if self._state.adding:
            if self.beneficiario_id is None:
                raise ValidationError({"beneficiario": "Beneficiário é obrigatório."})
            if self.beneficiario.setor_id is None:
                raise ValidationError(
                    {"beneficiario": "Beneficiário deve possuir setor para criar a requisição."}
                )
            self.setor_beneficiario_id = self.beneficiario.setor_id
        else:
            persisted = (
                type(self)
                .objects.filter(pk=self.pk)
                .values(
                    "beneficiario_id",
                    "setor_beneficiario_id",
                )
                .first()
            )
            if persisted is not None:
                errors = {}
                if self.beneficiario_id != persisted["beneficiario_id"]:
                    errors["beneficiario"] = "Beneficiário não pode ser alterado após a criação."
                if self.setor_beneficiario_id != persisted["setor_beneficiario_id"]:
                    errors["setor_beneficiario"] = (
                        "Setor beneficiário é snapshot histórico e não pode ser alterado."
                    )
                if errors:
                    raise ValidationError(errors)

        super().save(*args, **kwargs)


class ItemRequisicao(models.Model):
    requisicao = models.ForeignKey(
        Requisicao,
        on_delete=models.PROTECT,
        related_name="itens",
        help_text="Requisição pai",
    )
    material = models.ForeignKey(
        "materials.Material",
        on_delete=models.PROTECT,
        related_name="itens_requisicao",
        help_text="Material solicitado",
    )
    unidade_medida = models.CharField(
        max_length=20,
        help_text="Unidade de medida (snapshot do material no momento da criação)",
    )
    quantidade_solicitada = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Quantidade solicitada",
    )
    quantidade_autorizada = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        blank=True,
        help_text="Quantidade autorizada",
    )
    justificativa_autorizacao_parcial = models.TextField(
        blank=True,
        default="",
        help_text="Justificativa se autorizado em quantidade menor que solicitado",
    )
    quantidade_entregue = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text="Quantidade efetivamente entregue",
    )
    justificativa_atendimento_parcial = models.TextField(
        blank=True,
        default="",
        help_text="Justificativa se entregue em quantidade menor que autorizado",
    )
    observacao = models.TextField(
        blank=True,
        default="",
        help_text="Observações sobre o item",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Item de Requisição"
        verbose_name_plural = "Itens de Requisição"
        ordering = ["requisicao", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantidade_solicitada__gt=0),
                name="item_req_quantidade_solicitada_positiva",
            ),
            models.CheckConstraint(
                condition=Q(quantidade_autorizada__gte=0),
                name="item_req_quantidade_autorizada_nao_negativa",
            ),
            models.CheckConstraint(
                condition=Q(quantidade_entregue__gte=0),
                name="item_req_quantidade_entregue_nao_negativa",
            ),
            models.CheckConstraint(
                condition=Q(quantidade_autorizada__lte=F("quantidade_solicitada")),
                name="item_req_autorizada_lte_solicitada",
            ),
            models.CheckConstraint(
                condition=Q(quantidade_entregue__lte=F("quantidade_autorizada")),
                name="item_req_entregue_lte_autorizada",
            ),
            models.CheckConstraint(
                condition=Q(quantidade_autorizada=F("quantidade_solicitada"))
                | Q(quantidade_autorizada=0)
                | Q(justificativa_autorizacao_parcial__gt=""),
                name="item_req_just_autorizacao_obrigatoria_quando_parcial",
            ),
            models.CheckConstraint(
                condition=Q(quantidade_entregue=F("quantidade_autorizada"))
                | Q(quantidade_entregue=0)
                | Q(justificativa_atendimento_parcial__gt=""),
                name="item_req_just_atendimento_obrigatoria_quando_parcial",
            ),
        ]

    def __str__(self):
        return (
            f"{self.material.codigo_completo} — {self.quantidade_solicitada} {self.unidade_medida}"
        )


class EventoTimelineQuerySet(models.QuerySet):
    def delete(self):
        raise ValueError("Eventos de timeline não podem ser removidos em lote")

    def update(self, **kwargs):
        raise ValueError("Eventos de timeline são imutáveis")


class EventoTimelineManager(models.Manager.from_queryset(EventoTimelineQuerySet)):
    def bulk_update(self, objs, fields, batch_size=None):
        raise ValueError("Eventos de timeline são imutáveis")


class EventoTimeline(models.Model):
    requisicao = models.ForeignKey(
        Requisicao,
        on_delete=models.PROTECT,
        related_name="eventos",
        help_text="Requisição associada",
    )
    tipo_evento = models.CharField(
        max_length=30,
        choices=TipoEvento.choices,
        help_text="Tipo de evento registrado",
    )
    usuario = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="eventos_timeline",
        help_text="Usuário que causou o evento",
    )
    data_hora = models.DateTimeField(
        auto_now_add=True,
        help_text="Data e hora do evento",
    )
    observacao = models.TextField(
        blank=True,
        default="",
        help_text="Observações sobre o evento",
    )

    objects = EventoTimelineManager()

    class Meta:
        verbose_name = "Evento de Timeline"
        verbose_name_plural = "Eventos de Timeline"
        ordering = ["requisicao", "data_hora"]

    def __str__(self):
        return (
            f"REQ {self.requisicao.numero_publico or f'(rascunho {self.requisicao.id})'}"
            f" — {self.get_tipo_evento_display()} em {self.data_hora.strftime('%d/%m/%Y %H:%M')}"
        )

    def save(self, *args, **kwargs):
        if self.pk and EventoTimeline.objects.filter(pk=self.pk).exists():
            raise ValueError("Eventos de timeline são imutáveis")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Eventos de timeline não podem ser removidos")
