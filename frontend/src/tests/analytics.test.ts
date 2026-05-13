import { afterEach, describe, expect, it, vi } from "vitest";

import {
  reportApiError,
  sanitizeAnalyticsPayload,
  trackEvent,
} from "../features/analytics/analytics";
import { ApiError, supportDetailsFromError } from "../shared/api/errors";

describe("frontend analytics", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("remove payloads com campos sensiveis antes do envio", () => {
    expect(
      sanitizeAnalyticsPayload({
        event_type: "draft_saved",
        screen: "nova_requisicao",
        numero_publico: "REQ-2026-000001",
      }),
    ).toBeNull();
  });

  it("mantem somente campos permitidos", () => {
    expect(
      sanitizeAnalyticsPayload({
        event_type: "api_error",
        endpoint_key: "/api/v1/requisitions/{id}/",
        http_status: 500,
        ignored: "x",
      }),
    ).toEqual({
      event_type: "api_error",
      endpoint_key: "/api/v1/requisitions/{id}/",
      http_status: 500,
    });
  });

  it("recusa endpoint_key com identificador real", () => {
    expect(
      sanitizeAnalyticsPayload({
        event_type: "api_error",
        endpoint_key: "/api/v1/requisitions/123/",
        http_status: 500,
      }),
    ).toBeNull();
  });

  it("recusa endpoint_key com uuid ou hash", () => {
    expect(
      sanitizeAnalyticsPayload({
        event_type: "api_error",
        endpoint_key: "/api/v1/requisitions/550e8400-e29b-41d4-a716-446655440000/",
        http_status: 500,
      }),
    ).toBeNull();
    expect(
      sanitizeAnalyticsPayload({
        event_type: "api_error",
        endpoint_key: "/api/v1/requisitions/deadbeef/",
        http_status: 500,
      }),
    ).toBeNull();
  });

  it("envia evento permitido sem PII", async () => {
    const requests: unknown[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (request: Request) => {
        requests.push(await request.json());
        return new Response(
          JSON.stringify({
            event_type: "draft_saved",
            screen: "nova_requisicao",
            draft_step: "itens",
            action: "",
            endpoint_key: "",
            http_status: null,
            error_code: "",
            trace_id: "",
            created_at: "2026-05-12T00:00:00Z",
          }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        );
      }),
    );

    trackEvent({
      event_type: "draft_saved",
      screen: "nova_requisicao",
      draft_step: "itens",
    });
    await vi.waitFor(() => {
      expect(requests).toEqual([
        {
          event_type: "draft_saved",
          screen: "nova_requisicao",
          draft_step: "itens",
        },
      ]);
    });
  });

  it("normaliza erro de API por endpoint sem path com ID", async () => {
    const requests: unknown[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (request: Request) => {
        requests.push(await request.json());
        return new Response(
          JSON.stringify({
            event_type: "api_error",
            endpoint_key: "/api/v1/requisitions/{id}/",
            http_status: 409,
            error_code: "domain_conflict",
            trace_id: "trace-domain",
            screen: "",
            draft_step: "",
            action: "",
            created_at: "2026-05-12T00:00:00Z",
          }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        );
      }),
    );

    reportApiError(
      new ApiError(
        "Conflito.",
        409,
        {
          error: {
            code: "domain_conflict",
            message: "Conflito.",
            details: { item_id: 123 },
            trace_id: "trace-domain",
          },
        },
        "/api/v1/requisitions/{id}/",
      ),
    );

    await vi.waitFor(() => {
      expect(requests).toEqual([
        {
          event_type: "api_error",
          endpoint_key: "/api/v1/requisitions/{id}/",
          http_status: 409,
          error_code: "domain_conflict",
          trace_id: "trace-domain",
        },
      ]);
    });
  });

  it("detalhes de suporte nao incluem details bruto", () => {
    expect(
      supportDetailsFromError(
        new ApiError(
          "Conflito.",
          409,
          {
            error: {
              code: "domain_conflict",
              message: "Conflito.",
              details: { item_id: 123 },
              trace_id: "trace-domain",
            },
          },
          "/api/v1/requisitions/{id}/",
        ),
      ),
    ).toBe("status: 409\ncode: domain_conflict\ntrace_id: trace-domain");
  });
});
