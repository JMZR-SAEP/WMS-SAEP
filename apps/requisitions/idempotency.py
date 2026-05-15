from django.db import IntegrityError, transaction

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
        return RequisicaoIdempotencyKey.objects.select_for_update().get(**lookup), False
