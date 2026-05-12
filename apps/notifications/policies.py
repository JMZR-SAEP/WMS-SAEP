from django.db.models import Q, QuerySet

from apps.notifications.models import Notificacao
from apps.users.models import PapelChoices, User
from apps.users.policies import usuario_operacional_ativo


def queryset_notificacoes_visiveis(usuario: User) -> QuerySet[Notificacao]:
    return (
        Notificacao.objects.filter(Q(destinatario=usuario) | Q(papel_destinatario=usuario.papel))
        .select_related("content_type", "destinatario")
        .order_by("-created_at", "-id")
    )


def pode_gerenciar_push_subscription(usuario: User) -> bool:
    return usuario_operacional_ativo(usuario) and usuario.papel in (
        PapelChoices.CHEFE_SETOR,
        PapelChoices.CHEFE_ALMOXARIFADO,
    )
