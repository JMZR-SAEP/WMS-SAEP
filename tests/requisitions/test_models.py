from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.requisitions.models import (
    EventoTimeline,
    ItemRequisicao,
    Requisicao,
    StatusRequisicao,
    TipoEvento,
)
from apps.users.models import PapelChoices, Setor, User


@pytest.mark.django_db
class TestRequisicaoModel:
    @staticmethod
    def _criar_usuario(matricula="1001", nome="João", papel=PapelChoices.SOLICITANTE, setor=None):
        """Helper para criar usuário de teste"""
        if not setor:
            setor = TestRequisicaoModel._criar_setor(
                nome=f"Setor {matricula}",
                matricula_chefe=f"9{matricula}",
            )
        usuario, _ = User.objects.get_or_create(
            matricula_funcional=matricula,
            defaults={
                "nome_completo": nome,
                "papel": papel,
                "setor": setor,
            },
        )
        if usuario.setor_id != setor.id:
            usuario.setor = setor
            usuario.save(update_fields=["setor"])
        return usuario

    @staticmethod
    def _criar_setor(nome="Operacional", matricula_chefe="9901"):
        """Helper para criar setor"""
        chefe, _ = User.objects.get_or_create(
            matricula_funcional=matricula_chefe,
            defaults={
                "nome_completo": f"Chefe {nome}",
                "papel": PapelChoices.CHEFE_SETOR,
            },
        )
        setor, _ = Setor.objects.get_or_create(
            nome=nome,
            defaults={"chefe_responsavel": chefe},
        )
        if setor.chefe_responsavel_id != chefe.id:
            setor.chefe_responsavel = chefe
            setor.save(update_fields=["chefe_responsavel"])
        if chefe.setor_id != setor.id:
            chefe.setor = setor
            chefe.save(update_fields=["setor"])
        return setor

    @staticmethod
    def _criar_requisicao(criador=None, beneficiario=None, setor_beneficiario=None):
        """Helper para criar requisição básica"""
        if not criador:
            criador = TestRequisicaoModel._criar_usuario(matricula="1001", nome="João")
        if not beneficiario:
            beneficiario = TestRequisicaoModel._criar_usuario(matricula="1002", nome="Maria")
        if not setor_beneficiario:
            setor_beneficiario = beneficiario.setor

        return Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario,
            setor_beneficiario=setor_beneficiario,
        )

    def test_rascunho_sem_numero_publico(self):
        """REQ-01, REQ-02 — status padrão é rascunho, numero_publico é null"""
        req = self._criar_requisicao()
        assert req.status == StatusRequisicao.RASCUNHO
        assert req.numero_publico is None

    def test_snapshot_criador_beneficiario_setor(self):
        """REQ-07, PER-07 — campos FK preenchidos corretamente (snapshot)"""
        criador = self._criar_usuario(matricula="1001", nome="João")
        beneficiario = self._criar_usuario(matricula="1002", nome="Maria")
        setor = beneficiario.setor

        req = self._criar_requisicao(
            criador=criador,
            beneficiario=beneficiario,
            setor_beneficiario=setor,
        )

        assert req.criador == criador
        assert req.beneficiario == beneficiario
        assert req.setor_beneficiario == setor

    def test_constraint_motivo_recusa_obrigatorio(self):
        """REQ-domain — motivo_recusa obrigatório quando status=recusada"""
        req = self._criar_requisicao()
        req.status = StatusRequisicao.RECUSADA
        req.motivo_recusa = ""
        with pytest.raises(IntegrityError):
            req.save()

    def test_constraint_motivo_recusa_valido(self):
        """REQ-domain — motivo_recusa válido quando preenchido"""
        req = self._criar_requisicao()
        req.status = StatusRequisicao.RECUSADA
        req.motivo_recusa = "Material fora de estoque"
        req.save()
        assert req.status == StatusRequisicao.RECUSADA

    def test_constraint_motivo_cancelamento_obrigatorio(self):
        """REQ-domain — motivo_cancelamento obrigatório quando status=cancelada"""
        req = self._criar_requisicao()
        req.status = StatusRequisicao.CANCELADA
        req.motivo_cancelamento = ""
        with pytest.raises(IntegrityError):
            req.save()

    def test_constraint_motivo_cancelamento_valido(self):
        """REQ-domain — motivo_cancelamento válido quando preenchido"""
        req = self._criar_requisicao()
        req.status = StatusRequisicao.CANCELADA
        req.motivo_cancelamento = "Solicitação cancelada por diretor"
        req.save()
        assert req.status == StatusRequisicao.CANCELADA

    def test_numero_publico_unico_quando_preenchido(self):
        """REQ-04 — numero_publico é único quando preenchido (não-null)"""
        req1 = self._criar_requisicao()
        req1.numero_publico = "REQ-2026-000001"
        req1.save()

        req2 = self._criar_requisicao()
        req2.numero_publico = "REQ-2026-000001"
        with pytest.raises(IntegrityError):
            req2.save()

    def test_numero_publico_null_nao_e_unico(self):
        """REQ-02 — multiplas requisições podem ter numero_publico=None"""
        req1 = self._criar_requisicao()
        req2 = self._criar_requisicao()
        assert req1.numero_publico is None
        assert req2.numero_publico is None
        # Sem erro de IntegrityError

    def test_numero_publico_vazio_string_nao_e_unico(self):
        """REQ-02 — numero_publico="" é tratado como vazio (constraint conditional)"""
        req1 = self._criar_requisicao()
        req1.numero_publico = ""
        req1.save()

        req2 = self._criar_requisicao()
        req2.numero_publico = ""
        req2.save()
        # Sem erro de IntegrityError (ambos vazios)

    def test_str_representation(self):
        """Representação em string do modelo"""
        req = self._criar_requisicao()
        assert str(req) == f"REQ (rascunho {req.id}) — {req.beneficiario.nome_completo}"

        req.numero_publico = "REQ-2026-000001"
        req.save()
        assert str(req) == f"REQ REQ-2026-000001 — {req.beneficiario.nome_completo}"


