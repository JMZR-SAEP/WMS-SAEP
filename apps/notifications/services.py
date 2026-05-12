import json
from collections.abc import Iterable
from datetime import timedelta

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.notifications.models import (
    Notificacao,
    PushClientEvent,
    PushClientEventType,
    PushDiagnosticStatus,
    PushReminderState,
    PushReminderType,
    PushSubscription,
    TipoNotificacao,
)
from apps.notifications.policies import pode_gerenciar_push_subscription
from apps.requisitions.models import Requisicao, StatusRequisicao
from apps.users.models import PapelChoices, User

PUSH_REMINDER_COOLDOWN = timedelta(hours=4)
PUSH_REMINDER_OVERDUE_AFTER = timedelta(hours=4)


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
    _validar_usuario_push(usuario)

    with transaction.atomic():
        _validar_usuario_push(usuario)
        existing = PushSubscription.objects.select_for_update().filter(endpoint=endpoint).first()
        if existing is not None and existing.usuario_id != usuario.pk:
            raise PermissionDenied("Endpoint de push já vinculado a outro usuário.")

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
    _validar_usuario_push(usuario)

    with transaction.atomic():
        _validar_usuario_push(usuario)
        subscription = (
            PushSubscription.objects.select_for_update().filter(endpoint=endpoint).first()
        )
        if subscription is None:
            return
        if subscription.usuario_id != usuario.pk:
            raise PermissionDenied("Endpoint de push já vinculado a outro usuário.")
        subscription.active = False
        subscription.save(update_fields=["active", "updated_at"])


def registrar_push_client_event(
    *,
    usuario: User,
    event_type: PushClientEventType,
    diagnostic_status: PushDiagnosticStatus,
    notification_supported: bool,
    service_worker_supported: bool,
    push_manager_supported: bool,
    badging_supported: bool,
    standalone_display: bool,
) -> PushClientEvent:
    _validar_usuario_push(usuario)
    today = timezone.localdate()

    event, _ = PushClientEvent.objects.update_or_create(
        usuario=usuario,
        event_type=event_type,
        event_date=today,
        defaults={
            "papel": usuario.papel,
            "diagnostic_status": diagnostic_status,
            "notification_supported": notification_supported,
            "service_worker_supported": service_worker_supported,
            "push_manager_supported": push_manager_supported,
            "badging_supported": badging_supported,
            "standalone_display": standalone_display,
        },
    )
    return event


def _validar_usuario_push(usuario: User) -> None:
    if not pode_gerenciar_push_subscription(usuario):
        raise PermissionDenied("Usuário não pode gerenciar alertas push.")


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


def _enviar_push_para_usuario(*, usuario: User, payload: dict[str, object], ttl: int = 3600) -> int:
    private_key = getattr(settings, "WEB_PUSH_VAPID_PRIVATE_KEY", "")
    subject = getattr(settings, "WEB_PUSH_VAPID_SUBJECT", "")
    if not private_key or not subject:
        return 0

    subscriptions = PushSubscription.objects.filter(usuario=usuario, active=True)
    sent = 0
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
                ttl=ttl,
                timeout=10,
            )
        except Exception as exc:
            if _status_from_push_exception(exc) is None:
                raise
            _record_push_failure(subscription, exc)
            continue

        sent += 1
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

    return sent


def enviar_push_requisicao_aguardando_autorizacao(*, requisicao) -> None:
    chefe = requisicao.setor_beneficiario.chefe_responsavel
    payload = {
        "title": "Requisição aguardando autorização",
        "body": f"Beneficiário: {requisicao.beneficiario.nome_completo}",
        "url": f"/requisicoes/{requisicao.pk}?contexto=autorizacao",
        "tag": f"requisicao-autorizacao-{requisicao.pk}",
    }
    _enviar_push_para_usuario(usuario=chefe, payload=payload)


def enviar_push_lembretes_autorizacoes_atrasadas(*, now=None) -> int:
    current_time = now or timezone.now()
    overdue_before = current_time - PUSH_REMINDER_OVERDUE_AFTER
    overdue_rows = (
        Requisicao.objects.filter(
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao__lte=overdue_before,
            setor_beneficiario__chefe_responsavel__isnull=False,
        )
        .values("setor_beneficiario__chefe_responsavel")
        .annotate(total=Count("id"))
        .order_by("setor_beneficiario__chefe_responsavel")
    )
    sent_to_users = 0

    for row in overdue_rows:
        chefe_id = row["setor_beneficiario__chefe_responsavel"]
        total = row["total"]
        chefe = User.objects.filter(pk=chefe_id, is_active=True).first()
        if chefe is None or not pode_gerenciar_push_subscription(chefe):
            continue

        with transaction.atomic():
            state, _ = PushReminderState.objects.select_for_update().get_or_create(
                usuario=chefe,
                reminder_type=PushReminderType.OVERDUE_APPROVALS,
                defaults={"last_count": 0},
            )
            if (
                state.last_sent_at is not None
                and current_time - state.last_sent_at < PUSH_REMINDER_COOLDOWN
            ):
                continue

            body = (
                "1 autorização atrasada aguarda decisão."
                if total == 1
                else f"{total} autorizações atrasadas aguardam decisão."
            )
            payload = {
                "title": "Autorizações atrasadas",
                "body": body,
                "url": "/autorizacoes",
                "tag": "autorizacoes-atrasadas",
            }
            sent = _enviar_push_para_usuario(usuario=chefe, payload=payload, ttl=3600)
            if sent == 0:
                continue

            state.last_sent_at = current_time
            state.last_count = total
            state.save(update_fields=["last_sent_at", "last_count", "updated_at"])
            sent_to_users += 1

    return sent_to_users
