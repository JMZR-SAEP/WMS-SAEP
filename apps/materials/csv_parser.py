import re
from dataclasses import dataclass

CODIGO_SCPI_RE = re.compile(r"^\d{3}\.\d{3}\.\d{3}$")
CODIGO_SCPI_PARECIDO_RE = re.compile(r"^[\d.\-/ ]+$")

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

    linhas = conteudo_str.splitlines(keepends=True)
    if not linhas:
        raise ScpiCsvParserError("Arquivo CSV vazio")

    cabecalho = _normalizar_cabecalho(linhas[0])
    if not cabecalho:
        raise ScpiCsvParserError("Cabeçalho não encontrado no CSV")

    campos_faltantes = set(CAMPOS_OBRIGATORIOS) - set(cabecalho)
    if campos_faltantes:
        raise ScpiCsvParserError(
            f"Cabeçalho incompleto. Campos faltantes: {', '.join(sorted(campos_faltantes))}"
        )

    produtos = []
    linha_logica_atual = None
    linha_logica_inicio = None
    indice_campo_aberto = None

    for idx, linha in enumerate(linhas[1:], start=2):
        if not linha.strip():
            continue

        codigo_completo = linha.split(";", 1)[0].strip()
        if CODIGO_SCPI_RE.match(codigo_completo):
            if linha_logica_atual is not None:
                produtos.append(
                    _finalizar_registro_logico(linha_logica_atual, linha_logica_inicio, cabecalho)
                )
            linha_logica_atual = _partes_para_dict(
                cabecalho, [parte.rstrip("\r") for parte in linha.split(";")]
            )
            indice_campo_aberto = _indice_ultimo_campo_preenchido(linha_logica_atual, cabecalho)
            linha_logica_inicio = idx
            continue

        if linha_logica_atual is None:
            if codigo_completo:
                raise ScpiCsvParserError(f"Linha {idx}: código CADPRO inválido '{codigo_completo}'")
            raise ScpiCsvParserError(
                f"Linha {idx}: continuação de descrição encontrada antes do primeiro produto"
            )

        if codigo_completo and CODIGO_SCPI_PARECIDO_RE.match(codigo_completo):
            raise ScpiCsvParserError(f"Linha {idx}: código CADPRO inválido '{codigo_completo}'")

        _mesclar_linha_continuacao(
            linha_logica_atual,
            cabecalho,
            indice_campo_aberto,
            linha,
        )

    if linha_logica_atual is not None:
        produtos.append(
            _finalizar_registro_logico(linha_logica_atual, linha_logica_inicio, cabecalho)
        )

    return produtos


def _normalizar_cabecalho(linha: str) -> list[str]:
    cabecalho = [campo.strip() for campo in linha.split(";")]
    while cabecalho and cabecalho[-1] == "":
        cabecalho.pop()
    return cabecalho


def _partes_para_dict(cabecalho: list[str], partes: list[str]) -> dict[str, str]:
    row = {}
    for indice, campo in enumerate(cabecalho):
        row[campo] = partes[indice].strip() if indice < len(partes) else ""
    return row


def _indice_ultimo_campo_preenchido(row: dict[str, str], cabecalho: list[str]) -> int | None:
    for indice in range(len(cabecalho) - 1, -1, -1):
        if row.get(cabecalho[indice], "").strip():
            return indice
    return None


def _mesclar_linha_continuacao(
    row: dict[str, str],
    cabecalho: list[str],
    indice_campo_aberto: int | None,
    linha: str,
) -> None:
    if indice_campo_aberto is None:
        return

    partes = [parte.rstrip("\r") for parte in linha.split(";")]
    indice_fragmento = next((i for i, valor in enumerate(partes) if valor.strip()), None)
    if indice_fragmento is None:
        return

    fragmento = partes[indice_fragmento].strip()
    if fragmento:
        campo_aberto = cabecalho[indice_campo_aberto]
        valor_atual = row.get(campo_aberto, "")
        row[campo_aberto] = f"{valor_atual}\n{fragmento}".strip() if valor_atual else fragmento

    for offset, campo in enumerate(cabecalho[indice_campo_aberto + 1 :], start=1):
        indice_parte = indice_fragmento + offset
        if indice_parte >= len(partes):
            break
        valor = partes[indice_parte].strip()
        if valor:
            row[campo] = valor


def _finalizar_registro_logico(
    linha_logica: dict[str, str] | str, linha_inicio: int | None, cabecalho: list[str]
) -> ProdutoLogico:
    if isinstance(linha_logica, dict):
        row = dict(linha_logica)
    else:
        partes = [parte.rstrip("\r") for parte in linha_logica.split(";")]
        if len(partes) < len(cabecalho):
            partes.extend([""] * (len(cabecalho) - len(partes)))
        elif len(partes) > len(cabecalho):
            partes = partes[: len(cabecalho)]
        row = _partes_para_dict(cabecalho, partes)

    codigo_completo = row.get("CADPRO", "").strip()
    if not codigo_completo:
        raise ScpiCsvParserError(
            f"Linha {linha_inicio}: continuação de descrição encontrada antes do primeiro produto"
        )

    if not CODIGO_SCPI_RE.match(codigo_completo):
        raise ScpiCsvParserError(
            f"Linha {linha_inicio}: código CADPRO inválido '{codigo_completo}'"
        )

    try:
        return _montar_produto_logico(row)
    except Exception as e:
        raise ScpiCsvParserError(f"Erro ao processar produto na linha {linha_inicio}: {e}")


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

    campos_obrigatorios = {
        "CADPRO": codigo_completo,
        "DISC1": nome,
        "UNID1": unidade_medida,
        "QUAN3": saldo_fisico_inicial,
        "GRUPO": grupo_codigo,
        "SUBGRUPO": subgrupo_codigo,
        "NOMEGRUPO": grupo_nome,
        "NOMESUBGRUPO": subgrupo_nome,
    }
    campos_faltantes = [campo for campo, valor in campos_obrigatorios.items() if not valor]
    if campos_faltantes:
        sufixo = (
            "campo obrigatório faltando"
            if len(campos_faltantes) == 1
            else "campos obrigatórios faltando"
        )
        raise ScpiCsvParserError(
            f"Produto {codigo_completo}: {sufixo}: {', '.join(campos_faltantes)}"
        )

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
