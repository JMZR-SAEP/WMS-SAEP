from decimal import Decimal

import pytest

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.materials.services import importar_csv_scpi
from apps.stock.models import EstoqueMaterial, MovimentacaoEstoque, TipoMovimentacao


@pytest.mark.django_db
class TestImportarScpi:
    def test_importar_csv_cria_grupo_subgrupo_material_e_estoque_caminho_feliz(self):
        csv = (
            "CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            "001.002.003;Material Teste;UN;100;001;002;Grupo A;Subgrupo A;Descrição teste\n"
        ).encode()

        resultado = importar_csv_scpi(csv)

        assert resultado.grupos_criados == 1
        assert resultado.subgrupos_criados == 1
        assert resultado.materiais_criados == 1
        assert resultado.estoques_criados == 1
        assert len(resultado.erros) == 0

        grupo = GrupoMaterial.objects.get(codigo_grupo="001")
        assert grupo.nome == "Grupo A"

        subgrupo = SubgrupoMaterial.objects.get(codigo_subgrupo="002", grupo=grupo)
        assert subgrupo.nome == "Subgrupo A"

        material = Material.objects.get(codigo_completo="001.002.003")
        assert material.nome == "Material Teste"
        assert material.unidade_medida == "UN"
        assert material.descricao == "Descrição teste"

        estoque = EstoqueMaterial.objects.get(material=material)
        assert estoque.saldo_fisico == Decimal("100")
        assert estoque.saldo_reservado == Decimal("0")

    def test_importar_csv_tudo_ou_nada_erro_tecnico_nao_persiste_nada(self):
        from apps.materials.csv_parser import ScpiCsvParserError

        with pytest.raises(ScpiCsvParserError):
            importar_csv_scpi(b"arquivo_invalido")

        assert Material.objects.count() == 0
        assert GrupoMaterial.objects.count() == 0
        assert SubgrupoMaterial.objects.count() == 0
        assert EstoqueMaterial.objects.count() == 0

    def test_importar_csv_cria_movimentacao_saldo_inicial_para_cada_material(self):
        csv = (
            "CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            "001.002.003;Material Teste;UN;100;001;002;Grupo A;Subgrupo A;Descrição\n"
        ).encode()

        resultado = importar_csv_scpi(csv)

        assert resultado.materiais_criados == 1
        assert resultado.estoques_criados == 1

        movimentacoes = MovimentacaoEstoque.objects.filter(tipo=TipoMovimentacao.SALDO_INICIAL)
        assert movimentacoes.count() == 1

        mov = movimentacoes.first()
        assert mov.quantidade == Decimal("100")
        assert mov.saldo_anterior == Decimal("0")
        assert mov.saldo_posterior == Decimal("100")

    def test_importar_csv_multiplos_produtos(self):
        csv = (
            b"CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            b"001.002.003;Produto 1;UN;100;001;002;Grupo A;Subgrupo A;Desc 1\n"
            b"001.002.004;Produto 2;UN;50;001;002;Grupo A;Subgrupo A;Desc 2\n"
            b"005.006.007;Produto 3;UN;75;005;006;Grupo B;Subgrupo B;Desc 3\n"
        )

        resultado = importar_csv_scpi(csv)

        assert resultado.grupos_criados == 2
        assert resultado.subgrupos_criados == 2
        assert resultado.materiais_criados == 3
        assert resultado.estoques_criados == 3

        assert Material.objects.count() == 3
        assert EstoqueMaterial.objects.count() == 3

    def test_importar_csv_reutiliza_grupo_e_subgrupo_existentes(self):
        grupo = GrupoMaterial.objects.create(codigo_grupo="001", nome="Grupo Existente")
        SubgrupoMaterial.objects.create(
            grupo=grupo,
            codigo_subgrupo="002",
            nome="Subgrupo Existente",
        )

        csv = (
            b"CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            b"001.002.003;Produto 1;UN;100;001;002;Novo Nome Grupo;Novo Nome Subgrupo;Desc 1\n"
            b"001.002.004;Produto 2;UN;50;001;002;Novo Nome Grupo;Novo Nome Subgrupo;Desc 2\n"
        )

        resultado = importar_csv_scpi(csv)

        assert resultado.grupos_criados == 0
        assert resultado.subgrupos_criados == 0
        assert resultado.materiais_criados == 2

        assert GrupoMaterial.objects.count() == 1
        assert SubgrupoMaterial.objects.count() == 1

    def test_importar_csv_material_duplicado_levanta_erro(self):
        Material.objects.create(
            subgrupo=SubgrupoMaterial.objects.create(
                grupo=GrupoMaterial.objects.create(
                    codigo_grupo="001",
                    nome="Grupo",
                ),
                codigo_subgrupo="002",
                nome="Subgrupo",
            ),
            codigo_completo="001.002.003",
            sequencial="003",
            nome="Existente",
            unidade_medida="UN",
        )

        csv = (
            b"CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            b"001.002.003;Material Duplicado;UN;100;001;002;Grupo A;Subgrupo A;Desc\n"
        )

        with pytest.raises(ValueError, match="já existe"):
            importar_csv_scpi(csv)

        assert Material.objects.count() == 1

    def test_importar_csv_descricao_em_multiplas_linhas(self):
        csv = (
            "CADPRO;DISC1;UNID1;QUAN3;GRUPO;SUBGRUPO;NOMEGRUPO;NOMESUBGRUPO;DISCR1\n"
            "001.002.003;Material Teste;UN;100;001;002;Grupo A;Subgrupo A;Descrição linha 1\n"
            ";;;;;;;\n"
            ";;;;;;;;Descrição linha 2\n"
        ).encode()

        resultado = importar_csv_scpi(csv)

        assert resultado.materiais_criados == 1

        material = Material.objects.get(codigo_completo="001.002.003")
        assert "Descrição linha 1" in material.descricao
        assert "Descrição linha 2" in material.descricao
