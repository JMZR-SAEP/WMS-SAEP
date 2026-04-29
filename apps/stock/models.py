from decimal import Decimal

from django.db import models

from apps.materials.models import Material


class TipoMovimentacao(models.TextChoices):
    SALDO_INICIAL = "SALDO_INICIAL", "Saldo inicial (carga SCPI)"


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
    observacao = models.TextField(
        blank=True,
        default="",
        help_text="Observação opcional sobre a movimentação",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimentação de Estoque"
        verbose_name_plural = "Movimentações de Estoque"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.material.codigo_completo} - {self.get_tipo_display()} - {self.quantidade}"
