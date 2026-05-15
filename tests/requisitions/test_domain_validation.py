from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from apps.core.api.exceptions import DomainConflict
from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.requisitions.domain.types import ItemAutorizacaoData, ItemRascunhoData
from apps.requisitions.domain.validation import (
    _material_e_estoque_validos,
    _validar_itens_autorizacao,
    _validar_itens_rascunho,
)
from apps.requisitions.models import Requisicao, StatusRequisicao
from apps.users.models import PapelChoices, Setor, User
from tests.requisitions.helpers import criar_material


@pytest.mark.django_db
class TestMaterialEEstoqueValidos:
    def test_caminho_feliz(self):
        material = criar_material("001.001.001")
        _material_e_estoque_validos(material=material, quantidade_solicitada=Decimal("5"))

    def test_material_inativo(self):
        material = criar_material("001.001.002", is_active=False)
        with pytest.raises(DomainConflict):
            _material_e_estoque_validos(material=material, quantidade_solicitada=Decimal("1"))

    def test_material_sem_estoque(self):
        grupo, _ = GrupoMaterial.objects.get_or_create(codigo_grupo="001", defaults={"nome": "G1"})
        sub, _ = SubgrupoMaterial.objects.get_or_create(
            grupo=grupo, codigo_subgrupo="001", defaults={"nome": "S1"}
        )
        material = Material.objects.create(
            subgrupo=sub,
            codigo_completo="001.001.003",
            sequencial="003",
            nome="Sem Estoque",
            unidade_medida="UN",
            is_active=True,
        )
        with pytest.raises(DomainConflict):
            _material_e_estoque_validos(material=material, quantidade_solicitada=Decimal("1"))

    def test_saldo_zero(self):
        material = criar_material("001.001.004", saldo_fisico=Decimal("0"))
        material.refresh_from_db()
        material = Material.objects.select_related("estoque").get(pk=material.pk)
        with pytest.raises(DomainConflict):
            _material_e_estoque_validos(material=material, quantidade_solicitada=Decimal("1"))

    def test_quantidade_excede_saldo(self):
        material = criar_material("001.001.005", saldo_fisico=Decimal("5"))
        material = Material.objects.select_related("estoque").get(pk=material.pk)
        with pytest.raises(DomainConflict):
            _material_e_estoque_validos(material=material, quantidade_solicitada=Decimal("999"))


@pytest.mark.django_db
class TestValidarItensRascunho:
    def test_caminho_feliz(self):
        material = criar_material("002.001.001")
        itens = [ItemRascunhoData(material_id=material.pk, quantidade_solicitada=Decimal("3"))]
        result = _validar_itens_rascunho(itens)
        assert len(result) == 1
        assert result[0].pk == material.pk

    def test_lista_vazia(self):
        with pytest.raises(ValidationError) as exc:
            _validar_itens_rascunho([])
        assert "itens" in exc.value.detail

    def test_material_duplicado(self):
        material = criar_material("002.001.002")
        itens = [
            ItemRascunhoData(material_id=material.pk, quantidade_solicitada=Decimal("1")),
            ItemRascunhoData(material_id=material.pk, quantidade_solicitada=Decimal("2")),
        ]
        with pytest.raises(ValidationError) as exc:
            _validar_itens_rascunho(itens)
        assert "itens" in exc.value.detail

    def test_material_inexistente(self):
        itens = [ItemRascunhoData(material_id=999999, quantidade_solicitada=Decimal("1"))]
        with pytest.raises(ValidationError) as exc:
            _validar_itens_rascunho(itens)
        assert "itens" in exc.value.detail

    def test_quantidade_zero(self):
        material = criar_material("002.001.003")
        itens = [ItemRascunhoData(material_id=material.pk, quantidade_solicitada=Decimal("0"))]
        with pytest.raises(ValidationError) as exc:
            _validar_itens_rascunho(itens)
        assert "itens" in exc.value.detail

    def test_quantidade_negativa(self):
        material = criar_material("002.001.004")
        itens = [ItemRascunhoData(material_id=material.pk, quantidade_solicitada=Decimal("-1"))]
        with pytest.raises(ValidationError) as exc:
            _validar_itens_rascunho(itens)
        assert "itens" in exc.value.detail

    def test_material_inativo(self):
        material = criar_material("002.001.005", is_active=False)
        itens = [ItemRascunhoData(material_id=material.pk, quantidade_solicitada=Decimal("1"))]
        with pytest.raises(DomainConflict):
            _validar_itens_rascunho(itens)

    def test_quantidade_excede_saldo(self):
        material = criar_material("002.001.006", saldo_fisico=Decimal("5"))
        itens = [ItemRascunhoData(material_id=material.pk, quantidade_solicitada=Decimal("999"))]
        with pytest.raises(DomainConflict):
            _validar_itens_rascunho(itens)


