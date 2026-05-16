from typing import Protocol

from apps.requisitions.models import ItemRequisicao, Requisicao


class StockPort(Protocol):
    def aplicar_reservas_autorizacao(
        self,
        requisicao: Requisicao,
        itens_autorizados: list[ItemRequisicao],
    ) -> None: ...

    def liberar_reservas_cancelamento(
        self,
        requisicao: Requisicao,
        itens_autorizados: list[ItemRequisicao],
    ) -> None: ...

    def aplicar_saidas_e_liberacoes_retirada(
        self,
        requisicao: Requisicao,
        itens_autorizados: list[ItemRequisicao],
    ) -> None: ...
