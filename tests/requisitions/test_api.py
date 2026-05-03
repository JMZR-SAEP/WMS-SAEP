from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.requisitions.models import EventoTimeline, Requisicao, StatusRequisicao, TipoEvento
from apps.stock.models import EstoqueMaterial, MovimentacaoEstoque, TipoMovimentacao
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
        is_superuser: bool = False,
    ) -> User:
        return User.objects.create(
            matricula_funcional=matricula,
            nome_completo=nome,
            papel=papel,
            setor=setor,
            is_active=is_active,
            is_superuser=is_superuser,
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

    @staticmethod
    def _criar_requisicao_com_item(
        *,
        criador: User,
        beneficiario: User,
        material: Material,
        status: str = StatusRequisicao.RASCUNHO,
        numero_publico: str | None = None,
        observacao: str = "",
        quantidade_solicitada: str = "2",
    ) -> Requisicao:
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario,
            status=status,
            numero_publico=numero_publico,
            observacao=observacao,
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal(quantidade_solicitada),
        )
        return requisicao

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

    def test_criacao_com_beneficiario_inexistente_retorna_not_found(self):
        setor = self._criar_setor("Cadastro", "900071")
        usuario = self._criar_usuario("100081", "Solicitante Cadastro", setor=setor)
        material = self._criar_material_com_estoque("001.001.051")

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(
            reverse("requisicao-list"),
            self._payload_requisicao(beneficiario_id=999999, material_id=material.id),
            format="json",
        )

        assert response.status_code == 404
        assert response.data["error"]["code"] == "not_found"

    def test_lista_requisicoes_visiveis_paginada_e_leve(self):
        setor = self._criar_setor("Operacoes", "900072")
        outro_setor = self._criar_setor("Financeiro", "900073")
        usuario = self._criar_usuario("100082", "Solicitante Operacoes", setor=setor)
        outro_usuario = self._criar_usuario("100083", "Solicitante Financeiro", setor=outro_setor)
        material = self._criar_material_com_estoque("001.001.052")

        rascunho = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            observacao="Rascunho visivel",
        )
        submetida = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000111",
            observacao="Requisicao enviada",
        )
        self._criar_requisicao_com_item(
            criador=outro_usuario,
            beneficiario=outro_usuario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000222",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("requisicao-list"))

        assert response.status_code == 200
        assert response.data["count"] == 2
        assert response.data["page"] == 1
        assert response.data["page_size"] == 20
        resultado_ids = [item["id"] for item in response.data["results"]]
        assert resultado_ids == [submetida.id, rascunho.id]
        assert response.data["results"][1]["numero_publico"] is None
        assert response.data["results"][0]["total_itens"] == 1
        assert "itens" not in response.data["results"][0]
        assert "eventos" not in response.data["results"][0]

    def test_lista_requisicoes_nao_autenticado_retorna_403(self):
        client = APIClient()

        response = client.get(reverse("requisicao-list"))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "not_authenticated"

    def test_lista_requisicoes_almoxarife_ve_todos_os_setores(self):
        setor_a = self._criar_setor("Almoxarifado", "900079")
        setor_b = self._criar_setor("Manutencao", "900080")
        almoxarife = self._criar_usuario(
            "100090",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor_a,
        )
        usuario_b = self._criar_usuario("100091", "Solicitante B", setor=setor_b)
        material = self._criar_material_com_estoque("001.001.057")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario_b,
            beneficiario=usuario_b,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000777",
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.get(reverse("requisicao-list"))

        assert response.status_code == 200
        assert response.data["count"] >= 1
        assert any(item["id"] == requisicao.id for item in response.data["results"])

    def test_lista_requisicoes_filtra_por_status_e_busca_textual(self):
        setor = self._criar_setor("Compras", "900074")
        usuario = self._criar_usuario("100084", "Solicitante Compras", setor=setor)
        material = self._criar_material_com_estoque("001.001.053")

        self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            observacao="Rascunho para edicao",
        )
        aguardando = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000333",
            observacao="Fluxo de autorizacao",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)

        response_status = client.get(
            reverse("requisicao-list"),
            {"status": StatusRequisicao.AGUARDANDO_AUTORIZACAO},
        )
        assert response_status.status_code == 200
        assert response_status.data["count"] == 1
        assert response_status.data["results"][0]["id"] == aguardando.id

        response_search = client.get(reverse("requisicao-list"), {"search": "000333"})
        assert response_search.status_code == 200
        assert response_search.data["count"] == 1
        assert response_search.data["results"][0]["id"] == aguardando.id

    def test_detail_retorna_itens_justificativas_e_eventos(self):
        setor = self._criar_setor("Patrimonio", "900075")
        usuario = self._criar_usuario("100085", "Solicitante Patrimonio", setor=setor)
        autorizador = self._criar_usuario(
            "100086",
            "Chefe Patrimonio",
            papel=PapelChoices.CHEFE_SETOR,
            setor=setor,
        )
        material = self._criar_material_com_estoque("001.001.054")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.AUTORIZADA,
            numero_publico="REQ-2026-000444",
        )
        item = requisicao.itens.get()
        item.quantidade_autorizada = Decimal("1")
        item.justificativa_autorizacao_parcial = "Saldo parcial"
        item.save(update_fields=["quantidade_autorizada", "justificativa_autorizacao_parcial"])
        EventoTimeline.objects.create(
            requisicao=requisicao,
            tipo_evento=TipoEvento.AUTORIZACAO_PARCIAL,
            usuario=autorizador,
            observacao="Autorizado parcialmente por saldo.",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("requisicao-detail", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["id"] == requisicao.id
        assert response.data["itens"][0]["justificativa_autorizacao_parcial"] == "Saldo parcial"
        assert response.data["eventos"][0]["tipo_evento"] == TipoEvento.AUTORIZACAO_PARCIAL
        assert response.data["eventos"][0]["usuario"]["id"] == autorizador.id
        assert response.data["eventos"][0]["observacao"] == "Autorizado parcialmente por saldo."

    def test_detail_requisicao_fora_do_escopo_retorna_404(self):
        setor_a = self._criar_setor("TI", "900076")
        setor_b = self._criar_setor("Frota", "900077")
        usuario = self._criar_usuario("100087", "Solicitante TI", setor=setor_a)
        outro_usuario = self._criar_usuario("100088", "Solicitante Frota", setor=setor_b)
        material = self._criar_material_com_estoque("001.001.055")
        requisicao = self._criar_requisicao_com_item(
            criador=outro_usuario,
            beneficiario=outro_usuario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000555",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("requisicao-detail", args=[requisicao.id]))

        assert response.status_code == 404
        assert response.data["error"]["code"] == "not_found"

    def test_detail_ignora_filtros_de_listagem_na_url(self):
        setor = self._criar_setor("Obras", "900078")
        usuario = self._criar_usuario("100089", "Solicitante Obras", setor=setor)
        material = self._criar_material_com_estoque("001.001.056")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000666",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(
            reverse("requisicao-detail", args=[requisicao.id]),
            {"status": StatusRequisicao.RASCUNHO, "search": "nao-corresponde"},
        )

        assert response.status_code == 200
        assert response.data["id"] == requisicao.id

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

    def test_update_draft_substitui_beneficiario_observacao_e_itens(self):
        setor = self._criar_setor("Patio", "900091")
        criador = self._criar_usuario(
            "100101",
            "Criador Patio",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor,
        )
        beneficiario_inicial = self._criar_usuario("100102", "Beneficiario Inicial", setor=setor)
        beneficiario_novo = self._criar_usuario("100103", "Beneficiario Novo", setor=setor)
        material_antigo = self._criar_material_com_estoque("001.001.071")
        material_atualizado = self._criar_material_com_estoque("001.001.072")
        material_novo = self._criar_material_com_estoque("001.001.073")
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario_inicial,
            observacao="Observacao antiga",
        )
        item_antigo = requisicao.itens.create(
            material=material_antigo,
            unidade_medida=material_antigo.unidade_medida,
            quantidade_solicitada=Decimal("1"),
            observacao="Item antigo",
        )
        requisicao.itens.create(
            material=material_atualizado,
            unidade_medida=material_atualizado.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            observacao="Item manter",
        )

        client = APIClient()
        client.force_authenticate(user=criador)
        response = client.put(
            reverse("requisicao-update-draft", args=[requisicao.id]),
            {
                "beneficiario_id": beneficiario_novo.id,
                "observacao": "Observacao nova",
                "itens": [
                    {
                        "material_id": material_atualizado.id,
                        "quantidade_solicitada": "5.000",
                        "observacao": "Item atualizado",
                    },
                    {
                        "material_id": material_novo.id,
                        "quantidade_solicitada": "3.000",
                        "observacao": "Item novo",
                    },
                ],
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.RASCUNHO
        assert response.data["beneficiario"]["id"] == beneficiario_novo.id
        assert response.data["observacao"] == "Observacao nova"
        assert len(response.data["itens"]) == 2
        assert {
            (
                item["material"]["id"],
                item["quantidade_solicitada"],
                item["observacao"],
            )
            for item in response.data["itens"]
        } == {
            (material_atualizado.id, "5.000", "Item atualizado"),
            (material_novo.id, "3.000", "Item novo"),
        }

        requisicao.refresh_from_db()
        assert requisicao.beneficiario_id == beneficiario_novo.id
        assert requisicao.setor_beneficiario_id == beneficiario_novo.setor_id
        assert requisicao.observacao == "Observacao nova"
        assert not requisicao.itens.filter(id=item_antigo.id).exists()
        assert {
            (
                item.material_id,
                item.quantidade_solicitada,
                item.observacao,
            )
            for item in requisicao.itens.all()
        } == {
            (material_atualizado.id, Decimal("5.000"), "Item atualizado"),
            (material_novo.id, Decimal("3.000"), "Item novo"),
        }

    def test_update_draft_bloqueia_requisicao_fora_de_rascunho(self):
        setor = self._criar_setor("Patio Status", "900092")
        criador = self._criar_usuario(
            "100111",
            "Criador Patio Status",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor,
        )
        beneficiario = self._criar_usuario("100112", "Beneficiario Status", setor=setor)
        material = self._criar_material_com_estoque("001.001.074")
        requisicao = self._criar_requisicao_com_item(
            criador=criador,
            beneficiario=beneficiario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000321",
        )

        client = APIClient()
        client.force_authenticate(user=criador)
        response = client.put(
            reverse("requisicao-update-draft", args=[requisicao.id]),
            self._payload_requisicao(beneficiario_id=beneficiario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
        assert response.data["error"]["details"]["status_atual"] == (
            StatusRequisicao.AGUARDANDO_AUTORIZACAO
        )

    def test_update_draft_bloqueia_usuario_sem_permissao(self):
        setor = self._criar_setor("Patio Permissao", "900093")
        outro_setor = self._criar_setor("Outro Patio", "900094")
        criador = self._criar_usuario("100121", "Criador", setor=setor)
        beneficiario = self._criar_usuario("100122", "Beneficiario", setor=setor)
        intruso = self._criar_usuario("100123", "Intruso", setor=outro_setor)
        material = self._criar_material_com_estoque("001.001.075")
        requisicao = self._criar_requisicao_com_item(
            criador=criador,
            beneficiario=beneficiario,
            material=material,
        )

        client = APIClient()
        client.force_authenticate(user=intruso)
        response = client.put(
            reverse("requisicao-update-draft", args=[requisicao.id]),
            self._payload_requisicao(beneficiario_id=beneficiario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 404

    def test_update_draft_exige_autenticacao(self):
        setor = self._criar_setor("Patio Auth", "900095")
        usuario = self._criar_usuario("100131", "Usuario Auth", setor=setor)
        material = self._criar_material_com_estoque("001.001.076")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
        )

        client = APIClient()
        response = client.put(
            reverse("requisicao-update-draft", args=[requisicao.id]),
            self._payload_requisicao(beneficiario_id=usuario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "not_authenticated"

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

    def test_fila_atendimento_lista_requisicoes_autorizadas_para_almoxarifado(self):
        setor = self._criar_setor("Saneamento", "90030")
        almoxarife = self._criar_usuario(
            "10030",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        solicitante = self._criar_usuario("10031", "Solicitante Saneamento", setor=setor)
        material = self._criar_material_com_estoque(
            "001.001.030",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("2"),
        )
        autorizada = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000500",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        autorizada.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )
        pendente = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000501",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        pendente.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.get(reverse("requisicao-pending-fulfillments"))

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == autorizada.id
        assert response.data["results"][0]["numero_publico"] == "REQ-2026-000500"
        assert response.data["results"][0]["chefe_autorizador"] is None
        assert response.data["results"][0]["total_itens"] == 1
        assert pendente.id not in [item["id"] for item in response.data["results"]]

    def test_fila_atendimento_almoxarifado_ve_requisicoes_de_outros_setores(self):
        setor_almoxarifado = self._criar_setor("Almoxarifado", "90035")
        setor_obras = self._criar_setor("Obras", "90036")
        almoxarife = self._criar_usuario(
            "10038",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor_almoxarifado,
        )
        solicitante_obras = self._criar_usuario(
            "10039",
            "Solicitante Obras",
            setor=setor_obras,
        )
        material = self._criar_material_com_estoque(
            "001.001.034",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("2"),
        )
        autorizada_outro_setor = Requisicao.objects.create(
            criador=solicitante_obras,
            beneficiario=solicitante_obras,
            setor_beneficiario=setor_obras,
            numero_publico="REQ-2026-000505",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        autorizada_outro_setor.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.get(reverse("requisicao-pending-fulfillments"))

        # matriz-permissoes.md: Almoxarifado vê requisições de todos os setores
        # e fila de atendimento; não há isolamento por setor nesta fila.
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == autorizada_outro_setor.id
        assert response.data["results"][0]["setor_beneficiario"]["id"] == setor_obras.id

    def test_fila_atendimento_bloqueia_papel_sem_permissao(self):
        setor = self._criar_setor("Apoio Operacional", "90031")
        solicitante = self._criar_usuario("10032", "Solicitante Apoio", setor=setor)

        client = APIClient()
        client.force_authenticate(user=solicitante)
        response = client.get(reverse("requisicao-pending-fulfillments"))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_fila_atendimento_bloqueia_superuser(self):
        setor = self._criar_setor("Apoio Superuser", "90037")
        superuser = self._criar_usuario(
            "10042",
            "Superuser Apoio",
            setor=setor,
            is_superuser=True,
        )

        client = APIClient()
        client.force_authenticate(user=superuser)
        response = client.get(reverse("requisicao-pending-fulfillments"))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_fila_atendimento_bloqueia_usuario_inativo(self):
        setor = self._criar_setor("Apoio Inativo", "90038")
        usuario_inativo = self._criar_usuario(
            "10043",
            "Usuario Inativo Apoio",
            setor=setor,
            is_active=False,
        )

        client = APIClient()
        client.force_authenticate(user=usuario_inativo)
        response = client.get(reverse("requisicao-pending-fulfillments"))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_fulfill_atendimento_completo_baixa_estoque_e_registra_retirada(self):
        setor = self._criar_setor("Manutencao", "90032")
        solicitante = self._criar_usuario("10033", "Solicitante Manutencao", setor=setor)
        almoxarife = self._criar_usuario(
            "10034",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.031",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000502",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {
                "retirante_fisico": "Servidor Retirante",
                "observacao_atendimento": "Entrega no balcão",
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.ATENDIDA
        assert response.data["responsavel_atendimento"]["id"] == almoxarife.id
        assert response.data["retirante_fisico"] == "Servidor Retirante"
        assert response.data["observacao_atendimento"] == "Entrega no balcão"
        assert response.data["itens"][0]["quantidade_entregue"] == "3.000"
        requisicao.refresh_from_db()
        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.ATENDIMENTO).exists()
        assert item.quantidade_entregue == Decimal("3")
        assert material.estoque.saldo_fisico == Decimal("4")
        assert material.estoque.saldo_reservado == Decimal("0")

    def test_fulfill_com_itens_registra_atendimento_parcial_e_libera_reserva(self):
        setor = self._criar_setor("Manutencao Parcial", "90039")
        solicitante = self._criar_usuario("10044", "Solicitante Manutencao Parcial", setor=setor)
        almoxarife = self._criar_usuario(
            "10045",
            "Auxiliar Almoxarifado Parcial",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.036",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000507",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {
                "retirante_fisico": "Servidor Parcial",
                "itens": [
                    {
                        "item_id": item.id,
                        "quantidade_entregue": "1.000",
                        "justificativa_atendimento_parcial": "Saldo físico divergente",
                    }
                ],
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.ATENDIDA_PARCIALMENTE
        assert response.data["retirante_fisico"] == "Servidor Parcial"
        assert response.data["itens"][0]["quantidade_entregue"] == "1.000"
        assert (
            response.data["itens"][0]["justificativa_atendimento_parcial"]
            == "Saldo físico divergente"
        )
        requisicao.refresh_from_db()
        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.ATENDIMENTO_PARCIAL).exists()
        assert item.quantidade_entregue == Decimal("1")
        assert material.estoque.saldo_fisico == Decimal("6")
        assert material.estoque.saldo_reservado == Decimal("0")
        assert MovimentacaoEstoque.objects.filter(
            requisicao=requisicao,
            tipo=TipoMovimentacao.SAIDA_POR_ATENDIMENTO,
            quantidade=Decimal("1"),
        ).exists()
        assert MovimentacaoEstoque.objects.filter(
            requisicao=requisicao,
            tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
            quantidade=Decimal("2"),
        ).exists()

    def test_fulfill_com_itens_multi_item_mistura_entrega_total_e_parcial(self):
        setor = self._criar_setor("Manutencao Multi Item", "90052")
        solicitante = self._criar_usuario("10062", "Solicitante Multi Item", setor=setor)
        almoxarife = self._criar_usuario(
            "10063",
            "Auxiliar Almoxarifado Multi Item",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material_total = self._criar_material_com_estoque(
            "001.001.052",
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("4"),
        )
        material_parcial = self._criar_material_com_estoque(
            "001.001.053",
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("5"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000512",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item_total = requisicao.itens.create(
            material=material_total,
            unidade_medida=material_total.unidade_medida,
            quantidade_solicitada=Decimal("4"),
            quantidade_autorizada=Decimal("4"),
        )
        item_parcial = requisicao.itens.create(
            material=material_parcial,
            unidade_medida=material_parcial.unidade_medida,
            quantidade_solicitada=Decimal("5"),
            quantidade_autorizada=Decimal("5"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {
                "itens": [
                    {"item_id": item_total.id, "quantidade_entregue": "4.000"},
                    {
                        "item_id": item_parcial.id,
                        "quantidade_entregue": "2.000",
                        "justificativa_atendimento_parcial": "Retirada parcial solicitada",
                    },
                ],
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.ATENDIDA_PARCIALMENTE
        requisicao.refresh_from_db()
        item_total.refresh_from_db()
        item_parcial.refresh_from_db()
        material_total.estoque.refresh_from_db()
        material_parcial.estoque.refresh_from_db()
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.ATENDIMENTO_PARCIAL).exists()
        assert item_total.quantidade_entregue == Decimal("4")
        assert item_total.justificativa_atendimento_parcial == ""
        assert item_parcial.quantidade_entregue == Decimal("2")
        assert item_parcial.justificativa_atendimento_parcial == "Retirada parcial solicitada"
        assert material_total.estoque.saldo_fisico == Decimal("6")
        assert material_total.estoque.saldo_reservado == Decimal("0")
        assert material_parcial.estoque.saldo_fisico == Decimal("8")
        assert material_parcial.estoque.saldo_reservado == Decimal("0")
        assert not MovimentacaoEstoque.objects.filter(
            requisicao=requisicao,
            item_requisicao=item_total,
            tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
        ).exists()
        assert MovimentacaoEstoque.objects.filter(
            requisicao=requisicao,
            item_requisicao=item_parcial,
            tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
            quantidade=Decimal("3"),
        ).exists()

    def test_fulfill_com_itens_rejeita_parcial_sem_justificativa(self):
        setor = self._criar_setor("Manutencao Sem Justificativa", "90040")
        solicitante = self._criar_usuario("10046", "Solicitante Sem Justificativa", setor=setor)
        almoxarife = self._criar_usuario(
            "10047",
            "Auxiliar Almoxarifado Sem Justificativa",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.037",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000508",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {"itens": [{"item_id": item.id, "quantidade_entregue": "1.000"}]},
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert item.quantidade_entregue == Decimal("0")
        assert material.estoque.saldo_fisico == Decimal("7")
        assert material.estoque.saldo_reservado == Decimal("3")
        assert not MovimentacaoEstoque.objects.filter(requisicao=requisicao).exists()

    def test_fulfill_com_itens_rejeita_entrega_acima_do_autorizado(self):
        setor = self._criar_setor("Manutencao Excesso", "90041")
        solicitante = self._criar_usuario("10048", "Solicitante Excesso", setor=setor)
        almoxarife = self._criar_usuario(
            "10049",
            "Auxiliar Almoxarifado Excesso",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.038",
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000509",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {
                "itens": [
                    {
                        "item_id": item.id,
                        "quantidade_entregue": "5.000",
                        "justificativa_atendimento_parcial": "Erro de quantidade",
                    }
                ]
            },
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert item.quantidade_entregue == Decimal("0")
        assert material.estoque.saldo_fisico == Decimal("10")
        assert material.estoque.saldo_reservado == Decimal("3")
        assert not MovimentacaoEstoque.objects.filter(requisicao=requisicao).exists()

    def test_fulfill_todos_itens_zerados_rejeita_sem_efeitos(self):
        setor = self._criar_setor("Manutencao Zero Total", "90053")
        solicitante = self._criar_usuario("10064", "Solicitante Zero Total", setor=setor)
        almoxarife = self._criar_usuario(
            "10065",
            "Auxiliar Almoxarifado Zero Total",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.054",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000513",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {
                "itens": [
                    {
                        "item_id": item.id,
                        "quantidade_entregue": "0.000",
                        "justificativa_atendimento_parcial": "Sem saldo físico",
                    }
                ]
            },
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert item.quantidade_entregue == Decimal("0")
        assert material.estoque.saldo_fisico == Decimal("7")
        assert material.estoque.saldo_reservado == Decimal("3")
        assert not MovimentacaoEstoque.objects.filter(requisicao=requisicao).exists()

    def test_cancel_autorizada_sem_saldo_libera_reserva(self):
        setor = self._criar_setor("Cancelamento Operacional", "90055")
        solicitante = self._criar_usuario("10068", "Solicitante Cancelamento", setor=setor)
        almoxarife = self._criar_usuario(
            "10069",
            "Auxiliar Almoxarifado Cancelamento",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.057",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000515",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-cancel", args=[requisicao.id]),
            {"motivo_cancelamento": "Saldo físico zerado no momento da retirada"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.CANCELADA
        assert response.data["motivo_cancelamento"] == "Saldo físico zerado no momento da retirada"
        requisicao.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.responsavel_atendimento_id == almoxarife.id
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.CANCELAMENTO).exists()
        assert material.estoque.saldo_fisico == Decimal("0")
        assert material.estoque.saldo_reservado == Decimal("0")
        assert MovimentacaoEstoque.objects.filter(
            requisicao=requisicao,
            item_requisicao=item,
            tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
            quantidade=Decimal("3"),
        ).exists()

    def test_cancel_autorizada_sem_saldo_permite_criador(self):
        setor = self._criar_setor("Cancelamento Criador", "90061")
        solicitante = self._criar_usuario("10077", "Solicitante Criador", setor=setor)
        material = self._criar_material_com_estoque(
            "001.001.062",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000520",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=solicitante)
        response = client.post(
            reverse("requisicao-cancel", args=[requisicao.id]),
            {"motivo_cancelamento": "Sem saldo fisico para retirada"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.CANCELADA
        requisicao.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.responsavel_atendimento_id == solicitante.id
        assert material.estoque.saldo_reservado == Decimal("0")

    def test_cancel_autorizada_sem_saldo_exige_motivo(self):
        setor = self._criar_setor("Cancelamento Motivo", "90056")
        solicitante = self._criar_usuario("10070", "Solicitante Motivo", setor=setor)
        almoxarife = self._criar_usuario(
            "10071",
            "Auxiliar Almoxarifado Motivo",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.058",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000516",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-cancel", args=[requisicao.id]),
            {"motivo_cancelamento": "   "},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        requisicao.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.status == StatusRequisicao.AUTORIZADA
        assert material.estoque.saldo_reservado == Decimal("2")

    def test_cancel_autorizada_sem_saldo_bloqueia_quando_ainda_ha_saldo_fisico(self):
        setor = self._criar_setor("Cancelamento Parcial", "90057")
        solicitante = self._criar_usuario("10072", "Solicitante Parcial", setor=setor)
        almoxarife = self._criar_usuario(
            "10073",
            "Auxiliar Almoxarifado Parcial",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.059",
            saldo_fisico=Decimal("1"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000517",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-cancel", args=[requisicao.id]),
            {"motivo_cancelamento": "Tentativa de cancelar com saldo restante"},
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
        requisicao.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.status == StatusRequisicao.AUTORIZADA
        assert material.estoque.saldo_reservado == Decimal("3")

    def test_cancel_autorizada_sem_saldo_bloqueia_usuario_sem_permissao(self):
        setor = self._criar_setor("Cancelamento Permissao", "90058")
        solicitante = self._criar_usuario("10074", "Solicitante Permissao", setor=setor)
        chefe_setor = setor.chefe_responsavel
        material = self._criar_material_com_estoque(
            "001.001.060",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000518",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe_setor)
        response = client.post(
            reverse("requisicao-cancel", args=[requisicao.id]),
            {"motivo_cancelamento": "Sem saldo físico"},
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"
        requisicao.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.status == StatusRequisicao.AUTORIZADA
        assert material.estoque.saldo_reservado == Decimal("2")

    def test_cancel_autorizada_sem_saldo_unauthenticated(self):
        setor = self._criar_setor("Cancelamento Auth", "90059")
        solicitante = self._criar_usuario("10075", "Solicitante Auth", setor=setor)
        material = self._criar_material_com_estoque(
            "001.001.061",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000519",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        response = client.post(
            reverse("requisicao-cancel", args=[requisicao.id]),
            {"motivo_cancelamento": "Sem credenciais"},
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "not_authenticated"

    def test_cancel_autorizada_sem_saldo_not_found(self):
        setor = self._criar_setor("Cancelamento Not Found", "90060")
        almoxarife = self._criar_usuario(
            "10076",
            "Auxiliar Almoxarifado Not Found",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-cancel", args=[999999]),
            {"motivo_cancelamento": "Requisição inexistente"},
            format="json",
        )

        assert response.status_code == 404

    def test_fulfill_payload_incompleto_retorna_validation_error(self):
        setor = self._criar_setor("Manutencao Payload", "90054")
        solicitante = self._criar_usuario("10066", "Solicitante Payload", setor=setor)
        almoxarife = self._criar_usuario(
            "10067",
            "Auxiliar Almoxarifado Payload",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material_a = self._criar_material_com_estoque(
            "001.001.055",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("2"),
        )
        material_b = self._criar_material_com_estoque(
            "001.001.056",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000514",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item_a = requisicao.itens.create(
            material=material_a,
            unidade_medida=material_a.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )
        item_b = requisicao.itens.create(
            material=material_b,
            unidade_medida=material_b.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {"itens": [{"item_id": item_a.id, "quantidade_entregue": "2.000"}]},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert response.data["error"]["details"]["item_ids"] == [str(item_b.id)]

    def test_fulfill_bloqueia_usuario_sem_permissao(self):
        setor = self._criar_setor("Controle", "90033")
        solicitante = self._criar_usuario("10035", "Solicitante Controle", setor=setor)
        material = self._criar_material_com_estoque(
            "001.001.032",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000503",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=solicitante)
        response = client.post(reverse("requisicao-fulfill", args=[requisicao.id]), {})

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_fulfill_requisicao_fora_do_escopo_visivel_retorna_404(self):
        setor_origem = self._criar_setor("Controle Origem", "90042")
        setor_externo = self._criar_setor("Controle Externo", "90043")
        solicitante = self._criar_usuario("10050", "Solicitante Origem", setor=setor_origem)
        usuario_externo = self._criar_usuario("10051", "Solicitante Externo", setor=setor_externo)
        material = self._criar_material_com_estoque(
            "001.001.039",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor_origem,
            numero_publico="REQ-2026-000510",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario_externo)
        response = client.post(reverse("requisicao-fulfill", args=[requisicao.id]), {})

        assert response.status_code == 404

    def test_fulfill_bloqueia_superuser(self):
        setor = self._criar_setor("Controle Superior", "90035")
        solicitante = self._criar_usuario("10038", "Solicitante Controle Superior", setor=setor)
        superuser = self._criar_usuario(
            "10039",
            "Superuser Controle",
            papel=PapelChoices.SOLICITANTE,
            setor=setor,
            is_superuser=True,
        )
        material = self._criar_material_com_estoque(
            "001.001.034",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000505",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=superuser)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {"itens": [{"item_id": item.id, "quantidade_entregue": "2.000"}]},
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_fulfill_bloqueia_usuario_inativo(self):
        setor = self._criar_setor("Controle Inativo", "90036")
        solicitante = self._criar_usuario("10040", "Solicitante Controle Inativo", setor=setor)
        usuario_inativo = self._criar_usuario(
            "10041",
            "Usuario Inativo",
            setor=setor,
            is_active=False,
        )
        material = self._criar_material_com_estoque(
            "001.001.035",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000506",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario_inativo)
        response = client.post(reverse("requisicao-fulfill", args=[requisicao.id]), {})

        assert response.status_code == 404

    def test_fulfill_bloqueia_status_invalido(self):
        setor = self._criar_setor("Planejamento Campo", "90034")
        solicitante = self._criar_usuario("10036", "Solicitante Campo", setor=setor)
        almoxarife = self._criar_usuario(
            "10037",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque("001.001.033")
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000504",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(reverse("requisicao-fulfill", args=[requisicao.id]), {})

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
