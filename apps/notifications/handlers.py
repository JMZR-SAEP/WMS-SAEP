from apps.core.events import (
    PUSH_LEMBRETE_AUTORIZACOES_ATRASADAS,
    REQUISICAO_ATENDIDA,
    REQUISICAO_AUTORIZADA,
    REQUISICAO_CANCELADA,
    REQUISICAO_ENVIADA_AUTORIZACAO,
    REQUISICAO_RECUSADA,
    subscribe,
)
from apps.notifications.models import TipoNotificacao
from apps.notifications.services import (
    criar_notificacao_papel,
    criar_notificacoes_usuarios_unicos,
    enviar_push_payload_usuario,
    enviar_push_requisicao_aguardando_autorizacao,
)
from apps.requisitions.models import Requisicao
from apps.users.models import PapelChoices


def _carregar_requisicao(requisicao_id: int) -> Requisicao:
    return Requisicao.objects.select_related(
        "criador",
        "beneficiario",
        "setor_beneficiario__chefe_responsavel",
    ).get(pk=requisicao_id)


def _identificador(requisicao: Requisicao) -> str:
    return requisicao.numero_publico or f"#{requisicao.pk}"


def _notificar_envio_autorizacao(payload: dict[str, object]) -> None:
    requisicao = _carregar_requisicao(payload["requisicao_id"])
    chefe = requisicao.setor_beneficiario.chefe_responsavel
    criar_notificacoes_usuarios_unicos(
        destinatarios=[chefe],
        tipo=TipoNotificacao.REQUISICAO_ENVIADA_AUTORIZACAO,
        titulo="Requisição aguardando autorização",
        mensagem=f"A requisição {_identificador(requisicao)} aguarda autorização.",
        objeto_relacionado=requisicao,
    )
    enviar_push_requisicao_aguardando_autorizacao(requisicao=requisicao)


def _notificar_autorizacao(payload: dict[str, object]) -> None:
    requisicao = _carregar_requisicao(payload["requisicao_id"])
    criar_notificacoes_usuarios_unicos(
        destinatarios=[requisicao.criador, requisicao.beneficiario],
        tipo=TipoNotificacao.REQUISICAO_AUTORIZADA,
        titulo="Requisição autorizada",
        mensagem=f"A requisição {_identificador(requisicao)} foi autorizada.",
        objeto_relacionado=requisicao,
    )
    for papel in (PapelChoices.AUXILIAR_ALMOXARIFADO, PapelChoices.CHEFE_ALMOXARIFADO):
        criar_notificacao_papel(
            papel_destinatario=papel,
            tipo=TipoNotificacao.REQUISICAO_AUTORIZADA,
            titulo="Requisição autorizada para atendimento",
            mensagem=f"A requisição {_identificador(requisicao)} está pronta para atendimento.",
            objeto_relacionado=requisicao,
        )


def _notificar_recusa(payload: dict[str, object]) -> None:
    requisicao = _carregar_requisicao(payload["requisicao_id"])
    criar_notificacoes_usuarios_unicos(
        destinatarios=[requisicao.criador, requisicao.beneficiario],
        tipo=TipoNotificacao.REQUISICAO_RECUSADA,
        titulo="Requisição recusada",
        mensagem=f"A requisição {_identificador(requisicao)} foi recusada.",
        objeto_relacionado=requisicao,
    )


def _notificar_cancelamento(payload: dict[str, object]) -> None:
    requisicao = _carregar_requisicao(payload["requisicao_id"])
    criar_notificacoes_usuarios_unicos(
        destinatarios=[requisicao.criador, requisicao.beneficiario],
        tipo=TipoNotificacao.REQUISICAO_CANCELADA,
        titulo="Requisição cancelada",
        mensagem=f"A requisição {_identificador(requisicao)} foi cancelada.",
        objeto_relacionado=requisicao,
    )


def _notificar_atendimento(payload: dict[str, object]) -> None:
    requisicao = _carregar_requisicao(payload["requisicao_id"])
    criar_notificacoes_usuarios_unicos(
        destinatarios=[requisicao.criador, requisicao.beneficiario],
        tipo=TipoNotificacao.REQUISICAO_ATENDIDA,
        titulo="Requisição atendida",
        mensagem=f"A requisição {_identificador(requisicao)} foi atendida.",
        objeto_relacionado=requisicao,
    )


def _enviar_lembrete_autorizacoes_atrasadas(payload: dict[str, object]) -> None:
    enviar_push_payload_usuario(
        usuario_id=payload["usuario_id"],
        payload=payload["payload"],
        ttl=payload["ttl"],
    )


def register_event_handlers() -> None:
    subscribe(REQUISICAO_ENVIADA_AUTORIZACAO, _notificar_envio_autorizacao)
    subscribe(REQUISICAO_AUTORIZADA, _notificar_autorizacao)
    subscribe(REQUISICAO_RECUSADA, _notificar_recusa)
    subscribe(REQUISICAO_CANCELADA, _notificar_cancelamento)
    subscribe(REQUISICAO_ATENDIDA, _notificar_atendimento)
    subscribe(PUSH_LEMBRETE_AUTORIZACOES_ATRASADAS, _enviar_lembrete_autorizacoes_atrasadas)
