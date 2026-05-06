import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { z } from "zod";

import { requireSession } from "../../features/auth/guards";
import { authQueryKeys, isAuthError } from "../../features/auth/session";
import {
  displayRequisitionIdentifier,
  formatDateTime,
  isThirdPartyBeneficiary,
  requisitionDetailQueryOptions,
  statusLabel,
  type RequisicaoActionItem,
  type RequisicaoTimelineEvent,
} from "../../features/requisitions/requisitions";

const detailSearchSchema = z.object({
  contexto: z.enum(["autorizacao", "atendimento"]).optional().catch(undefined),
});

export const Route = createFileRoute("/requisicoes/$id")({
  validateSearch: detailSearchSchema,
  beforeLoad: ({ context, location }) =>
    requireSession({ queryClient: context.queryClient, locationHref: location.href }),
  component: DetalheRequisicaoPage,
});

function queryErrorMessage(error: unknown) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Não foi possível carregar a requisição.";
}

function QuantityBlock({ item }: { item: RequisicaoActionItem }) {
  return (
    <div className="quantity-grid">
      <span>
        Solicitado
        <strong>
          {item.quantidade_solicitada} {item.unidade_medida}
        </strong>
      </span>
      <span>
        Autorizado
        <strong>
          {item.quantidade_autorizada} {item.unidade_medida}
        </strong>
      </span>
      <span>
        Entregue
        <strong>
          {item.quantidade_entregue} {item.unidade_medida}
        </strong>
      </span>
    </div>
  );
}

function TimelineEvent({ event }: { event: RequisicaoTimelineEvent }) {
  return (
    <li className="timeline-event">
      <div>
        <p className="font-semibold">{event.tipo_evento.replaceAll("_", " ")}</p>
        <p className="text-sm text-[var(--ink-soft)]">
          {event.usuario.nome_completo} - {formatDateTime(event.data_hora)}
        </p>
      </div>
      {event.observacao ? <p className="mt-2 text-sm text-[var(--ink-soft)]">{event.observacao}</p> : null}
    </li>
  );
}

