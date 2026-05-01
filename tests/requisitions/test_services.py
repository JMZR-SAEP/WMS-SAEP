from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import close_old_connections
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.api.exceptions import DomainConflict
from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.requisitions.models import (
    ItemRequisicao,
    Requisicao,
    StatusRequisicao,
    TipoEvento,
)
from apps.requisitions.services import (
    ItemAtendimentoData,
    ItemAutorizacaoData,
    _gerar_numero_publico,
    atender_requisicao_com_itens,
    atender_requisicao_completa,
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
            setor_beneficiario=beneficiario.setor,
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
        assert (
            MovimentacaoEstoque.objects.filter(
                tipo=TipoMovimentacao.RESERVA_POR_AUTORIZACAO,
                requisicao=autorizado,
                item_requisicao=item,
            ).count()
            == 1
        )

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

    def test_autoriza_parcial_com_justificativa_so_com_espacos_falha(self):
        setor = self._criar_setor("Oficina Pesada", "91031")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11031", "Solicitante Oficina Pesada", setor=setor)
        material = self._criar_material_com_estoque("001.002.031", saldo_fisico=Decimal("8"))
        requisicao, item = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100031",
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
                        justificativa_autorizacao_parcial="   ",
                    )
                ],
            )

    def test_autoriza_quantidade_negativa_falha_no_service(self):
        setor = self._criar_setor("Planejamento", "91032")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11032", "Solicitante Planejamento", setor=setor)
        material = self._criar_material_com_estoque("001.002.032", saldo_fisico=Decimal("8"))
        requisicao, item = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100032",
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
                        quantidade_autorizada=Decimal("-1"),
                        justificativa_autorizacao_parcial="Inválida",
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
        assert (
            MovimentacaoEstoque.objects.filter(
                requisicao=recusada,
                tipo=TipoMovimentacao.RESERVA_POR_AUTORIZACAO,
            ).count()
            == 0
        )

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

    @pytest.mark.postgres
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