@pytest.mark.django_db
class TestItemRequisicaoModel:
    @staticmethod
    def _criar_material():
        """Helper para criar material de teste"""
        grupo = GrupoMaterial.objects.create(codigo_grupo="001", nome="Grupo 1")
        subgrupo = SubgrupoMaterial.objects.create(
            grupo=grupo,
            codigo_subgrupo="01",
            nome="Subgrupo 1",
        )
        return Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="001.01.001",
            sequencial="001",
            nome="Material 1",
            unidade_medida="UNI",
        )

    @staticmethod
    def _criar_usuario(matricula="1001"):
        """Helper para criar usuário"""
        chefe, _ = User.objects.get_or_create(
            matricula_funcional=f"9{matricula}",
            defaults={
                "nome_completo": f"Chefe {matricula}",
                "papel": PapelChoices.CHEFE_SETOR,
            },
        )
        setor, _ = Setor.objects.get_or_create(
            nome=f"Setor {matricula}",
            defaults={"chefe_responsavel": chefe},
        )
        if setor.chefe_responsavel_id != chefe.id:
            setor.chefe_responsavel = chefe
            setor.save(update_fields=["chefe_responsavel"])
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        usuario, _ = User.objects.get_or_create(
            matricula_funcional=matricula,
            defaults={
                "nome_completo": "João",
                "papel": PapelChoices.SOLICITANTE,
                "setor": setor,
            },
        )
        if usuario.setor_id != setor.id:
            usuario.setor = setor
            usuario.save(update_fields=["setor"])
        return usuario

    @staticmethod
    def _criar_requisicao():
        """Helper para criar requisição"""
        criador = TestItemRequisicaoModel._criar_usuario("1001")
        beneficiario = TestItemRequisicaoModel._criar_usuario("1002")
        return Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario,
            setor_beneficiario=beneficiario.setor,
        )

    @staticmethod
    def _criar_item(requisicao=None, material=None, quantidade_solicitada=Decimal("10.000")):
        """Helper para criar item de requisição"""
        if not requisicao:
            requisicao = TestItemRequisicaoModel._criar_requisicao()
        if not material:
            material = TestItemRequisicaoModel._criar_material()

        return ItemRequisicao.objects.create(
            requisicao=requisicao,
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=quantidade_solicitada,
        )

    def test_item_valido_criado(self):
        """ITEM-domain — caminho feliz de criação de item"""
        req = self._criar_requisicao()
        material = self._criar_material()

        item = ItemRequisicao.objects.create(
            requisicao=req,
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("10.000"),
        )

        assert item.requisicao == req
        assert item.material == material
        assert item.quantidade_solicitada == Decimal("10.000")
        assert item.quantidade_autorizada == Decimal("0")
        assert item.quantidade_entregue == Decimal("0")

    def test_quantidade_solicitada_zero_invalida(self):
        """ITEM-01 — quantidade_solicitada deve ser > 0"""
        req = self._criar_requisicao()
        material = self._criar_material()

        with pytest.raises(IntegrityError):
            ItemRequisicao.objects.create(
                requisicao=req,
                material=material,
                unidade_medida=material.unidade_medida,
                quantidade_solicitada=Decimal("0"),
            )

    def test_quantidade_autorizada_maior_que_solicitada_invalida(self):
        """ITEM-01 — quantidade_autorizada > quantidade_solicitada é inválido"""
        item = self._criar_item(quantidade_solicitada=Decimal("10.000"))
        item.quantidade_autorizada = Decimal("15.000")

        with pytest.raises(IntegrityError):
            item.save()

    def test_quantidade_entregue_maior_que_autorizada_invalida(self):
        """ITEM-02 — quantidade_entregue > quantidade_autorizada é inválido"""
        item = self._criar_item()
        item.quantidade_autorizada = Decimal("5.000")
        item.quantidade_entregue = Decimal("6.000")

        with pytest.raises(IntegrityError):
            item.save()

    def test_quantidade_entregue_zero_valido(self):
        """ITEM-02 — quantidade_entregue=0 é válido (default)"""
        item = self._criar_item()
        assert item.quantidade_entregue == Decimal("0")

    def test_quantidade_autorizada_zero_valido(self):
        """ITEM-domain — quantidade_autorizada=0 é válido (não autorizado ainda)"""
        item = self._criar_item()
        assert item.quantidade_autorizada == Decimal("0")

    def test_str_representation(self):
        """Representação em string do item"""
        item = self._criar_item()
        assert (
            str(item)
            == f"{item.material.codigo_completo} — {item.quantidade_solicitada} {item.unidade_medida}"
        )


