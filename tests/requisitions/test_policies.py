"""
Testes das funções de policy de object-level em apps/requisitions/policies.py.

Cobre invariantes PER-01 a PER-08 na perspectiva requisição+usuário:
- pode_visualizar_requisicao
- pode_manipular_pre_autorizacao
- pode_cancelar_autorizada
- pode_autorizar_requisicao
- pode_atender_requisicao
- pode_retirar_requisicao
- pode_criar_requisicao_para (via requisitions.policies — interface exclusiva)
"""

import pytest

from apps.requisitions.models import Requisicao, StatusRequisicao
from apps.requisitions.policies import (
    pode_atender_requisicao,
    pode_autorizar_requisicao,
    pode_cancelar_autorizada,
    pode_criar_requisicao_para,
    pode_manipular_pre_autorizacao,
    pode_retirar_requisicao,
    pode_visualizar_requisicao,
    queryset_fila_atendimento,
    queryset_fila_autorizacao,
)
from apps.users.models import PapelChoices, Setor, User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(matricula, papel=PapelChoices.SOLICITANTE, setor=None, *, is_active=True):
    return User.objects.create_user(
        matricula_funcional=matricula,
        password="testpass123",
        nome_completo=f"Usuário {matricula}",
        papel=papel,
        setor=setor,
        is_active=is_active,
    )


def _setor(nome, chefe):
    return Setor.objects.create(nome=nome, chefe_responsavel=chefe)


def _requisicao(criador, beneficiario, setor_beneficiario, status=StatusRequisicao.RASCUNHO):
    return Requisicao.objects.create(
        criador=criador,
        beneficiario=beneficiario,
        setor_beneficiario=setor_beneficiario,
        status=status,
    )


# ---------------------------------------------------------------------------
# 1. pode_criar_requisicao_para — importado de requisitions.policies (PER-01)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPodeCriarRequisicaoParaViaRequisitionsPolicies:
    """Garante que pode_criar_requisicao_para é acessível via requisitions.policies."""

    def test_solicitante_pode_criar_para_si(self):
        user = _user("P001")
        assert pode_criar_requisicao_para(user, user) is True

    def test_solicitante_nao_pode_criar_para_terceiro(self):
        user = _user("P002")
        outro = _user("P003")
        assert pode_criar_requisicao_para(user, outro) is False

    def test_almoxarifado_pode_criar_para_qualquer_funcionario(self):
        chefe_alm = _user("P004", PapelChoices.CHEFE_ALMOXARIFADO)
        setor_alm = _setor("Almoxarifado", chefe_alm)
        aux = _user("P005", PapelChoices.AUXILIAR_ALMOXARIFADO, setor=setor_alm)
        chefe_outro = _user("P006", PapelChoices.CHEFE_SETOR)
        setor_outro = _setor("RH", chefe_outro)
        beneficiario = _user("P007", setor=setor_outro)
        assert pode_criar_requisicao_para(aux, beneficiario) is True

    def test_usuario_inativo_nao_pode_criar(self):
        user = _user("P008", is_active=False)
        assert pode_criar_requisicao_para(user, user) is False


