from django.db import models


class GrupoMaterial(models.Model):
    codigo_grupo = models.CharField(
        max_length=10, unique=True, help_text="Código xxx do grupo no SCPI"
    )
    nome = models.CharField(max_length=200, help_text="Nome descritivo vindo do SCPI")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Grupo de Material"
        verbose_name_plural = "Grupos de Material"
        ordering = ["codigo_grupo"]

    def __str__(self):
        return f"{self.codigo_grupo} — {self.nome}"


class SubgrupoMaterial(models.Model):
    grupo = models.ForeignKey(
        GrupoMaterial,
        on_delete=models.PROTECT,
        related_name="subgrupos",
        help_text="Grupo de material pai",
    )
    codigo_subgrupo = models.CharField(max_length=10, help_text="Código yyy do subgrupo no SCPI")
    nome = models.CharField(max_length=200, help_text="Nome descritivo vindo do SCPI")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Subgrupo de Material"
        verbose_name_plural = "Subgrupos de Material"
        ordering = ["grupo", "codigo_subgrupo"]
        constraints = [
            models.UniqueConstraint(
                fields=["grupo", "codigo_subgrupo"], name="unique_subgrupo_por_grupo"
            )
        ]

    def __str__(self):
        return f"{self.grupo.codigo_grupo}.{self.codigo_subgrupo} — {self.nome}"
