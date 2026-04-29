from django.db import models


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
