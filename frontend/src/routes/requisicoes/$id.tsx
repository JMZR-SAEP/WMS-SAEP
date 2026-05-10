import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { z } from "zod";

import { requireOperationalPapel, requireSession } from "../../features/auth/guards";
import {
  authQueryKeys,
  isUnauthenticatedError,
  meQueryOptions,
} from "../../features/auth/session";
import { DraftRequisitionEditor } from "../../features/requisitions/DraftRequisitionEditor";
import { draftStepSchema, type DraftStep } from "../../features/requisitions/draftSteps";
import {
  authorizeRequisition,
  cancelAuthorizedRequisition,
  displayRequisitionIdentifier,
  formatDateTime,
  formatQuantity,
  fulfillRequisition,
  isThirdPartyBeneficiary,
  queryErrorMessage,
  refuseRequisition,
  requisitionDetailQueryOptions,
  requisitionsQueryKeys,
  statusLabel,
  tipoEventoLabel,
  type RequisicaoActionItem,
  type RequisicaoAuthorizeInput,
  type RequisicaoCancelInput,
  type RequisicaoDetail,
  type RequisicaoFulfillInput,
  type RequisicaoRefuseInput,
  type RequisicaoTimelineEvent,
} from "../../features/requisitions/requisitions";

const detailSearchSchema = z.object({
  contexto: z.enum(["autorizacao", "atendimento"]).optional().catch(undefined),
  etapa: draftStepSchema.optional().catch("beneficiario"),
  page: z.coerce.number().int().min(1).optional().catch(undefined),
});

