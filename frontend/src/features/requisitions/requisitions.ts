import { keepPreviousData, queryOptions } from "@tanstack/react-query";

import { isAuthError } from "../auth/session";
import { apiClient } from "../../shared/api/client";
import {
  ApiError,
  messageFromErrorPayload,
  queryErrorMessage as sharedQueryErrorMessage,
  type ErrorResponse,
} from "../../shared/api/errors";
import type { components } from "../../shared/api/schema";

export type RequisicaoListItem = components["schemas"]["RequisicaoListOutput"];
export type RequisicaoListResponse = components["schemas"]["RequisicaoListPaginated"];
export type RequisicaoDetail = components["schemas"]["RequisicaoDetailOutput"];
export type RequisicaoStatus = components["schemas"]["StatusEnum"];
export type RequisicaoTimelineEvent = components["schemas"]["RequisicaoTimelineEventOutput"];
export type RequisicaoActionItem = components["schemas"]["RequisicaoActionOutput"];
export type RequisicaoTimelineEventType = components["schemas"]["TipoEventoEnum"];
export type RequisicaoDraftInput = components["schemas"]["RequisicaoCreateInput"];
export type RequisicaoAuthorizeInput = components["schemas"]["RequisicaoAuthorizeInput"];
export type RequisicaoRefuseInput = components["schemas"]["RequisicaoRefuseInput"];
export type RequisicaoFulfillInput = components["schemas"]["RequisicaoFulfillInput"];
export type RequisicaoCancelInput = components["schemas"]["RequisicaoCancelInput"];
export type RequisicaoPendingApprovalItem = components["schemas"]["RequisicaoPendingApprovalOutput"];
export type RequisicaoPendingApprovalResponse = components["schemas"]["RequisicaoPendingApprovalPaginated"];
export type RequisicaoPendingFulfillmentItem =
  components["schemas"]["RequisicaoPendingFulfillmentOutput"];
export type RequisicaoPendingFulfillmentResponse =
  components["schemas"]["RequisicaoPendingFulfillmentPaginated"];
export type MaterialListItem = components["schemas"]["MaterialListOutput"];
export type MaterialListResponse = components["schemas"]["MaterialListPaginated"];
export type BeneficiaryLookupItem = components["schemas"]["BeneficiaryLookupOutput"];

export const STATUS_OPTIONS: Array<{ value: RequisicaoStatus; label: string }> = [
  { value: "rascunho", label: "Rascunho" },
  { value: "aguardando_autorizacao", label: "Aguardando autorização" },
  { value: "recusada", label: "Recusada" },
  { value: "autorizada", label: "Autorizada" },
  { value: "pronta_para_retirada_parcial", label: "Pronta para retirada (parcial)" },
  { value: "pronta_para_retirada", label: "Pronta para retirada" },
  { value: "retirada", label: "Retirada" },
  { value: "cancelada", label: "Cancelada" },
  { value: "estornada", label: "Estornada" },
];

const TIPO_EVENTO_OPTIONS: Array<{ value: RequisicaoTimelineEventType; label: string }> = [
  { value: "criacao", label: "Criação" },
  { value: "envio_autorizacao", label: "Envio para autorização" },
  { value: "retorno_rascunho", label: "Retorno para rascunho" },
  { value: "reenvio_autorizacao", label: "Reenvio para autorização" },
  { value: "autorizacao_total", label: "Autorização total" },
  { value: "autorizacao_parcial", label: "Autorização parcial" },
  { value: "recusa", label: "Recusa" },
  { value: "atendimento_parcial", label: "Atendimento parcial" },
  { value: "atendimento", label: "Atendimento" },
  { value: "cancelamento", label: "Cancelamento" },
  { value: "estorno", label: "Estorno" },
];

export type RequisicoesListParams = {
  page: number;
  pageSize: number;
  search?: string;
  status?: RequisicaoStatus;
};

export type PendingApprovalsParams = {
  page: number;
  pageSize: number;
};

export type PendingFulfillmentsParams = {
  page: number;
  pageSize: number;
};

const requisitionsBaseQueryKey = ["requisitions"] as const;
const pendingApprovalsBaseQueryKey = [...requisitionsBaseQueryKey, "pending-approvals"] as const;
const pendingFulfillmentsBaseQueryKey = [
  ...requisitionsBaseQueryKey,
  "pending-fulfillments",
] as const;

