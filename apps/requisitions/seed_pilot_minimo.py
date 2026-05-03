from decimal import Decimal

from django.conf import settings
from django.core.management.base import CommandError
from django.db import transaction

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.materials.services import criar_material
from apps.requisitions.models import Requisicao
from apps.requisitions.services import (
    ItemAtendimentoData,
    ItemAutorizacaoData,
    ItemRascunhoData,
    atender_requisicao,
    autorizar_requisicao,
    criar_rascunho_requisicao,
    enviar_para_autorizacao,
)
from apps.stock.models import EstoqueMaterial
from apps.stock.services import registrar_saldo_inicial
from apps.users.models import PapelChoices, Setor, User

SEED_PASSWORD = "senha-segura-123"
SEED_OBSERVACAO_PREFIX = "SEED_PILOT_MINIMO"
SEED_RASCUNHO = f"{SEED_OBSERVACAO_PREFIX}:rascunho"
SEED_AGUARDANDO = f"{SEED_OBSERVACAO_PREFIX}:aguardando"
SEED_AUTORIZADA = f"{SEED_OBSERVACAO_PREFIX}:autorizada_parcial"
SEED_ATENDIDA = f"{SEED_OBSERVACAO_PREFIX}:atendida_parcial"


def _ensure_ephemeral_environment() -> None:
    if not settings.EPHEMERAL_ENVIRONMENT:
        raise CommandError("Seed piloto mínima só pode ser executada em ambiente efêmero.")


def _upsert_usuario(
    *,
    matricula: str,
    nome_completo: str,
    papel: str,
    setor: Setor | None = None,
    is_active: bool = True,
    is_superuser: bool = False,
    is_staff: bool = False,
) -> User:
    defaults = {
        "nome_completo": nome_completo,
        "papel": papel,
        "setor": setor,
        "is_active": is_active,
        "is_superuser": is_superuser,
        "is_staff": is_staff,
    }
    user, created = User.objects.get_or_create(
        matricula_funcional=matricula,
        defaults=defaults,
    )
    if created:
        user.set_password(SEED_PASSWORD)
        user.save()
        return user

    changed_fields: list[str] = []
    for field, value in defaults.items():
        if getattr(user, field) != value:
            setattr(user, field, value)
            changed_fields.append(field)

    if not user.check_password(SEED_PASSWORD):
        user.set_password(SEED_PASSWORD)
        changed_fields.append("password")

    if changed_fields:
        user.save()
    return user


def _upsert_setor(*, nome: str, chefe_responsavel: User) -> Setor:
    setor, _ = Setor.objects.get_or_create(
        nome=nome,
        defaults={"chefe_responsavel": chefe_responsavel},
    )
    if setor.chefe_responsavel_id != chefe_responsavel.id:
        setor.chefe_responsavel = chefe_responsavel
        setor.save(update_fields=["chefe_responsavel", "updated_at"])
    return setor


def _upsert_material(
    *,
    subgrupo: SubgrupoMaterial,
    codigo_completo: str,
    sequencial: str,
    nome: str,
    unidade_medida: str,
    saldo_inicial: Decimal | None,
    is_active: bool = True,
) -> Material:
    material = Material.objects.filter(codigo_completo=codigo_completo).first()
    if material is None:
        material = criar_material(
            codigo_completo=codigo_completo,
            nome=nome,
            unidade_medida=unidade_medida,
            subgrupo=subgrupo,
            sequencial=sequencial,
        )

    changed_fields: list[str] = []
    if material.subgrupo_id != subgrupo.id:
        material.subgrupo = subgrupo
        changed_fields.append("subgrupo")
    if material.sequencial != sequencial:
        material.sequencial = sequencial
        changed_fields.append("sequencial")
    if material.nome != nome:
        material.nome = nome
        changed_fields.append("nome")
    if material.unidade_medida != unidade_medida:
        material.unidade_medida = unidade_medida
        changed_fields.append("unidade_medida")
    if material.is_active != is_active:
        material.is_active = is_active
        changed_fields.append("is_active")
    if changed_fields:
        material.full_clean()
        material.save(update_fields=[*changed_fields, "updated_at"])

    if saldo_inicial is None:
        return material

    estoque = EstoqueMaterial.objects.filter(material=material).first()
    if estoque is None:
        registrar_saldo_inicial(material=material, quantidade=saldo_inicial)
        return material

    if (
        estoque.saldo_fisico != saldo_inicial
        and not Requisicao.objects.filter(itens__material=material).exists()
    ):
        estoque.saldo_fisico = saldo_inicial
        estoque.saldo_reservado = Decimal("0")
        estoque.save(update_fields=["saldo_fisico", "saldo_reservado", "updated_at"])
    return material


