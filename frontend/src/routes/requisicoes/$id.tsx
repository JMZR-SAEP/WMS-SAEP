import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { z } from "zod";

import { requireSession } from "../../features/auth/guards";
import { authQueryKeys, isAuthError, meQueryOptions } from "../../features/auth/session";
import { DraftRequisitionEditor } from "../../features/requisitions/DraftRequisitionEditor";
import {
    authorizeRequisition,
    displayRequisitionIdentifier,
    formatDateTime,
    formatQuantity,
    isThirdPartyBeneficiary,
    queryErrorMessage,
    refuseRequisition,
    requisitionDetailQueryOptions,
    requisitionsQueryKeys,
    statusLabel,
    tipoEventoLabel,
    type RequisicaoActionItem,
    type RequisicaoAuthorizeInput,
    type RequisicaoDetail,
    type RequisicaoTimelineEvent,
  } from "../../features/requisitions/requisitions";

const detailSearchSchema = z.object({
  contexto: z.enum(["autorizacao", "atendimento"]).optional().catch(undefined),
  page: z.coerce.number().int().min(1).optional().catch(undefined),
});

export const Route = createFileRoute("/requisicoes/$id")({
  validateSearch: detailSearchSchema,
  beforeLoad: ({ context, location }) =>
    requireSession({ queryClient: context.queryClient, locationHref: location.href }),
  component: DetalheRequisicaoPage,
});

function QuantityBlock({ item }: { item: RequisicaoActionItem }) {
  return (
    <div className="quantity-grid">
      <span>
        Solicitado
        <strong>
          {formatQuantity(item.quantidade_solicitada)} {item.unidade_medida}
        </strong>
      </span>
      <span>
        Autorizado
        <strong>
          {formatQuantity(item.quantidade_autorizada)} {item.unidade_medida}
        </strong>
      </span>
      <span>
        Entregue
        <strong>
          {formatQuantity(item.quantidade_entregue)} {item.unidade_medida}
        </strong>
      </span>
    </div>
  );
}

function hasText(value: string | null | undefined) {
  return Boolean(value?.trim());
}

function TimelineEvent({ event }: { event: RequisicaoTimelineEvent }) {
  return (
    <li className="timeline-event">
      <div>
        <p className="font-semibold">{tipoEventoLabel(event.tipo_evento)}</p>
        <p className="text-sm text-[var(--ink-soft)]">
          {event.usuario.nome_completo} - {formatDateTime(event.data_hora)}
        </p>
      </div>
      {event.observacao ? <p className="mt-2 text-sm text-[var(--ink-soft)]">{event.observacao}</p> : null}
    </li>
  );
}

type AuthorizationItemForm = {
  itemId: number;
  label: string;
  requestedQuantity: string;
  authorizedQuantity: string;
  justification: string;
};

function quantityNumber(value: string) {
  const normalizedValue = value.replace(",", ".").trim();
  if (!normalizedValue) {
    return Number.NaN;
  }
  return Number(normalizedValue);
}

function authorizationItemLabel(item: RequisicaoActionItem) {
  return item.material.nome;
}

function authorizationItemsFromRequisition(requisicao: RequisicaoDetail): AuthorizationItemForm[] {
  return requisicao.itens.map((item) => ({
    itemId: item.id,
    label: authorizationItemLabel(item),
    requestedQuantity: item.quantidade_solicitada,
    authorizedQuantity: item.quantidade_solicitada,
    justification: item.justificativa_autorizacao_parcial,
  }));
}

