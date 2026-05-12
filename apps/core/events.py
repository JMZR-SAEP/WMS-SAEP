import logging
from collections import defaultdict
from collections.abc import Callable
from functools import partial
from typing import Any

from django.db import transaction

logger = logging.getLogger(__name__)

REQUISICAO_ENVIADA_AUTORIZACAO = "requisicao.enviada_autorizacao"
REQUISICAO_AUTORIZADA = "requisicao.autorizada"
REQUISICAO_RECUSADA = "requisicao.recusada"
REQUISICAO_CANCELADA = "requisicao.cancelada"
REQUISICAO_ATENDIDA = "requisicao.atendida"
PUSH_LEMBRETE_AUTORIZACOES_ATRASADAS = "push.lembrete_autorizacoes_atrasadas"

EventPayload = dict[str, Any]
EventHandler = Callable[[EventPayload], None]

_subscribers: dict[str, list[EventHandler]] = defaultdict(list)


def subscribe(event_name: str, handler: EventHandler) -> None:
    handlers = _subscribers[event_name]
    if handler not in handlers:
        handlers.append(handler)


def clear_subscribers() -> None:
    _subscribers.clear()


def publish(event_name: str, payload: EventPayload) -> None:
    for handler in tuple(_subscribers[event_name]):
        try:
            handler(payload)
        except Exception:
            logger.exception("Falha ao processar evento %s", event_name)


def publish_on_commit(event_name: str, payload: EventPayload) -> None:
    transaction.on_commit(partial(publish, event_name, payload))
