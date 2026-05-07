from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.materials.models import Material
from apps.requisitions.models import Requisicao, StatusRequisicao, TipoEvento
from apps.requisitions.seed_pilot_minimo import carregar_seed_pilot_minimo
from apps.stock.models import EstoqueMaterial
from apps.users.models import PapelChoices, User


@pytest.mark.django_db
class TestSeedPilotMinimoCommand:
    @override_settings(EPHEMERAL_ENVIRONMENT=False)
    def test_bloqueia_execucao_fora_de_ambiente_efemero(self):
        with pytest.raises(
            CommandError,
            match="Seed piloto mínima só pode ser executada em ambiente efêmero.",
        ):
            carregar_seed_pilot_minimo()

    def test_cria_cenario_minimo_oficial_para_validacao_manual_e_playwright(self):
        stdout = StringIO()

        call_command("seed_pilot_minimo", stdout=stdout)

        usuarios = {
            user.matricula_funcional: user
            for user in User.objects.select_related("setor").order_by("matricula_funcional")
        }
        assert set(usuarios) == {
            "91002",
            "auxiliar-almox",
            "auxiliar-setor-2",
            "chefe-almox",
            "chefe-setor",
            "chefe-setor-2",
            "inativo",
            "solicitante1",
            "solicitante2",
            "solicitante3",
            "super",
        }
        assert usuarios["91002"].papel == PapelChoices.AUXILIAR_SETOR
        assert usuarios["chefe-setor"].papel == PapelChoices.CHEFE_SETOR
        assert usuarios["chefe-setor-2"].papel == PapelChoices.CHEFE_SETOR
        assert usuarios["solicitante1"].papel == PapelChoices.SOLICITANTE
        assert usuarios["solicitante2"].papel == PapelChoices.SOLICITANTE
        assert usuarios["solicitante3"].papel == PapelChoices.SOLICITANTE
        assert usuarios["chefe-almox"].papel == PapelChoices.CHEFE_ALMOXARIFADO
        assert usuarios["auxiliar-almox"].papel == PapelChoices.AUXILIAR_ALMOXARIFADO
        assert usuarios["super"].is_superuser is True
        assert usuarios["super"].is_staff is True
        assert usuarios["super"].setor_id is None
        assert usuarios["super"].papel == PapelChoices.SOLICITANTE
        assert usuarios["inativo"].is_active is False

        materiais = {
            material.codigo_completo: material
            for material in Material.objects.select_related("estoque").order_by("codigo_completo")
        }
        assert set(materiais) == {
            "010.001.001",
            "010.001.002",
            "010.001.003",
            "010.001.004",
            "010.001.005",
            "010.001.006",
            "010.001.007",
        }
        assert materiais["010.001.001"].estoque.saldo_fisico == 50
        assert not hasattr(materiais["010.001.003"], "estoque")
        assert materiais["010.001.004"].is_active is False
        assert materiais["010.001.005"].estoque.saldo_fisico == 12
        assert materiais["010.001.006"].estoque.saldo_fisico == 19
        assert materiais["010.001.007"].estoque.saldo_fisico == 13

        requisicoes = list(
            Requisicao.objects.select_related(
                "criador",
                "beneficiario",
                "chefe_autorizador",
                "responsavel_atendimento",
            )
            .prefetch_related("itens__material", "eventos__usuario")
            .order_by("id")
        )
        assert len(requisicoes) == 14
        assert [requisicao.status for requisicao in requisicoes] == [
            StatusRequisicao.RASCUNHO,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            StatusRequisicao.AUTORIZADA,
            StatusRequisicao.ATENDIDA_PARCIALMENTE,
            StatusRequisicao.RASCUNHO,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            StatusRequisicao.RASCUNHO,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            StatusRequisicao.AUTORIZADA,
            StatusRequisicao.ATENDIDA_PARCIALMENTE,
            StatusRequisicao.RASCUNHO,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            StatusRequisicao.AUTORIZADA,
            StatusRequisicao.ATENDIDA,
        ]

        (
            rascunho,
            aguardando,
            autorizada_parcial,
            atendida_parcial,
            _rascunho_setor_secundario,
            _aguardando_setor_secundario,
            rascunho_manutencao_terceiro,
            _aguardando_manutencao,
            _autorizada_manutencao,
            _atendida_manutencao,
            _rascunho_manutencao_puro,
            _aguardando_secundario_terceiro,
            _autorizada_secundario,
            atendida_secundario,
        ) = requisicoes

        assert rascunho.criador_id != rascunho.beneficiario_id
        assert rascunho.criador.matricula_funcional == "91002"
        assert rascunho.beneficiario.matricula_funcional == "solicitante2"
        assert rascunho.numero_publico is None
        assert rascunho_manutencao_terceiro.criador.matricula_funcional == "91002"
        assert rascunho_manutencao_terceiro.beneficiario.matricula_funcional == "solicitante2"

        assert aguardando.numero_publico is not None
        assert autorizada_parcial.numero_publico is not None
        assert atendida_parcial.numero_publico is not None
        assert atendida_secundario.numero_publico is not None

        item_autorizado = autorizada_parcial.itens.get()
        assert item_autorizado.quantidade_autorizada < item_autorizado.quantidade_solicitada
        assert autorizada_parcial.chefe_autorizador.matricula_funcional == "chefe-setor"

        item_atendido = atendida_parcial.itens.get()
        assert item_atendido.quantidade_entregue < item_atendido.quantidade_autorizada
        assert atendida_parcial.responsavel_atendimento.matricula_funcional == "auxiliar-almox"

        material_baixo = materiais["010.001.002"]
        estoque_baixo = EstoqueMaterial.objects.get(material=material_baixo)
        assert estoque_baixo.saldo_fisico == 2
        assert estoque_baixo.saldo_reservado == 1

        assert "Seed piloto mínima carregada com sucesso" in stdout.getvalue()

    def test_seed_is_idempotent(self):
        call_command("seed_pilot_minimo")
        call_command("seed_pilot_minimo")

        assert User.objects.count() == 11
        assert Material.objects.count() == 7
        assert Requisicao.objects.count() == 14
        assert list(
            Requisicao.objects.filter(observacao__startswith="SEED_PILOT_MINIMO")
            .values_list("status", flat=True)
            .order_by("id")
        ) == [
            StatusRequisicao.RASCUNHO,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            StatusRequisicao.AUTORIZADA,
            StatusRequisicao.ATENDIDA_PARCIALMENTE,
            StatusRequisicao.RASCUNHO,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            StatusRequisicao.RASCUNHO,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            StatusRequisicao.AUTORIZADA,
            StatusRequisicao.ATENDIDA_PARCIALMENTE,
            StatusRequisicao.RASCUNHO,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            StatusRequisicao.AUTORIZADA,
            StatusRequisicao.ATENDIDA,
        ]

    def test_seed_reconcilia_beneficiario_do_cenario_secundario_terceiro(self):
        call_command("seed_pilot_minimo")

        requisicao = Requisicao.objects.get(
            observacao="SEED_PILOT_MINIMO:aguardando_secundario_terceiro"
        )
        beneficiario_errado = User.objects.get(matricula_funcional="solicitante2")
        Requisicao.objects.filter(pk=requisicao.pk).update(beneficiario=beneficiario_errado)

        call_command("seed_pilot_minimo")

        requisicao_corrigida = Requisicao.objects.get(
            observacao="SEED_PILOT_MINIMO:aguardando_secundario_terceiro"
        )
        assert requisicao_corrigida.status == StatusRequisicao.AGUARDANDO_AUTORIZACAO
        assert requisicao_corrigida.beneficiario.matricula_funcional == "solicitante3"
        assert requisicao_corrigida.setor_beneficiario == requisicao_corrigida.beneficiario.setor
        assert requisicao_corrigida.eventos.filter(tipo_evento=TipoEvento.RETORNO_RASCUNHO).exists()
        assert requisicao_corrigida.eventos.filter(
            tipo_evento=TipoEvento.REENVIO_AUTORIZACAO
        ).exists()

    def test_seed_reconcilia_aguardando_secundario_terceiro_quando_item_diverge(self):
        call_command("seed_pilot_minimo")

        requisicao = Requisicao.objects.get(
            observacao="SEED_PILOT_MINIMO:aguardando_secundario_terceiro"
        )
        material_errado = Material.objects.get(codigo_completo="010.001.001")
        requisicao.itens.update(
            material=material_errado,
            unidade_medida=material_errado.unidade_medida,
            quantidade_solicitada=Decimal("9"),
            observacao="Item divergente do seed",
        )

        call_command("seed_pilot_minimo")

        requisicao_corrigida = Requisicao.objects.get(
            observacao="SEED_PILOT_MINIMO:aguardando_secundario_terceiro"
        )
        item_corrigido = requisicao_corrigida.itens.get()

        assert requisicao_corrigida.status == StatusRequisicao.AGUARDANDO_AUTORIZACAO
        assert item_corrigido.material.codigo_completo == "010.001.007"
        assert item_corrigido.quantidade_solicitada == Decimal("2")
        assert item_corrigido.observacao == "Aguardando autorizacao com terceiro beneficiario"
        assert requisicao_corrigida.eventos.filter(tipo_evento=TipoEvento.RETORNO_RASCUNHO).exists()
        assert requisicao_corrigida.eventos.filter(
            tipo_evento=TipoEvento.REENVIO_AUTORIZACAO
        ).exists()

    def test_seed_reconcilia_rascunho_manutencao_terceiro_quando_item_diverge(self):
        call_command("seed_pilot_minimo")

        requisicao = Requisicao.objects.get(
            observacao="SEED_PILOT_MINIMO:rascunho_manutencao_terceiro"
        )
        beneficiario_errado = User.objects.get(matricula_funcional="solicitante1")
        material_errado = Material.objects.get(codigo_completo="010.001.001")
        requisicao.beneficiario = beneficiario_errado
        requisicao.setor_beneficiario = beneficiario_errado.setor
        requisicao.save(update_fields=["beneficiario", "setor_beneficiario", "updated_at"])
        requisicao.itens.update(
            material=material_errado,
            unidade_medida=material_errado.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            observacao="Item desatualizado do seed",
        )

        call_command("seed_pilot_minimo")

        requisicao_corrigida = Requisicao.objects.get(
            observacao="SEED_PILOT_MINIMO:rascunho_manutencao_terceiro"
        )
        item_corrigido = requisicao_corrigida.itens.get()

        assert requisicao_corrigida.beneficiario.matricula_funcional == "solicitante2"
        assert item_corrigido.material.codigo_completo == "010.001.006"
        assert item_corrigido.quantidade_solicitada == Decimal("1")
        assert item_corrigido.observacao == "Rascunho de manutencao com beneficiario de terceiro"