function AuthorizationDecisionPanel({
  authorizationPage,
  requisicao,
}: {
  authorizationPage: number | undefined;
  requisicao: RequisicaoDetail;
}) {
  const [items, setItems] = useState(() => authorizationItemsFromRequisition(requisicao));
  const [refusalReason, setRefusalReason] = useState("");
  const [validationError, setValidationError] = useState("");
  const queryClient = useQueryClient();
  const navigate = useNavigate({ from: "/requisicoes/$id" });

  async function afterDecisionSuccess(updatedRequisition: RequisicaoDetail) {
    queryClient.setQueryData(requisitionsQueryKeys.detail(requisicao.id), updatedRequisition);
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: requisitionsQueryKeys.pendingApprovalsAll }),
      queryClient.invalidateQueries({ queryKey: requisitionsQueryKeys.detail(requisicao.id) }),
    ]);
    await navigate({
      to: "/autorizacoes",
      search: {
        page: authorizationPage && authorizationPage > 1 ? authorizationPage : undefined,
      },
    });
  }

  const authorizeMutation = useMutation({
    mutationFn: (input: RequisicaoAuthorizeInput) => authorizeRequisition(requisicao.id, input),
    onSuccess: afterDecisionSuccess,
  });
  const refuseMutation = useMutation({
    mutationFn: (input: { motivo_recusa: string }) => refuseRequisition(requisicao.id, input),
    onSuccess: afterDecisionSuccess,
  });
  const pending = authorizeMutation.isPending || refuseMutation.isPending;
  const mutationError = authorizeMutation.error ?? refuseMutation.error;

  function updateItem(itemId: number, field: "authorizedQuantity" | "justification", value: string) {
    setItems((currentItems) =>
      currentItems.map((item) => (item.itemId === itemId ? { ...item, [field]: value } : item)),
    );
    setValidationError("");
  }

  function payloadFromItems(nextItems: AuthorizationItemForm[]) {
    return {
      itens: nextItems.map((item) => ({
        item_id: item.itemId,
        quantidade_autorizada: item.authorizedQuantity.trim(),
        justificativa_autorizacao_parcial: item.justification.trim(),
      })),
    };
  }

  function validateAuthorization(nextItems: AuthorizationItemForm[]) {
    const authorizedQuantities = nextItems.map((item) => quantityNumber(item.authorizedQuantity));

    if (authorizedQuantities.some((quantity) => Number.isNaN(quantity) || quantity < 0)) {
      return "Informe quantidades autorizadas válidas.";
    }

    const itemAboveRequested = nextItems.find(
      (item) => quantityNumber(item.authorizedQuantity) > quantityNumber(item.requestedQuantity),
    );

    if (itemAboveRequested) {
      return "Quantidade autorizada não pode exceder a quantidade solicitada.";
    }

    if (authorizedQuantities.every((quantity) => quantity === 0)) {
      return "Para negar todos os itens, use Recusar requisição.";
    }

    const partialWithoutJustification = nextItems.find(
      (item) =>
        quantityNumber(item.authorizedQuantity) < quantityNumber(item.requestedQuantity) &&
        !item.justification.trim(),
    );

    if (partialWithoutJustification) {
      return "Informe justificativa para autorização parcial ou zerada.";
    }

    return "";
  }

  function authorizeAll() {
    const nextItems = requisicao.itens.map((item) => ({
      itemId: item.id,
      label: authorizationItemLabel(item),
      requestedQuantity: item.quantidade_solicitada,
      authorizedQuantity: item.quantidade_solicitada,
      justification: "",
    }));
    setItems(nextItems);
    setValidationError("");
    authorizeMutation.mutate(payloadFromItems(nextItems));
  }

  function authorizeAdjusted(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const error = validateAuthorization(items);

    if (error) {
      setValidationError(error);
      return;
    }

    setValidationError("");
    authorizeMutation.mutate(payloadFromItems(items));
  }

  function refuse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedReason = refusalReason.trim();

    if (!trimmedReason) {
      setValidationError("Informe o motivo da recusa.");
      return;
    }

    setValidationError("");
    refuseMutation.mutate({ motivo_recusa: trimmedReason });
  }

  return (
    <section className="detail-panel authorization-panel">
      <div className="authorization-panel-header">
        <div>
          <p className="eyebrow">Decisão da chefia</p>
          <h2>Autorizar ou recusar requisição</h2>
          <p>O backend revalida saldo, setor, estado e permissão no momento da decisão.</p>
        </div>
        <button
          className="preview-button draft-primary"
          disabled={pending}
          onClick={authorizeAll}
          type="button"
        >
          {authorizeMutation.isPending ? "Autorizando..." : "Autorizar tudo como solicitado"}
        </button>
      </div>

      {validationError ? <div className="error-panel compact-error">{validationError}</div> : null}
      {mutationError ? (
        <div className="error-panel compact-error">
          {queryErrorMessage(mutationError, "Não foi possível concluir a decisão.")}
        </div>
      ) : null}

      <form className="authorization-form" onSubmit={authorizeAdjusted}>
        <div className="authorization-items">
          {items.map((item) => (
            <article className="draft-item-card" key={item.itemId}>
              <div>
                <h2>{item.label}</h2>
                <p>Solicitado: {formatQuantity(item.requestedQuantity)}</p>
              </div>
              <div className="authorization-item-fields">
                <label className="preview-label">
                  Quantidade autorizada para {item.label}
                  <input
                    className="preview-input"
                    disabled={pending}
                    onChange={(event) =>
                      updateItem(item.itemId, "authorizedQuantity", event.target.value)
                    }
                    value={item.authorizedQuantity}
                  />
                </label>
                <label className="preview-label">
                  Justificativa para {item.label}
                  <input
                    className="preview-input"
                    disabled={pending}
                    onChange={(event) => updateItem(item.itemId, "justification", event.target.value)}
                    placeholder="Obrigatória quando parcial ou zerada"
                    value={item.justification}
                  />
                </label>
              </div>
            </article>
          ))}
        </div>
        <div className="draft-actions">
          <button className="preview-button draft-primary" disabled={pending} type="submit">
            Autorizar conforme ajustes
          </button>
        </div>
      </form>

      <form className="authorization-refusal" onSubmit={refuse}>
        <label className="preview-label">
          Motivo da recusa
          <textarea
            className="preview-input draft-textarea"
            disabled={pending}
            onChange={(event) => {
              setRefusalReason(event.target.value);
              setValidationError("");
            }}
            rows={3}
            value={refusalReason}
          />
        </label>
        <div className="draft-actions">
          <button className="preview-button draft-primary danger-action" disabled={pending} type="submit">
            Recusar requisição
          </button>
        </div>
      </form>
    </section>
  );
}

