from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models

from .managers import UserManager


class PapelChoices(models.TextChoices):
    """Papéis operacionais do sistema WMS-SAEP."""

    SOLICITANTE = "solicitante", "Solicitante"
    AUXILIAR_SETOR = "auxiliar_setor", "Auxiliar de Setor"
    CHEFE_SETOR = "chefe_setor", "Chefe de Setor"
    AUXILIAR_ALMOXARIFADO = "auxiliar_almoxarifado", "Auxiliar de Almoxarifado"
    CHEFE_ALMOXARIFADO = "chefe_almoxarifado", "Chefe de Almoxarifado"


class Setor(models.Model):
    nome = models.CharField(
        max_length=200,
        unique=True,
        help_text="Nome do setor organizacional.",
    )
    chefe_responsavel = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="setor_como_chefe",
        help_text="Chefe responsável pelo setor.",
    )
    # Auxiliary ownership is provisional and may later expand to admin, seed,
    # policies, and tests once the full workflow is closed.
    auxiliar_responsavel = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="setor_como_auxiliar",
        help_text="Auxiliar responsável pelo setor",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Setores inativos permanecem em históricos mas não recebem novas requisições.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Setor"
        verbose_name_plural = "Setores"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} (Chefe: {self.chefe_responsavel.matricula_funcional})"

    def _validar_responsavel_no_setor(self, *, field_name: str, label: str) -> None:
        if not getattr(self, f"{field_name}_id"):
            return

        responsavel = getattr(self, field_name)
        setor_do_responsavel = getattr(responsavel, "setor", None)
        if setor_do_responsavel is not None and setor_do_responsavel.pk == self.pk:
            return

        if setor_do_responsavel is None:
            raise ValidationError({field_name: "O usuário não possui setor atribuído."})

        raise ValidationError(
            {
                field_name: (
                    f"O {label} pertence ao setor '{setor_do_responsavel.nome}', não a este setor."
                )
            }
        )

    def clean(self):
        super().clean()
        self._validar_responsavel_no_setor(
            field_name="chefe_responsavel",
            label="chefe responsável",
        )
        self._validar_responsavel_no_setor(
            field_name="auxiliar_responsavel",
            label="auxiliar responsável",
        )


class User(AbstractBaseUser, PermissionsMixin):
    matricula_funcional = models.CharField(
        max_length=20,
        unique=True,
        help_text="Identificador único de login (matrícula funcional).",
    )
    nome_completo = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    setor = models.ForeignKey(
        "Setor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuarios",
        db_index=True,
        help_text="Setor ao qual o usuário pertence.",
    )
    papel = models.CharField(
        max_length=30,
        choices=PapelChoices.choices,
        default=PapelChoices.SOLICITANTE,
        db_index=True,
        help_text="Papel operacional do usuário no sistema.",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "matricula_funcional"
    REQUIRED_FIELDS = ["nome_completo"]

    objects = UserManager()

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ["matricula_funcional"]

    def __str__(self):
        return f"{self.matricula_funcional} - {self.nome_completo}"