def _seed_requisicao_rascunho(
    *, criador: User, beneficiario: User, material: Material
) -> Requisicao:
    requisicao = Requisicao.objects.filter(observacao=SEED_RASCUNHO).first()
    if requisicao is not None:
        return requisicao

    return criar_rascunho_requisicao(
        criador=criador,
        beneficiario=beneficiario,
        observacao=SEED_RASCUNHO,
        itens=[
            ItemRascunhoData(
                material_id=material.id,
                quantidade_solicitada=Decimal("2"),
                observacao="Rascunho para terceiro",
            )
        ],
    )


def _seed_requisicao_aguardando(*, criador: User, material: Material) -> Requisicao:
    requisicao = Requisicao.objects.filter(observacao=SEED_AGUARDANDO).first()
    if requisicao is not None:
        return requisicao

    requisicao = criar_rascunho_requisicao(
        criador=criador,
        beneficiario=criador,
        observacao=SEED_AGUARDANDO,
        itens=[
            ItemRascunhoData(
                material_id=material.id,
                quantidade_solicitada=Decimal("3"),
                observacao="Aguardando autorizacao",
            )
        ],
    )
    return enviar_para_autorizacao(requisicao=requisicao, ator=criador)


def _seed_requisicao_autorizada_parcial(
    *, solicitante: User, chefe_setor: User, material: Material
) -> Requisicao:
    requisicao = Requisicao.objects.filter(observacao=SEED_AUTORIZADA).first()
    if requisicao is not None:
        return requisicao

    requisicao = criar_rascunho_requisicao(
        criador=solicitante,
        beneficiario=solicitante,
        observacao=SEED_AUTORIZADA,
        itens=[
            ItemRascunhoData(
                material_id=material.id,
                quantidade_solicitada=Decimal("2"),
                observacao="Autorizacao parcial",
            )
        ],
    )
    requisicao = enviar_para_autorizacao(requisicao=requisicao, ator=solicitante)
    item = requisicao.itens.get()
    return autorizar_requisicao(
        requisicao=requisicao,
        ator=chefe_setor,
        itens=[
            ItemAutorizacaoData(
                item_id=item.id,
                quantidade_autorizada=Decimal("1"),
                justificativa_autorizacao_parcial="Saldo reservado para cenario seed.",
            )
        ],
    )


def _seed_requisicao_atendida_parcial(
    *, solicitante: User, chefe_setor: User, auxiliar_almox: User, material: Material
) -> Requisicao:
    requisicao = Requisicao.objects.filter(observacao=SEED_ATENDIDA).first()
    if requisicao is not None:
        return requisicao

    requisicao = criar_rascunho_requisicao(
        criador=solicitante,
        beneficiario=solicitante,
        observacao=SEED_ATENDIDA,
        itens=[
            ItemRascunhoData(
                material_id=material.id,
                quantidade_solicitada=Decimal("2"),
                observacao="Atendimento parcial",
            )
        ],
    )
    requisicao = enviar_para_autorizacao(requisicao=requisicao, ator=solicitante)
    item = requisicao.itens.get()
    requisicao = autorizar_requisicao(
        requisicao=requisicao,
        ator=chefe_setor,
        itens=[
            ItemAutorizacaoData(
                item_id=item.id,
                quantidade_autorizada=Decimal("2"),
            )
        ],
    )
    item = requisicao.itens.get()
    return atender_requisicao(
        requisicao=requisicao,
        ator=auxiliar_almox,
        itens=[
            ItemAtendimentoData(
                item_id=item.id,
                quantidade_entregue=Decimal("1"),
                justificativa_atendimento_parcial="Entrega parcial para cenario seed.",
            )
        ],
        retirante_fisico="Servidor piloto",
        observacao_atendimento=SEED_OBSERVACAO_PREFIX,
    )