function DetalheRequisicaoPage() {
  const { id } = Route.useParams();
  const { contexto, page: authorizationPage } = Route.useSearch();
  const requisicaoId = Number(id);
  const backTo =
    contexto === "autorizacao"
      ? "/autorizacoes"
      : contexto === "atendimento"
        ? "/atendimentos"
        : "/minhas-requisicoes";
  const queryClient = useQueryClient();
  const navigate = useNavigate({ from: "/requisicoes/$id" });
  const detailQuery = useQuery({
    ...requisitionDetailQueryOptions(requisicaoId),
    enabled: Number.isInteger(requisicaoId) && requisicaoId > 0,
  });
  const sessionQuery = useQuery(meQueryOptions);
  const authError = detailQuery.isError && isAuthError(detailQuery.error);

  useEffect(() => {
    if (!authError) {
      return;
    }
    queryClient.removeQueries({ queryKey: authQueryKeys.me });
    void navigate({
      to: "/login",
      search: {
        redirect: `/requisicoes/${id}`,
      },
    });
  }, [authError, id, navigate, queryClient]);

  if (!Number.isInteger(requisicaoId) || requisicaoId <= 0) {
    return <div className="error-panel">Identificador de requisição inválido.</div>;
  }

  if (detailQuery.isPending) {
    return <div className="loading-state">Carregando requisição...</div>;
  }

  if (authError) {
    return null;
  }

  if (detailQuery.isError) {
    return (
      <div className="error-panel">
        {queryErrorMessage(detailQuery.error, "Não foi possível carregar a requisição.")}
      </div>
    );
  }

  const requisicao = detailQuery.data;
  if (requisicao.status === "rascunho") {
    if (sessionQuery.isLoading) {
      return <div className="loading-state">Carregando sessão...</div>;
    }
    if (sessionQuery.isError) {
      return (
        <div className="error-panel">
          {queryErrorMessage(sessionQuery.error, "Não foi possível carregar a sessão.")}
        </div>
      );
    }
    if (!sessionQuery.data) {
      return <div className="error-panel">Sessão indisponível.</div>;
    }
    return <DraftRequisitionEditor initialRequisition={requisicao} session={sessionQuery.data} />;
  }

  const thirdParty = isThirdPartyBeneficiary(requisicao);

  return (
    <section className="space-y-6">
      <div className="detail-hero">
        <div>
          <p className="eyebrow">Detalhe canônico</p>
          <h1>{displayRequisitionIdentifier(requisicao) ?? statusLabel(requisicao.status)}</h1>
          <p>
            {statusLabel(requisicao.status)} - {requisicao.setor_beneficiario.nome}
          </p>
        </div>
        <div className="detail-actions">
          {contexto ? <span className="context-chip">Contexto: {contexto}</span> : null}
          <Link
            className="action-link compact-action"
            search={
              contexto === "autorizacao"
                ? { page: authorizationPage && authorizationPage > 1 ? authorizationPage : undefined }
                : undefined
            }
            to={backTo}
          >
            Voltar
          </Link>
        </div>
      </div>

      {contexto === "autorizacao" && requisicao.status === "aguardando_autorizacao" ? (
        <AuthorizationDecisionPanel
          authorizationPage={authorizationPage}
          key={requisicao.id}
          requisicao={requisicao}
        />
      ) : null}

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

      {hasText(requisicao.observacao) ||
      hasText(requisicao.observacao_atendimento) ||
      hasText(requisicao.motivo_recusa) ||
      hasText(requisicao.motivo_cancelamento) ||
      hasText(requisicao.retirante_fisico) ? (
        <section className="detail-panel">
          <p className="eyebrow">Observações</p>
          <dl className="info-list notes-list">
            {hasText(requisicao.observacao) ? (
              <div>
                <dt>Geral</dt>
                <dd>{requisicao.observacao}</dd>
              </div>
            ) : null}
            {hasText(requisicao.observacao_atendimento) ? (
              <div>
                <dt>Atendimento</dt>
                <dd>{requisicao.observacao_atendimento}</dd>
              </div>
            ) : null}
            {hasText(requisicao.motivo_recusa) ? (
              <div>
                <dt>Recusa</dt>
                <dd>{requisicao.motivo_recusa}</dd>
              </div>
            ) : null}
            {hasText(requisicao.motivo_cancelamento) ? (
              <div>
                <dt>Cancelamento</dt>
                <dd>{requisicao.motivo_cancelamento}</dd>
              </div>
            ) : null}
            {hasText(requisicao.retirante_fisico) ? (
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
