from apps.requisitions.models import Requisicao


def recarregar_para_autorizacao(requisicao: Requisicao) -> Requisicao:
    return (
        Requisicao.objects.select_for_update()
        .select_related("criador", "beneficiario", "setor_beneficiario")
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=requisicao.pk)
    )


def recarregar_para_atendimento(requisicao: Requisicao) -> Requisicao:
    return (
        Requisicao.objects.select_for_update()
        .select_related("criador", "beneficiario", "setor_beneficiario")
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=requisicao.pk)
    )


def recarregar_detalhe(requisicao_id: int) -> Requisicao:
    return (
        Requisicao.objects.select_related(
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "chefe_autorizador",
            "responsavel_atendimento",
        )
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=requisicao_id)
    )
