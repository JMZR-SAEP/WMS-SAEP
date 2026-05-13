import type { components } from "./schema";

export type ErrorResponse = components["schemas"]["ErrorResponse"];

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly payload?: ErrorResponse,
    readonly endpointKey?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function messageFromErrorPayload(error: ErrorResponse | undefined, fallback: string) {
  return error?.error?.message || fallback;
}

export function queryErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

export function supportDetailsFromError(error: unknown) {
  if (!(error instanceof ApiError)) {
    return null;
  }

  const details = [
    `status: ${error.status}`,
    error.payload?.error?.code ? `code: ${error.payload.error.code}` : null,
    error.payload?.error?.trace_id ? `trace_id: ${error.payload.error.trace_id}` : null,
  ].filter(Boolean);

  if (details.length === 1 && !error.payload?.error?.code && !error.payload?.error?.trace_id) {
    return null;
  }

  return details.join("\n");
}

export function apiErrorCode(error: unknown) {
  return error instanceof ApiError ? error.payload?.error?.code : undefined;
}

export function apiErrorTraceId(error: unknown) {
  return error instanceof ApiError ? error.payload?.error?.trace_id : undefined;
}
