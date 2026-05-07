import { queryOptions } from "@tanstack/react-query";

import { ApiError, isAuthError, type ErrorResponse } from "../auth/session";
import { apiClient } from "../../shared/api/client";
import type { components } from "../../shared/api/schema";

export type RequisicaoListItem = components["schemas"]["RequisicaoListOutput"];
export type RequisicaoListResponse = components["schemas"]["RequisicaoListPaginated"];
export type RequisicaoDetail = components["schemas"]["RequisicaoDetailOutput"];
export type RequisicaoStatus = components["schemas"]["StatusEnum"];
export type RequisicaoTimelineEvent = components["schemas"]["RequisicaoTimelineEventOutput"];
export type RequisicaoActionItem = components["schemas"]["RequisicaoActionOutput"];
export type RequisicaoTimelineEventType = components["schemas"]["TipoEventoEnum"];

export const STATUS_OPTIONS: Array<{ value: RequisicaoStatus; label: string }> = [
  { value: "rascunho", label: "Rascunho" },
  { value: "aguardando_autorizacao", label: "Aguardando autorização" },
  { value: "recusada", label: "Recusada" },
  { value: "autorizada", label: "Autorizada" },
  { value: "atendida_parcialmente", label: "Atendida parcialmente" },
  { value: "atendida", label: "Atendida" },
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

export const requisitionsQueryKeys = {
  all: ["requisitions"] as const,
  mine: (params: RequisicoesListParams) =>
    [
      ...requisitionsQueryKeys.all,
      "mine",
      {
        page: params.page,
        pageSize: params.pageSize,
        search: params.search ?? "",
        status: params.status ?? "",
      },
    ] as const,
  detail: (id: number) => [...requisitionsQueryKeys.all, "detail", id] as const,
};

function messageFromError(error: ErrorResponse | undefined, fallback: string) {
  return error?.error?.message || fallback;
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
    );
  }

  return data;
}

export function myRequisitionsQueryOptions(params: RequisicoesListParams) {
  return queryOptions({
    queryKey: requisitionsQueryKeys.mine(params),
    queryFn: () => fetchMyRequisitions(params),
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

export function queryErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
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