@pytest.mark.django_db
class TestValidarItensAutorizacao:
    @staticmethod
    def _criar_setor(nome: str, chefe_matricula: str) -> Setor:
        chefe = User.objects.create(
            matricula_funcional=chefe_matricula,
            nome_completo=f"Chefe {nome}",
            papel=PapelChoices.CHEFE_SETOR,
            is_active=True,
        )
        setor = Setor.objects.create(nome=nome, chefe_responsavel=chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        return setor

    def _criar_requisicao_com_item(self, quantidade_solicitada: Decimal = Decimal("10")):
        setor = self._criar_setor("Setor Val", "99001")
        solicitante = User.objects.create(
            matricula_funcional="99002",
            nome_completo="Solicitante",
            papel=PapelChoices.SOLICITANTE,
            setor=setor,
            is_active=True,
        )
        material = criar_material("003.001.001")
        req = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-990001",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        item = req.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=quantidade_solicitada,
        )
        return req, item

    def test_caminho_feliz(self):
        _, item = self._criar_requisicao_com_item(quantidade_solicitada=Decimal("10"))
        itens_data = [ItemAutorizacaoData(item_id=item.pk, quantidade_autorizada=Decimal("10"))]
        result = _validar_itens_autorizacao(itens_requisicao=[item], itens=itens_data)
        assert item.pk in result

    def test_lista_vazia(self):
        _, item = self._criar_requisicao_com_item()
        with pytest.raises(ValidationError) as exc:
            _validar_itens_autorizacao(itens_requisicao=[item], itens=[])
        assert "itens" in exc.value.detail

    def test_item_duplicado(self):
        _, item = self._criar_requisicao_com_item()
        itens_data = [
            ItemAutorizacaoData(item_id=item.pk, quantidade_autorizada=Decimal("3")),
            ItemAutorizacaoData(item_id=item.pk, quantidade_autorizada=Decimal("2")),
        ]
        with pytest.raises(ValidationError) as exc:
            _validar_itens_autorizacao(itens_requisicao=[item], itens=itens_data)
        assert "itens" in exc.value.detail

    def test_item_ausente_na_requisicao(self):
        _, item = self._criar_requisicao_com_item()
        itens_data = [ItemAutorizacaoData(item_id=999999, quantidade_autorizada=Decimal("5"))]
        with pytest.raises(ValidationError) as exc:
            _validar_itens_autorizacao(itens_requisicao=[item], itens=itens_data)
        assert "itens" in exc.value.detail

    def test_item_extra_nao_pertence_a_requisicao(self):
        _, item = self._criar_requisicao_com_item()
        itens_data = [
            ItemAutorizacaoData(item_id=item.pk, quantidade_autorizada=Decimal("5")),
            ItemAutorizacaoData(item_id=item.pk + 999, quantidade_autorizada=Decimal("2")),
        ]
        with pytest.raises(ValidationError) as exc:
            _validar_itens_autorizacao(itens_requisicao=[item], itens=itens_data)
        assert "itens" in exc.value.detail

    def test_quantidade_autorizada_negativa(self):
        _, item = self._criar_requisicao_com_item()
        itens_data = [ItemAutorizacaoData(item_id=item.pk, quantidade_autorizada=Decimal("-1"))]
        with pytest.raises(ValidationError) as exc:
            _validar_itens_autorizacao(itens_requisicao=[item], itens=itens_data)
        assert "itens" in exc.value.detail

    def test_quantidade_autorizada_maior_que_solicitada(self):
        _, item = self._criar_requisicao_com_item(quantidade_solicitada=Decimal("5"))
        itens_data = [ItemAutorizacaoData(item_id=item.pk, quantidade_autorizada=Decimal("10"))]
        with pytest.raises(ValidationError) as exc:
            _validar_itens_autorizacao(itens_requisicao=[item], itens=itens_data)
        assert "itens" in exc.value.detail

    def test_autorizacao_parcial_sem_justificativa(self):
        _, item = self._criar_requisicao_com_item(quantidade_solicitada=Decimal("10"))
        itens_data = [ItemAutorizacaoData(item_id=item.pk, quantidade_autorizada=Decimal("5"))]
        with pytest.raises(ValidationError) as exc:
            _validar_itens_autorizacao(itens_requisicao=[item], itens=itens_data)
        assert "itens" in exc.value.detail

    def test_todos_itens_com_quantidade_zero(self):
        _, item = self._criar_requisicao_com_item()
        itens_data = [
            ItemAutorizacaoData(
                item_id=item.pk,
                quantidade_autorizada=Decimal("0"),
                justificativa_autorizacao_parcial="motivo",
            )
        ]
        with pytest.raises(DomainConflict):
            _validar_itens_autorizacao(itens_requisicao=[item], itens=itens_data)

    def test_autorizacao_parcial_com_justificativa(self):
        _, item = self._criar_requisicao_com_item(quantidade_solicitada=Decimal("10"))
        itens_data = [
            ItemAutorizacaoData(
                item_id=item.pk,
                quantidade_autorizada=Decimal("5"),
                justificativa_autorizacao_parcial="estoque insuficiente",
            )
        ]
        result = _validar_itens_autorizacao(itens_requisicao=[item], itens=itens_data)
        assert item.pk in result
