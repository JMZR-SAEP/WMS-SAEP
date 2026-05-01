from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.materials.models import Material


class TipoMovimentacao(models.TextChoices):
    SALDO_INICIAL = "SALDO_INICIAL", "Saldo inicial (carga SCPI)"
    RESERVA_POR_AUTORIZACAO = (
        "RESERVA_POR_AUTORIZACAO",
        "Reserva por autorização",
    )


class MovimentacaoEstoqueQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValueError("Movimentações de estoque são imutáveis")

    def delete(self):
        raise ValueError("Movimentações de estoque não podem ser removidas")


class MovimentacaoEstoqueManager(models.Manager.from_queryset(MovimentacaoEstoqueQuerySet)):
    def bulk_create(self, objs, **kwargs):
        objs = list(objs)
        for obj in objs:
            obj.full_clean()
        return super().bulk_create(objs, **kwargs)

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValueError("Movimentações de estoque são imutáveis")


class EstoqueMaterial(models.Model):
    material = models.OneToOneField(
        Material,
        on_delete=models.PROTECT,
        related_name="estoque",
        help_text="Material único para este estoque",
    )
    saldo_fisico = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text="Quantidade física em mão",
    )
    saldo_reservado = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text="Quantidade reservada por requisições autorizadas",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estoque de Material"
        verbose_name_plural = "Estoques de Materiais"
        ordering = ["material__codigo_completo"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(saldo_fisico__gte=0),
                name="check_saldo_fisico_nao_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(saldo_reservado__gte=0),
                name="check_saldo_reservado_nao_negativo",
            ),
        ]

    def __str__(self):
        return f"Estoque: {self.material.codigo_completo}"

    @property
    def saldo_disponivel(self) -> Decimal:
        return self.saldo_fisico - self.saldo_reservado


class MovimentacaoEstoque(models.Model):
    """
    Movimentações auditáveis de estoque.

    Invariantes:
    - SALDO_INICIAL nunca referencia requisição/item.
    - RESERVA_POR_AUTORIZACAO sempre referencia a requisição e o item reservados.
    - Tipos futuros devem declarar explicitamente sua origem, sem reutilizar
      registros já persistidos.
    """

    # SALDO_INICIAL é uma carga de origem; movimentações operacionais apontam
    # para a requisição/item que consumiu ou reservou saldo.
    requisicao = models.ForeignKey(
        "requisitions.Requisicao",
        on_delete=models.PROTECT,
        related_name="movimentacoes_estoque",
        null=True,
        blank=True,
        help_text="Requisição relacionada à movimentação",
    )
    item_requisicao = models.ForeignKey(
        "requisitions.ItemRequisicao",
        on_delete=models.PROTECT,
        related_name="movimentacoes_estoque",
        null=True,
        blank=True,
        help_text="Item de requisição relacionado à movimentação",
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="movimentacoes",
        help_text="Material relacionado à movimentação",
    )
    tipo = models.CharField(
        max_length=30,
        choices=TipoMovimentacao.choices,
        help_text="Tipo de movimentação",
    )
    quantidade = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Quantidade movimentada",
    )
    saldo_anterior = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Saldo físico anterior à movimentação",
    )
    saldo_posterior = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Saldo físico posterior à movimentação",
    )
    saldo_reservado_anterior = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text="Saldo reservado anterior à movimentação",
    )
    saldo_reservado_posterior = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text="Saldo reservado posterior à movimentação",
    )
    observacao = models.TextField(
        blank=True,
        default="",
        help_text="Observação opcional sobre a movimentação",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = MovimentacaoEstoqueManager()

    class Meta:
        verbose_name = "Movimentação de Estoque"
        verbose_name_plural = "Movimentações de Estoque"
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantidade__gte=0),
                name="check_movimentacao_quantidade_nao_negativa",
            ),
            models.CheckConstraint(
                condition=models.Q(saldo_anterior__gte=0),
                name="check_movimentacao_saldo_anterior_nao_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(saldo_posterior__gte=0),
                name="check_movimentacao_saldo_posterior_nao_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    tipo__in=[
                        TipoMovimentacao.SALDO_INICIAL,
                        TipoMovimentacao.RESERVA_POR_AUTORIZACAO,
                    ]
                ),
                name="check_movimentacao_tipo_valido",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(tipo=TipoMovimentacao.SALDO_INICIAL)
                    | (
                        models.Q(saldo_anterior=0)
                        & models.Q(saldo_posterior=models.F("quantidade"))
                        & models.Q(saldo_reservado_anterior=0)
                        & models.Q(saldo_reservado_posterior=0)
                        & models.Q(requisicao__isnull=True)
                        & models.Q(item_requisicao__isnull=True)
                    )
                ),
                name="check_movimentacao_saldo_inicial_coerente",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(tipo=TipoMovimentacao.RESERVA_POR_AUTORIZACAO)
                    & models.Q(saldo_anterior=models.F("saldo_posterior"))
                    & models.Q(
                        saldo_reservado_posterior=(
                            models.F("saldo_reservado_anterior") + models.F("quantidade")
                        )
                    )
                    & models.Q(requisicao__isnull=False)
                    & models.Q(item_requisicao__isnull=False)
                )
                | ~models.Q(tipo=TipoMovimentacao.RESERVA_POR_AUTORIZACAO),
                name="check_movimentacao_reserva_por_autorizacao_coerente",
            ),
        ]

    def __str__(self):
        return f"{self.material.codigo_completo} - {self.get_tipo_display()} - {self.quantidade}"

    def save(self, *args, **kwargs):
        if self.pk and MovimentacaoEstoque.objects.filter(pk=self.pk).exists():
            raise ValueError("Movimentações de estoque são imutáveis")
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        if self.tipo == TipoMovimentacao.SALDO_INICIAL:
            if self.requisicao_id is not None or self.item_requisicao_id is not None:
                raise ValidationError(
                    {
                        "requisicao": "Movimentação de saldo inicial não pode referenciar requisição.",
                        "item_requisicao": "Movimentação de saldo inicial não pode referenciar item.",
                    }
                )
            return

        if self.tipo == TipoMovimentacao.RESERVA_POR_AUTORIZACAO:
            errors = {}
            if self.requisicao_id is None:
                errors["requisicao"] = "Reserva por autorização exige requisição."
            if self.item_requisicao_id is None:
                errors["item_requisicao"] = "Reserva por autorização exige item."
            if self.item_requisicao_id is not None:
                item = self.item_requisicao
                if self.requisicao_id is not None and item.requisicao_id != self.requisicao_id:
                    errors["requisicao"] = "Requisição deve ser a mesma do item da movimentação."
                if self.material_id != item.material_id:
                    errors["material"] = "Material deve ser o mesmo do item da movimentação."
            if errors:
                raise ValidationError(errors)

    def delete(self, *args, **kwargs):
        raise ValueError("Movimentações de estoque não podem ser removidas")
