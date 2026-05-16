from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.requisitions.models import SequenciaNumeroRequisicao


def gerar_numero_publico(*, ano: int | None = None) -> str:
    ano = ano or timezone.localdate().year

    with transaction.atomic():
        try:
            sequencia = SequenciaNumeroRequisicao.objects.select_for_update().get(ano=ano)
        except SequenciaNumeroRequisicao.DoesNotExist:
            try:
                with transaction.atomic():
                    sequencia = SequenciaNumeroRequisicao.objects.create(
                        ano=ano,
                        ultimo_numero=0,
                    )
            except IntegrityError:
                sequencia = SequenciaNumeroRequisicao.objects.select_for_update().get(ano=ano)

        sequencia.ultimo_numero += 1
        sequencia.save(update_fields=["ultimo_numero", "updated_at"])
        return f"REQ-{ano}-{sequencia.ultimo_numero:06d}"