# ---------------------------------------------------------------------------
# 2. pode_visualizar_requisicao
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPodeVisualizarRequisicao:
    def setup_method(self):
        self.chefe = _user("V001", PapelChoices.CHEFE_SETOR)
        self.setor = _setor("TI", self.chefe)
        self.chefe.setor = self.setor
        self.chefe.save(update_fields=["setor"])

        self.criador = _user("V002", setor=self.setor)
        self.beneficiario = _user("V003", setor=self.setor)
        self.terceiro = _user("V004")

        chefe_alm = _user("V005", PapelChoices.CHEFE_ALMOXARIFADO)
        setor_alm = _setor("Almoxarifado", chefe_alm)
        self.aux_alm = _user("V006", PapelChoices.AUXILIAR_ALMOXARIFADO, setor=setor_alm)

        chefe_outro = _user("V007", PapelChoices.CHEFE_SETOR)
        self.setor_outro = _setor("RH", chefe_outro)
        chefe_outro.setor = self.setor_outro
        chefe_outro.save(update_fields=["setor"])
        self.chefe_outro = chefe_outro

    def test_criador_ve_proprio_rascunho(self):
        req = _requisicao(self.criador, self.beneficiario, self.setor)
        assert pode_visualizar_requisicao(self.criador, req) is True

    def test_nao_criador_nao_ve_rascunho_de_terceiro(self):
        req = _requisicao(self.criador, self.beneficiario, self.setor)
        assert pode_visualizar_requisicao(self.terceiro, req) is False

    def test_almoxarifado_nao_ve_rascunho_de_terceiro(self):
        req = _requisicao(self.criador, self.beneficiario, self.setor)
        assert pode_visualizar_requisicao(self.aux_alm, req) is False

    def test_criador_ve_requisicao_nao_rascunho(self):
        req = _requisicao(
            self.criador, self.beneficiario, self.setor, StatusRequisicao.AGUARDANDO_AUTORIZACAO
        )
        assert pode_visualizar_requisicao(self.criador, req) is True

    def test_beneficiario_ve_requisicao_nao_rascunho(self):
        req = _requisicao(
            self.criador, self.beneficiario, self.setor, StatusRequisicao.AGUARDANDO_AUTORIZACAO
        )
        assert pode_visualizar_requisicao(self.beneficiario, req) is True

    def test_almoxarifado_ve_qualquer_nao_rascunho(self):
        req = _requisicao(self.criador, self.beneficiario, self.setor, StatusRequisicao.AUTORIZADA)
        assert pode_visualizar_requisicao(self.aux_alm, req) is True

    def test_chefe_setor_ve_requisicao_do_proprio_setor(self):
        req = _requisicao(
            self.criador, self.beneficiario, self.setor, StatusRequisicao.AGUARDANDO_AUTORIZACAO
        )
        assert pode_visualizar_requisicao(self.chefe, req) is True

    def test_chefe_setor_nao_ve_requisicao_de_outro_setor(self):
        req = _requisicao(
            self.criador, self.beneficiario, self.setor, StatusRequisicao.AGUARDANDO_AUTORIZACAO
        )
        assert pode_visualizar_requisicao(self.chefe_outro, req) is False

    def test_usuario_inativo_nao_ve_nada(self):
        req = _requisicao(self.criador, self.beneficiario, self.setor, StatusRequisicao.AUTORIZADA)
        assert pode_visualizar_requisicao(self.criador, req) is True
        self.criador.is_active = False
        self.criador.save(update_fields=["is_active"])
        assert pode_visualizar_requisicao(self.criador, req) is False


# ---------------------------------------------------------------------------
# 3. pode_manipular_pre_autorizacao
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPodeManipularPreAutorizacao:
    def setup_method(self):
        chefe = _user("M001", PapelChoices.CHEFE_SETOR)
        setor = _setor("Financeiro", chefe)
        self.criador = _user("M002", setor=setor)
        self.beneficiario = _user("M003", setor=setor)
        self.terceiro = _user("M004")

    def test_criador_pode_manipular_rascunho(self):
        req = _requisicao(self.criador, self.beneficiario, self.beneficiario.setor)
        assert pode_manipular_pre_autorizacao(self.criador, req) is True

    def test_nao_criador_nao_pode_manipular_rascunho(self):
        req = _requisicao(self.criador, self.beneficiario, self.beneficiario.setor)
        assert pode_manipular_pre_autorizacao(self.terceiro, req) is False

    def test_beneficiario_nao_pode_manipular_rascunho_de_terceiro(self):
        req = _requisicao(self.criador, self.beneficiario, self.beneficiario.setor)
        assert pode_manipular_pre_autorizacao(self.beneficiario, req) is False

    def test_criador_pode_manipular_aguardando_autorizacao(self):
        req = _requisicao(
            self.criador,
            self.beneficiario,
            self.beneficiario.setor,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        )
        assert pode_manipular_pre_autorizacao(self.criador, req) is True

    def test_beneficiario_pode_manipular_aguardando_autorizacao(self):
        req = _requisicao(
            self.criador,
            self.beneficiario,
            self.beneficiario.setor,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        )
        assert pode_manipular_pre_autorizacao(self.beneficiario, req) is True

    def test_terceiro_nao_pode_manipular_aguardando_autorizacao(self):
        req = _requisicao(
            self.criador,
            self.beneficiario,
            self.beneficiario.setor,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        )
        assert pode_manipular_pre_autorizacao(self.terceiro, req) is False

    def test_usuario_inativo_nao_pode_manipular(self):
        req = _requisicao(self.criador, self.beneficiario, self.beneficiario.setor)
        assert pode_manipular_pre_autorizacao(self.criador, req) is True
        self.criador.is_active = False
        self.criador.save(update_fields=["is_active"])
        assert pode_manipular_pre_autorizacao(self.criador, req) is False


