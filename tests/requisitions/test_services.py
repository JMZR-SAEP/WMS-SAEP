from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import close_old_connections
from rest_framework.exceptions import ValidationError

from apps.core.api.exceptions import DomainConflict
from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.requisitions.models import (
    EventoTimeline,
    ItemRequisicao,
    Requisicao,
    StatusRequisicao,
    TipoEvento,
)
from apps.requisitions.services import (
    ItemAutorizacaoData,
    _gerar_numero_publico,
    autorizar_requisicao,
    recusar_requisicao,
)
from apps.stock.models import EstoqueMaterial, MovimentacaoEstoque, TipoMovimentacao
from apps.users.models import PapelChoices, Setor, User


@pytest.mark.django_db(transaction=True)
class TestSequenciaNumeroRequisicaoService:
    def test_gera_numeros_incrementais_no_mesmo_ano(self):
        primeiro = _gerar_numero_publico(ano=2026)
        segundo = _gerar_numero_publico(ano=2026)

        assert primeiro == "REQ-2026-000001"
        assert segundo == "REQ-2026-000002"

    def test_reinicia_sequencia_em_novo_ano(self):
        numero_2026 = _gerar_numero_publico(ano=2026)
        numero_2027 = _gerar_numero_publico(ano=2027)

        assert numero_2026 == "REQ-2026-000001"
        assert numero_2027 == "REQ-2027-000001"