def carregar_seed_pilot_minimo() -> None:
    _ensure_ephemeral_environment()

    with transaction.atomic():
        chefe_setor = _upsert_usuario(
            matricula="91001",
            nome_completo="Chefe Operacional",
            papel=PapelChoices.CHEFE_SETOR,
        )
        chefe_almox = _upsert_usuario(
            matricula="91005",
            nome_completo="Chefe Almoxarifado",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
        )

        setor_operacional = _upsert_setor(
            nome="Setor Operacional Seed",
            chefe_responsavel=chefe_setor,
        )
        setor_almox = _upsert_setor(
            nome="Almoxarifado Seed",
            chefe_responsavel=chefe_almox,
        )

        chefe_setor = _upsert_usuario(
            matricula="91001",
            nome_completo="Chefe Operacional",
            papel=PapelChoices.CHEFE_SETOR,
            setor=setor_operacional,
        )
        chefe_almox = _upsert_usuario(
            matricula="91005",
            nome_completo="Chefe Almoxarifado",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
            setor=setor_almox,
        )
        auxiliar_setor = _upsert_usuario(
            matricula="91002",
            nome_completo="Auxiliar Operacional",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor_operacional,
        )
        solicitante = _upsert_usuario(
            matricula="91003",
            nome_completo="Solicitante Operacional",
            papel=PapelChoices.SOLICITANTE,
            setor=setor_operacional,
        )
        beneficiario_terceiro = _upsert_usuario(
            matricula="91004",
            nome_completo="Beneficiario Operacional",
            papel=PapelChoices.SOLICITANTE,
            setor=setor_operacional,
        )
        auxiliar_almox = _upsert_usuario(
            matricula="91006",
            nome_completo="Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor_almox,
        )
        _upsert_usuario(
            matricula="91998",
            nome_completo="Superusuario Tecnico Seed",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
            setor=setor_almox,
            is_active=True,
            is_superuser=True,
            is_staff=True,
        )
        _upsert_usuario(
            matricula="91999",
            nome_completo="Usuario Inativo Seed",
            papel=PapelChoices.SOLICITANTE,
            setor=setor_operacional,
            is_active=False,
        )

        grupo, _ = GrupoMaterial.objects.get_or_create(
            codigo_grupo="010",
            defaults={"nome": "Materiais de Consumo Seed"},
        )
        if grupo.nome != "Materiais de Consumo Seed":
            grupo.nome = "Materiais de Consumo Seed"
            grupo.save(update_fields=["nome", "updated_at"])

        subgrupo, _ = SubgrupoMaterial.objects.get_or_create(
            grupo=grupo,
            codigo_subgrupo="001",
            defaults={"nome": "Uso Diario Seed"},
        )
        if subgrupo.nome != "Uso Diario Seed":
            subgrupo.nome = "Uso Diario Seed"
            subgrupo.save(update_fields=["nome", "updated_at"])

        material_saldo_confortavel = _upsert_material(
            subgrupo=subgrupo,
            codigo_completo="010.001.001",
            sequencial="001",
            nome="Papel sulfite A4",
            unidade_medida="UN",
            saldo_inicial=Decimal("50"),
        )
        material_saldo_baixo = _upsert_material(
            subgrupo=subgrupo,
            codigo_completo="010.001.002",
            sequencial="002",
            nome="Cafe torrado 500g",
            unidade_medida="UN",
            saldo_inicial=Decimal("3"),
        )
        _upsert_material(
            subgrupo=subgrupo,
            codigo_completo="010.001.003",
            sequencial="003",
            nome="Sabonete liquido reserva",
            unidade_medida="UN",
            saldo_inicial=None,
        )
        _upsert_material(
            subgrupo=subgrupo,
            codigo_completo="010.001.004",
            sequencial="004",
            nome="Material inativo seed",
            unidade_medida="UN",
            saldo_inicial=Decimal("8"),
            is_active=False,
        )

        _seed_requisicao_rascunho(
            criador=auxiliar_setor,
            beneficiario=beneficiario_terceiro,
            material=material_saldo_confortavel,
        )
        _seed_requisicao_aguardando(
            criador=solicitante,
            material=material_saldo_confortavel,
        )
        _seed_requisicao_autorizada_parcial(
            solicitante=solicitante,
            chefe_setor=chefe_setor,
            material=material_saldo_baixo,
        )
        _seed_requisicao_atendida_parcial(
            solicitante=solicitante,
            chefe_setor=chefe_setor,
            auxiliar_almox=auxiliar_almox,
            material=material_saldo_baixo,
        )
