from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.requisitions.models import EventoTimeline, Requisicao, StatusRequisicao, TipoEvento
from apps.stock.models import EstoqueMaterial
from apps.users.models import PapelChoices, Setor, User


@pytest.mark.django_db
class TestRequisicaoAPI:
    @staticmethod
    def _criar_setor(nome: str, chefe_matricula: str, papel=PapelChoices.CHEFE_SETOR) -> Setor:
        chefe = User.objects.create(
            matricula_funcional=chefe_matricula,
            nome_completo=f"Chefe {nome}",
            papel=papel,
            is_active=True,
        )
        setor = Setor.objects.create(nome=nome, chefe_responsavel=chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        return setor

    @staticmethod
    def _criar_usuario(
        matricula: str,
        nome: str,
        *,
        papel=PapelChoices.SOLICITANTE,
        setor: Setor | None = None,
        is_active: bool = True,
    ) -> User:
        return User.objects.create(
            matricula_funcional=matricula,
            nome_completo=nome,
            papel=papel,
            setor=setor,
            is_active=is_active,
        )

    @staticmethod
    def _criar_material_com_estoque(
        codigo: str,
        *,
        saldo_fisico: Decimal = Decimal("10"),
        saldo_reservado: Decimal = Decimal("0"),
        is_active: bool = True,
    ) -> Material:
        grupo_codigo, subgrupo_codigo, sequencial = codigo.split(".")
        grupo, _ = GrupoMaterial.objects.get_or_create(
            codigo_grupo=grupo_codigo,
            defaults={"nome": f"Grupo {grupo_codigo}"},
        )
        subgrupo, _ = SubgrupoMaterial.objects.get_or_create(
            grupo=grupo,
            codigo_subgrupo=subgrupo_codigo,
            defaults={"nome": f"Subgrupo {subgrupo_codigo}"},
        )
        material = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo=codigo,
            sequencial=sequencial,
            nome=f"Material {codigo}",
            unidade_medida="UN",
            is_active=is_active,
        )
        EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=saldo_fisico,
            saldo_reservado=saldo_reservado,
        )
        return material

    @staticmethod
    def _payload_requisicao(*, beneficiario_id: int, material_id: int, quantidade="2.000"):
        return {
            "beneficiario_id": beneficiario_id,
            "observacao": "Observacao de teste",
            "itens": [
                {
                    "material_id": material_id,
                    "quantidade_solicitada": quantidade,
                    "observacao": "Item de teste",
                }
            ],
        }

    @staticmethod
    def _payload_autorizacao(*, item_id: int, quantidade_autorizada: str, justificativa: str = ""):
        return {
            "itens": [
                {
                    "item_id": item_id,
                    "quantidade_autorizada": quantidade_autorizada,
                    "justificativa_autorizacao_parcial": justificativa,
                }
            ]
        }

    def test_cria_rascunho_para_si(self):
        setor = self._criar_setor("Operacional", "90001")
        usuario = self._criar_usuario("10001", "Solicitante", setor=setor)
        material = self._criar_material_com_estoque("001.001.001")

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(
            reverse("requisicao-list"),
            self._payload_requisicao(beneficiario_id=usuario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 201
        assert response.data["status"] == StatusRequisicao.RASCUNHO
        assert response.data["numero_publico"] is None
        assert response.data["beneficiario"]["id"] == usuario.id
        assert response.data["setor_beneficiario"]["id"] == setor.id
        assert response.data["itens"][0]["material"]["id"] == material.id
        assert Requisicao.objects.count() == 1

    def test_bloqueia_criacao_para_outro_setor_por_solicitante(self):
        setor_a = self._criar_setor("Financeiro", "90002")
        setor_b = self._criar_setor("Obras", "90003")
        solicitante = self._criar_usuario("10002", "Solicitante A", setor=setor_a)
        beneficiario = self._criar_usuario("10003", "Beneficiario B", setor=setor_b)
        material = self._criar_material_com_estoque("001.001.002")

        client = APIClient()
        client.force_authenticate(user=solicitante)
        response = client.post(
            reverse("requisicao-list"),
            self._payload_requisicao(beneficiario_id=beneficiario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_auxiliar_setor_pode_criar_para_funcionario_do_mesmo_setor(self):
        setor = self._criar_setor("TI", "90004")
        auxiliar = self._criar_usuario(
            "10004",
            "Auxiliar TI",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor,
        )
        beneficiario = self._criar_usuario("10005", "Funcionario TI", setor=setor)
        material = self._criar_material_com_estoque("001.001.003")

        client = APIClient()
        client.force_authenticate(user=auxiliar)
        response = client.post(
            reverse("requisicao-list"),
            self._payload_requisicao(beneficiario_id=beneficiario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 201
        assert response.data["beneficiario"]["id"] == beneficiario.id

    def test_bloqueia_rascunho_sem_itens(self):
        setor = self._criar_setor("RH", "90005")
        usuario = self._criar_usuario("10006", "Solicitante RH", setor=setor)

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(
            reverse("requisicao-list"),
            {"beneficiario_id": usuario.id, "itens": []},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"

    def test_bloqueia_criacao_com_material_inativo(self):
        setor = self._criar_setor("Compras", "90006")
        usuario = self._criar_usuario("10007", "Solicitante Compras", setor=setor)
        material = self._criar_material_com_estoque("001.001.004", is_active=False)

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(
            reverse("requisicao-list"),
            self._payload_requisicao(beneficiario_id=usuario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"

    def test_bloqueia_criacao_com_quantidade_maior_que_saldo(self):
        setor = self._criar_setor("Juridico", "90007")
        usuario = self._criar_usuario("10008", "Solicitante Juridico", setor=setor)
        material = self._criar_material_com_estoque("001.001.005", saldo_fisico=Decimal("3"))

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(
            reverse("requisicao-list"),
            self._payload_requisicao(
                beneficiario_id=usuario.id,
                material_id=material.id,
                quantidade="5.000",
            ),
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"

    def test_submit_gera_numero_publico_e_entrada_na_fila(self):
        setor = self._criar_setor("Planejamento", "90008")
        usuario = self._criar_usuario("10009", "Solicitante Planejamento", setor=setor)
        material = self._criar_material_com_estoque("001.001.006")
        requisicao = Requisicao.objects.create(criador=usuario, beneficiario=usuario)
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
        )
        assert item.quantidade_autorizada == 0

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(reverse("requisicao-submit", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.AGUARDANDO_AUTORIZACAO
        assert response.data["numero_publico"] == "REQ-2026-000001"
        requisicao.refresh_from_db()
        assert requisicao.numero_publico == "REQ-2026-000001"
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.ENVIO_AUTORIZACAO).exists()

    def test_return_to_draft_preserva_numero_publico(self):
        setor = self._criar_setor("Patrimonio", "90009")
        usuario = self._criar_usuario("10010", "Solicitante Patrimonio", setor=setor)
        material = self._criar_material_com_estoque("001.001.007")
        requisicao = Requisicao.objects.create(
            criador=usuario,
            beneficiario=usuario,
            numero_publico="REQ-2026-000010",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(reverse("requisicao-return-to-draft", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.RASCUNHO
        assert response.data["numero_publico"] == "REQ-2026-000010"
        assert EventoTimeline.objects.filter(
            requisicao=requisicao,
            tipo_evento=TipoEvento.RETORNO_RASCUNHO,
        ).exists()

    def test_reenvio_preserva_numero_publico(self):
        setor = self._criar_setor("Frota", "90010")
        usuario = self._criar_usuario("10011", "Solicitante Frota", setor=setor)
        material = self._criar_material_com_estoque("001.001.008")
        requisicao = Requisicao.objects.create(
            criador=usuario,
            beneficiario=usuario,
            numero_publico="REQ-2026-000123",
            status=StatusRequisicao.RASCUNHO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(reverse("requisicao-submit", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["numero_publico"] == "REQ-2026-000123"
        assert EventoTimeline.objects.filter(
            requisicao=requisicao,
            tipo_evento=TipoEvento.REENVIO_AUTORIZACAO,
        ).exists()

    def test_discard_remove_rascunho_nunca_enviado(self):
        setor = self._criar_setor("Fiscal", "90011")
        usuario = self._criar_usuario("10012", "Solicitante Fiscal", setor=setor)
        material = self._criar_material_com_estoque("001.001.009")
        requisicao = Requisicao.objects.create(criador=usuario, beneficiario=usuario)
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.delete(reverse("requisicao-discard", args=[requisicao.id]))

        assert response.status_code == 204
        assert not Requisicao.objects.filter(pk=requisicao.pk).exists()

    def test_discard_rascunho_formalizado_retorna_domain_conflict(self):
        setor = self._criar_setor("Fiscal Formalizado", "900111")
        usuario = self._criar_usuario("100121", "Solicitante Fiscal Formalizado", setor=setor)
        material = self._criar_material_com_estoque("001.001.099")
        requisicao = Requisicao.objects.create(
            criador=usuario,
            beneficiario=usuario,
            numero_publico="REQ-2026-009999",
            status=StatusRequisicao.RASCUNHO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.delete(reverse("requisicao-discard", args=[requisicao.id]))

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
        assert Requisicao.objects.filter(pk=requisicao.pk).exists()

    def test_cancela_rascunho_numerado_sem_justificativa(self):
        setor = self._criar_setor("Almox Interno", "90012")
        usuario = self._criar_usuario("10013", "Solicitante Almox Interno", setor=setor)
        material = self._criar_material_com_estoque("001.001.010")
        requisicao = Requisicao.objects.create(
            criador=usuario,
            beneficiario=usuario,
            numero_publico="REQ-2026-000200",
            status=StatusRequisicao.RASCUNHO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(reverse("requisicao-cancel", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.CANCELADA
        assert response.data["numero_publico"] == "REQ-2026-000200"

    def test_authorize_total_reserva_estoque_e_define_autorizador(self):
        setor = self._criar_setor("Producao", "90016")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("10017", "Solicitante Producao", setor=setor)
        material = self._criar_material_com_estoque("001.001.012", saldo_fisico=Decimal("10"))
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000400",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("4"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe)
        response = client.post(
            reverse("requisicao-authorize", args=[requisicao.id]),
            self._payload_autorizacao(item_id=item.id, quantidade_autorizada="4.000"),
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.AUTORIZADA
        assert response.data["chefe_autorizador"]["id"] == chefe.id
        assert response.data["itens"][0]["quantidade_autorizada"] == "4.000"
        requisicao.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.chefe_autorizador_id == chefe.id
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.AUTORIZACAO_TOTAL).exists()
        estoque = material.estoque
        assert estoque.saldo_fisico == Decimal("10")
        assert estoque.saldo_reservado == Decimal("4")

    def test_refuse_requer_motivo_e_nao_reserva_estoque(self):
        setor = self._criar_setor("Transporte", "90017")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("10018", "Solicitante Transporte", setor=setor)
        material = self._criar_material_com_estoque("001.001.013", saldo_fisico=Decimal("7"))
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000401",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe)
        response = client.post(
            reverse("requisicao-refuse", args=[requisicao.id]),
            {"motivo_recusa": "Item fora de prioridade"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.RECUSADA
        assert response.data["motivo_recusa"] == "Item fora de prioridade"
        assert response.data["chefe_autorizador"]["id"] == chefe.id
        requisicao.refresh_from_db()
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.RECUSA).exists()
        material.estoque.refresh_from_db()
        assert material.estoque.saldo_reservado == Decimal("0")

    def test_authorize_bloqueia_usuario_sem_permissao(self):
        setor = self._criar_setor("Oficina", "90018")
        usuario = self._criar_usuario("10019", "Solicitante Oficina", setor=setor)
        material = self._criar_material_com_estoque("001.001.014")
        requisicao = Requisicao.objects.create(
            criador=usuario,
            beneficiario=usuario,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000402",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(
            reverse("requisicao-authorize", args=[requisicao.id]),
            self._payload_autorizacao(item_id=item.id, quantidade_autorizada="1.000"),
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_authorize_rejeita_saldo_estavel_insuficiente(self):
        setor = self._criar_setor("Logistica", "90019")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("10020", "Solicitante Logistica", setor=setor)
        material = self._criar_material_com_estoque("001.001.015", saldo_fisico=Decimal("5"))
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000403",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("4"),
        )
        material.estoque.saldo_fisico = Decimal("2")
        material.estoque.save(update_fields=["saldo_fisico", "updated_at"])

        client = APIClient()
        client.force_authenticate(user=chefe)
        response = client.post(
            reverse("requisicao-authorize", args=[requisicao.id]),
            self._payload_autorizacao(item_id=item.id, quantidade_autorizada="4.000"),
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
        material.estoque.refresh_from_db()
        assert material.estoque.saldo_reservado == Decimal("0")

    def test_authorize_partial_and_zero_require_justificativa(self):
        setor = self._criar_setor("Apoio", "90020")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("10021", "Solicitante Apoio", setor=setor)
        material_a = self._criar_material_com_estoque("001.001.016", saldo_fisico=Decimal("8"))
        material_b = self._criar_material_com_estoque("001.001.017", saldo_fisico=Decimal("8"))
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000404",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        item_a = requisicao.itens.create(
            material=material_a,
            unidade_medida=material_a.unidade_medida,
            quantidade_solicitada=Decimal("5"),
        )
        item_b = requisicao.itens.create(
            material=material_b,
            unidade_medida=material_b.unidade_medida,
            quantidade_solicitada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe)
        response = client.post(
            reverse("requisicao-authorize", args=[requisicao.id]),
            {
                "itens": [
                    {
                        "item_id": item_a.id,
                        "quantidade_autorizada": "4.000",
                        "justificativa_autorizacao_parcial": "Saldo limitado",
                    },
                    {
                        "item_id": item_b.id,
                        "quantidade_autorizada": "0.000",
                        "justificativa_autorizacao_parcial": "Não prioritário",
                    },
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.AUTORIZADA
        assert response.data["chefe_autorizador"]["id"] == chefe.id
        assert response.data["itens"][0]["quantidade_autorizada"] == "4.000"
        requisicao.refresh_from_db()
        material_a.estoque.refresh_from_db()
        material_b.estoque.refresh_from_db()
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.AUTORIZACAO_PARCIAL).exists()
        assert material_a.estoque.saldo_reservado == Decimal("4")
        assert material_b.estoque.saldo_reservado == Decimal("0")

    def test_authorize_partial_and_zero_sem_justificativa_falha(self):
        setor = self._criar_setor("Apoio Financeiro", "90024")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("10024", "Solicitante Apoio Financeiro", setor=setor)
        material_a = self._criar_material_com_estoque("001.001.020", saldo_fisico=Decimal("8"))
        material_b = self._criar_material_com_estoque("001.001.021", saldo_fisico=Decimal("8"))
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000406",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        item_a = requisicao.itens.create(
            material=material_a,
            unidade_medida=material_a.unidade_medida,
            quantidade_solicitada=Decimal("5"),
        )
        item_b = requisicao.itens.create(
            material=material_b,
            unidade_medida=material_b.unidade_medida,
            quantidade_solicitada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe)
        response = client.post(
            reverse("requisicao-authorize", args=[requisicao.id]),
            {
                "itens": [
                    {
                        "item_id": item_a.id,
                        "quantidade_autorizada": "4.000",
                        "justificativa_autorizacao_parcial": "",
                    },
                    {
                        "item_id": item_b.id,
                        "quantidade_autorizada": "0.000",
                        "justificativa_autorizacao_parcial": "",
                    },
                ]
            },
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert response.data["error"]["details"]["itens"][0]["justificativa_autorizacao_parcial"]
        assert response.data["error"]["details"]["itens"][1]["justificativa_autorizacao_parcial"]

        requisicao.refresh_from_db()
        material_a.estoque.refresh_from_db()
        material_b.estoque.refresh_from_db()
        assert requisicao.status == StatusRequisicao.AGUARDANDO_AUTORIZACAO
        assert not requisicao.eventos.exists()
        assert material_a.estoque.saldo_reservado == Decimal("0")
        assert material_b.estoque.saldo_reservado == Decimal("0")

    def test_authorize_rejeita_status_invalido(self):
        setor = self._criar_setor("Qualidade", "90021")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("10022", "Solicitante Qualidade", setor=setor)
        material = self._criar_material_com_estoque("001.001.018")
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            setor_beneficiario=setor,
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe)
        response = client.post(
            reverse("requisicao-authorize", args=[requisicao.id]),
            self._payload_autorizacao(item_id=item.id, quantidade_autorizada="1.000"),
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"

    def test_refuse_sem_motivo_falha_validacao(self):
        setor = self._criar_setor("Fiscalizacao", "90022")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("10023", "Solicitante Fiscalizacao", setor=setor)
        material = self._criar_material_com_estoque("001.001.019")
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000405",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe)
        response = client.post(
            reverse("requisicao-refuse", args=[requisicao.id]), {}, format="json"
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"

    def test_fila_autorizacao_retorna_apenas_setor_do_chefe(self):
        setor_a = self._criar_setor("Administrativo", "90013")
        setor_b = self._criar_setor("Obras B", "90014")
        chefe_a = setor_a.chefe_responsavel
        solicitante_a = self._criar_usuario("10014", "Solicitante A", setor=setor_a)
        solicitante_b = self._criar_usuario("10015", "Solicitante B", setor=setor_b)
        material = self._criar_material_com_estoque("001.001.011")

        req_a = Requisicao.objects.create(
            criador=solicitante_a,
            beneficiario=solicitante_a,
            numero_publico="REQ-2026-000300",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        req_a.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )
        req_b = Requisicao.objects.create(
            criador=solicitante_b,
            beneficiario=solicitante_b,
            numero_publico="REQ-2026-000301",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T11:00:00Z",
        )
        req_b.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe_a)
        response = client.get(reverse("requisicao-pending-approvals"))

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == req_a.id
        assert response.data["results"][0]["numero_publico"] == "REQ-2026-000300"
        assert response.data["results"][0]["total_itens"] == 1
        assert req_b.id not in [item["id"] for item in response.data["results"]]

    def test_fila_autorizacao_bloqueia_papel_sem_permissao(self):
        setor = self._criar_setor("Gabinete", "90015")
        solicitante = self._criar_usuario("10016", "Solicitante Gabinete", setor=setor)

        client = APIClient()
        client.force_authenticate(user=solicitante)
        response = client.get(reverse("requisicao-pending-approvals"))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"
