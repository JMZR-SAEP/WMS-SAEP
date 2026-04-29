import csv
import re
from dataclasses import dataclass

CODIGO_SCPI_RE = re.compile(r"^\d{3}\.\d{3}\.\d{3}$")

CAMPOS_OBRIGATORIOS = [
    "CADPRO",
    "DISC1",
    "UNID1",
    "QUAN3",
    "GRUPO",
    "SUBGRUPO",
    "NOMEGRUPO",
    "NOMESUBGRUPO",
    "DISCR1",
]


@dataclass
class ProdutoLogico:
    codigo_completo: str
    nome: str
    unidade_medida: str
    saldo_fisico_inicial: str
    grupo_codigo: str
    subgrupo_codigo: str
    grupo_nome: str
    subgrupo_nome: str
    descricao: str

    @property
    def sequencial(self) -> str:
        return self.codigo_completo.split(".")[2]


class ScpiCsvParserError(Exception):
    pass


def parse_scpi_csv(conteudo_bytes: bytes) -> list[ProdutoLogico]:
    try:
        conteudo_str = conteudo_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ScpiCsvParserError(f"Erro ao decodificar CSV como UTF-8: {e}")

    linhas = conteudo_str.splitlines()
    if not linhas:
        raise ScpiCsvParserError("Arquivo CSV vazio")

    reader = csv.DictReader(
        linhas,
        delimiter=";",
    )

    if not reader.fieldnames:
        raise ScpiCsvParserError("Cabeçalho não encontrado no CSV")

    campos_faltantes = set(CAMPOS_OBRIGATORIOS) - set(reader.fieldnames or [])
    if campos_faltantes:
        raise ScpiCsvParserError(
            f"Cabeçalho incompleto. Campos faltantes: {', '.join(sorted(campos_faltantes))}"
        )

    produtos = []
    linha_logica_atual = None

    for idx, row in enumerate(reader, start=2):
        if not row or all(not v or not v.strip() for v in row.values()):
            continue

        codigo_completo = row.get("CADPRO", "").strip()

        if codigo_completo:
            if not CODIGO_SCPI_RE.match(codigo_completo):
                raise ScpiCsvParserError(f"Linha {idx}: código CADPRO inválido '{codigo_completo}'")

            if linha_logica_atual:
                try:
                    produtos.append(_montar_produto_logico(linha_logica_atual))
                except Exception as e:
                    raise ScpiCsvParserError(f"Erro ao processar produto na linha {idx}: {e}")

            linha_logica_atual = dict(row)
        else:
            if linha_logica_atual is None:
                raise ScpiCsvParserError(
                    f"Linha {idx}: continuação de descrição encontrada antes do primeiro produto"
                )

            descricao_anterior = linha_logica_atual.get("DISCR1", "")
            descricao_nova = row.get("DISCR1", "")
            if descricao_anterior and descricao_nova:
                linha_logica_atual["DISCR1"] = (descricao_anterior + " " + descricao_nova).strip()
            elif descricao_nova:
                linha_logica_atual["DISCR1"] = descricao_nova.strip()

    if linha_logica_atual:
        try:
            produtos.append(_montar_produto_logico(linha_logica_atual))
        except Exception as e:
            raise ScpiCsvParserError(f"Erro ao processar último produto: {e}")

    return produtos


def _montar_produto_logico(row: dict) -> ProdutoLogico:
    codigo_completo = row.get("CADPRO", "").strip()
    nome = row.get("DISC1", "").strip()
    unidade_medida = row.get("UNID1", "").strip()
    saldo_fisico_inicial = row.get("QUAN3", "").strip()
    grupo_codigo = row.get("GRUPO", "").strip()
    subgrupo_codigo = row.get("SUBGRUPO", "").strip()
    grupo_nome = row.get("NOMEGRUPO", "").strip()
    subgrupo_nome = row.get("NOMESUBGRUPO", "").strip()
    descricao = row.get("DISCR1", "").strip()

    if not all(
        [
            codigo_completo,
            nome,
            unidade_medida,
            saldo_fisico_inicial,
            grupo_codigo,
            subgrupo_codigo,
            grupo_nome,
            subgrupo_nome,
        ]
    ):
        raise ScpiCsvParserError(f"Produto {codigo_completo}: campos obrigatórios faltam")

    if not CODIGO_SCPI_RE.match(codigo_completo):
        raise ScpiCsvParserError(
            f"Código {codigo_completo} inválido (esperado formato xxx.yyy.zzz)"
        )

    return ProdutoLogico(
        codigo_completo=codigo_completo,
        nome=nome,
        unidade_medida=unidade_medida,
        saldo_fisico_inicial=saldo_fisico_inicial,
        grupo_codigo=grupo_codigo,
        subgrupo_codigo=subgrupo_codigo,
        grupo_nome=grupo_nome,
        subgrupo_nome=subgrupo_nome,
        descricao=descricao,
    )
