from decimal import Decimal

from django.db import transaction

from apps.materials.models import GrupoMaterial, SubgrupoMaterial
from apps.materials.services import criar_material
from apps.requisitions.services import (
    ItemAtendimentoData,
    ItemAutorizacaoData,
    ItemRascunhoData,
    atender_requisicao,
    autorizar_requisicao,
    criar_rascunho_requisicao,
    enviar_para_autorizacao,
)
from apps.stock.services import registrar_saldo_inicial
from apps.users.models import PapelChoices, Setor, User

SEED_PASSWORD = "senha-segura-123"
SEED_OBSERVACAO = "SEED_PILOT_MINIMO"


def _criar_usuario(
    *,
    matricula: str,
    nome_completo: str,
    papel: str,
    setor: Setor | None = None,
    is_active: bool = True,
) -> User:
    return User.objects.create_user(
        matricula_funcional=matricula,
        password=SEED_PASSWORD,
        nome_completo=nome_completo,
        papel=papel,
        setor=setor,
        is_active=is_active,
    )


def carregar_seed_pilot_minimo() -> None:
    with transaction.atomic():
        chefe_setor = _criar_usuario(
            matricula="91001",
            nome_completo="Chefe Operacional",
            papel=PapelChoices.CHEFE_SETOR,
        )
        chefe_almox = _criar_usuario(
            matricula="91005",
            nome_completo="Chefe Almoxarifado",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
        )

        setor_operacional = Setor.objects.create(
            nome="Setor Operacional Seed",
            chefe_responsavel=chefe_setor,
        )
        setor_almox = Setor.objects.create(
            nome="Almoxarifado Seed",
            chefe_responsavel=chefe_almox,
        )

        chefe_setor.setor = setor_operacional
        chefe_setor.save(update_fields=["setor"])
        chefe_almox.setor = setor_almox
        chefe_almox.save(update_fields=["setor"])

        auxiliar_setor = _criar_usuario(
            matricula="91002",
            nome_completo="Auxiliar Operacional",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor_operacional,
        )
        solicitante = _criar_usuario(
            matricula="91003",
            nome_completo="Solicitante Operacional",
            papel=PapelChoices.SOLICITANTE,
            setor=setor_operacional,
        )
        beneficiario_terceiro = _criar_usuario(
            matricula="91004",
            nome_completo="Beneficiario Operacional",
            papel=PapelChoices.SOLICITANTE,
            setor=setor_operacional,
        )
        auxiliar_almox = _criar_usuario(
            matricula="91006",
            nome_completo="Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor_almox,
        )
        superuser = User.objects.create_superuser(
            matricula_funcional="91998",
            password=SEED_PASSWORD,
            nome_completo="Superusuario Tecnico Seed",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
            setor=setor_almox,
            is_active=True,
        )
        if not superuser.is_staff:
            superuser.is_staff = True
            superuser.save(update_fields=["is_staff"])
        _criar_usuario(
            matricula="91999",
            nome_completo="Usuario Inativo Seed",
            papel=PapelChoices.SOLICITANTE,
            setor=setor_operacional,
            is_active=False,
        )

        grupo = GrupoMaterial.objects.create(
            codigo_grupo="010",
            nome="Materiais de Consumo Seed",
        )
        subgrupo = SubgrupoMaterial.objects.create(
            grupo=grupo,
            codigo_subgrupo="001",
            nome="Uso Diario Seed",
        )

        material_saldo_confortavel = criar_material(
            codigo_completo="010.001.001",
            nome="Papel sulfite A4",
            unidade_medida="UN",
            subgrupo=subgrupo,
            sequencial="001",
        )
        registrar_saldo_inicial(
            material=material_saldo_confortavel,
            quantidade=Decimal("50"),
        )

        material_saldo_baixo = criar_material(
            codigo_completo="010.001.002",
            nome="Cafe torrado 500g",
            unidade_medida="UN",
            subgrupo=subgrupo,
            sequencial="002",
        )
        registrar_saldo_inicial(
            material=material_saldo_baixo,
            quantidade=Decimal("3"),
        )

        criar_material(
            codigo_completo="010.001.003",
            nome="Sabonete liquido reserva",
            unidade_medida="UN",
            subgrupo=subgrupo,
            sequencial="003",
        )

        material_inativo = criar_material(
            codigo_completo="010.001.004",
            nome="Material inativo seed",
            unidade_medida="UN",
            subgrupo=subgrupo,
            sequencial="004",
        )
        material_inativo.is_active = False
        material_inativo.save(update_fields=["is_active", "updated_at"])
        registrar_saldo_inicial(
            material=material_inativo,
            quantidade=Decimal("8"),
        )

        criar_rascunho_requisicao(
            criador=auxiliar_setor,
            beneficiario=beneficiario_terceiro,
            observacao=SEED_OBSERVACAO,
            itens=[
                ItemRascunhoData(
                    material_id=material_saldo_confortavel.id,
                    quantidade_solicitada=Decimal("2"),
                    observacao="Rascunho para terceiro",
                )
            ],
        )

        requisicao_aguardando = criar_rascunho_requisicao(
            criador=solicitante,
            beneficiario=solicitante,
            observacao=SEED_OBSERVACAO,
            itens=[
                ItemRascunhoData(
                    material_id=material_saldo_confortavel.id,
                    quantidade_solicitada=Decimal("3"),
                    observacao="Aguardando autorizacao",
                )
            ],
        )
        enviar_para_autorizacao(requisicao=requisicao_aguardando, ator=solicitante)

        requisicao_autorizada = criar_rascunho_requisicao(
            criador=solicitante,
            beneficiario=solicitante,
            observacao=SEED_OBSERVACAO,
            itens=[
                ItemRascunhoData(
                    material_id=material_saldo_baixo.id,
                    quantidade_solicitada=Decimal("2"),
                    observacao="Autorizacao parcial",
                )
            ],
        )
        requisicao_autorizada = enviar_para_autorizacao(
            requisicao=requisicao_autorizada,
            ator=solicitante,
        )
        item_autorizada = requisicao_autorizada.itens.get()
        autorizar_requisicao(
            requisicao=requisicao_autorizada,
            ator=chefe_setor,
            itens=[
                ItemAutorizacaoData(
                    item_id=item_autorizada.id,
                    quantidade_autorizada=Decimal("1"),
                    justificativa_autorizacao_parcial="Saldo reservado para cenario seed.",
                )
            ],
        )

        requisicao_atendida = criar_rascunho_requisicao(
            criador=solicitante,
            beneficiario=solicitante,
            observacao=SEED_OBSERVACAO,
            itens=[
                ItemRascunhoData(
                    material_id=material_saldo_baixo.id,
                    quantidade_solicitada=Decimal("2"),
                    observacao="Atendimento parcial",
                )
            ],
        )
        requisicao_atendida = enviar_para_autorizacao(
            requisicao=requisicao_atendida,
            ator=solicitante,
        )
        item_atendida = requisicao_atendida.itens.get()
        requisicao_atendida = autorizar_requisicao(
            requisicao=requisicao_atendida,
            ator=chefe_setor,
            itens=[
                ItemAutorizacaoData(
                    item_id=item_atendida.id,
                    quantidade_autorizada=Decimal("2"),
                )
            ],
        )
        item_atendida = requisicao_atendida.itens.get()
        atender_requisicao(
            requisicao=requisicao_atendida,
            ator=auxiliar_almox,
            itens=[
                ItemAtendimentoData(
                    item_id=item_atendida.id,
                    quantidade_entregue=Decimal("1"),
                    justificativa_atendimento_parcial="Entrega parcial para cenario seed.",
                )
            ],
            retirante_fisico="Servidor piloto",
            observacao_atendimento=SEED_OBSERVACAO,
        )
