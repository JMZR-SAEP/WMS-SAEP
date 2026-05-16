import hashlib
import json
from collections.abc import Callable
from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.core.api.exceptions import DomainConflict
from apps.requisitions.domain.types import ItemAtendimentoData
from apps.requisitions.models import RequisicaoIdempotencyKey, StatusIdempotencia
from apps.users.models import User


def get_or_create_idempotency_record(
    *,
    usuario: User,
    requisicao,
    operation: str,
    key: str,
    payload_hash: str,
) -> tuple[RequisicaoIdempotencyKey, bool]:
    lookup = {
        "usuario": usuario,
        "requisicao": requisicao,
        "endpoint": operation,
        "key": key,
    }
    try:
        with transaction.atomic():
            return RequisicaoIdempotencyKey.objects.select_for_update().get_or_create(
                **lookup,
                defaults={
                    "payload_hash": payload_hash,
                    "status": StatusIdempotencia.IN_PROGRESS,
                },
            )
    except IntegrityError:
        with transaction.atomic():
            return RequisicaoIdempotencyKey.objects.select_for_update().get(**lookup), False


def _decimal_canonico(value: Decimal) -> str:
    return format(value.normalize(), "f")


def normalizar_itens(
    itens: list[ItemAtendimentoData | dict[str, object]] | None,
) -> list[ItemAtendimentoData] | None:
    if itens is None:
        return None
    return [
        item if isinstance(item, ItemAtendimentoData) else ItemAtendimentoData(**item)
        for item in itens
    ]


def hash_payload_atendimento(
    *,
    itens: list[ItemAtendimentoData] | None,
    observacao_atendimento: str,
) -> str:
    payload: dict[str, object] = {
        "itens": None,
        "observacao_atendimento": observacao_atendimento.strip(),
    }
    if itens is not None:
        payload["itens"] = [
            {
                "item_id": item.item_id,
                "justificativa_atendimento_parcial": (
                    item.justificativa_atendimento_parcial.strip()
                ),
                "quantidade_entregue": _decimal_canonico(item.quantidade_entregue),
            }
            for item in sorted(itens, key=lambda item: item.item_id)
        ]
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload_json.encode()).hexdigest()


def hash_payload_retirada(retirante_fisico: str) -> str:
    return hashlib.sha256(
        json.dumps({"retirante_fisico": retirante_fisico.strip()}, sort_keys=True).encode()
    ).hexdigest()


def handle_idempotency[T](
    registro: RequisicaoIdempotencyKey,
    criado: bool,
    payload_hash: str,
    key: str,
    endpoint: str,
    in_progress_msg: str,
    result_fn: Callable[[], T],
) -> T | None:
    """Retorna resultado cacheado se COMPLETED, None se deve prosseguir, ou levanta DomainConflict."""
    if criado:
        return None
    if registro.payload_hash != payload_hash:
        raise DomainConflict(
            "Chave de idempotência já usada com payload diferente.",
            details={"idempotency_key": key, "endpoint": endpoint},
        )
    if registro.status == StatusIdempotencia.COMPLETED:
        return result_fn()
    raise DomainConflict(
        in_progress_msg,
        details={"idempotency_key": key, "endpoint": endpoint},
    )