# ---------------------------------------------------------------------------
# 4. pode_cancelar_autorizada
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPodeCancelarAutorizada:
    def setup_method(self):
        chefe = _user("C001", PapelChoices.CHEFE_SETOR)
        setor = _setor("Obras", chefe)
        self.criador = _user("C002", setor=setor)
        self.beneficiario = _user("C003", setor=setor)
        self.terceiro = _user("C004")

        chefe_alm = _user("C005", PapelChoices.CHEFE_ALMOXARIFADO)
        setor_alm = _setor("Almoxarifado", chefe_alm)
        self.aux_alm = _user("C006", PapelChoices.AUXILIAR_ALMOXARIFADO, setor=setor_alm)

        self.req = _requisicao(self.criador, self.beneficiario, setor, StatusRequisicao.AUTORIZADA)

    def test_criador_pode_cancelar_autorizada(self):
        assert pode_cancelar_autorizada(self.criador, self.req) is True

    def test_beneficiario_pode_cancelar_autorizada(self):
        assert pode_cancelar_autorizada(self.beneficiario, self.req) is True

    def test_almoxarifado_pode_cancelar_autorizada(self):
        assert pode_cancelar_autorizada(self.aux_alm, self.req) is True

    def test_terceiro_nao_pode_cancelar_autorizada(self):
        assert pode_cancelar_autorizada(self.terceiro, self.req) is False

    def test_usuario_inativo_nao_pode_cancelar_autorizada(self):
        assert pode_cancelar_autorizada(self.criador, self.req) is True
        self.criador.is_active = False
        self.criador.save(update_fields=["is_active"])
        assert pode_cancelar_autorizada(self.criador, self.req) is False


# ---------------------------------------------------------------------------
# 5. pode_autorizar_requisicao
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPodeAutorizarRequisicao:
    def setup_method(self):
        self.chefe = _user("A001", PapelChoices.CHEFE_SETOR)
        self.setor = _setor("Compras", self.chefe)
        self.chefe.setor = self.setor
        self.chefe.save(update_fields=["setor"])

        chefe_outro = _user("A002", PapelChoices.CHEFE_SETOR)
        self.setor_outro = _setor("Juridico", chefe_outro)
        chefe_outro.setor = self.setor_outro
        chefe_outro.save(update_fields=["setor"])
        self.chefe_outro = chefe_outro

        criador = _user("A003", setor=self.setor)
        beneficiario = _user("A004", setor=self.setor)
        self.req = _requisicao(
            criador, beneficiario, self.setor, StatusRequisicao.AGUARDANDO_AUTORIZACAO
        )

        self.auxiliar = _user("A005", PapelChoices.AUXILIAR_SETOR, setor=self.setor)
        self.solicitante = _user("A006", setor=self.setor)

    def test_chefe_setor_pode_autorizar_proprio_setor(self):
        assert pode_autorizar_requisicao(self.chefe, self.req) is True

    def test_chefe_setor_nao_pode_autorizar_outro_setor(self):
        assert pode_autorizar_requisicao(self.chefe_outro, self.req) is False

    def test_auxiliar_setor_nao_pode_autorizar(self):
        assert pode_autorizar_requisicao(self.auxiliar, self.req) is False

    def test_solicitante_nao_pode_autorizar(self):
        assert pode_autorizar_requisicao(self.solicitante, self.req) is False

    def test_usuario_inativo_nao_pode_autorizar(self):
        assert pode_autorizar_requisicao(self.chefe, self.req) is True
        self.chefe.is_active = False
        self.chefe.save(update_fields=["is_active"])
        assert pode_autorizar_requisicao(self.chefe, self.req) is False


# ---------------------------------------------------------------------------
# 6. pode_atender_requisicao e pode_retirar_requisicao
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPodeAtenderERetirarRequisicao:
    def setup_method(self):
        chefe = _user("AT001", PapelChoices.CHEFE_SETOR)
        setor = _setor("Manutencao", chefe)
        criador = _user("AT002", setor=setor)
        beneficiario = _user("AT003", setor=setor)

        chefe_alm = _user("AT004", PapelChoices.CHEFE_ALMOXARIFADO)
        setor_alm = _setor("Almoxarifado", chefe_alm)
        chefe_alm.setor = setor_alm
        chefe_alm.save(update_fields=["setor"])
        self.chefe_alm = chefe_alm
        self.aux_alm = _user("AT005", PapelChoices.AUXILIAR_ALMOXARIFADO, setor=setor_alm)
        self.solicitante = _user("AT006", setor=setor)

        self.req_autorizada = _requisicao(criador, beneficiario, setor, StatusRequisicao.AUTORIZADA)
        self.req_pronta = _requisicao(
            criador, beneficiario, setor, StatusRequisicao.PRONTA_PARA_RETIRADA
        )

    def test_auxiliar_almoxarifado_pode_atender(self):
        assert pode_atender_requisicao(self.aux_alm, self.req_autorizada) is True

    def test_chefe_almoxarifado_pode_atender(self):
        assert pode_atender_requisicao(self.chefe_alm, self.req_autorizada) is True

    def test_solicitante_nao_pode_atender(self):
        assert pode_atender_requisicao(self.solicitante, self.req_autorizada) is False

    def test_auxiliar_almoxarifado_pode_retirar(self):
        assert pode_retirar_requisicao(self.aux_alm, self.req_pronta) is True

    def test_chefe_almoxarifado_pode_retirar(self):
        assert pode_retirar_requisicao(self.chefe_alm, self.req_pronta) is True

    def test_solicitante_nao_pode_retirar(self):
        assert pode_retirar_requisicao(self.solicitante, self.req_pronta) is False

    def test_usuario_inativo_nao_pode_atender_nem_retirar(self):
        inativo = _user("AT099", PapelChoices.AUXILIAR_ALMOXARIFADO, is_active=False)
        assert pode_atender_requisicao(inativo, self.req_autorizada) is False
        assert pode_retirar_requisicao(inativo, self.req_pronta) is False


