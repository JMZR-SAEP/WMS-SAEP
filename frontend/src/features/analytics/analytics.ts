import { ApiError, apiErrorCode, apiErrorTraceId } from "../../shared/api/errors";
import { apiClient } from "../../shared/api/client";

export type AnalyticsEventType =
  | "login_success"
  | "draft_started"
  | "draft_saved"
  | "draft_submitted"
  | "draft_abandoned"
  | "authorization_total"
  | "authorization_partial"
  | "authorization_refused"
  | "api_error";

export type AnalyticsScreen =
  | "login"
  | "minhas_requisicoes"
  | "nova_requisicao"
  | "requisicao_detalhe"
  | "autorizacoes"
  | "atendimentos"
  | "alertas"
  | "shell";

export type AnalyticsDraftStep = "beneficiario" | "itens" | "revisao" | "envio";

export type AnalyticsEventInput = {
  event_type: AnalyticsEventType;
  screen?: AnalyticsScreen;
  draft_step?: AnalyticsDraftStep;
  action?: string;
  endpoint_key?: string;
  http_status?: number;
  error_code?: string;
  trace_id?: string;
};

const ALLOWED_ANALYTICS_KEYS = new Set([
  "event_type",
  "screen",
  "draft_step",
  "action",
  "endpoint_key",
  "http_status",
  "error_code",
  "trace_id",
]);

const SENSITIVE_ANALYTICS_KEYS = new Set([
  "beneficiario",
  "beneficiario_id",
  "content",
  "details",
  "endpoint",
  "id",
  "itens",
  "material",
  "material_id",
  "mensagem",
  "nome",
  "numero",
  "numero_publico",
  "password",
  "raw_url",
  "requisicao",
  "requisicao_id",
  "text",
  "user",
  "user_id",
  "usuario",
  "usuario_id",
]);

const UUID_ENDPOINT_SEGMENT_PATTERN =
  /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/;
const HEX_ENDPOINT_SEGMENT_PATTERN = /^[0-9a-fA-F]{8,}$/;

function endpointSegmentHasIdentifier(segment: string) {
  return (
    /^\d+$/.test(segment) ||
    UUID_ENDPOINT_SEGMENT_PATTERN.test(segment) ||
    HEX_ENDPOINT_SEGMENT_PATTERN.test(segment)
  );
}

function isSafeEndpointKey(value: unknown) {
  if (value === undefined || value === "") {
    return true;
  }
  if (typeof value !== "string") {
    return false;
  }
  if (value.includes("?") || value.includes("#")) {
    return false;
  }

  return !value
    .split("/")
    .filter(Boolean)
    .some((segment) => endpointSegmentHasIdentifier(segment));
}

export function sanitizeAnalyticsPayload(input: Record<string, unknown>) {
  if (Object.keys(input).some((key) => SENSITIVE_ANALYTICS_KEYS.has(key))) {
    return null;
  }
  if (!isSafeEndpointKey(input.endpoint_key)) {
    return null;
  }

  return Object.fromEntries(
    Object.entries(input).filter(
      ([key, value]) => ALLOWED_ANALYTICS_KEYS.has(key) && value !== undefined && value !== "",
    ),
  ) as AnalyticsEventInput;
}

export async function recordAnalyticsEvent(input: AnalyticsEventInput) {
  const payload = sanitizeAnalyticsPayload(input);
  if (!payload) {
    return null;
  }

  const { data, error, response } = await apiClient.POST("/api/v1/analytics/events/", {
    body: payload,
  });

  if (error || !data) {
    throw new ApiError(
      error?.error?.message || "Não foi possível registrar analytics.",
      response.status,
      error,
      "/api/v1/analytics/events/",
    );
  }

  return data;
}

export function trackEvent(input: AnalyticsEventInput) {
  void recordAnalyticsEvent(input).catch(() => undefined);
}

export function reportApiError(error: unknown) {
  if (!(error instanceof ApiError) || error.endpointKey === "/api/v1/analytics/events/") {
    return;
  }
  if (error.status === 401 || error.payload?.error?.code === "not_authenticated") {
    return;
  }

  trackEvent({
    event_type: "api_error",
    endpoint_key: error.endpointKey,
    http_status: error.status,
    error_code: apiErrorCode(error),
    trace_id: apiErrorTraceId(error) ?? undefined,
  });
}
