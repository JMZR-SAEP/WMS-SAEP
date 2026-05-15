from decimal import Decimal

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.stock.models import EstoqueMaterial


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
