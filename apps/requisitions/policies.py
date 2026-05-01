from django.db.models import Q, QuerySet

from apps.requisitions.models import Requisicao, StatusRequisicao
from apps.users.models import PapelChoices
from apps.users.policies import pode_autorizar_setor


def _usuario_operacional_ativo(user) -> bool:
    return user.is_authenticated and user.is_active and not user.is_superuser


def pode_visualizar_requisicao(user, requisicao: Requisicao) -> bool:
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if requisicao.criador_id == user.pk or requisicao.beneficiario_id == user.pk:
        return True

    if user.papel in (PapelChoices.AUXILIAR_ALMOXARIFADO, PapelChoices.CHEFE_ALMOXARIFADO):
        return _usuario_operacional_ativo(user)

    return _usuario_operacional_ativo(user) and pode_autorizar_setor(
        user, requisicao.setor_beneficiario
    )


def queryset_requisicoes_visiveis(user) -> QuerySet[Requisicao]:
    queryset = Requisicao.objects.select_related(
        "criador",
        "beneficiario",
        "setor_beneficiario",
        "chefe_autorizador",
        "responsavel_atendimento",
    ).prefetch_related(
        "itens__material",
        "eventos__usuario",
    )

    if not user.is_authenticated:
        return queryset.none()

    if user.is_superuser:
        return queryset

    if not _usuario_operacional_ativo(user):
        return queryset.none()

    if user.papel in (PapelChoices.AUXILIAR_ALMOXARIFADO, PapelChoices.CHEFE_ALMOXARIFADO):
        return queryset

    filtro = Q(criador_id=user.pk) | Q(beneficiario_id=user.pk)
    setor_responsavel = getattr(user, "setor_responsavel", None)
    if setor_responsavel is not None:
        filtro |= Q(setor_beneficiario=setor_responsavel)

    return queryset.filter(filtro).distinct()


def pode_manipular_pre_autorizacao(user, requisicao: Requisicao) -> bool:
    return _usuario_operacional_ativo(user) and (
        requisicao.criador_id == user.pk or requisicao.beneficiario_id == user.pk
    )


def pode_autorizar_requisicao(user, requisicao: Requisicao) -> bool:
    return _usuario_operacional_ativo(user) and pode_autorizar_setor(
        user, requisicao.setor_beneficiario
    )


def queryset_fila_autorizacao(user) -> QuerySet[Requisicao]:
    if not _usuario_operacional_ativo(user):
        return Requisicao.objects.none()

    if user.papel == PapelChoices.CHEFE_SETOR:
        setor_responsavel = getattr(user, "setor_responsavel", None)
        if setor_responsavel is None:
            return Requisicao.objects.none()
        return Requisicao.objects.filter(
            setor_beneficiario=setor_responsavel,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        )

    # INVARIANTE: CHEFE_ALMOXARIFADO precisa estar lotado no setor do almoxarifado.
    # Se `setor_id` vier vazio, tratamos como configuração inválida e retornamos vazio.
    if user.papel == PapelChoices.CHEFE_ALMOXARIFADO and user.setor_id is not None:
        return Requisicao.objects.filter(
            setor_beneficiario_id=user.setor_id,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        )

    return Requisicao.objects.none()