export const Route = createFileRoute("/requisicoes/$id")({
  validateSearch: detailSearchSchema,
  beforeLoad: async ({ context, location, search }) => {
    if (search.contexto === "autorizacao") {
      await requireOperationalPapel({
        allowedPapeis: ["chefe_setor", "chefe_almoxarifado"],
        queryClient: context.queryClient,
        locationHref: location.href,
      });
      return;
    }

    if (search.contexto === "atendimento") {
      await requireOperationalPapel({
        allowedPapeis: ["auxiliar_almoxarifado", "chefe_almoxarifado"],
        queryClient: context.queryClient,
        locationHref: location.href,
      });
      return;
    }

    await requireSession({ queryClient: context.queryClient, locationHref: location.href });
  },
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

type FulfillmentItemForm = {
  itemId: number;
  label: string;
  authorizedQuantity: string;
  deliveredQuantity: string;
  justification: string;
};

function quantityNumber(value: string) {
  const normalizedValue = value.replace(",", ".").trim();
  if (!normalizedValue) {
    return Number.NaN;
  }
  return Number(normalizedValue);
}

function normalizeQuantityInput(value: string) {
  return value.replace(",", ".").trim();
}

function buildRequisicaoRedirect({
  sourcePage,
  contexto,
  id,
}: {
  sourcePage: number | undefined;
  contexto: "autorizacao" | "atendimento" | undefined;
  id: string;
}) {
  const pageSearch = sourcePage && sourcePage > 1 ? `&page=${sourcePage}` : "";

  if (contexto === "autorizacao") {
    return `/requisicoes/${id}?contexto=autorizacao${pageSearch}`;
  }

  if (contexto === "atendimento") {
    return `/requisicoes/${id}?contexto=atendimento${pageSearch}`;
  }

  return `/requisicoes/${id}`;
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

function fulfillmentItemLabel(item: RequisicaoActionItem) {
  return item.material.nome;
}

function fulfillmentItemsFromRequisition(requisicao: RequisicaoDetail): FulfillmentItemForm[] {
  return requisicao.itens
    .filter((item) => quantityNumber(item.quantidade_autorizada) > 0)
    .map((item) => ({
      itemId: item.id,
      label: fulfillmentItemLabel(item),
      authorizedQuantity: item.quantidade_autorizada,
      deliveredQuantity: item.quantidade_entregue,
      justification: item.justificativa_atendimento_parcial,
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

  function redirectToLoginAfterAuthError(error: unknown) {
    if (!isUnauthenticatedError(error)) {
      return;
    }

    queryClient.removeQueries({ queryKey: authQueryKeys.me });
    void navigate({
      to: "/login",
      search: {
        redirect: buildRequisicaoRedirect({
          id: String(requisicao.id),
          contexto: "autorizacao",
          sourcePage: authorizationPage,
        }),
      },
    });
  }

  async function afterDecisionSuccess() {
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
    onError: redirectToLoginAfterAuthError,
    onSuccess: afterDecisionSuccess,
  });
  const refuseMutation = useMutation({
    mutationFn: (input: RequisicaoRefuseInput) => refuseRequisition(requisicao.id, input),
    onError: redirectToLoginAfterAuthError,
    onSuccess: afterDecisionSuccess,
  });
  const pending = authorizeMutation.isPending || refuseMutation.isPending;
  const mutationError = authorizeMutation.error ?? refuseMutation.error;

  function resetDecisionFeedback() {
    setValidationError("");
    authorizeMutation.reset();
    refuseMutation.reset();
  }

  function updateItem(itemId: number, field: "authorizedQuantity" | "justification", value: string) {
    setItems((currentItems) =>
      currentItems.map((item) => (item.itemId === itemId ? { ...item, [field]: value } : item)),
    );
    resetDecisionFeedback();
  }

  function payloadFromItems(nextItems: AuthorizationItemForm[]) {
    return {
      itens: nextItems.map((item) => ({
        item_id: item.itemId,
        quantidade_autorizada: normalizeQuantityInput(item.authorizedQuantity),
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
    resetDecisionFeedback();
    authorizeMutation.mutate(payloadFromItems(nextItems));
  }

  function authorizeAdjusted(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetDecisionFeedback();
    const error = validateAuthorization(items);

    if (error) {
      setValidationError(error);
      return;
    }

    authorizeMutation.mutate(payloadFromItems(items));
  }

  function refuse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetDecisionFeedback();
    const trimmedReason = refusalReason.trim();

    if (!trimmedReason) {
      setValidationError("Informe o motivo da recusa.");
      return;
    }

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
                    inputMode="decimal"
                    onChange={(event) =>
                      updateItem(item.itemId, "authorizedQuantity", event.target.value)
                    }
                    value={item.authorizedQuantity}
                  />
                </label>
                <label className="preview-label">
                  Justificativa para {item.label}
                  <textarea
                    className="preview-input"
                    disabled={pending}
                    onChange={(event) => updateItem(item.itemId, "justification", event.target.value)}
                    placeholder="Obrigatória quando parcial ou zerada"
                    rows={3}
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
              resetDecisionFeedback();
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

function FulfillmentDecisionPanel({
  fulfillmentPage,
  requisicao,
}: {
  fulfillmentPage: number | undefined;
  requisicao: RequisicaoDetail;
}) {
  const [items, setItems] = useState(() => fulfillmentItemsFromRequisition(requisicao));
  const [retiranteFisico, setRetiranteFisico] = useState("");
  const [observacaoAtendimento, setObservacaoAtendimento] = useState("");
  const [motivoCancelamento, setMotivoCancelamento] = useState("");
  const [validationError, setValidationError] = useState("");
  const queryClient = useQueryClient();
  const navigate = useNavigate({ from: "/requisicoes/$id" });

  function redirectToLoginAfterAuthError(error: unknown) {
    if (!isUnauthenticatedError(error)) {
      return;
    }

    queryClient.removeQueries({ queryKey: authQueryKeys.me });
    void navigate({
      to: "/login",
      search: {
        redirect: buildRequisicaoRedirect({
          id: String(requisicao.id),
          contexto: "atendimento",
          sourcePage: fulfillmentPage,
        }),
      },
    });
  }

  async function afterDecisionSuccess() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: requisitionsQueryKeys.pendingFulfillmentsAll }),
      queryClient.invalidateQueries({ queryKey: requisitionsQueryKeys.detail(requisicao.id) }),
    ]);
    await navigate({
      to: "/atendimentos",
      search: {
        page: fulfillmentPage && fulfillmentPage > 1 ? fulfillmentPage : undefined,
      },
    });
  }

  const fulfillMutation = useMutation({
    mutationFn: (input: RequisicaoFulfillInput) => fulfillRequisition(requisicao.id, input),
    onError: redirectToLoginAfterAuthError,
    onSuccess: afterDecisionSuccess,
  });
  const cancelMutation = useMutation({
    mutationFn: (input: RequisicaoCancelInput) =>
      cancelAuthorizedRequisition(requisicao.id, input),
    onError: redirectToLoginAfterAuthError,
    onSuccess: afterDecisionSuccess,
  });
  const pending = fulfillMutation.isPending || cancelMutation.isPending;
  const mutationError = fulfillMutation.error ?? cancelMutation.error;

  function resetDecisionFeedback() {
    setValidationError("");
    fulfillMutation.reset();
    cancelMutation.reset();
  }

  function updateItem(itemId: number, field: "deliveredQuantity" | "justification", value: string) {
    setItems((currentItems) =>
      currentItems.map((item) => (item.itemId === itemId ? { ...item, [field]: value } : item)),
    );
    resetDecisionFeedback();
  }

  function fillCompleteDelivery() {
    setItems((currentItems) =>
      currentItems.map((item) => ({
        ...item,
        deliveredQuantity: item.authorizedQuantity,
        justification: "",
      })),
    );
    resetDecisionFeedback();
  }

  function payloadFromItems(nextItems: FulfillmentItemForm[]): RequisicaoFulfillInput {
    return {
      retirante_fisico: retiranteFisico.trim(),
      observacao_atendimento: observacaoAtendimento.trim(),
      itens: nextItems.map((item) => ({
        item_id: item.itemId,
        quantidade_entregue: normalizeQuantityInput(item.deliveredQuantity),
        justificativa_atendimento_parcial: item.justification.trim(),
      })),
    };
  }

  function validateFulfillment(nextItems: FulfillmentItemForm[]) {
    const deliveredQuantities = nextItems.map((item) => quantityNumber(item.deliveredQuantity));

    if (deliveredQuantities.some((quantity) => Number.isNaN(quantity) || quantity < 0)) {
      return "Informe quantidades entregues válidas.";
    }

    const itemAboveAuthorized = nextItems.find(
      (item) => quantityNumber(item.deliveredQuantity) > quantityNumber(item.authorizedQuantity),
    );

    if (itemAboveAuthorized) {
      return "Quantidade entregue não pode exceder a quantidade autorizada.";
    }

    if (deliveredQuantities.every((quantity) => quantity === 0)) {
      return "Atendimento deve entregar ao menos um item.";
    }

    const partialWithoutJustification = nextItems.find(
      (item) =>
        quantityNumber(item.deliveredQuantity) < quantityNumber(item.authorizedQuantity) &&
        !item.justification.trim(),
    );

    if (partialWithoutJustification) {
      return "Informe justificativa para atendimento parcial ou zerado.";
    }

    return "";
  }

  function fulfill(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetDecisionFeedback();
    const error = validateFulfillment(items);

    if (error) {
      setValidationError(error);
      return;
    }

    fulfillMutation.mutate(payloadFromItems(items));
  }

  function cancel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetDecisionFeedback();
    const trimmedReason = motivoCancelamento.trim();

    if (!trimmedReason) {
      setValidationError("Informe o motivo do cancelamento.");
      return;
    }

    cancelMutation.mutate({ motivo_cancelamento: trimmedReason });
  }

  return (
    <section className="detail-panel authorization-panel">
      <div className="authorization-panel-header">
        <div>
          <p className="eyebrow">Atendimento do Almoxarifado</p>
          <h2>Registrar atendimento</h2>
          <p>O backend revalida estoque, reserva, estado e permissão no momento da retirada.</p>
        </div>
        <button
          className="preview-button draft-primary"
          disabled={pending}
          onClick={fillCompleteDelivery}
          type="button"
        >
          Preencher entrega completa
        </button>
      </div>

      {validationError ? <div className="error-panel compact-error">{validationError}</div> : null}
      {mutationError ? (
        <div className="error-panel compact-error">
          {queryErrorMessage(mutationError, "Não foi possível concluir a ação de atendimento.")}
        </div>
      ) : null}

      <form className="authorization-form" onSubmit={fulfill}>
        <div className="authorization-item-fields">
          <label className="preview-label">
            Retirante físico
            <input
              className="preview-input"
              disabled={pending}
              onChange={(event) => {
                setRetiranteFisico(event.target.value);
                resetDecisionFeedback();
              }}
              value={retiranteFisico}
            />
          </label>
          <label className="preview-label">
            Observação do atendimento
            <textarea
              className="preview-input"
              disabled={pending}
              onChange={(event) => {
                setObservacaoAtendimento(event.target.value);
                resetDecisionFeedback();
              }}
              rows={3}
              value={observacaoAtendimento}
            />
          </label>
        </div>

        <div className="authorization-items">
          {items.map((item) => (
            <article className="draft-item-card" key={item.itemId}>
              <div>
                <h2>{item.label}</h2>
                <p>Autorizado: {formatQuantity(item.authorizedQuantity)}</p>
              </div>
              <div className="authorization-item-fields">
                <label className="preview-label">
                  Quantidade entregue para {item.label}
                  <input
                    className="preview-input"
                    disabled={pending}
                    inputMode="decimal"
                    onChange={(event) =>
                      updateItem(item.itemId, "deliveredQuantity", event.target.value)
                    }
                    value={item.deliveredQuantity}
                  />
                </label>
                <label className="preview-label">
                  Justificativa de atendimento para {item.label}
                  <textarea
                    className="preview-input"
                    disabled={pending}
                    onChange={(event) => updateItem(item.itemId, "justification", event.target.value)}
                    placeholder="Obrigatória quando parcial ou zerada"
                    rows={3}
                    value={item.justification}
                  />
                </label>
              </div>
            </article>
          ))}
        </div>

        <div className="draft-actions">
          <button className="preview-button draft-primary" disabled={pending} type="submit">
            {pending ? "Registrando..." : "Registrar atendimento"}
          </button>
        </div>
      </form>

      <form className="fulfillment-cancellation" onSubmit={cancel}>
        <label className="preview-label">
          Motivo do cancelamento operacional
          <textarea
            className="preview-input draft-textarea"
            disabled={pending}
            onChange={(event) => {
              setMotivoCancelamento(event.target.value);
              resetDecisionFeedback();
            }}
            rows={3}
            value={motivoCancelamento}
          />
        </label>
        <div className="draft-actions">
          <button className="preview-button draft-primary danger-action" disabled={pending} type="submit">
            Cancelar requisição autorizada
          </button>
        </div>
      </form>
    </section>
  );
}

function DetalheRequisicaoPage() {
  const { id } = Route.useParams();
  const { contexto, etapa = "beneficiario", page: sourcePage } = Route.useSearch();
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
  const sessionQuery = useQuery({
    ...meQueryOptions,
    enabled: detailQuery.data?.status === "rascunho",
  });
  const authError = detailQuery.isError && isUnauthenticatedError(detailQuery.error);

  function handleDraftStepChange(step: DraftStep) {
    void navigate({
      to: "/requisicoes/$id",
      params: { id },
      search: (prev) => ({ ...prev, etapa: step }),
    });
  }

  useEffect(() => {
    if (!authError) {
      return;
    }
    queryClient.removeQueries({ queryKey: authQueryKeys.me });
    void navigate({
      to: "/login",
      search: {
        redirect: buildRequisicaoRedirect({ id, contexto, sourcePage }),
      },
    });
  }, [authError, contexto, id, navigate, queryClient, sourcePage]);

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
    return (
      <DraftRequisitionEditor
        activeStep={etapa}
        initialRequisition={requisicao}
        onStepChange={handleDraftStepChange}
        session={sessionQuery.data}
      />
    );
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
              contexto
                ? { page: sourcePage && sourcePage > 1 ? sourcePage : undefined }
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
          authorizationPage={sourcePage}
          key={requisicao.id}
          requisicao={requisicao}
        />
      ) : null}

      {contexto === "atendimento" && requisicao.status === "autorizada" ? (
        <FulfillmentDecisionPanel
          fulfillmentPage={sourcePage}
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
