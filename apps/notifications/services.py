from collections.abc import Iterable

from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import PermissionDenied

from apps.notifications.models import Notificacao, TipoNotificacao
from apps.users.models import PapelChoices, User


def _content_type_e_object_id(objeto_relacionado):
    if objeto_relacionado is None:
        return None, None
    return ContentType.objects.get_for_model(objeto_relacionado), objeto_relacionado.pk


def criar_notificacao_usuario(
    *,
    destinatario: User,
    tipo: TipoNotificacao,
    titulo: str,
    mensagem: str,
    objeto_relacionado=None,
) -> Notificacao | None:
    if not destinatario.is_active:
        return None

    content_type, object_id = _content_type_e_object_id(objeto_relacionado)
    return Notificacao.objects.create(
        destinatario=destinatario,
        tipo=tipo,
        titulo=titulo,
        mensagem=mensagem,
        content_type=content_type,
        object_id=object_id,
    )


def criar_notificacao_papel(
    *,
    papel_destinatario: PapelChoices,
    tipo: TipoNotificacao,
    titulo: str,
    mensagem: str,
    objeto_relacionado=None,
) -> Notificacao:
    content_type, object_id = _content_type_e_object_id(objeto_relacionado)
    return Notificacao.objects.create(
        papel_destinatario=papel_destinatario,
        tipo=tipo,
        titulo=titulo,
        mensagem=mensagem,
        content_type=content_type,
        object_id=object_id,
    )


def criar_notificacoes_usuarios_unicos(
    *,
    destinatarios: Iterable[User],
    tipo: TipoNotificacao,
    titulo: str,
    mensagem: str,
    objeto_relacionado=None,
) -> list[Notificacao]:
    notificacoes = []
    vistos = set()
    for destinatario in destinatarios:
        if destinatario.pk in vistos:
            continue
        vistos.add(destinatario.pk)
        notificacao = criar_notificacao_usuario(
            destinatario=destinatario,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            objeto_relacionado=objeto_relacionado,
        )
        if notificacao is not None:
            notificacoes.append(notificacao)
    return notificacoes


def marcar_notificacao_como_lida(*, notificacao: Notificacao, usuario: User) -> Notificacao:
    if notificacao.destinatario_id is None:
        raise PermissionDenied("Notificações coletivas por papel não possuem leitura individual.")
    if notificacao.destinatario_id != usuario.pk:
        raise PermissionDenied("Usuário não é destinatário desta notificação.")
    notificacao.marcar_como_lida()
    return notificacao