@pytest.mark.django_db
class TestEventoTimelineImutavel:
    @staticmethod
    def _criar_usuario(matricula="1001"):
        chefe, _ = User.objects.get_or_create(
            matricula_funcional=f"9{matricula}",
            defaults={
                "nome_completo": f"Chefe {matricula}",
                "papel": PapelChoices.CHEFE_SETOR,
            },
        )
        setor, _ = Setor.objects.get_or_create(
            nome=f"Setor {matricula}",
            defaults={"chefe_responsavel": chefe},
        )
        if setor.chefe_responsavel_id != chefe.id:
            setor.chefe_responsavel = chefe
            setor.save(update_fields=["chefe_responsavel"])
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        usuario, _ = User.objects.get_or_create(
            matricula_funcional=matricula,
            defaults={
                "nome_completo": "João",
                "papel": PapelChoices.SOLICITANTE,
                "setor": setor,
            },
        )
        if usuario.setor_id != setor.id:
            usuario.setor = setor
            usuario.save(update_fields=["setor"])
        return usuario

    @staticmethod
    def _criar_requisicao():
        criador = TestEventoTimelineImutavel._criar_usuario("1001")
        beneficiario = TestEventoTimelineImutavel._criar_usuario("1002")
        return Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario,
            setor_beneficiario=beneficiario.setor,
        )

    @staticmethod
    def _criar_evento(requisicao=None, usuario=None):
        if not requisicao:
            requisicao = TestEventoTimelineImutavel._criar_requisicao()
        if not usuario:
            usuario = TestEventoTimelineImutavel._criar_usuario()

        return EventoTimeline.objects.create(
            requisicao=requisicao,
            tipo_evento=TipoEvento.CRIACAO,
            usuario=usuario,
        )

    def test_evento_criado_com_sucesso(self):
        """EventoTimeline — caminho feliz de criação"""
        req = self._criar_requisicao()
        usuario = self._criar_usuario()

        evento = EventoTimeline.objects.create(
            requisicao=req,
            tipo_evento=TipoEvento.CRIACAO,
            usuario=usuario,
        )

        assert evento.requisicao == req
        assert evento.tipo_evento == TipoEvento.CRIACAO
        assert evento.usuario == usuario

    def test_save_existente_lanca_value_error(self):
        """EventoTimeline imutável — .save() em instância existente levanta ValueError"""
        evento = self._criar_evento()
        evento.observacao = "Novo texto"

        with pytest.raises(ValueError, match="Eventos de timeline são imutáveis"):
            evento.save()

    def test_delete_lanca_value_error(self):
        """EventoTimeline imutável — .delete() levanta ValueError"""
        evento = self._criar_evento()

        with pytest.raises(ValueError, match="Eventos de timeline não podem ser removidos"):
            evento.delete()

    def test_queryset_delete_lanca_value_error(self):
        """EventoTimeline imutável — QuerySet.delete() levanta ValueError"""
        self._criar_evento()

        with pytest.raises(ValueError, match="Eventos de timeline não podem ser removidos em lote"):
            EventoTimeline.objects.all().delete()

    def test_queryset_update_lanca_value_error(self):
        """EventoTimeline imutável — QuerySet.update() levanta ValueError"""
        evento = self._criar_evento()

        with pytest.raises(ValueError, match="Eventos de timeline são imutáveis"):
            EventoTimeline.objects.filter(pk=evento.pk).update(observacao="Novo")

    def test_bulk_update_lanca_value_error(self):
        """EventoTimeline imutável — Manager.bulk_update() levanta ValueError"""
        evento = self._criar_evento()
        evento.observacao = "Novo"

        with pytest.raises(ValueError, match="Eventos de timeline são imutáveis"):
            EventoTimeline.objects.bulk_update([evento], ["observacao"])

    def test_str_representation(self):
        """Representação em string do evento"""
        evento = self._criar_evento()
        expected = f"REQ (rascunho {evento.requisicao.id}) — Criação em {evento.data_hora.strftime('%d/%m/%Y %H:%M')}"
        assert str(evento) == expected