export const requisitionsQueryKeys = {
  all: requisitionsBaseQueryKey,
  mine: (params: RequisicoesListParams) =>
    [
      ...requisitionsBaseQueryKey,
      "mine",
      {
        page: params.page,
        pageSize: params.pageSize,
        search: params.search ?? "",
        status: params.status ?? "",
      },
    ] as const,
  pendingApprovalsAll: pendingApprovalsBaseQueryKey,
  pendingFulfillmentsAll: pendingFulfillmentsBaseQueryKey,
  pendingApprovals: (params: PendingApprovalsParams) =>
    [
      ...pendingApprovalsBaseQueryKey,
      {
        page: params.page,
        pageSize: params.pageSize,
      },
    ] as const,
  pendingFulfillments: (params: PendingFulfillmentsParams) =>
    [
      ...pendingFulfillmentsBaseQueryKey,
      {
        page: params.page,
        pageSize: params.pageSize,
      },
    ] as const,
  detail: (id: number) => [...requisitionsBaseQueryKey, "detail", id] as const,
  materials: (search: string) => [...requisitionsBaseQueryKey, "materials", search] as const,
  beneficiaries: (search: string) =>
    [...requisitionsBaseQueryKey, "beneficiaries", search] as const,
};

function messageFromError(error: ErrorResponse | undefined, fallback: string) {
  return messageFromErrorPayload(error, fallback);
}

export async function fetchMyRequisitions(params: RequisicoesListParams) {
  const { data, error, response } = await apiClient.GET("/api/v1/requisitions/mine/", {
    params: {
      query: {
        page: params.page,
        page_size: params.pageSize,
        search: params.search || undefined,
        status: params.status,
      },
    },
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível carregar requisições."),
      response.status,
      error,
      "/api/v1/requisitions/mine/",
    );
  }

  return data;
}

export async function fetchPendingApprovals(params: PendingApprovalsParams) {
  const { data, error, response } = await apiClient.GET("/api/v1/requisitions/pending-approvals/", {
    params: {
      query: {
        page: params.page,
        page_size: params.pageSize,
      },
    },
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível carregar autorizações pendentes."),
      response.status,
      error,
      "/api/v1/requisitions/pending-approvals/",
    );
  }

  return data;
}

export async function fetchPendingFulfillments(params: PendingFulfillmentsParams) {
  const { data, error, response } = await apiClient.GET(
    "/api/v1/requisitions/pending-fulfillments/",
    {
      params: {
        query: {
          page: params.page,
          page_size: params.pageSize,
        },
      },
    },
  );

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível carregar atendimentos pendentes."),
      response.status,
      error,
      "/api/v1/requisitions/pending-fulfillments/",
    );
  }

  return data;
}

export async function fetchRequisitionDetail(id: number) {
  const { data, error, response } = await apiClient.GET("/api/v1/requisitions/{id}/", {
    params: {
      path: {
        id,
      },
    },
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível carregar a requisição."),
      response.status,
      error,
      "/api/v1/requisitions/{id}/",
    );
  }

  return data;
}

export async function authorizeRequisition(id: number, input: RequisicaoAuthorizeInput) {
  const { data, error, response } = await apiClient.POST("/api/v1/requisitions/{id}/authorize/", {
    params: {
      path: {
        id,
      },
    },
    body: input,
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível autorizar a requisição."),
      response.status,
      error,
      "/api/v1/requisitions/{id}/authorize/",
    );
  }

  return data;
}

export async function refuseRequisition(id: number, input: RequisicaoRefuseInput) {
  const { data, error, response } = await apiClient.POST("/api/v1/requisitions/{id}/refuse/", {
    params: {
      path: {
        id,
      },
    },
    body: input,
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível recusar a requisição."),
      response.status,
      error,
      "/api/v1/requisitions/{id}/refuse/",
    );
  }

  return data;
}

