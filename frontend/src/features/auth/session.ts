import { queryOptions } from "@tanstack/react-query";

import { apiClient } from "../../shared/api/client";
import type { components } from "../../shared/api/schema";

export type AuthSession = components["schemas"]["AuthSessionOutput"];
export type AuthLoginInput = components["schemas"]["AuthLoginInput"];
export type ErrorResponse = components["schemas"]["ErrorResponse"];

export const PAPEL_OPERACIONAL_VALUES = [
  "solicitante",
  "auxiliar_setor",
  "chefe_setor",
  "auxiliar_almoxarifado",
  "chefe_almoxarifado",
] as const;

export type PapelOperacional = (typeof PAPEL_OPERACIONAL_VALUES)[number];

export const UNKNOWN_ROLE_PATH = "/unknown-role";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly payload?: ErrorResponse,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const authQueryKeys = {
  me: ["auth", "me"] as const,
};

function messageFromError(error: ErrorResponse | undefined, fallback: string) {
  return error?.error?.message || fallback;
}

export function isAuthError(error: unknown) {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

export function isUnauthenticatedError(error: unknown) {
  if (!(error instanceof ApiError)) {
    return false;
  }

  if (error.status === 401) {
    return true;
  }

  return error.status === 403 && error.payload?.error?.code === "not_authenticated";
}

export async function ensureCsrfCookie() {
  const result = await apiClient.GET("/api/v1/auth/csrf/");
  const error = result.error as ErrorResponse | undefined;

  if (error || !result.data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível preparar a sessão."),
      result.response.status,
      error,
    );
  }
}

export async function fetchCurrentSession() {
  // Contract: GET /auth/me/ bootstraps session state and does not require CSRF.
  const { data, error, response } = await apiClient.GET("/api/v1/auth/me/");

  if (error || !data) {
    throw new ApiError(messageFromError(error, "Sessão expirada."), response.status, error);
  }

  return data;
}

export async function loginWithMatricula(input: AuthLoginInput) {
  await ensureCsrfCookie();

  const { data, error, response } = await apiClient.POST("/api/v1/auth/login/", {
    body: input,
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Matrícula funcional ou senha inválidas."),
      response.status,
      error,
    );
  }

  return data;
}

export async function logoutSession() {
  await ensureCsrfCookie();

  const { error, response } = await apiClient.POST("/api/v1/auth/logout/");

  if (error) {
    throw new ApiError(messageFromError(error, "Não foi possível encerrar a sessão."), response.status, error);
  }
}

export const meQueryOptions = queryOptions({
  queryKey: authQueryKeys.me,
  queryFn: fetchCurrentSession,
  retry: false,
});

export function isPapelOperacional(value: string): value is PapelOperacional {
  return PAPEL_OPERACIONAL_VALUES.includes(value as PapelOperacional);
}

export function homePathForPapel(papel: string) {
  switch (papel as PapelOperacional) {
    case "solicitante":
    case "auxiliar_setor":
      return "/minhas-requisicoes";
    case "chefe_setor":
      return "/autorizacoes";
    case "auxiliar_almoxarifado":
    case "chefe_almoxarifado":
      return "/atendimentos";
    default:
      return UNKNOWN_ROLE_PATH;
  }
}
