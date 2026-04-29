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
        assert "Descrição linha 1" in produtos[0].descricao
        assert "Descrição linha 2" in produtos[0].descricao
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

        with pytest.raises(ScpiCsvParserError, match="CADPRO inválido"):
            parse_scpi_csv(csv)

    def test_codigo_invalido_no_meio_levanta_erro(self):
        csv = (
            b"CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            b"001.002.003;Material Teste;UN;100;001;002;Grupo A;Subgrupo A;Desc\n"
            b"001-002-004;Material Invalido;UN;50;001;002;Grupo A;Subgrupo A;Desc\n"
        )

        with pytest.raises(ScpiCsvParserError, match="CADPRO inválido"):
            parse_scpi_csv(csv)

    def test_campo_obrigatorio_vazio_levanta_erro(self):
        csv = (
            b"CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            b"001.002.003;;UN;100;001;002;Grupo A;Subgrupo A;Desc\n"
        )

        with pytest.raises(
            ScpiCsvParserError,
            match=r"Produto 001\.002\.003: campo obrigatório faltando: DISC1",
        ):
            parse_scpi_csv(csv)

    def test_campo_obrigatorio_vazio_usa_linha_do_produto_logico(self):
        csv = (
            b"CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            b"000.021.304;CADO DE MADEIRA COM ROSCA;;6;000;021;GERAL;GERAL;;0;0;13012;000021304;Nao;;01/01/2015;;;;\n"
            b"000.021.514;TE PBA 110 X 110;PC;6;000;021;GERAL;GERAL;;0;0;13397;000021514;Nao;gaspar;29/10/2015 12:12:45;;;;\n"
        )

        with pytest.raises(
            ScpiCsvParserError,
            match=r"Erro ao processar produto na linha 2: Produto 000\.021\.304: campo obrigatório faltando: UNID1",
        ):
            parse_scpi_csv(csv)

    def test_descricao_com_newline_e_tail_na_linha_seguinte(self):
        csv = (
            "CADPRO;DISC1;UNID1;QUAN3;VAUN1;PRECOMEDIO;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1;QUANMIN;QUANMAX;CODREDUZ;CODBARRA;NOCULTAR;USUARIO;DTAINSERE;USUALT;DTAALT;LOCALFISICO;\n"
            "002.000.005;CABO FLEXÍVEL 2,5 MM² AZUL;M;150;0,73;0,73;002;000;MATERIAL ELETRICO; MATERIAL ELETRICO;Cabo de cobre flexível 2,5 mm² para tensões nominais até 450/750 V, formado por fios de cobre nu, eletrolítico, têmpera mole,\n"
            "encordoamento Classes 4 ou 5 (flexíveis), isolado com policloreto de vinila (PVC), tipo PVC/A para 70 ºC, antichama (BWF-B). Cor azul.;0;0;28983;002000005;Não;;01/01/2014;ALINE MAYRA DENOFRE;31/01/2025 13:24:10;;\n"
        ).encode()

        produtos = parse_scpi_csv(csv)

        assert len(produtos) == 1
        assert produtos[0].codigo_completo == "002.000.005"
        assert "têmpera mole," in produtos[0].descricao
        assert "encordoamento Classes 4 ou 5" in produtos[0].descricao
        assert produtos[0].grupo_codigo == "002"

    def test_disc1_com_multiplas_quebras_de_linha_e_tail_na_ultima_linha(self):
        csv = (
            "CADPRO;DISC1;UNID1;QUAN3;VAUN1;PRECOMEDIO;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1;QUANMIN;QUANMAX;CODREDUZ;CODBARRA;NOCULTAR;USUARIO;DTAINSERE;USUALT;DTAALT;LOCALFISICO;\n"
            "004.001.002;VÁLVULA DE ESFERA\n"
            "HIDRÁULICA ALTA PRESSÃO 3/4\n"
            " NPT T VH3V;UN;3;656,1;656,1;004;001;MATERIAL HIDRAULICO;REGISTROS E VÁLVULAS;Válvula De Esfera Hidráulica Alta Pressão 3/4 NPT T VH3V Tipo: Válvula de esfera para unidade hidráulica Modelo: VH3V-3/4 Vias: 3 Dimensão da Rosca: 3/4 Material (corpo/esfera/mandril): Aço carbono Conexão: Rosca NPT Aplicação: Controle de fluxo em sistemas hidráulicos de alta pressão Pressão máxima de trabalho: no mínimo 315 no máximo 500 bar Temperatura de operação: -20°C a 80°C Fluído: Água;0;0;31194;004001002;Não;ALINE MAYRA DENOFRE;05/02/2026 13:41:35;;;\n"
        ).encode()

        produtos = parse_scpi_csv(csv)

        assert len(produtos) == 1
        assert produtos[0].codigo_completo == "004.001.002"
        assert "VÁLVULA DE ESFERA" in produtos[0].nome
        assert "HIDRÁULICA ALTA PRESSÃO 3/4" in produtos[0].nome
        assert "NPT T VH3V" in produtos[0].nome
        assert produtos[0].unidade_medida == "UN"
