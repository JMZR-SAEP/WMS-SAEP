import pytest

from apps.materials.csv_parser import (
    ScpiCsvParserError,
    parse_scpi_csv,
)


class TestScpiCsvParser:
    def test_parse_csv_utf8_bom_lido_corretamente(self):
        csv_com_bom = (
            "﻿CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            "001.002.003;Material Teste;UN;100;001;002;Grupo A;Subgrupo A;Descrição teste\n"
        ).encode()

        produtos = parse_scpi_csv(csv_com_bom)

        assert len(produtos) == 1
        assert produtos[0].codigo_completo == "001.002.003"
        assert produtos[0].nome == "Material Teste"
        assert not produtos[0].codigo_completo.startswith("﻿")

    def test_produto_logico_simples_uma_linha(self):
        csv = (
            "CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            "001.002.003;Material Teste;UN;100;001;002;Grupo A;Subgrupo A;Descrição\n"
        ).encode()

        produtos = parse_scpi_csv(csv)

        assert len(produtos) == 1
        produto = produtos[0]
        assert produto.codigo_completo == "001.002.003"
        assert produto.nome == "Material Teste"
        assert produto.unidade_medida == "UN"
        assert produto.saldo_fisico_inicial == "100"
        assert produto.grupo_codigo == "001"
        assert produto.subgrupo_codigo == "002"
        assert produto.grupo_nome == "Grupo A"
        assert produto.subgrupo_nome == "Subgrupo A"
        assert produto.descricao == "Descrição"

    def test_produto_logico_com_descricao_em_multiplas_linhas(self):
        csv = (
            "CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            "001.002.003;Material Teste;UN;100;001;002;Grupo A;Subgrupo A;Descrição linha 1\n"
            ";;;;;;;\n"
            ";;;;;;;;Descrição linha 2\n"
            "005.006.007;Outro Material;UN;50;005;006;Grupo B;Subgrupo B;Outra desc\n"
        ).encode()

        produtos = parse_scpi_csv(csv)

        assert len(produtos) == 2
        assert produtos[0].codigo_completo == "001.002.003"
        assert "Descrição linha 1 Descrição linha 2" in produtos[0].descricao
        assert produtos[1].codigo_completo == "005.006.007"

    def test_cabecalho_ausente_levanta_erro(self):
        csv = b"001.002.003;Material Teste;UN;100;001;002;Grupo A;Subgrupo A;Desc\n"

        with pytest.raises(ScpiCsvParserError, match="Cabeçalho incompleto"):
            parse_scpi_csv(csv)

    def test_campo_obrigatorio_faltante_levanta_erro(self):
        csv = (
            b"CADPRO;DISC1;UNID1;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            b"001.002.003;Material Teste;UN;001;002;Grupo A;Subgrupo A;Desc\n"
        )

        with pytest.raises(ScpiCsvParserError, match="Cabeçalho incompleto"):
            parse_scpi_csv(csv)

    def test_arquivo_vazio_levanta_erro(self):
        csv = b""

        with pytest.raises(ScpiCsvParserError, match="vazio"):
            parse_scpi_csv(csv)

    def test_multiplos_produtos_logicos_reconstruidos(self):
        csv = (
            "CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            "001.002.003;Produto 1;UN;100;001;002;Grupo A;Subgrupo A;Descrição 1 parte 1\n"
            ";;;;;;;\n"
            ";;;;;;;;Descrição 1 parte 2\n"
            "005.006.007;Produto 2;UN;50;005;006;Grupo B;Subgrupo B;Descrição 2 parte 1\n"
            ";;;;;;;\n"
            ";;;;;;;;Descrição 2 parte 2\n"
            "009.010.011;Produto 3;UN;75;009;010;Grupo C;Subgrupo C;Descrição 3\n"
        ).encode()

        produtos = parse_scpi_csv(csv)

        assert len(produtos) == 3
        assert produtos[0].codigo_completo == "001.002.003"
        assert produtos[1].codigo_completo == "005.006.007"
        assert produtos[2].codigo_completo == "009.010.011"

    def test_codigo_invalido_levanta_erro(self):
        csv = (
            b"CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            b"001-002-003;Material Teste;UN;100;001;002;Grupo A;Subgrupo A;Desc\n"
        )

        with pytest.raises(ScpiCsvParserError, match="continuação"):
            parse_scpi_csv(csv)

    def test_campo_obrigatorio_vazio_levanta_erro(self):
        csv = (
            b"CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            b"001.002.003;;UN;100;001;002;Grupo A;Subgrupo A;Desc\n"
        )

        with pytest.raises(ScpiCsvParserError, match="faltam"):
            parse_scpi_csv(csv)
