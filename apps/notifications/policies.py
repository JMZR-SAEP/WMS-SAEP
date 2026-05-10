from django.db.models import Q, QuerySet

from apps.notifications.models import Notificacao
from apps.users.models import User


def queryset_notificacoes_visiveis(usuario: User) -> QuerySet[Notificacao]:
    return (
        Notificacao.objects.filter(Q(destinatario=usuario) | Q(papel_destinatario=usuario.papel))
        .select_related("content_type", "destinatario")
        .order_by("-created_at", "-id")
    )