function DetalheRequisicaoPage() {
  const { id } = Route.useParams();
  const { contexto } = Route.useSearch();
  const requisicaoId = Number(id);
  const queryClient = useQueryClient();
  const navigate = useNavigate({ from: "/requisicoes/$id" });
  const detailQuery = useQuery({
    ...requisitionDetailQueryOptions(requisicaoId),
    enabled: Number.isInteger(requisicaoId) && requisicaoId > 0,
  });

  if (detailQuery.isError && isAuthError(detailQuery.error)) {
    queryClient.removeQueries({ queryKey: authQueryKeys.me });
    void navigate({
      to: "/login",
      search: {
        redirect: `/requisicoes/${id}`,
      },
    });
  }

  if (!Number.isInteger(requisicaoId) || requisicaoId <= 0) {
    return <div className="error-panel">Identificador de requisição inválido.</div>;
  }

  if (detailQuery.isPending) {
    return <div className="loading-state">Carregando requisição...</div>;
  }

  if (detailQuery.isError) {
    return <div className="error-panel">{queryErrorMessage(detailQuery.error)}</div>;
  }

  const requisicao = detailQuery.data;
  const thirdParty = isThirdPartyBeneficiary(requisicao);

  return (
    <section className="space-y-6">
      <div className="detail-hero">
        <div>
          <p className="eyebrow">Detalhe canônico</p>
          <h1>{displayRequisitionIdentifier(requisicao)}</h1>
          <p>
            {statusLabel(requisicao.status)} - {requisicao.setor_beneficiario.nome}
          </p>
        </div>
        <div className="detail-actions">
          {contexto ? <span className="context-chip">Contexto: {contexto}</span> : null}
          <Link className="action-link compact-action" to="/minhas-requisicoes">
            Voltar
          </Link>
        </div>
      </div>

      <div className="detail-grid">
        <section className="detail-panel">
          <p className="eyebrow">Pessoas</p>
          <dl className="info-list">
            <div>
              <dt>Criador</dt>
              <dd>{requisicao.criador.nome_completo}</dd>
            </div>
            <div>
              <dt>Beneficiário</dt>
              <dd>
                {requisicao.beneficiario.nome_completo}
                {thirdParty ? <span className="third-party-badge inline-badge">Terceiro</span> : null}
              </dd>
            </div>
            <div>
              <dt>Setor</dt>
              <dd>{requisicao.setor_beneficiario.nome}</dd>
            </div>
            {requisicao.chefe_autorizador ? (
              <div>
                <dt>Autorizador</dt>
                <dd>{requisicao.chefe_autorizador.nome_completo}</dd>
              </div>
            ) : null}
            {requisicao.responsavel_atendimento ? (
              <div>
                <dt>Atendimento</dt>
                <dd>{requisicao.responsavel_atendimento.nome_completo}</dd>
              </div>
            ) : null}
          </dl>
        </section>

        <section className="detail-panel">
          <p className="eyebrow">Datas</p>
          <dl className="info-list">
            <div>
              <dt>Criação</dt>
              <dd>{formatDateTime(requisicao.data_criacao)}</dd>
            </div>
            <div>
              <dt>Envio para autorização</dt>
              <dd>{formatDateTime(requisicao.data_envio_autorizacao)}</dd>
            </div>
            <div>
              <dt>Decisão</dt>
              <dd>{formatDateTime(requisicao.data_autorizacao_ou_recusa)}</dd>
            </div>
            <div>
              <dt>Finalização</dt>
              <dd>{formatDateTime(requisicao.data_finalizacao)}</dd>
            </div>
          </dl>
        </section>
      </div>

      {requisicao.observacao ||
      requisicao.observacao_atendimento ||
      requisicao.motivo_recusa ||
      requisicao.motivo_cancelamento ||
      requisicao.retirante_fisico ? (
        <section className="detail-panel">
          <p className="eyebrow">Observações</p>
          <dl className="info-list notes-list">
            {requisicao.observacao ? (
              <div>
                <dt>Geral</dt>
                <dd>{requisicao.observacao}</dd>
              </div>
            ) : null}
            {requisicao.observacao_atendimento ? (
              <div>
                <dt>Atendimento</dt>
                <dd>{requisicao.observacao_atendimento}</dd>
              </div>
            ) : null}
            {requisicao.motivo_recusa ? (
              <div>
                <dt>Recusa</dt>
                <dd>{requisicao.motivo_recusa}</dd>
              </div>
            ) : null}
            {requisicao.motivo_cancelamento ? (
              <div>
                <dt>Cancelamento</dt>
                <dd>{requisicao.motivo_cancelamento}</dd>
              </div>
            ) : null}
            {requisicao.retirante_fisico ? (
              <div>
                <dt>Retirante físico</dt>
                <dd>{requisicao.retirante_fisico}</dd>
              </div>
            ) : null}
          </dl>
        </section>
      ) : null}

      <section className="detail-panel">
        <p className="eyebrow">Itens</p>
        <div className="item-list">
          {requisicao.itens.map((item) => (
            <article className="item-card" key={item.id}>
              <div>
                <h2>{item.material.nome}</h2>
                <p>
                  {item.material.codigo_completo} - {item.material.unidade_medida}
                </p>
              </div>
              <QuantityBlock item={item} />
              {item.observacao ||
              item.justificativa_autorizacao_parcial ||
              item.justificativa_atendimento_parcial ? (
                <div className="item-notes">
                  {item.observacao ? <p>Obs.: {item.observacao}</p> : null}
                  {item.justificativa_autorizacao_parcial ? (
                    <p>Autorização parcial: {item.justificativa_autorizacao_parcial}</p>
                  ) : null}
                  {item.justificativa_atendimento_parcial ? (
                    <p>Atendimento parcial: {item.justificativa_atendimento_parcial}</p>
                  ) : null}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </section>

      <section className="detail-panel">
        <p className="eyebrow">Timeline</p>
        {requisicao.eventos.length > 0 ? (
          <ol className="timeline-list">
            {requisicao.eventos.map((event) => (
              <TimelineEvent event={event} key={event.id} />
            ))}
          </ol>
        ) : (
          <p className="text-sm text-[var(--ink-soft)]">Nenhum evento registrado.</p>
        )}
      </section>
    </section>
  );
}
