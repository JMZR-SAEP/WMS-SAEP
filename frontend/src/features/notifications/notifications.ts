import { queryOptions } from "@tanstack/react-query";

import { apiClient } from "../../shared/api/client";
import { ApiError, messageFromErrorPayload, type ErrorResponse } from "../../shared/api/errors";
import type { components } from "../../shared/api/schema";

export type NotificationItem = components["schemas"]["NotificacaoOutput"];
export type NotificationListResponse = components["schemas"]["NotificacaoListPaginated"];
export type NotificationUnreadCountResponse =
  components["schemas"]["NotificacaoUnreadCountOutput"];
export type NotificationType = NotificationItem["tipo"];

export type NotificationListParams = {
  page: number;
  pageSize: number;
};

const notificationsBaseQueryKey = ["notifications"] as const;
const notificationsUnreadCountKey = [...notificationsBaseQueryKey, "unread-count"] as const;

export const notificationsQueryKeys = {
  all: notificationsBaseQueryKey,
  list: (params: NotificationListParams) =>
    [
      ...notificationsBaseQueryKey,
      "list",
      { page: params.page, pageSize: params.pageSize },
    ] as const,
  unreadCount: notificationsUnreadCountKey,
};

function messageFromError(error: ErrorResponse | undefined, fallback: string) {
  return messageFromErrorPayload(error, fallback);
}

export async function fetchNotifications(params: NotificationListParams) {
  const { data, error, response } = await apiClient.GET("/api/v1/notifications/", {
    params: {
      query: {
        page: params.page,
        page_size: params.pageSize,
      },
    },
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível carregar notificações."),
      response.status,
      error,
      "/api/v1/notifications/",
    );
  }

  return data;
}

export async function fetchNotificationUnreadCount() {
  const { data, error, response } = await apiClient.GET("/api/v1/notifications/unread-count/");

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível carregar contador de notificações."),
      response.status,
      error,
      "/api/v1/notifications/unread-count/",
    );
  }

  return data;
}

export async function markNotificationRead(id: number) {
  const { data, error, response } = await apiClient.POST("/api/v1/notifications/{id}/mark-read/", {
    params: {
      path: { id },
    },
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível marcar notificação como lida."),
      response.status,
      error,
      "/api/v1/notifications/{id}/mark-read/",
    );
  }

  return data;
}

export const notificationListQueryOptions = (params: NotificationListParams) =>
  queryOptions({
    queryKey: notificationsQueryKeys.list(params),
    queryFn: () => fetchNotifications(params),
    retry: false,
  });

export const notificationUnreadCountQueryOptions = queryOptions({
  queryKey: notificationsQueryKeys.unreadCount,
  queryFn: fetchNotificationUnreadCount,
  retry: false,
});

export function notificationOperationalContext(tipo: NotificationType) {
  if (tipo === "requisicao_enviada_autorizacao") {
    return "autorizacao" as const;
  }
  if (tipo === "requisicao_autorizada") {
    return "atendimento" as const;
  }
  if (tipo === "requisicao_pronta_para_retirada") {
    return "atendimento" as const;
  }
  return undefined;
}

export function notificationOperationalLabel(tipo: NotificationType) {
  if (tipo === "requisicao_enviada_autorizacao") {
    return "Fila de autorizações";
  }
  if (tipo === "requisicao_autorizada") {
    return "Fila de atendimentos";
  }
  if (tipo === "requisicao_pronta_para_retirada") {
    return "Fila de atendimentos";
  }
  return undefined;
}

export function formatNotificationDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}