export async function fulfillRequisition(
  id: number,
  input: RequisicaoFulfillInput,
  idempotencyKey: string,
) {
  if (typeof idempotencyKey !== "string") {
    throw new ApiError(
      "Idempotency-Key inválida para registrar atendimento.",
      400,
      undefined,
      "/api/v1/requisitions/{id}/fulfill/",
    );
  }
  const normalizedIdempotencyKey = idempotencyKey.trim();
  if (normalizedIdempotencyKey.length === 0 || normalizedIdempotencyKey.length > 128) {
    throw new ApiError(
      "Idempotency-Key inválida para registrar atendimento.",
      400,
      undefined,
      "/api/v1/requisitions/{id}/fulfill/",
    );
  }
  const { data, error, response } = await apiClient.POST("/api/v1/requisitions/{id}/fulfill/", {
    params: {
      header: {
        "Idempotency-Key": normalizedIdempotencyKey,
      },
      path: {
        id,
      },
    },
    body: input,
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível registrar atendimento."),
      response.status,
      error,
      "/api/v1/requisitions/{id}/fulfill/",
    );
  }

  return data;
}


export async function pickupRequisition(
  id: number,
  input: { retirante_fisico: string },
  idempotencyKey: string,
) {
  if (typeof idempotencyKey !== "string") {
    throw new ApiError(
      "Idempotency-Key inválida para registrar retirada.",
      400,
      undefined,
      "/api/v1/requisitions/{id}/pickup/",
    );
  }
  const normalizedIdempotencyKey = idempotencyKey.trim();
  if (normalizedIdempotencyKey.length === 0 || normalizedIdempotencyKey.length > 128) {
    throw new ApiError(
      "Idempotency-Key inválida para registrar retirada.",
      400,
      undefined,
      "/api/v1/requisitions/{id}/pickup/",
    );
  }
  const { data, error, response } = await apiClient.POST(
    "/api/v1/requisitions/{id}/pickup/",
    {
      params: {
        header: {
          "Idempotency-Key": normalizedIdempotencyKey,
        },
        path: {
          id,
        },
      },
      body: input,
    },
  );

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível registrar retirada."),
      response.status,
      error,
      "/api/v1/requisitions/{id}/pickup/",
    );
  }

  return data;
}

export async function cancelAuthorizedRequisition(id: number, input: RequisicaoCancelInput) {
  const { data, error, response } = await apiClient.POST("/api/v1/requisitions/{id}/cancel/", {
    params: {
      path: {
        id,
      },
    },
    body: input,
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível cancelar a requisição."),
      response.status,
      error,
      "/api/v1/requisitions/{id}/cancel/",
    );
  }

  return data;
}

export async function fetchMaterialsForDraft(search: string) {
  const { data, error, response } = await apiClient.GET("/api/v1/materials/", {
    params: {
      query: {
        search,
        page_size: 10,
      },
    },
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível buscar materiais."),
      response.status,
      error,
      "/api/v1/materials/",
    );
  }

  return data;
}

export async function fetchBeneficiariesForDraft(search: string) {
  const { data, error, response } = await apiClient.GET("/api/v1/users/beneficiary-lookup/", {
    params: {
      query: {
        q: search,
      },
    },
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível buscar beneficiários."),
      response.status,
      error,
      "/api/v1/users/beneficiary-lookup/",
    );
  }

  return data;
}

export async function createDraftRequisition(input: RequisicaoDraftInput) {
  const { data, error, response } = await apiClient.POST("/api/v1/requisitions/", {
    body: input,
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível salvar o rascunho."),
      response.status,
      error,
      "/api/v1/requisitions/",
    );
  }

  return data;
}

export async function updateDraftRequisition(id: number, input: RequisicaoDraftInput) {
  const { data, error, response } = await apiClient.PUT("/api/v1/requisitions/{id}/draft/", {
    params: {
      path: {
        id,
      },
    },
    body: input,
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível atualizar o rascunho."),
      response.status,
      error,
      "/api/v1/requisitions/{id}/draft/",
    );
  }

  return data;
}

export async function submitDraftRequisition(id: number) {
  const { data, error, response } = await apiClient.POST("/api/v1/requisitions/{id}/submit/", {
    params: {
      path: {
        id,
      },
    },
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível enviar para autorização."),
      response.status,
      error,
      "/api/v1/requisitions/{id}/submit/",
    );
  }

  return data;
}

export async function discardDraftRequisition(id: number) {
  const { error, response } = await apiClient.DELETE("/api/v1/requisitions/{id}/discard/", {
    params: {
      path: {
        id,
      },
    },
  });

  if (error) {
    throw new ApiError(
      messageFromError(error, "Não foi possível descartar o rascunho."),
      response.status,
      error,
      "/api/v1/requisitions/{id}/discard/",
    );
  }
}

