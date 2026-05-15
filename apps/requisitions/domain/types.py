from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ItemRascunhoData:
    material_id: int
    quantidade_solicitada: Decimal
    observacao: str = ""


@dataclass(frozen=True)
class ItemAutorizacaoData:
    item_id: int
    quantidade_autorizada: Decimal
    justificativa_autorizacao_parcial: str = ""


@dataclass(frozen=True)
class ItemAtendimentoData:
    item_id: int
    quantidade_entregue: Decimal
    justificativa_atendimento_parcial: str = ""
