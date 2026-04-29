import re
from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction

from apps.materials.csv_parser import (
    ScpiCsvParserError,
    parse_scpi_csv,
)
from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.stock.services import registrar_saldo_inicial


def criar_material(
    *,
    codigo_completo: str,
    nome: str,
    unidade_medida: str,
    subgrupo: SubgrupoMaterial,
    sequencial: str,
    descricao: str = "",
) -> Material:
    """Cria um Material com validação de coerência SCPI via full_clean().

    Fonte canônica para criação de materiais (importação, admin, futuras APIs).
    Levanta ValidationError se houver inconsistência de código/subgrupo/sequencial.
    NÃO cria EstoqueMaterial — responsabilidade do chamador.
    """
    nome_normalizado = re.sub(r"\s+", " ", nome.replace("\r", " ").replace("\n", " ")).strip()

    material = Material(
        codigo_completo=codigo_completo,
        nome=nome_normalizado,
        unidade_medida=unidade_medida,
        subgrupo=subgrupo,
        sequencial=sequencial,
        descricao=descricao,
    )
    material.full_clean()
    material.save()
    return material


@dataclass
class ResultadoImportacao:
    grupos_criados: int = 0
    subgrupos_criados: int = 0
    materiais_criados: int = 0
    estoques_criados: int = 0
    erros: list[str] = field(default_factory=list)


def _parse_decimal_scpi(valor: str) -> Decimal:
    valor_normalizado = valor.strip().replace(".", "").replace(",", ".")
    return Decimal(valor_normalizado)


def importar_csv_scpi(conteudo_bytes: bytes) -> ResultadoImportacao:
    """Orquestra a importação de carga inicial do CSV SCPI.

    Regra tudo-ou-nada: toda a operação ocorre dentro de transaction.atomic().
    Em caso de ScpiCsvParserError ou qualquer exceção, levanta e desfaz tudo.

    Fluxo por produto:
      1. get_or_create GrupoMaterial
      2. get_or_create SubgrupoMaterial
      3. criar_material() para cada produto lógico
      4. registrar_saldo_inicial() no stock.services

    Escopo piloto: carga inicial apenas — materiais duplicados levantam erro.
    """
    try:
        produtos = parse_scpi_csv(conteudo_bytes)
    except ScpiCsvParserError as e:
        raise ScpiCsvParserError(f"Erro ao normalizar CSV: {e}") from e

    resultado = ResultadoImportacao()

    with transaction.atomic():
        for produto in produtos:
            try:
                grupo, grupo_criado = GrupoMaterial.objects.get_or_create(
                    codigo_grupo=produto.grupo_codigo,
                    defaults={"nome": produto.grupo_nome},
                )
                if grupo_criado:
                    resultado.grupos_criados += 1

                subgrupo, subgrupo_criado = SubgrupoMaterial.objects.get_or_create(
                    grupo=grupo,
                    codigo_subgrupo=produto.subgrupo_codigo,
                    defaults={"nome": produto.subgrupo_nome},
                )
                if subgrupo_criado:
                    resultado.subgrupos_criados += 1

                if Material.objects.filter(codigo_completo=produto.codigo_completo).exists():
                    raise ValueError(
                        f"Material {produto.codigo_completo} já existe (piloto: sem reimportação)"
                    )

                material = criar_material(
                    codigo_completo=produto.codigo_completo,
                    nome=produto.nome,
                    unidade_medida=produto.unidade_medida,
                    subgrupo=subgrupo,
                    sequencial=produto.sequencial,
                    descricao=produto.descricao,
                )
                resultado.materiais_criados += 1

                quantidade = _parse_decimal_scpi(produto.saldo_fisico_inicial)
                registrar_saldo_inicial(
                    material=material,
                    quantidade=quantidade,
                )
                resultado.estoques_criados += 1

            except Exception as e:
                resultado.erros.append(f"Erro ao importar {produto.codigo_completo}: {str(e)}")
                raise

    return resultado