export async function cancelDraftRequisition(id: number) {
  const { data, error, response } = await apiClient.POST("/api/v1/requisitions/{id}/cancel/", {
    params: {
      path: {
        id,
      },
    },
    body: {
      motivo_cancelamento: "",
    },
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível cancelar a requisição."),
      response.status,
      error,
      "/api/v1/requisitions/{id}/cancel/",
    );
  }

  return data;
}

export function myRequisitionsQueryOptions(params: RequisicoesListParams) {
  return queryOptions({
    queryKey: requisitionsQueryKeys.mine(params),
    queryFn: () => fetchMyRequisitions(params),
    placeholderData: keepPreviousData,
    retry: retryUnlessClientOrAuthError,
  });
}

export function pendingApprovalsQueryOptions(params: PendingApprovalsParams) {
  return queryOptions({
    queryKey: requisitionsQueryKeys.pendingApprovals(params),
    queryFn: () => fetchPendingApprovals(params),
    placeholderData: keepPreviousData,
    retry: retryUnlessClientOrAuthError,
  });
}

export function pendingFulfillmentsQueryOptions(params: PendingFulfillmentsParams) {
  return queryOptions({
    queryKey: requisitionsQueryKeys.pendingFulfillments(params),
    queryFn: () => fetchPendingFulfillments(params),
    placeholderData: keepPreviousData,
    retry: retryUnlessClientOrAuthError,
  });
}

export function requisitionDetailQueryOptions(id: number) {
  return queryOptions({
    queryKey: requisitionsQueryKeys.detail(id),
    queryFn: () => fetchRequisitionDetail(id),
    retry: retryUnlessClientOrAuthError,
  });
}

export function draftMaterialsQueryOptions(search: string) {
  return queryOptions({
    queryKey: requisitionsQueryKeys.materials(search),
    queryFn: () => fetchMaterialsForDraft(search),
    retry: retryUnlessClientOrAuthError,
  });
}

export function draftBeneficiariesQueryOptions(search: string) {
  return queryOptions({
    queryKey: requisitionsQueryKeys.beneficiaries(search),
    queryFn: () => fetchBeneficiariesForDraft(search),
    retry: retryUnlessClientOrAuthError,
  });
}

export function statusLabel(status: RequisicaoStatus) {
  return STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

export function isThirdPartyBeneficiary(item: RequisicaoListItem | RequisicaoDetail) {
  return item.beneficiario.id !== item.criador.id;
}

export function displayRequisitionIdentifier(requisicao: Pick<RequisicaoListItem, "numero_publico">) {
  return requisicao.numero_publico ?? null;
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "Não informado";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Não informado";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatQuantity(value: string) {
  const fractionDigits = value.includes(".") ? value.split(".")[1].length : 0;
  const numericValue = Number.parseFloat(value);
  if (Number.isNaN(numericValue)) {
    return value;
  }

  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: fractionDigits,
  }).format(numericValue);
}

export function queryErrorMessage(error: unknown, fallback: string) {
  return sharedQueryErrorMessage(error, fallback);
}

export function tipoEventoLabel(tipoEvento: RequisicaoTimelineEventType) {
  return TIPO_EVENTO_OPTIONS.find((option) => option.value === tipoEvento)?.label ?? tipoEvento.replaceAll("_", " ");
}

function retryUnlessClientOrAuthError(failureCount: number, error: unknown) {
  if (isAuthError(error)) {
    return false;
  }
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
    return false;
  }
  return failureCount < 2;
}

export function contextualDateLabel(requisicao: RequisicaoListItem) {
  if (requisicao.data_finalizacao) {
    return `Finalizada em ${formatDateTime(requisicao.data_finalizacao)}`;
  }

  if (requisicao.data_autorizacao_ou_recusa) {
    return `Decidida em ${formatDateTime(requisicao.data_autorizacao_ou_recusa)}`;
  }

  if (requisicao.data_envio_autorizacao) {
    return `Enviada em ${formatDateTime(requisicao.data_envio_autorizacao)}`;
  }

  return `Atualizada em ${formatDateTime(requisicao.updated_at)}`;
}
