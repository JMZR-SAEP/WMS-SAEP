from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.core.api.exceptions import DomainConflict
from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.requisitions.models import ItemRequisicao, Requisicao, StatusRequisicao
from apps.stock.models import EstoqueMaterial, MovimentacaoEstoque, TipoMovimentacao
from apps.stock.services import (
    registrar_reserva_por_autorizacao,
    registrar_saida_por_atendimento,
    registrar_saldo_inicial,
)
from apps.users.models import PapelChoices, Setor, User


@pytest.mark.django_db
class TestRegistrarSaldoInicial:
    @staticmethod
    def _criar_material():
        grupo = GrupoMaterial.objects.create(
            codigo_grupo="001",
            nome="Grupo Teste",
        )
        subgrupo = SubgrupoMaterial.objects.create(
            grupo=grupo,
            codigo_subgrupo="002",
            nome="Subgrupo Teste",
        )
        material = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="001.002.003",
            sequencial="003",
            nome="Material Teste",
            unidade_medida="UN",
        )
        return material

    def test_registrar_saldo_inicial_cria_estoque_com_quantidade_correta(self):
        material = self._criar_material()
        quantidade = Decimal("100.000")

        estoque, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=quantidade,
        )

        assert estoque.id is not None
        assert estoque.material == material
        assert estoque.saldo_fisico == quantidade
        assert estoque.saldo_reservado == Decimal("0")

        estoque_recuperado = EstoqueMaterial.objects.get(material=material)
        assert estoque_recuperado.saldo_fisico == quantidade

    def test_registrar_saldo_inicial_cria_movimentacao_tipo_saldo_inicial(self):
        material = self._criar_material()
        quantidade = Decimal("100.000")

        estoque, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=quantidade,
        )

        assert movimentacao.id is not None
        assert movimentacao.material == material
        assert movimentacao.tipo == TipoMovimentacao.SALDO_INICIAL
        assert movimentacao.quantidade == quantidade
        assert movimentacao.saldo_anterior == Decimal("0")
        assert movimentacao.saldo_posterior == quantidade

    def test_registrar_saldo_inicial_saldo_reservado_zero(self):
        material = self._criar_material()

        estoque, _ = registrar_saldo_inicial(
            material=material,
            quantidade=Decimal("50.000"),
        )

        assert estoque.saldo_disponivel == Decimal("50.000")
        assert estoque.saldo_reservado == Decimal("0")

    def test_registrar_saldo_inicial_levanta_se_estoque_ja_existe(self):
        material = self._criar_material()
        EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=Decimal("50"),
            saldo_reservado=Decimal("0"),
        )

        with pytest.raises(ValueError, match="já existe"):
            registrar_saldo_inicial(
                material=material,
                quantidade=Decimal("100"),
            )

    def test_registrar_saldo_inicial_levanta_se_quantidade_negativa(self):
        material = self._criar_material()

        with pytest.raises(ValueError, match="não pode ser negativa"):
            registrar_saldo_inicial(
                material=material,
                quantidade=Decimal("-10"),
            )

    def test_registrar_saldo_inicial_quantidade_zero_permitida(self):
        material = self._criar_material()

        estoque, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=Decimal("0"),
        )

        assert estoque.saldo_fisico == Decimal("0")
        assert movimentacao.quantidade == Decimal("0")

    def test_movimentacao_tem_saldo_anterior_zero_e_posterior_igual_quantidade(self):
        material = self._criar_material()
        quantidade = Decimal("75.500")

        _, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=quantidade,
        )

        assert movimentacao.saldo_anterior == Decimal("0")
        assert movimentacao.saldo_posterior == quantidade
        assert movimentacao.observacao == ""

    def test_movimentacao_nao_pode_ser_atualizada_por_save(self):
        material = self._criar_material()
        _, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=Decimal("75.500"),
        )

        movimentacao.quantidade = Decimal("80.000")

        with pytest.raises(ValueError, match="imutáveis"):
            movimentacao.save()

    def test_movimentacao_nao_pode_ser_removida_por_delete(self):
        material = self._criar_material()
        _, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=Decimal("75.500"),
        )

        with pytest.raises(ValueError, match="não podem ser removidas"):
            movimentacao.delete()

    def test_movimentacao_nao_pode_ser_atualizada_por_queryset_update(self):
        material = self._criar_material()
        _, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=Decimal("75.500"),
        )

        with pytest.raises(ValueError, match="imutáveis"):
            MovimentacaoEstoque.objects.filter(pk=movimentacao.pk).update(
                quantidade=Decimal("80.000")
            )

    def test_movimentacao_nao_pode_ser_atualizada_por_bulk_update(self):
        material = self._criar_material()
        _, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=Decimal("75.500"),
        )

        movimentacao.quantidade = Decimal("80.000")

        with pytest.raises(ValueError, match="imutáveis"):
            MovimentacaoEstoque.objects.bulk_update([movimentacao], ["quantidade"])

    def test_movimentacao_nao_pode_ser_removida_por_queryset_delete(self):
        material = self._criar_material()
        _, movimentacao = registrar_saldo_inicial(
            material=material,
            quantidade=Decimal("75.500"),
        )

        with pytest.raises(ValueError, match="não podem ser removidas"):
            MovimentacaoEstoque.objects.filter(pk=movimentacao.pk).delete()

    def test_movimentacao_saldo_inicial_precisa_ser_coerente_no_banco(self):
        material = self._criar_material()

        with pytest.raises(ValidationError):
            MovimentacaoEstoque.objects.create(
                material=material,
                tipo=TipoMovimentacao.SALDO_INICIAL,
                quantidade=Decimal("75.500"),
                saldo_anterior=Decimal("10.000"),
                saldo_posterior=Decimal("85.500"),
            )

    def test_movimentacao_reserva_rejeita_requisicao_material_inconsistentes(self):
        chefe = User.objects.create(
            matricula_funcional="99001",
            nome_completo="Chefe Estoque",
            papel=PapelChoices.CHEFE_SETOR,
            is_active=True,
        )
        setor = Setor.objects.create(nome="Setor Estoque", chefe_responsavel=chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        material_a = self._criar_material()
        grupo = material_a.subgrupo.grupo
        subgrupo = SubgrupoMaterial.objects.create(
            grupo=grupo,
            codigo_subgrupo="004",
            nome="Subgrupo B",
        )
        material_b = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="001.004.001",
            sequencial="001",
            nome="Material B",
            unidade_medida="UN",
        )
        EstoqueMaterial.objects.create(
            material=material_a,
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("0"),
        )
        EstoqueMaterial.objects.create(
            material=material_b,
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("0"),
        )
        requisicao_a = Requisicao.objects.create(
            criador=chefe,
            beneficiario=chefe,
            setor_beneficiario=setor,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        )
        requisicao_b = Requisicao.objects.create(
            criador=chefe,
            beneficiario=chefe,
            setor_beneficiario=setor,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        )
        item_a = ItemRequisicao.objects.create(
            requisicao=requisicao_a,
            material=material_a,
            unidade_medida=material_a.unidade_medida,
            quantidade_solicitada=Decimal("2.000"),
        )

        with pytest.raises(ValidationError):
            MovimentacaoEstoque.objects.create(
                requisicao=requisicao_b,
                item_requisicao=item_a,
                material=material_b,
                tipo=TipoMovimentacao.RESERVA_POR_AUTORIZACAO,
                quantidade=Decimal("2.000"),
                saldo_anterior=Decimal("10.000"),
                saldo_posterior=Decimal("10.000"),
                saldo_reservado_anterior=Decimal("0.000"),
                saldo_reservado_posterior=Decimal("2.000"),
                observacao="Reserva inconsistente",
            )

    def test_movimentacao_bulk_create_valida_invariantes(self):
        chefe = User.objects.create(
            matricula_funcional="99002",
            nome_completo="Chefe Estoque 2",
            papel=PapelChoices.CHEFE_SETOR,
            is_active=True,
        )
        setor = Setor.objects.create(nome="Setor Estoque 2", chefe_responsavel=chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        material_a = self._criar_material()
        grupo = material_a.subgrupo.grupo
        subgrupo = SubgrupoMaterial.objects.create(
            grupo=grupo,
            codigo_subgrupo="005",
            nome="Subgrupo C",
        )
        material_b = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="001.005.001",
            sequencial="001",
            nome="Material C",
            unidade_medida="UN",
        )
        requisicao = Requisicao.objects.create(
            criador=chefe,
            beneficiario=chefe,
            setor_beneficiario=setor,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        )
        item = ItemRequisicao.objects.create(
            requisicao=requisicao,
            material=material_a,
            unidade_medida=material_a.unidade_medida,
            quantidade_solicitada=Decimal("2.000"),
        )

        with pytest.raises(ValidationError):
            MovimentacaoEstoque.objects.bulk_create(
                [
                    MovimentacaoEstoque(
                        requisicao=requisicao,
                        item_requisicao=item,
                        material=material_b,
                        tipo=TipoMovimentacao.RESERVA_POR_AUTORIZACAO,
                        quantidade=Decimal("2.000"),
                        saldo_anterior=Decimal("10.000"),
                        saldo_posterior=Decimal("10.000"),
                        saldo_reservado_anterior=Decimal("0.000"),
                        saldo_reservado_posterior=Decimal("2.000"),
                        observacao="Reserva inconsistente em lote",
                    )
                ]
            )

    def test_registrar_reserva_rejeita_quantidade_nao_positiva(self):
        chefe = User.objects.create(
            matricula_funcional="99003",
            nome_completo="Chefe Estoque 3",
            papel=PapelChoices.CHEFE_SETOR,
            is_active=True,
        )
        setor = Setor.objects.create(nome="Setor Estoque 3", chefe_responsavel=chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        material = self._criar_material()
        estoque = EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=chefe,
            beneficiario=chefe,
            setor_beneficiario=setor,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        )
        item = ItemRequisicao.objects.create(
            requisicao=requisicao,
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2.000"),
        )

        with pytest.raises(DomainConflict):
            registrar_reserva_por_autorizacao(
                requisicao=requisicao,
                item=item,
                quantidade=Decimal("0"),
            )
        with pytest.raises(DomainConflict):
            registrar_reserva_por_autorizacao(
                requisicao=requisicao,
                item=item,
                quantidade=Decimal("-1"),
            )

        estoque.refresh_from_db()
        assert estoque.saldo_reservado == Decimal("3")
        assert MovimentacaoEstoque.objects.count() == 0

    def test_registrar_saida_por_atendimento_baixa_fisico_e_reserva(self):
        chefe = User.objects.create(
            matricula_funcional="99004",
            nome_completo="Chefe Estoque 4",
            papel=PapelChoices.CHEFE_SETOR,
            is_active=True,
        )
        setor = Setor.objects.create(nome="Setor Estoque 4", chefe_responsavel=chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        material = self._criar_material()
        estoque = EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("4"),
        )
        requisicao = Requisicao.objects.create(
            criador=chefe,
            beneficiario=chefe,
            setor_beneficiario=setor,
            status=StatusRequisicao.AUTORIZADA,
        )
        item = ItemRequisicao.objects.create(
            requisicao=requisicao,
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("4.000"),
            quantidade_autorizada=Decimal("4.000"),
        )

        _, movimentacao = registrar_saida_por_atendimento(
            requisicao=requisicao,
            item=item,
            quantidade=Decimal("4"),
        )

        estoque.refresh_from_db()
        assert estoque.saldo_fisico == Decimal("6")
        assert estoque.saldo_reservado == Decimal("0")
        assert movimentacao.tipo == TipoMovimentacao.SAIDA_POR_ATENDIMENTO
        assert movimentacao.saldo_anterior == Decimal("10")
        assert movimentacao.saldo_posterior == Decimal("6")
        assert movimentacao.saldo_reservado_anterior == Decimal("4")
        assert movimentacao.saldo_reservado_posterior == Decimal("0")

    def test_registrar_saida_rejeita_saldo_fisico_ou_reserva_insuficiente(self):
        chefe = User.objects.create(
            matricula_funcional="99005",
            nome_completo="Chefe Estoque 5",
            papel=PapelChoices.CHEFE_SETOR,
            is_active=True,
        )
        setor = Setor.objects.create(nome="Setor Estoque 5", chefe_responsavel=chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        material = self._criar_material()
        estoque = EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=Decimal("3"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=chefe,
            beneficiario=chefe,
            setor_beneficiario=setor,
            status=StatusRequisicao.AUTORIZADA,
        )
        item = ItemRequisicao.objects.create(
            requisicao=requisicao,
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("4.000"),
            quantidade_autorizada=Decimal("4.000"),
        )

        with pytest.raises(DomainConflict):
            registrar_saida_por_atendimento(
                requisicao=requisicao,
                item=item,
                quantidade=Decimal("4"),
            )
        with pytest.raises(DomainConflict):
            registrar_saida_por_atendimento(
                requisicao=requisicao,
                item=item,
                quantidade=Decimal("3"),
            )

        estoque.refresh_from_db()
        assert estoque.saldo_fisico == Decimal("3")
        assert estoque.saldo_reservado == Decimal("2")
        assert MovimentacaoEstoque.objects.count() == 0
