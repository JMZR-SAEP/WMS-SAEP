import json
from collections.abc import Iterable

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.notifications.models import Notificacao, PushSubscription, TipoNotificacao
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
    Notificacao.objects.filter(pk=notificacao.pk, lida=False).update(
        lida=True,
        lida_em=timezone.now(),
    )
    notificacao.refresh_from_db(fields=["lida", "lida_em"])
    return notificacao


def contar_notificacoes_individuais_nao_lidas(*, usuario: User) -> int:
    return Notificacao.objects.filter(destinatario=usuario, lida=False).count()


def registrar_push_subscription(
    *,
    usuario: User,
    endpoint: str,
    p256dh: str,
    auth: str,
) -> PushSubscription:
    subscription, _ = PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "usuario": usuario,
            "p256dh": p256dh,
            "auth": auth,
            "active": True,
            "last_failure_status": None,
            "last_failure_reason": "",
        },
    )
    return subscription


def desativar_push_subscription(*, usuario: User, endpoint: str) -> None:
    PushSubscription.objects.filter(usuario=usuario, endpoint=endpoint).update(active=False)


def _webpush(**kwargs):
    from pywebpush import webpush

    return webpush(**kwargs)


def _status_from_push_exception(exc: Exception) -> int | None:
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    return None


def _record_push_failure(subscription: PushSubscription, exc: Exception) -> None:
    status_code = _status_from_push_exception(exc)
    subscription.active = status_code not in (404, 410)
    subscription.last_failure_at = timezone.now()
    subscription.last_failure_status = status_code
    subscription.last_failure_reason = str(exc)[:200]
    subscription.save(
        update_fields=[
            "active",
            "last_failure_at",
            "last_failure_status",
            "last_failure_reason",
            "updated_at",
        ]
    )


def enviar_push_requisicao_aguardando_autorizacao(*, requisicao) -> None:
    private_key = getattr(settings, "WEB_PUSH_VAPID_PRIVATE_KEY", "")
    subject = getattr(settings, "WEB_PUSH_VAPID_SUBJECT", "")
    if not private_key or not subject:
        return

    chefe = requisicao.setor_beneficiario.chefe_responsavel
    subscriptions = PushSubscription.objects.filter(usuario=chefe, active=True)
    if not subscriptions.exists():
        return

    payload = {
        "title": "Requisição aguardando autorização",
        "body": f"Beneficiário: {requisicao.beneficiario.nome_completo}",
        "url": f"/requisicoes/{requisicao.pk}?contexto=autorizacao",
        "tag": f"requisicao-autorizacao-{requisicao.pk}",
    }

    for subscription in subscriptions:
        try:
            _webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    },
                },
                data=json.dumps(payload),
                vapid_private_key=private_key,
                vapid_claims={"sub": subject},
                ttl=3600,
                timeout=10,
            )
        except Exception as exc:
            _record_push_failure(subscription, exc)
            continue

        subscription.last_success_at = timezone.now()
        subscription.last_failure_status = None
        subscription.last_failure_reason = ""
        subscription.save(
            update_fields=[
                "last_success_at",
                "last_failure_status",
                "last_failure_reason",
                "updated_at",
            ]
        )
