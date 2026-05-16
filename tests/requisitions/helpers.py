from decimal import Decimal

from apps.core.api.exceptions import DomainConflict
from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.requisitions.models import ItemRequisicao, Requisicao
from apps.stock.models import EstoqueMaterial


class StubStockPort:
    def __init__(self) -> None:
        self.reservas_aplicadas: list[tuple[Requisicao, list[ItemRequisicao]]] = []
        self.cancelamentos_liberados: list[tuple[Requisicao, list[ItemRequisicao]]] = []
        self.retiradas_aplicadas: list[tuple[Requisicao, list[ItemRequisicao]]] = []
        self.deve_falhar_em: str | None = None

    def aplicar_reservas_autorizacao(
        self, requisicao: Requisicao, itens_autorizados: list[ItemRequisicao]
    ) -> None:
        if self.deve_falhar_em == "aplicar_reservas_autorizacao":
            raise DomainConflict("stub: falha simulada")
        self.reservas_aplicadas.append((requisicao, list(itens_autorizados)))

    def liberar_reservas_cancelamento(
        self, requisicao: Requisicao, itens_autorizados: list[ItemRequisicao]
    ) -> None:
        if self.deve_falhar_em == "liberar_reservas_cancelamento":
            raise DomainConflict("stub: falha simulada")
        self.cancelamentos_liberados.append((requisicao, list(itens_autorizados)))

    def aplicar_saidas_e_liberacoes_retirada(
        self, requisicao: Requisicao, itens_autorizados: list[ItemRequisicao]
    ) -> None:
        if self.deve_falhar_em == "aplicar_saidas_e_liberacoes_retirada":
            raise DomainConflict("stub: falha simulada")
        self.retiradas_aplicadas.append((requisicao, list(itens_autorizados)))


def criar_material(
    codigo: str, *, saldo_fisico: Decimal = Decimal("10"), is_active: bool = True
) -> Material:
    grupo_codigo, subgrupo_codigo, sequencial = codigo.split(".")
    grupo, _ = GrupoMaterial.objects.get_or_create(
        codigo_grupo=grupo_codigo,
        defaults={"nome": f"Grupo {grupo_codigo}"},
    )
    subgrupo, _ = SubgrupoMaterial.objects.get_or_create(
        grupo=grupo,
        codigo_subgrupo=subgrupo_codigo,
        defaults={"nome": f"Subgrupo {subgrupo_codigo}"},
    )
    material = Material.objects.create(
        subgrupo=subgrupo,
        codigo_completo=codigo,
        sequencial=sequencial,
        nome=f"Material {codigo}",
        unidade_medida="UN",
        is_active=is_active,
    )
    EstoqueMaterial.objects.create(
        material=material, saldo_fisico=saldo_fisico, saldo_reservado=Decimal("0")
    )
    return material