@pytest.mark.django_db(transaction=True)
class TestAtendimentoRequisicaoService:
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
    def _criar_requisicao_autorizada(
        *,
        criador: User,
        beneficiario: User,
        numero_publico: str,
        material: Material,
        quantidade_autorizada: Decimal,
    ) -> tuple[Requisicao, ItemRequisicao]:
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario,
            setor_beneficiario=beneficiario.setor,
            numero_publico=numero_publico,
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=quantidade_autorizada,
            quantidade_autorizada=quantidade_autorizada,
        )
        return requisicao, item

    def test_atendimento_completo_baixa_fisico_consumindo_reserva_e_timeline(self):
        setor = self._criar_setor("Operacional", "92001")
        requisitante = self._criar_usuario("12001", "Solicitante Operacional", setor=setor)
        atendente = self._criar_usuario(
            "12002",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.001",
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("4"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200001",
            material=material,
            quantidade_autorizada=Decimal("4"),
        )

        atendida = atender_requisicao_completa(
            requisicao=requisicao,
            ator=atendente,
            retirante_fisico="Servidor retirante",
            observacao_atendimento="Retirada no balcão",
        )

        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert atendida.status == StatusRequisicao.ATENDIDA
        assert atendida.responsavel_atendimento_id == atendente.id
        assert atendida.retirante_fisico == "Servidor retirante"
        assert atendida.observacao_atendimento == "Retirada no balcão"
        assert atendida.eventos.filter(tipo_evento=TipoEvento.ATENDIMENTO).exists()
        assert item.quantidade_entregue == Decimal("4")
        assert material.estoque.saldo_fisico == Decimal("6")
        assert material.estoque.saldo_reservado == Decimal("0")
        assert MovimentacaoEstoque.objects.filter(
            requisicao=atendida,
            item_requisicao=item,
            tipo=TipoMovimentacao.SAIDA_POR_ATENDIMENTO,
        ).exists()

    def test_atendimento_completo_ignora_item_autorizado_zero(self):
        setor = self._criar_setor("Oficina", "92002")
        requisitante = self._criar_usuario("12003", "Solicitante Oficina", setor=setor)
        atendente = self._criar_usuario(
            "12004",
            "Chefe Almoxarifado",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
            setor=setor,
        )
        material_a = self._criar_material_com_estoque(
            "001.003.002",
            saldo_fisico=Decimal("8"),
            saldo_reservado=Decimal("3"),
        )
        material_b = self._criar_material_com_estoque("001.003.003", saldo_fisico=Decimal("8"))
        requisicao, item_a = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200002",
            material=material_a,
            quantidade_autorizada=Decimal("3"),
        )
        item_b = requisicao.itens.create(
            material=material_b,
            unidade_medida=material_b.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("0"),
            justificativa_autorizacao_parcial="Não autorizado",
        )

        atender_requisicao_completa(requisicao=requisicao, ator=atendente)

        item_a.refresh_from_db()
        item_b.refresh_from_db()
        material_a.estoque.refresh_from_db()
        material_b.estoque.refresh_from_db()
        assert item_a.quantidade_entregue == Decimal("3")
        assert item_b.quantidade_entregue == Decimal("0")
        assert material_a.estoque.saldo_fisico == Decimal("5")
        assert material_a.estoque.saldo_reservado == Decimal("0")
        assert material_b.estoque.saldo_fisico == Decimal("8")
        assert material_b.estoque.saldo_reservado == Decimal("0")

    def test_atendimento_parcial_entrega_item_e_libera_reserva_nao_entregue(self):
        setor = self._criar_setor("Atendimento Parcial", "92020")
        requisitante = self._criar_usuario("12020", "Solicitante Parcial", setor=setor)
        atendente = self._criar_usuario(
            "12021",
            "Auxiliar Almoxarifado Parcial",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.020",
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("5"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200020",
            material=material,
            quantidade_autorizada=Decimal("5"),
        )

        atendida = atender_requisicao_com_itens(
            requisicao=requisicao,
            ator=atendente,
            itens=[
                ItemAtendimentoData(
                    item_id=item.id,
                    quantidade_entregue=Decimal("3"),
                    justificativa_atendimento_parcial="Estoque físico divergente",
                )
            ],
            retirante_fisico="Servidor parcial",
        )

        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert atendida.status == StatusRequisicao.ATENDIDA_PARCIALMENTE
        assert atendida.eventos.filter(tipo_evento=TipoEvento.ATENDIMENTO_PARCIAL).exists()
        assert item.quantidade_entregue == Decimal("3")
        assert item.justificativa_atendimento_parcial == "Estoque físico divergente"
        assert material.estoque.saldo_fisico == Decimal("7")
        assert material.estoque.saldo_reservado == Decimal("0")
        assert MovimentacaoEstoque.objects.filter(
            requisicao=atendida,
            item_requisicao=item,
            tipo=TipoMovimentacao.SAIDA_POR_ATENDIMENTO,
            quantidade=Decimal("3"),
        ).exists()
        assert MovimentacaoEstoque.objects.filter(
            requisicao=atendida,
            item_requisicao=item,
            tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
            quantidade=Decimal("2"),
        ).exists()

    def test_atendimento_com_itens_integral_preserva_status_atendida(self):
        setor = self._criar_setor("Atendimento Integral", "92022")
        requisitante = self._criar_usuario("12022", "Solicitante Integral", setor=setor)
        atendente = self._criar_usuario(
            "12023",
            "Auxiliar Almoxarifado Integral",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.021",
            saldo_fisico=Decimal("6"),
            saldo_reservado=Decimal("2"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200021",
            material=material,
            quantidade_autorizada=Decimal("2"),
        )

        atendida = atender_requisicao_com_itens(
            requisicao=requisicao,
            ator=atendente,
            itens=[ItemAtendimentoData(item_id=item.id, quantidade_entregue=Decimal("2"))],
        )

        item.refresh_from_db()
        assert atendida.status == StatusRequisicao.ATENDIDA
        assert atendida.eventos.filter(tipo_evento=TipoEvento.ATENDIMENTO).exists()
        assert item.quantidade_entregue == Decimal("2")
        assert item.justificativa_atendimento_parcial == ""

    def test_atendimento_parcial_exige_justificativa_e_alguma_entrega(self):
        setor = self._criar_setor("Atendimento Zero", "92024")
        requisitante = self._criar_usuario("12024", "Solicitante Zero", setor=setor)
        atendente = self._criar_usuario(
            "12025",
            "Auxiliar Almoxarifado Zero",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.022",
            saldo_fisico=Decimal("6"),
            saldo_reservado=Decimal("2"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200022",
            material=material,
            quantidade_autorizada=Decimal("2"),
        )

        with pytest.raises(DomainConflict):
            atender_requisicao_com_itens(
                requisicao=requisicao,
                ator=atendente,
                itens=[ItemAtendimentoData(item_id=item.id, quantidade_entregue=Decimal("1"))],
            )
        with pytest.raises(DomainConflict):
            atender_requisicao_com_itens(
                requisicao=requisicao,
                ator=atendente,
                itens=[
                    ItemAtendimentoData(
                        item_id=item.id,
                        quantidade_entregue=Decimal("0"),
                        justificativa_atendimento_parcial="Sem retirada",
                    )
                ],
            )

        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert item.quantidade_entregue == Decimal("0")
        assert material.estoque.saldo_fisico == Decimal("6")
        assert material.estoque.saldo_reservado == Decimal("2")
        assert MovimentacaoEstoque.objects.count() == 0

    def test_atendimento_com_itens_rejeita_payload_incompleto_duplicado_ou_excessivo(self):
        setor = self._criar_setor("Atendimento Payload", "92026")
        requisitante = self._criar_usuario("12026", "Solicitante Payload", setor=setor)
        atendente = self._criar_usuario(
            "12027",
            "Auxiliar Almoxarifado Payload",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material_a = self._criar_material_com_estoque(
            "001.003.023",
            saldo_fisico=Decimal("6"),
            saldo_reservado=Decimal("2"),
        )
        material_b = self._criar_material_com_estoque(
            "001.003.024",
            saldo_fisico=Decimal("6"),
            saldo_reservado=Decimal("2"),
        )
        requisicao, item_a = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200023",
            material=material_a,
            quantidade_autorizada=Decimal("2"),
        )
        item_b = requisicao.itens.create(
            material=material_b,
            unidade_medida=material_b.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        cenarios = [
            [ItemAtendimentoData(item_id=item_a.id, quantidade_entregue=Decimal("2"))],
            [
                ItemAtendimentoData(item_id=item_a.id, quantidade_entregue=Decimal("2")),
                ItemAtendimentoData(item_id=item_a.id, quantidade_entregue=Decimal("2")),
            ],
            [
                ItemAtendimentoData(item_id=item_a.id, quantidade_entregue=Decimal("3")),
                ItemAtendimentoData(item_id=item_b.id, quantidade_entregue=Decimal("2")),
            ],
        ]
        for itens in cenarios:
            with pytest.raises(DomainConflict):
                atender_requisicao_com_itens(
                    requisicao=requisicao,
                    ator=atendente,
                    itens=itens,
                )

        item_a.refresh_from_db()
        item_b.refresh_from_db()
        material_a.estoque.refresh_from_db()
        material_b.estoque.refresh_from_db()
        assert item_a.quantidade_entregue == Decimal("0")
        assert item_b.quantidade_entregue == Decimal("0")
        assert material_a.estoque.saldo_reservado == Decimal("2")
        assert material_b.estoque.saldo_reservado == Decimal("2")
        assert MovimentacaoEstoque.objects.count() == 0

    def test_atendimento_bloqueia_usuario_sem_permissao_e_status_invalido(self):
        setor = self._criar_setor("Financeiro", "92003")
        solicitante = self._criar_usuario("12005", "Solicitante Financeiro", setor=setor)
        material = self._criar_material_com_estoque(
            "001.003.004",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("2"),
        )
        requisicao, _ = self._criar_requisicao_autorizada(
            criador=solicitante,
            beneficiario=solicitante,
            numero_publico="REQ-2026-200003",
            material=material,
            quantidade_autorizada=Decimal("2"),
        )

        with pytest.raises(PermissionDenied):
            atender_requisicao_completa(requisicao=requisicao, ator=solicitante)

        atendente = self._criar_usuario(
            "12006",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        requisicao.status = StatusRequisicao.ATENDIDA
        requisicao.save(update_fields=["status", "updated_at"])

        with pytest.raises(DomainConflict):
            atender_requisicao_completa(requisicao=requisicao, ator=atendente)

    def test_atendimento_bloqueia_saldo_fisico_insuficiente(self):
        setor = self._criar_setor("Logistica", "92004")
        requisitante = self._criar_usuario("12007", "Solicitante Logistica", setor=setor)
        atendente = self._criar_usuario(
            "12008",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.005",
            saldo_fisico=Decimal("1"),
            saldo_reservado=Decimal("3"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200004",
            material=material,
            quantidade_autorizada=Decimal("3"),
        )

        with pytest.raises(DomainConflict):
            atender_requisicao_completa(requisicao=requisicao, ator=atendente)

        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert item.quantidade_entregue == Decimal("0")
        assert material.estoque.saldo_fisico == Decimal("1")
        assert material.estoque.saldo_reservado == Decimal("3")
        assert MovimentacaoEstoque.objects.count() == 0

    def test_atendimento_bloqueia_saldo_reservado_insuficiente(self):
        setor = self._criar_setor("Logistica Reserva", "92006")
        requisitante = self._criar_usuario("12011", "Solicitante Logistica Reserva", setor=setor)
        atendente = self._criar_usuario(
            "12012",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.007",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("1"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200006",
            material=material,
            quantidade_autorizada=Decimal("3"),
        )

        with pytest.raises(DomainConflict):
            atender_requisicao_completa(requisicao=requisicao, ator=atendente)

        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert item.quantidade_entregue == Decimal("0")
        assert material.estoque.saldo_fisico == Decimal("5")
        assert material.estoque.saldo_reservado == Decimal("1")
        assert MovimentacaoEstoque.objects.count() == 0

    @pytest.mark.postgres
    def test_atendimentos_concorrentes_nao_duplicam_baixa(self):
        setor = self._criar_setor("Almoxarifado", "92005")
        requisitante = self._criar_usuario("12009", "Solicitante Almoxarifado", setor=setor)
        atendente = self._criar_usuario(
            "12010",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.006",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("5"),
        )
        requisicao, _ = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200005",
            material=material,
            quantidade_autorizada=Decimal("5"),
        )

        barrier = Barrier(2)

        def atender(req_id: int):
            close_old_connections()
            try:
                barrier.wait()
                requisicao_atendimento = Requisicao.objects.get(pk=req_id)
                atender_requisicao_completa(
                    requisicao=requisicao_atendimento,
                    ator=atendente,
                )
                return "ok"
            except Exception as exc:  # noqa: BLE001
                return type(exc).__name__
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultado_a = executor.submit(atender, requisicao.id)
            resultado_b = executor.submit(atender, requisicao.id)

        resultados = {resultado_a.result(), resultado_b.result()}
        close_old_connections()

        material.estoque.refresh_from_db()
        requisicao.refresh_from_db()

        assert resultados == {"ok", "DomainConflict"}
        assert requisicao.status == StatusRequisicao.ATENDIDA
        assert material.estoque.saldo_fisico == Decimal("0")
        assert material.estoque.saldo_reservado == Decimal("0")
        assert (
            MovimentacaoEstoque.objects.filter(
                requisicao=requisicao,
                tipo=TipoMovimentacao.SAIDA_POR_ATENDIMENTO,
            ).count()
            == 1
        )
