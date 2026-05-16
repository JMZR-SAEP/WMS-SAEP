from django.db import transaction

from apps.core.api.exceptions import DomainConflict
from apps.requisitions.models import ItemRequisicao, Requisicao
from apps.stock.models import EstoqueMaterial
from apps.stock.services import (
    registrar_liberacao_reserva_por_atendimento,
    registrar_reserva_por_autorizacao,
    registrar_saida_por_atendimento,
)


def _travar_estoques(
    itens: list[ItemRequisicao],
) -> dict[int, EstoqueMaterial]:
    material_ids = sorted({item.material_id for item in itens})
    estoques = list(
        EstoqueMaterial.objects.select_for_update()
        .select_related("material")
        .filter(material_id__in=material_ids)
        .order_by("material_id")
    )
    estoques_por_material_id = {e.material_id: e for e in estoques}
    material_ids_sem_estoque = set(material_ids) - set(estoques_por_material_id)
    if material_ids_sem_estoque:
        raise DomainConflict(
            "Material autorizado não possui estoque cadastrado.",
            details={"material_ids": sorted(material_ids_sem_estoque)},
        )
    return estoques_por_material_id


class StockAdapter:
    def aplicar_reservas_autorizacao(
        self,
        requisicao: Requisicao,
        itens_autorizados: list[ItemRequisicao],
    ) -> None:
        for item in itens_autorizados:
            if item.quantidade_autorizada <= 0:
                continue
            registrar_reserva_por_autorizacao(
                requisicao=requisicao,
                item=item,
                quantidade=item.quantidade_autorizada,
            )

    def liberar_reservas_cancelamento(
        self,
        requisicao: Requisicao,
        itens_autorizados: list[ItemRequisicao],
    ) -> None:
        with transaction.atomic():
            estoques = _travar_estoques(itens_autorizados)
            itens_com_saldo_fisico = [
                item.id for item in itens_autorizados if estoques[item.material_id].saldo_fisico > 0
            ]
            if itens_com_saldo_fisico:
                raise DomainConflict(
                    "Ainda há saldo físico para atendimento parcial da requisição.",
                    details={"item_ids": itens_com_saldo_fisico},
                )
            for item in itens_autorizados:
                if item.quantidade_autorizada <= 0:
                    continue
                registrar_liberacao_reserva_por_atendimento(
                    requisicao=requisicao,
                    item=item,
                    quantidade=item.quantidade_autorizada,
                    estoque_travado=estoques[item.material_id],
                )

    def aplicar_saidas_e_liberacoes_retirada(
        self,
        requisicao: Requisicao,
        itens_autorizados: list[ItemRequisicao],
    ) -> None:
        with transaction.atomic():
            estoques = _travar_estoques(itens_autorizados)
            for item in itens_autorizados:
                estoque = estoques[item.material_id]
                if item.quantidade_entregue > 0:
                    registrar_saida_por_atendimento(
                        requisicao=requisicao,
                        item=item,
                        quantidade=item.quantidade_entregue,
                        estoque_travado=estoque,
                    )
                quantidade_nao_entregue = item.quantidade_autorizada - item.quantidade_entregue
                if quantidade_nao_entregue > 0:
                    registrar_liberacao_reserva_por_atendimento(
                        requisicao=requisicao,
                        item=item,
                        quantidade=quantidade_nao_entregue,
                        estoque_travado=estoque,
                    )