# ---------------------------------------------------------------------------
# 7. queryset_fila_autorizacao
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestQuerysetFilaAutorizacao:
    def test_chefe_setor_ve_fila_do_proprio_setor(self):
        chefe = _user("Q001", PapelChoices.CHEFE_SETOR)
        setor = _setor("Planejamento", chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        criador = _user("Q002", setor=setor)
        _requisicao(criador, criador, setor, StatusRequisicao.AGUARDANDO_AUTORIZACAO)

        qs = queryset_fila_autorizacao(chefe)
        assert qs.count() == 1

    def test_chefe_setor_nao_ve_fila_de_outro_setor(self):
        chefe_a = _user("Q003", PapelChoices.CHEFE_SETOR)
        setor_a = _setor("Contabilidade", chefe_a)
        chefe_a.setor = setor_a
        chefe_a.save(update_fields=["setor"])

        chefe_b = _user("Q004", PapelChoices.CHEFE_SETOR)
        setor_b = _setor("Juridico", chefe_b)
        criador = _user("Q005", setor=setor_b)
        _requisicao(criador, criador, setor_b, StatusRequisicao.AGUARDANDO_AUTORIZACAO)

        qs = queryset_fila_autorizacao(chefe_a)
        assert qs.count() == 0

    def test_solicitante_recebe_queryset_vazio(self):
        user = _user("Q006")
        assert queryset_fila_autorizacao(user).count() == 0

    def test_requisicao_em_outro_status_nao_aparece_na_fila(self):
        chefe = _user("Q007", PapelChoices.CHEFE_SETOR)
        setor = _setor("Obras", chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        criador = _user("Q008", setor=setor)
        _requisicao(criador, criador, setor, StatusRequisicao.AUTORIZADA)

        assert queryset_fila_autorizacao(chefe).count() == 0


# ---------------------------------------------------------------------------
# 8. queryset_fila_atendimento
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestQuerysetFilaAtendimento:
    def setup_method(self):
        chefe_alm = _user("QA001", PapelChoices.CHEFE_ALMOXARIFADO)
        setor_alm = _setor("Almoxarifado", chefe_alm)
        chefe_alm.setor = setor_alm
        chefe_alm.save(update_fields=["setor"])
        self.aux_alm = _user("QA002", PapelChoices.AUXILIAR_ALMOXARIFADO, setor=setor_alm)
        self.solicitante = _user("QA003")

        chefe = _user("QA004", PapelChoices.CHEFE_SETOR)
        setor = _setor("RH", chefe)
        criador = _user("QA005", setor=setor)

        self.req_autorizada = _requisicao(criador, criador, setor, StatusRequisicao.AUTORIZADA)
        self.req_pronta = _requisicao(
            criador, criador, setor, StatusRequisicao.PRONTA_PARA_RETIRADA
        )
        self.req_pronta_parcial = _requisicao(
            criador, criador, setor, StatusRequisicao.PRONTA_PARA_RETIRADA_PARCIAL
        )
        self.req_rascunho = _requisicao(criador, criador, setor)

    def test_almoxarifado_ve_todos_os_estados_da_fila(self):
        qs = queryset_fila_atendimento(self.aux_alm)
        ids = set(qs.values_list("id", flat=True))
        assert self.req_autorizada.id in ids
        assert self.req_pronta.id in ids
        assert self.req_pronta_parcial.id in ids

    def test_rascunho_nao_aparece_na_fila(self):
        qs = queryset_fila_atendimento(self.aux_alm)
        ids = set(qs.values_list("id", flat=True))
        assert self.req_rascunho.id not in ids

    def test_solicitante_recebe_queryset_vazio(self):
        assert queryset_fila_atendimento(self.solicitante).count() == 0
