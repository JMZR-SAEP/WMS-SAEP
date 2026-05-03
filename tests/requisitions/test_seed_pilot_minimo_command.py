from io import StringIO

import pytest
from django.core.management import call_command

from apps.materials.models import Material
from apps.requisitions.models import Requisicao, StatusRequisicao
from apps.stock.models import EstoqueMaterial
from apps.users.models import PapelChoices, User


@pytest.mark.django_db
class TestSeedPilotMinimoCommand:
    def test_cria_cenario_minimo_oficial_para_validacao_manual_e_playwright(self):
        stdout = StringIO()

        call_command("seed_pilot_minimo", stdout=stdout)

        usuarios = {
            user.matricula_funcional: user
            for user in User.objects.select_related("setor").order_by("matricula_funcional")
        }
        assert set(usuarios) == {
            "91001",
            "91002",
            "91003",
            "91004",
            "91005",
            "91006",
            "91998",
            "91999",
        }
        assert usuarios["91001"].papel == PapelChoices.CHEFE_SETOR
        assert usuarios["91002"].papel == PapelChoices.AUXILIAR_SETOR
        assert usuarios["91003"].papel == PapelChoices.SOLICITANTE
        assert usuarios["91004"].papel == PapelChoices.SOLICITANTE
        assert usuarios["91005"].papel == PapelChoices.CHEFE_ALMOXARIFADO
        assert usuarios["91006"].papel == PapelChoices.AUXILIAR_ALMOXARIFADO
        assert usuarios["91998"].is_superuser is True
        assert usuarios["91998"].is_staff is True
        assert usuarios["91999"].is_active is False

        materiais = {
            material.codigo_completo: material
            for material in Material.objects.select_related("estoque").order_by("codigo_completo")
        }
        assert set(materiais) == {
            "010.001.001",
            "010.001.002",
            "010.001.003",
            "010.001.004",
        }
        assert materiais["010.001.001"].estoque.saldo_fisico == 50
        assert not hasattr(materiais["010.001.003"], "estoque")
        assert materiais["010.001.004"].is_active is False

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
        assert [requisicao.status for requisicao in requisicoes] == [
            StatusRequisicao.RASCUNHO,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            StatusRequisicao.AUTORIZADA,
            StatusRequisicao.ATENDIDA_PARCIALMENTE,
        ]

        rascunho, aguardando, autorizada_parcial, atendida_parcial = requisicoes

        assert rascunho.criador_id != rascunho.beneficiario_id
        assert rascunho.criador.matricula_funcional == "91002"
        assert rascunho.beneficiario.matricula_funcional == "91004"

        assert aguardando.numero_publico is not None

        item_autorizado = autorizada_parcial.itens.get()
        assert item_autorizado.quantidade_autorizada < item_autorizado.quantidade_solicitada
        assert autorizada_parcial.chefe_autorizador.matricula_funcional == "91001"

        item_atendido = atendida_parcial.itens.get()
        assert item_atendido.quantidade_entregue < item_atendido.quantidade_autorizada
        assert atendida_parcial.responsavel_atendimento.matricula_funcional == "91006"

        material_baixo = materiais["010.001.002"]
        estoque_baixo = EstoqueMaterial.objects.get(material=material_baixo)
        assert estoque_baixo.saldo_fisico == 2
        assert estoque_baixo.saldo_reservado == 1

        assert "Seed piloto mínima carregada com sucesso" in stdout.getvalue()