@pytest.mark.django_db(transaction=True)
class TestAutorizacaoRequisicaoService:
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
            is_active=True,
        )
        EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=saldo_fisico,
            saldo_reservado=saldo_reservado,
        )
        return material

    @staticmethod
    def _criar_requisicao_aguardando(
        *,
        criador: User,
        beneficiario: User,
        numero_publico: str,
        item_quantidade: Decimal,
        material: Material,
    ) -> tuple[Requisicao, ItemRequisicao]:
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario,
            numero_publico=numero_publico,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=item_quantidade,
        )
        return requisicao, item

    def test_autoriza_total_persiste_reserva_e_timeline(self):
        setor = self._criar_setor("Compras", "91001")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11001", "Solicitante Compras", setor=setor)
        material = self._criar_material_com_estoque("001.002.001", saldo_fisico=Decimal("10"))
        requisicao, item = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100001",
            item_quantidade=Decimal("4"),
            material=material,
        )

        autorizado = autorizar_requisicao(
            requisicao=requisicao,
            ator=chefe,
            itens=[
                ItemAutorizacaoData(
                    item_id=item.id,
                    quantidade_autorizada=Decimal("4"),
                )
            ],
        )

        autorizado.refresh_from_db()
        item.refresh_from_db()
        material.estoque.refresh_from_db()

        assert autorizado.status == StatusRequisicao.AUTORIZADA
        assert autorizado.chefe_autorizador_id == chefe.id
        assert autorizado.eventos.filter(tipo_evento=TipoEvento.AUTORIZACAO_TOTAL).exists()
        assert item.quantidade_autorizada == Decimal("4")
        assert item.justificativa_autorizacao_parcial == ""
        assert material.estoque.saldo_fisico == Decimal("10")
        assert material.estoque.saldo_reservado == Decimal("4")
        assert MovimentacaoEstoque.objects.filter(
            tipo=TipoMovimentacao.RESERVA_POR_AUTORIZACAO,
            requisicao=autorizado,
            item_requisicao=item,
        ).count() == 1

    def test_autoriza_parcial_e_zero_com_justificativa(self):
        setor = self._criar_setor("Apoio", "91002")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11002", "Solicitante Apoio", setor=setor)
        material_a = self._criar_material_com_estoque("001.002.002", saldo_fisico=Decimal("8"))
        material_b = self._criar_material_com_estoque("001.002.003", saldo_fisico=Decimal("8"))
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100002",
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

        autorizado = autorizar_requisicao(
            requisicao=requisicao,
            ator=chefe,
            itens=[
                ItemAutorizacaoData(
                    item_id=item_a.id,
                    quantidade_autorizada=Decimal("4"),
                    justificativa_autorizacao_parcial="Saldo limitado",
                ),
                ItemAutorizacaoData(
                    item_id=item_b.id,
                    quantidade_autorizada=Decimal("0"),
                    justificativa_autorizacao_parcial="Sem prioridade",
                ),
            ],
        )

        autorizado.refresh_from_db()
        item_a.refresh_from_db()
        item_b.refresh_from_db()
        material_a.estoque.refresh_from_db()
        material_b.estoque.refresh_from_db()

        assert autorizado.status == StatusRequisicao.AUTORIZADA
        assert autorizado.eventos.filter(tipo_evento=TipoEvento.AUTORIZACAO_PARCIAL).exists()
        assert item_a.quantidade_autorizada == Decimal("4")
        assert item_a.justificativa_autorizacao_parcial == "Saldo limitado"
        assert item_b.quantidade_autorizada == Decimal("0")
        assert item_b.justificativa_autorizacao_parcial == "Sem prioridade"
        assert material_a.estoque.saldo_reservado == Decimal("4")
        assert material_b.estoque.saldo_reservado == Decimal("0")

    def test_autoriza_parcial_sem_justificativa_falha(self):
        setor = self._criar_setor("Oficina", "91003")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11003", "Solicitante Oficina", setor=setor)
        material = self._criar_material_com_estoque("001.002.004", saldo_fisico=Decimal("8"))
        requisicao, item = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100003",
            item_quantidade=Decimal("5"),
            material=material,
        )

        with pytest.raises(ValidationError):
            autorizar_requisicao(
                requisicao=requisicao,
                ator=chefe,
                itens=[
                    ItemAutorizacaoData(
                        item_id=item.id,
                        quantidade_autorizada=Decimal("4"),
                    )
                ],
            )

    def test_autoriza_todos_itens_zerados_falha(self):
        setor = self._criar_setor("Financeiro", "91004")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11004", "Solicitante Financeiro", setor=setor)
        material = self._criar_material_com_estoque("001.002.005", saldo_fisico=Decimal("8"))
        requisicao, item = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100004",
            item_quantidade=Decimal("5"),
            material=material,
        )

        with pytest.raises(DomainConflict):
            autorizar_requisicao(
                requisicao=requisicao,
                ator=chefe,
                itens=[
                    ItemAutorizacaoData(
                        item_id=item.id,
                        quantidade_autorizada=Decimal("0"),
                        justificativa_autorizacao_parcial="Não autorizado",
                    )
                ],
            )

    def test_autoriza_recalcula_saldo_atual(self):
        setor = self._criar_setor("Patrimonio", "91005")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11005", "Solicitante Patrimonio", setor=setor)
        material = self._criar_material_com_estoque("001.002.006", saldo_fisico=Decimal("5"))
        requisicao, item = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100005",
            item_quantidade=Decimal("4"),
            material=material,
        )
        material.estoque.saldo_fisico = Decimal("2")
        material.estoque.save(update_fields=["saldo_fisico", "updated_at"])

        with pytest.raises(DomainConflict):
            autorizar_requisicao(
                requisicao=requisicao,
                ator=chefe,
                itens=[
                    ItemAutorizacaoData(
                        item_id=item.id,
                        quantidade_autorizada=Decimal("4"),
                    )
                ],
            )

    def test_recusa_exige_motivo_e_nao_reserva(self):
        setor = self._criar_setor("Transporte", "91006")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11006", "Solicitante Transporte", setor=setor)
        material = self._criar_material_com_estoque("001.002.007", saldo_fisico=Decimal("5"))
        requisicao, _ = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100006",
            item_quantidade=Decimal("2"),
            material=material,
        )

        recusada = recusar_requisicao(
            requisicao=requisicao,
            ator=chefe,
            motivo_recusa="Requisição fora de prioridade",
        )

        recusada.refresh_from_db()
        material.estoque.refresh_from_db()

        assert recusada.status == StatusRequisicao.RECUSADA
        assert recusada.motivo_recusa == "Requisição fora de prioridade"
        assert recusada.chefe_autorizador_id == chefe.id
        assert recusada.eventos.filter(tipo_evento=TipoEvento.RECUSA).exists()
        assert material.estoque.saldo_reservado == Decimal("0")
        assert MovimentacaoEstoque.objects.filter(
            requisicao=recusada,
            tipo=TipoMovimentacao.RESERVA_POR_AUTORIZACAO,
        ).count() == 0

    def test_recusa_sem_motivo_falha(self):
        setor = self._criar_setor("Apoio Administrativo", "91007")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11007", "Solicitante Apoio Administrativo", setor=setor)
        material = self._criar_material_com_estoque("001.002.008")
        requisicao, _ = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100007",
            item_quantidade=Decimal("1"),
            material=material,
        )

        with pytest.raises(ValidationError):
            recusar_requisicao(requisicao=requisicao, ator=chefe, motivo_recusa="   ")

    def test_autorizacoes_concorrentes_nao_dividem_mesmo_saldo(self):
        setor = self._criar_setor("Logistica", "91008")
        chefe = setor.chefe_responsavel
        requisitante_a = self._criar_usuario("11008", "Solicitante A", setor=setor)
        requisitante_b = self._criar_usuario("11009", "Solicitante B", setor=setor)
        material = self._criar_material_com_estoque("001.002.009", saldo_fisico=Decimal("5"))
        req_a, item_a = self._criar_requisicao_aguardando(
            criador=requisitante_a,
            beneficiario=requisitante_a,
            numero_publico="REQ-2026-100008",
            item_quantidade=Decimal("5"),
            material=material,
        )
        req_b, item_b = self._criar_requisicao_aguardando(
            criador=requisitante_b,
            beneficiario=requisitante_b,
            numero_publico="REQ-2026-100009",
            item_quantidade=Decimal("5"),
            material=material,
        )

        barrier = Barrier(2)

        def autorizar(req_id: int, item_id: int):
            close_old_connections()
            try:
                barrier.wait()
                requisicao = Requisicao.objects.get(pk=req_id)
                autorizar_requisicao(
                    requisicao=requisicao,
                    ator=chefe,
                    itens=[
                        ItemAutorizacaoData(
                            item_id=item_id,
                            quantidade_autorizada=Decimal("5"),
                        )
                    ],
                )
                return "ok"
            except Exception as exc:  # noqa: BLE001
                return type(exc).__name__
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultado_a = executor.submit(autorizar, req_a.id, item_a.id)
            resultado_b = executor.submit(autorizar, req_b.id, item_b.id)

        resultados = {resultado_a.result(), resultado_b.result()}
        close_old_connections()

        material.estoque.refresh_from_db()
        req_a.refresh_from_db()
        req_b.refresh_from_db()

        assert resultados == {"ok", "DomainConflict"}
        assert material.estoque.saldo_reservado == Decimal("5")
        assert {req_a.status, req_b.status} == {
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            StatusRequisicao.AUTORIZADA,
        }
