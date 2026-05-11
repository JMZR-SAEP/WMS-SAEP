import { RouterProvider } from "@tanstack/react-router";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../app/providers";
import { createAppQueryClient } from "../app/query-client";
import { buildRouter } from "../app/router";
import { formatDateTime } from "../features/requisitions/requisitions";

const originalClipboardDescriptor = Object.getOwnPropertyDescriptor(navigator, "clipboard");

function renderRoute(pathname: string) {
  window.history.replaceState({}, "", pathname);
  const queryClient = createAppQueryClient();
  const router = buildRouter({ queryClient });

  return render(
    <AppProviders queryClient={queryClient}>
      <RouterProvider router={router} />
    </AppProviders>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.sessionStorage.clear();
  if (originalClipboardDescriptor) {
    Object.defineProperty(navigator, "clipboard", originalClipboardDescriptor);
  } else {
    Reflect.deleteProperty(navigator, "clipboard");
  }
});

const jsonHeaders = { "Content-Type": "application/json" };

function requestUrl(request: Request) {
  return request.url;
}

function requestSearchParam(request: Request, name: string) {
  return new URL(requestUrl(request)).searchParams.get(name);
}

function mockWorklistViewport(isMobile: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      matches: isMobile && query === "(max-width: 860px)",
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  );
}

function authSession(papel = "solicitante") {
  return {
    id: 10,
    matricula_funcional: "91003",
    nome_completo: "Usuario Piloto",
    papel,
    setor: {
      id: 1,
      nome: "Operacao",
    },
    is_authenticated: true,
  };
}

function chefeSession() {
  return {
    id: 20,
    matricula_funcional: "91003",
    nome_completo: "Chefe Piloto",
    papel: "chefe_setor",
    setor: {
      id: 2,
      nome: "Manutencao",
    },
    is_authenticated: true,
  };
}

function sessionResponse(session = authSession()) {
  return new Response(JSON.stringify(session), { status: 200, headers: jsonHeaders });
}

function requisitionListItem(overrides = {}) {
  return {
    id: 101,
    numero_publico: "REQ-2026-000101",
    status: "aguardando_autorizacao",
    criador: {
      id: 10,
      matricula_funcional: "91003",
      nome_completo: "Usuario Piloto",
    },
    beneficiario: {
      id: 10,
      matricula_funcional: "91003",
      nome_completo: "Usuario Piloto",
    },
    setor_beneficiario: {
      id: 1,
      nome: "Operacao",
    },
    data_criacao: "2026-05-01T10:00:00Z",
    data_envio_autorizacao: "2026-05-01T11:00:00Z",
    data_autorizacao_ou_recusa: null,
    data_finalizacao: null,
    updated_at: "2026-05-01T11:00:00Z",
    total_itens: 1,
    ...overrides,
  };
}

function requisitionListResponse(results = [requisitionListItem()]) {
  return new Response(
    JSON.stringify({
      count: results.length,
      page: 1,
      page_size: 20,
      total_pages: 1,
      next: null,
      previous: null,
      results,
    }),
    { status: 200, headers: jsonHeaders },
  );
}

function pendingApprovalListItem(overrides = {}) {
  return {
    id: 101,
    numero_publico: "REQ-2026-000101",
    status: "aguardando_autorizacao",
    data_envio_autorizacao: "2026-05-01T11:00:00Z",
    criador: {
      id: 10,
      matricula_funcional: "91003",
      nome_completo: "Usuario Piloto",
    },
    beneficiario: {
      id: 11,
      matricula_funcional: "91004",
      nome_completo: "Beneficiario Piloto",
    },
    setor_beneficiario: {
      id: 2,
      nome: "Manutencao",
    },
    total_itens: 2,
    ...overrides,
  };
}

function pendingApprovalListResponse(results = [pendingApprovalListItem()]) {
  return new Response(
    JSON.stringify({
      count: results.length,
      page: 1,
      page_size: 20,
      total_pages: 1,
      next: null,
      previous: null,
      results,
    }),
    { status: 200, headers: jsonHeaders },
  );
}

function warehouseSession() {
  return {
    id: 30,
    matricula_funcional: "91005",
    nome_completo: "Almoxarifado Piloto",
    papel: "auxiliar_almoxarifado",
    setor: {
      id: 3,
      nome: "Almoxarifado",
    },
    is_authenticated: true,
  };
}

function pendingFulfillmentListItem(overrides = {}) {
  return {
    id: 101,
    numero_publico: "REQ-2026-000101",
    status: "autorizada",
    beneficiario: {
      id: 11,
      matricula_funcional: "91004",
      nome_completo: "Beneficiario Piloto",
    },
    setor_beneficiario: {
      id: 2,
      nome: "Manutencao",
    },
    chefe_autorizador: {
      id: 20,
      matricula_funcional: "91001",
      nome_completo: "Chefe Piloto",
    },
    data_autorizacao_ou_recusa: "2026-05-01T12:00:00Z",
    total_itens: 2,
    ...overrides,
  };
}

function pendingFulfillmentListResponse(results = [pendingFulfillmentListItem()]) {
  return new Response(
    JSON.stringify({
      count: results.length,
      page: 1,
      page_size: 20,
      total_pages: 1,
      next: null,
      previous: null,
      results,
    }),
    { status: 200, headers: jsonHeaders },
  );
}

function notificationListItem(overrides = {}) {
  return {
    id: 901,
    tipo: "requisicao_enviada_autorizacao",
    titulo: "Requisição aguardando autorização",
    mensagem: "A requisição REQ-2026-000101 aguarda autorização.",
    created_at: "2026-05-02T09:30:00Z",
    lida: false,
    lida_em: null,
    leitura_suportada: true,
    destino: {
      tipo: "usuario",
      usuario_id: 10,
      papel: null,
    },
    objeto_relacionado: {
      tipo: "requisicao",
      id: 101,
      numero_publico: "REQ-2026-000101",
      status: "aguardando_autorizacao",
    },
    ...overrides,
  };
}

function notificationListResponse(results = [notificationListItem()]) {
  return new Response(
    JSON.stringify({
      count: results.length,
      page: 1,
      page_size: 6,
      total_pages: 1,
      next: null,
      previous: null,
      results,
    }),
    { status: 200, headers: jsonHeaders },
  );
}

function notificationUnreadCountResponse(unreadCount = 0) {
  return new Response(
    JSON.stringify({
      unread_count: unreadCount,
    }),
    { status: 200, headers: jsonHeaders },
  );
}

function maybeNotificationsRequest(request: Request) {
  if (
    requestUrl(request).includes("/api/v1/notifications/") &&
    request.method === "GET" &&
    requestUrl(request).includes("/api/v1/notifications/unread-count/")
  ) {
    return notificationUnreadCountResponse(1);
  }

  if (
    requestUrl(request).includes("/api/v1/notifications/") &&
    request.method === "GET" &&
    !requestUrl(request).includes("/mark-read/")
  ) {
    return notificationListResponse();
  }

  if (
    requestUrl(request).includes("/api/v1/notifications/") &&
    request.method === "POST" &&
    requestUrl(request).includes("/mark-read/")
  ) {
    return new Response(
      JSON.stringify(
        notificationListItem({
          lida: true,
          lida_em: "2026-05-02T09:35:00Z",
        }),
      ),
      { status: 200, headers: jsonHeaders },
    );
  }

  return null;
}

function requisitionDetailResponse(
  itemOverrides: Record<string, unknown> = {},
  requisitionOverrides: Record<string, unknown> = {},
) {
  return new Response(
    JSON.stringify({
      id: 101,
      numero_publico: "REQ-2026-000101",
      status: "autorizada",
      criador: {
        id: 10,
        matricula_funcional: "91003",
        nome_completo: "Usuario Piloto",
      },
      beneficiario: {
        id: 10,
        matricula_funcional: "91003",
        nome_completo: "Usuario Piloto",
      },
      setor_beneficiario: {
        id: 1,
        nome: "Operacao",
      },
      chefe_autorizador: {
        id: 20,
        matricula_funcional: "91001",
        nome_completo: "Chefe Piloto",
      },
      responsavel_atendimento: null,
      data_criacao: "2026-05-01T10:00:00Z",
      data_envio_autorizacao: "2026-05-01T11:00:00Z",
      data_autorizacao_ou_recusa: "2026-05-01T12:00:00Z",
      motivo_recusa: "",
      motivo_cancelamento: "",
      data_finalizacao: null,
      retirante_fisico: "",
      observacao: "Observacao operacional",
      observacao_atendimento: "",
      itens: [
        {
          id: 501,
          material: {
            id: 301,
            codigo_completo: "010.001.001",
            nome: "Papel sulfite A4",
            unidade_medida: "UN",
          },
          unidade_medida: "UN",
          quantidade_solicitada: "2.000",
          quantidade_autorizada: "1.000",
          quantidade_entregue: "0.000",
          justificativa_autorizacao_parcial: "Saldo parcial",
          justificativa_atendimento_parcial: "",
          observacao: "Urgente",
          ...itemOverrides,
        },
      ],
      eventos: [
        {
          id: 701,
          tipo_evento: "autorizacao_parcial",
          usuario: {
            id: 20,
            matricula_funcional: "91001",
            nome_completo: "Chefe Piloto",
          },
          data_hora: "2026-05-01T12:00:00Z",
          observacao: "Autorizado parcialmente por saldo.",
        },
      ],
      ...requisitionOverrides,
    }),
    { status: 200, headers: jsonHeaders },
  );
}

function pendingApprovalDetailResponse(itemOverrides = {}) {
  return new Response(
    JSON.stringify({
      id: 101,
      numero_publico: "REQ-2026-000101",
      status: "aguardando_autorizacao",
      criador: {
        id: 10,
        matricula_funcional: "91003",
        nome_completo: "Usuario Piloto",
      },
      beneficiario: {
        id: 11,
        matricula_funcional: "91004",
        nome_completo: "Beneficiario Piloto",
      },
      setor_beneficiario: {
        id: 2,
        nome: "Manutencao",
      },
      chefe_autorizador: null,
      responsavel_atendimento: null,
      data_criacao: "2026-05-01T10:00:00Z",
      data_envio_autorizacao: "2026-05-01T11:00:00Z",
      data_autorizacao_ou_recusa: null,
      motivo_recusa: "",
      motivo_cancelamento: "",
      data_finalizacao: null,
      retirante_fisico: "",
      observacao: "Observacao operacional",
      observacao_atendimento: "",
      itens: [
        {
          id: 501,
          material: {
            id: 301,
            codigo_completo: "010.001.001",
            nome: "Papel sulfite A4",
            unidade_medida: "UN",
          },
          unidade_medida: "UN",
          quantidade_solicitada: "2.000",
          quantidade_autorizada: "0.000",
          quantidade_entregue: "0.000",
          justificativa_autorizacao_parcial: "",
          justificativa_atendimento_parcial: "",
          observacao: "Urgente",
          ...itemOverrides,
        },
      ],
      eventos: [
        {
          id: 701,
          tipo_evento: "envio_autorizacao",
          usuario: {
            id: 10,
            matricula_funcional: "91003",
            nome_completo: "Usuario Piloto",
          },
          data_hora: "2026-05-01T11:00:00Z",
          observacao: "Enviada para avaliação.",
        },
      ],
    }),
    { status: 200, headers: jsonHeaders },
  );
}

function draftRequisitionDetailResponse(overrides = {}) {
  return new Response(
    JSON.stringify({
      id: 101,
      numero_publico: null,
      status: "rascunho",
      criador: {
        id: 10,
        matricula_funcional: "91003",
        nome_completo: "Usuario Piloto",
      },
      beneficiario: {
        id: 10,
        matricula_funcional: "91003",
        nome_completo: "Usuario Piloto",
      },
      setor_beneficiario: {
        id: 1,
        nome: "Operacao",
      },
      chefe_autorizador: null,
      responsavel_atendimento: null,
      data_criacao: "2026-05-01T10:00:00Z",
      data_envio_autorizacao: null,
      data_autorizacao_ou_recusa: null,
      motivo_recusa: "",
      motivo_cancelamento: "",
      data_finalizacao: null,
      retirante_fisico: "",
      observacao: "Observacao antiga",
      observacao_atendimento: "",
      itens: [
        {
          id: 501,
          material: {
            id: 301,
            codigo_completo: "010.001.001",
            nome: "Papel sulfite A4",
            unidade_medida: "UN",
          },
          unidade_medida: "UN",
          quantidade_solicitada: "2.000",
          quantidade_autorizada: "0.000",
          quantidade_entregue: "0.000",
          justificativa_autorizacao_parcial: "",
          justificativa_atendimento_parcial: "",
          observacao: "Item antigo",
        },
      ],
      eventos: [],
      ...overrides,
    }),
    { status: 200, headers: jsonHeaders },
  );
}

function materialListResponse(results = [
  {
    id: 301,
    codigo_completo: "010.001.001",
    nome: "Papel sulfite A4",
    descricao: "Pacote com 500 folhas",
    unidade_medida: "UN",
    saldo_disponivel: 12,
  },
]) {
  return new Response(
    JSON.stringify({
      count: results.length,
      page: 1,
      page_size: 10,
      total_pages: 1,
      next: null,
      previous: null,
      results,
    }),
    { status: 200, headers: jsonHeaders },
  );
}

function beneficiaryLookupResponse() {
  return new Response(
    JSON.stringify([
      {
        id: 11,
        matricula_funcional: "91004",
        nome_completo: "Beneficiario Terceiro",
        setor: {
          id: 1,
          nome: "Operacao",
        },
      },
    ]),
    { status: 200, headers: jsonHeaders },
  );
}

function csrfResponse() {
  return new Response(JSON.stringify({ csrf_token: "csrf-token" }), {
    status: 200,
    headers: jsonHeaders,
  });
}

function unauthenticatedResponse() {
  return new Response(
    JSON.stringify({
      error: {
        code: "not_authenticated",
        message: "Autenticação necessária.",
        details: {},
        trace_id: null,
      },
    }),
    { status: 401, headers: jsonHeaders },
  );
}

function unauthenticatedForbiddenResponse() {
  return new Response(
    JSON.stringify({
      error: {
        code: "not_authenticated",
        message: "Autenticação necessária.",
        details: {},
        trace_id: null,
      },
    }),
    { status: 403, headers: jsonHeaders },
  );
}

function forbiddenResponse() {
  return new Response(
    JSON.stringify({
      error: {
        code: "permission_denied",
        message: "Permissão negada.",
        details: {},
        trace_id: null,
      },
    }),
    { status: 403, headers: jsonHeaders },
  );
}

function mockCurrentSession(papel = "solicitante") {
  vi.stubGlobal(
    "fetch",
    vi.fn((request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(authSession(papel));
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    }),
  );
}

describe("frontend pilot router", () => {
  it("renders login with SAEP identity and no scaffold copy", async () => {
    renderRoute("/login");

    expect(await screen.findAllByRole("img", { name: "SAEP" })).toHaveLength(1);
    expect(screen.getByRole("heading", { name: "Entrar no piloto" })).toBeInTheDocument();
    expect(screen.queryByText(/scaffold/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/próxima slice/i)).not.toBeInTheDocument();
  });

  it("resolves root to home by operational papel", async () => {
    mockCurrentSession("chefe_setor");

    const { container } = renderRoute("/");

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/autorizacoes");
    });
  });

  it("resolves unknown operational papel to neutral fallback", async () => {
    mockCurrentSession("papel_novo");

    const { container } = renderRoute("/");

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/unknown-role");
    });
    expect(
      await screen.findByRole("heading", { name: "Papel operacional não mapeado" }),
    ).toBeInTheDocument();
  });

  it("renders authenticated shell with operational SAEP copy", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        if (requestUrl(request).includes("/api/v1/requisitions/mine/")) {
          return requisitionListResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
        if (notificationsResponse) return notificationsResponse;
        throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/minhas-requisicoes");

    expect(await screen.findByRole("img", { name: "SAEP" })).toBeInTheDocument();
    expect(screen.getByText("WMS-SAEP")).toBeInTheDocument();
    expect(screen.getByText("Requisições de materiais")).toBeInTheDocument();
    expect(screen.queryByText(/scaffold/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/fundação/i)).not.toBeInTheDocument();
  });

  it("logs in with matricula and sends chefe de setor to authorization queue", async () => {
    let loggedIn = false;
    const session = chefeSession();
    const fetchMock = vi.fn((request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return loggedIn ? sessionResponse(session) : unauthenticatedResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/auth/csrf/")) {
        return csrfResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/auth/login/")) {
        loggedIn = true;
        return sessionResponse(session);
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderRoute("/login");

    fireEvent.change(await screen.findByLabelText("Matrícula funcional"), {
      target: { value: "91003" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "senha-segura-123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/autorizacoes");
    });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.objectContaining({
        method: "POST",
        url: expect.stringContaining("/api/v1/auth/login/"),
      }),
    );
  });

  it("shows backend authentication error on invalid credentials", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return unauthenticatedResponse();
        }

        if (requestUrl(request).endsWith("/api/v1/auth/csrf/")) {
          return csrfResponse();
        }

        if (requestUrl(request).endsWith("/api/v1/auth/login/")) {
          return new Response(
            JSON.stringify({
              error: {
                code: "authentication_failed",
                message: "Matrícula funcional ou senha inválidas.",
                details: {},
                trace_id: null,
              },
            }),
            { status: 401, headers: jsonHeaders },
          );
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/login");

    fireEvent.change(await screen.findByLabelText("Matrícula funcional"), {
      target: { value: "91003" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "errada" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(
      await screen.findByText("Matrícula funcional ou senha inválidas."),
    ).toBeInTheDocument();
  });

  it("ignores external redirect after login", async () => {
    let loggedIn = false;
    const fetchMock = vi.fn((request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return loggedIn ? sessionResponse(authSession("solicitante")) : unauthenticatedResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/auth/csrf/")) {
        return csrfResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/auth/login/")) {
        loggedIn = true;
        return sessionResponse(authSession("solicitante"));
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderRoute("/login?redirect=https%3A%2F%2Fevil.example%2Fsteal");

    fireEvent.change(await screen.findByLabelText("Matrícula funcional"), {
      target: { value: "91003" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "senha-segura-123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/minhas-requisicoes");
    });
    expect(container.ownerDocument.location.search).toBe("");
  });

  it("strips nested redirect from safe internal redirect", async () => {
    let loggedIn = false;
    const fetchMock = vi.fn((request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return loggedIn ? sessionResponse(authSession("solicitante")) : unauthenticatedResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/auth/csrf/")) {
        return csrfResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/auth/login/")) {
        loggedIn = true;
        return sessionResponse(authSession("solicitante"));
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const encodedRedirect = encodeURIComponent("/minhas-requisicoes?redirect=/login#secao");
    const { container } = renderRoute(`/login?redirect=${encodedRedirect}`);

    fireEvent.change(await screen.findByLabelText("Matrícula funcional"), {
      target: { value: "91003" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "senha-segura-123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/minhas-requisicoes");
    });
    expect(container.ownerDocument.location.search).toBe("");
    expect(container.ownerDocument.location.hash).toBe("#secao");
  });

  it("redirects protected routes without session to login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return unauthenticatedResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/minhas-requisicoes");

    expect(await screen.findByRole("heading", { name: "Entrar no piloto" })).toBeInTheDocument();
    expect(container.ownerDocument.location.pathname).toBe("/login");
    expect(container.ownerDocument.location.search).toBe("?redirect=%2Fminhas-requisicoes");
  });

  it("redirects protected routes on forbidden session bootstrap", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return forbiddenResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/atendimentos");

    expect(await screen.findByRole("heading", { name: "Entrar no piloto" })).toBeInTheDocument();
    expect(container.ownerDocument.location.pathname).toBe("/login");
    expect(container.ownerDocument.location.search).toBe("?redirect=%2Fatendimentos");
  });

  it("renders minhas requisicoes worklist", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        if (requestUrl(request).includes("/api/v1/requisitions/mine/")) {
          return requisitionListResponse([
            requisitionListItem(),
            requisitionListItem({
              id: 102,
              numero_publico: null,
              status: "rascunho",
              beneficiario: {
                id: 11,
                matricula_funcional: "91004",
                nome_completo: "Beneficiario Terceiro",
              },
            }),
          ]);
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );
    renderRoute("/minhas-requisicoes");

    expect(
      await screen.findByRole("heading", { name: "Minhas requisições" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("REQ-2026-000101")).toBeInTheDocument();
    expect(screen.getAllByText("Rascunho").length).toBeGreaterThan(0);
    expect(screen.getByText("Beneficiário terceiro")).toBeInTheDocument();
  });

  it("renders minhas requisicoes as mobile cards without table", async () => {
    mockWorklistViewport(true);
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        if (requestUrl(request).includes("/api/v1/requisitions/mine/")) {
          return requisitionListResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/minhas-requisicoes");

    expect(await screen.findByLabelText("Cards de minhas requisições")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir" })).toHaveAttribute(
      "href",
      "/requisicoes/101",
    );
  });

  it("keeps minhas requisicoes as a desktop table", async () => {
    mockWorklistViewport(false);
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        if (requestUrl(request).includes("/api/v1/requisitions/mine/")) {
          return requisitionListResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/minhas-requisicoes");

    expect(await screen.findByRole("table")).toBeInTheDocument();
    expect(screen.queryByLabelText("Cards de minhas requisições")).not.toBeInTheDocument();
  });

  it("shows a screen skeleton while minhas requisicoes loads", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        if (requestUrl(request).includes("/api/v1/requisitions/mine/")) {
          return new Promise<Response>(() => {});
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/minhas-requisicoes");

    expect(await screen.findByRole("status", { name: "Carregando requisições" })).toBeInTheDocument();
    expect(screen.queryByText("Carregando requisições...")).not.toBeInTheDocument();
  });

  it("does not show third-party badge when creator and beneficiary are the same", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).includes("/api/v1/requisitions/mine/")) {
          return requisitionListResponse([
            requisitionListItem({
              criador: {
                id: 10,
                matricula_funcional: "91003",
                nome_completo: "Solicitante Operacional",
              },
              beneficiario: {
                id: 10,
                matricula_funcional: "91003",
                nome_completo: "Solicitante Operacional",
              },
            }),
          ]);
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/minhas-requisicoes");

    expect(await screen.findByText("REQ-2026-000101")).toBeInTheDocument();
    expect(screen.queryByText("Beneficiário terceiro")).not.toBeInTheDocument();
  });

  it("shows pluralized record count in the status chip", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        if (requestUrl(request).includes("/api/v1/requisitions/mine/")) {
          return requisitionListResponse([
            requisitionListItem(),
            requisitionListItem({
              id: 102,
              numero_publico: "REQ-2026-000102",
            }),
          ]);
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/minhas-requisicoes");

    expect(await screen.findByText("REQ-2026-000101")).toBeInTheDocument();
    expect(screen.getByText("2 registros")).toBeInTheDocument();
  });

  it("shows only the error panel when requisitions loading fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        if (requestUrl(request).includes("/api/v1/requisitions/mine/")) {
          return new Response(
            JSON.stringify({
              error: {
                code: "validation_error",
                message: "Falha no backend",
                details: null,
                trace_id: "trace-router-smoke",
              },
            }),
            {
              status: 422,
              headers: jsonHeaders,
            },
          );
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/minhas-requisicoes");

    expect(await screen.findByText("Erro ao carregar")).toBeInTheDocument();
    expect(screen.getByText("Falha no backend")).toBeInTheDocument();
    expect(screen.queryByText("Nenhuma requisição encontrada")).not.toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("sends list filters from the URL to backend", async () => {
    const requestedUrls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        requestedUrls.push(requestUrl(request));

        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        if (requestUrl(request).includes("/api/v1/requisitions/mine/")) {
          return requisitionListResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/minhas-requisicoes?page=2&search=REQ-2026&status=rascunho");

    expect(await screen.findByText("REQ-2026-000101")).toBeInTheDocument();

    const listUrl = new URL(requestedUrls.find((url) => url.includes("/api/v1/requisitions/mine/"))!);
    expect(listUrl.searchParams.get("page")).toBe("2");
    expect(listUrl.searchParams.get("page_size")).toBe("20");
    expect(listUrl.searchParams.get("search")).toBe("REQ-2026");
    expect(listUrl.searchParams.get("status")).toBe("rascunho");
  });

  it("updates filters in the URL and resets pagination", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        if (requestUrl(request).includes("/api/v1/requisitions/mine/")) {
          return requisitionListResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/minhas-requisicoes?page=3");

    expect(await screen.findByText("REQ-2026-000101")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Busca"), {
      target: { value: "papel" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Filtrar" }));

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/minhas-requisicoes");
      expect(container.ownerDocument.location.search).not.toContain("page=3");
      expect(container.ownerDocument.location.search).toContain("search=papel");
    });
  });

  it("renders authorization queue worklist", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).includes("/api/v1/requisitions/pending-approvals/")) {
          return pendingApprovalListResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/autorizacoes");

    expect(await screen.findByRole("heading", { name: "Fila de autorizações" })).toBeInTheDocument();
    expect(await screen.findByText("REQ-2026-000101")).toBeInTheDocument();
    expect(screen.getByText("Beneficiario Piloto")).toBeInTheDocument();
    expect(screen.getByText("1 registro")).toBeInTheDocument();
  });

  it("renders authorization queue as mobile cards without table", async () => {
    mockWorklistViewport(true);
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).includes("/api/v1/requisitions/pending-approvals/")) {
          return pendingApprovalListResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/autorizacoes?page=2");

    expect(await screen.findByLabelText("Cards da fila de autorizações")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir" })).toHaveAttribute(
      "href",
      "/requisicoes/101?contexto=autorizacao&page=2",
    );
  });

  it("redirects solicitante away from authorization queue", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(authSession("solicitante"));
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/autorizacoes");

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/minhas-requisicoes");
    });
  });

  it("renders formatted envio timestamp in authorization queue", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).includes("/api/v1/requisitions/pending-approvals/")) {
          return pendingApprovalListResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/autorizacoes");

    expect(await screen.findByText("REQ-2026-000101")).toBeInTheDocument();
    expect(screen.getByText(formatDateTime("2026-05-01T11:00:00Z"))).toBeInTheDocument();
  });

  it("sends authorization queue pagination from the URL to backend", async () => {
    const requestedUrls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        requestedUrls.push(requestUrl(request));

        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).includes("/api/v1/requisitions/pending-approvals/")) {
          return pendingApprovalListResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/autorizacoes?page=2");

    expect(await screen.findByText("REQ-2026-000101")).toBeInTheDocument();
    const listUrl = new URL(
      requestedUrls.find((url) => url.includes("/api/v1/requisitions/pending-approvals/"))!,
    );
    expect(listUrl.searchParams.get("page")).toBe("2");
    expect(listUrl.searchParams.get("page_size")).toBe("20");
  });

  it("opens canonical requisition detail from authorization queue with context", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return pendingApprovalDetailResponse();
        }

        if (requestUrl(request).includes("/api/v1/requisitions/pending-approvals/")) {
          return pendingApprovalListResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/autorizacoes");

    expect(await screen.findByText("REQ-2026-000101")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Abrir" }));

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/requisicoes/101");
      expect(container.ownerDocument.location.search).toBe("?contexto=autorizacao");
    });
    expect(await screen.findByRole("link", { name: "Voltar" })).toHaveAttribute("href", "/autorizacoes");
  });

  it("renders fulfillment queue worklist", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(warehouseSession());
        }

        if (requestUrl(request).includes("/api/v1/requisitions/pending-fulfillments/")) {
          return pendingFulfillmentListResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/atendimentos");

    expect(await screen.findByRole("heading", { name: "Fila de atendimento" })).toBeInTheDocument();
    expect(await screen.findByText("REQ-2026-000101")).toBeInTheDocument();
    expect(screen.getByText("Beneficiario Piloto")).toBeInTheDocument();
    expect(screen.getByText("Chefe Piloto")).toBeInTheDocument();
    expect(screen.getByText(formatDateTime("2026-05-01T12:00:00Z"))).toBeInTheDocument();
    expect(screen.getByText("1 registro")).toBeInTheDocument();
  });

  it("renders fulfillment queue as mobile cards without table", async () => {
    mockWorklistViewport(true);
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(warehouseSession());
        }

        if (requestUrl(request).includes("/api/v1/requisitions/pending-fulfillments/")) {
          return pendingFulfillmentListResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/atendimentos?page=2");

    expect(await screen.findByLabelText("Cards da fila de atendimento")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir" })).toHaveAttribute(
      "href",
      "/requisicoes/101?contexto=atendimento&page=2",
    );
  });

  it("opens canonical requisition detail from fulfillment queue with context", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(warehouseSession());
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return requisitionDetailResponse();
        }

        if (requestUrl(request).includes("/api/v1/requisitions/pending-fulfillments/")) {
          return pendingFulfillmentListResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/atendimentos?page=2");

    expect(await screen.findByText("REQ-2026-000101")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Abrir" }));

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/requisicoes/101");
      expect(container.ownerDocument.location.search).toBe("?contexto=atendimento&page=2");
    });
    expect(await screen.findByRole("link", { name: "Voltar" })).toHaveAttribute(
      "href",
      "/atendimentos?page=2",
    );
  });

  it("opens canonical requisition detail from the list", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return requisitionDetailResponse();
        }

        if (requestUrl(request).includes("/api/v1/requisitions/mine/")) {
          return requisitionListResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/minhas-requisicoes?search=REQ");

    expect(await screen.findByText("REQ-2026-000101")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Abrir" }));

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/requisicoes/101");
    });
    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    expect(screen.queryByText("Terceiro")).not.toBeInTheDocument();
    expect(screen.getByText("Papel sulfite A4")).toBeInTheDocument();
    expect(screen.getByText("Autorização parcial: Saldo parcial")).toBeInTheDocument();
    expect(screen.getByText("Autorizado parcialmente por saldo.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "Voltar" }));

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/minhas-requisicoes");
    });
  });

  it("shows a detail skeleton while requisition detail loads", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return new Promise<Response>(() => {});
        }

        const notificationsResponse = maybeNotificationsRequest(request);
        if (notificationsResponse) return notificationsResponse;
        throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/requisicoes/101");

    expect(await screen.findByRole("status", { name: "Carregando requisição" })).toBeInTheDocument();
    expect(screen.queryByText("Carregando requisição...")).not.toBeInTheDocument();
  });

  it("returns from requisition detail to authorization queue when opened with authorization context", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return requisitionDetailResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/requisicoes/101?contexto=autorizacao");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Voltar" }));

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/autorizacoes");
    });
  });

  it("returns from requisition detail to fulfillment queue when opened with fulfillment context", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(warehouseSession());
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return requisitionDetailResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/requisicoes/101?contexto=atendimento&page=2");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Voltar" }));

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/atendimentos");
      expect(container.ownerDocument.location.search).toBe("?page=2");
    });
  });

  it("redirects solicitante away from fulfillment detail context", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(authSession("solicitante"));
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/requisicoes/101?contexto=atendimento");

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/minhas-requisicoes");
    });
  });

  it("keeps permission denied detail errors inline instead of redirecting to login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return forbiddenResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/requisicoes/101?contexto=autorizacao");

    expect(await screen.findByText("Permissão negada.")).toBeInTheDocument();
    expect(container.ownerDocument.location.pathname).toBe("/requisicoes/101");
  });

  it("does not render authorization panel outside pending authorization status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return requisitionDetailResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/requisicoes/101?contexto=autorizacao");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    expect(screen.getByText("Ação bloqueada neste estado")).toBeInTheDocument();
    expect(
      screen.getByText("Requisição autorizada; volte para a fila de autorizações."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ação indisponível" })).toBeDisabled();
    expect(screen.queryByRole("heading", { name: "Autorizar ou recusar requisição" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Autorizar tudo como solicitado" })).not.toBeInTheDocument();
  });

  it("shows blocked reason outside authorized fulfillment status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(warehouseSession());
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return pendingApprovalDetailResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
        if (notificationsResponse) return notificationsResponse;
        throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/requisicoes/101?contexto=atendimento");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    expect(
      screen.getByText("Requisição aguardando autorização; volte para a fila de atendimento."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ação indisponível" })).toBeDisabled();
    expect(screen.queryByRole("heading", { name: "Registrar atendimento" })).not.toBeInTheDocument();
  });

  it("formats requisition quantities with pt-BR decimal rendering", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return requisitionDetailResponse({
            quantidade_solicitada: "2.500",
            quantidade_autorizada: "1.250",
            quantidade_entregue: "0.125",
          });
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/requisicoes/101");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    expect(screen.getByText("2,5 UN")).toBeInTheDocument();
    expect(screen.getByText("1,25 UN")).toBeInTheDocument();
    expect(screen.getByText("0,125 UN")).toBeInTheDocument();
  });

  it("authorizes all requested items from authorization context", async () => {
    let authorizePayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(chefeSession());
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
        return pendingApprovalDetailResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/authorize/")) {
        authorizePayload = await request.json();
        return requisitionDetailResponse({ quantidade_autorizada: "2.000" });
      }

      if (requestUrl(request).includes("/api/v1/requisitions/pending-approvals/")) {
        return pendingApprovalListResponse([]);
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderRoute("/requisicoes/101?contexto=autorizacao");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    const primaryAction = screen.getByRole("button", { name: "Autorizar tudo como solicitado" });
    expect(primaryAction.closest(".detail-primary-action")).not.toBeNull();
    fireEvent.click(primaryAction);

    await waitFor(() => {
      expect(authorizePayload).toEqual({
        itens: [
          {
            item_id: 501,
            quantidade_autorizada: "2.000",
            justificativa_autorizacao_parcial: "",
          },
        ],
      });
      expect(container.ownerDocument.location.pathname).toBe("/autorizacoes");
    });
    expect(await screen.findByText("Nenhuma autorização pendente")).toBeInTheDocument();
  });

  it("fulfills all authorized items from fulfillment context", async () => {
    let fulfillPayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(warehouseSession());
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
        return requisitionDetailResponse({ quantidade_autorizada: "1.000" });
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/fulfill/")) {
        fulfillPayload = await request.json();
        return requisitionDetailResponse({
          quantidade_autorizada: "1.000",
          quantidade_entregue: "1.000",
        });
      }

      if (requestUrl(request).includes("/api/v1/requisitions/pending-fulfillments/")) {
        return pendingFulfillmentListResponse([]);
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderRoute("/requisicoes/101?contexto=atendimento");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Retirante físico"), {
      target: { value: "Joao da Silva" },
    });
    fireEvent.change(screen.getByLabelText("Observação do atendimento"), {
      target: { value: "Retirada no balcão" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preencher entrega completa" }));
    const primaryAction = screen.getByRole("button", { name: "Registrar atendimento" });
    expect(primaryAction.closest(".detail-primary-action")).not.toBeNull();
    fireEvent.click(primaryAction);

    await waitFor(() => {
      expect(fulfillPayload).toEqual({
        retirante_fisico: "Joao da Silva",
        observacao_atendimento: "Retirada no balcão",
        itens: [
          {
            item_id: 501,
            quantidade_entregue: "1.000",
            justificativa_atendimento_parcial: "",
          },
        ],
      });
      expect(container.ownerDocument.location.pathname).toBe("/atendimentos");
    });
    expect(await screen.findByText("Nenhum atendimento pendente")).toBeInTheDocument();
  });

  it("requires inline justification for partial fulfillment", async () => {
    let fulfillPayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(warehouseSession());
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
        return requisitionDetailResponse({ quantidade_autorizada: "2.000" });
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/fulfill/")) {
        fulfillPayload = await request.json();
        return requisitionDetailResponse({
          quantidade_autorizada: "2.000",
          quantidade_entregue: "1.500",
          justificativa_atendimento_parcial: "Retirada parcial",
        });
      }

      if (requestUrl(request).includes("/api/v1/requisitions/pending-fulfillments/")) {
        return pendingFulfillmentListResponse([]);
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderRoute("/requisicoes/101?contexto=atendimento");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Quantidade entregue para Papel sulfite A4"), {
      target: { value: "1,5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Registrar atendimento" }));

    expect(await screen.findByText("Informe justificativa para atendimento parcial ou zerado.")).toBeInTheDocument();
    expect(fulfillPayload).toBeUndefined();

    fireEvent.change(screen.getByLabelText("Justificativa de atendimento para Papel sulfite A4"), {
      target: { value: "Retirada parcial" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Registrar atendimento" }));

    await waitFor(() => {
      expect(fulfillPayload).toEqual({
        retirante_fisico: "",
        observacao_atendimento: "",
        itens: [
          {
            item_id: 501,
            quantidade_entregue: "1.5",
            justificativa_atendimento_parcial: "Retirada parcial",
          },
        ],
      });
    });
  });

  it("keeps user on detail when fulfillment action returns domain error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(warehouseSession());
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return requisitionDetailResponse({ quantidade_autorizada: "1.000" });
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/fulfill/")) {
          return new Response(
            JSON.stringify({
              error: {
                code: "domain_conflict",
                message: "Somente requisições autorizadas podem ser atendidas.",
                details: {},
                trace_id: "trace-domain",
              },
            }),
            { status: 409, headers: jsonHeaders },
          );
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/requisicoes/101?contexto=atendimento");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Preencher entrega completa" }));
    fireEvent.click(screen.getByRole("button", { name: "Registrar atendimento" }));

    expect(await screen.findByText("Somente requisições autorizadas podem ser atendidas.")).toBeInTheDocument();
    expect(container.ownerDocument.location.pathname).toBe("/requisicoes/101");
    expect(container.ownerDocument.location.search).toBe("?contexto=atendimento");
  });

  it("redirects to login when fulfillment action returns 401", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn((request: Request) => {
          if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
            return sessionResponse(warehouseSession());
          }

          if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
            return requisitionDetailResponse({ quantidade_autorizada: "1.000" });
          }

          if (requestUrl(request).endsWith("/api/v1/requisitions/101/fulfill/")) {
            return new Response(null, { status: 401, headers: jsonHeaders });
          }

          const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
        }),
      );

      const { container } = renderRoute("/requisicoes/101?contexto=atendimento");

      expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Preencher entrega completa" }));
      fireEvent.click(screen.getByRole("button", { name: "Registrar atendimento" }));

      expect(await screen.findByRole("heading", { name: "Entrar no piloto" })).toBeInTheDocument();
      expect(container.ownerDocument.location.pathname).toBe("/login");
      expect(container.ownerDocument.location.search).toBe(
        "?redirect=%2Frequisicoes%2F101%3Fcontexto%3Datendimento",
      );
    },
  );

  it("cancels authorized requisition from fulfillment context only with a reason", async () => {
    let cancelPayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(warehouseSession());
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
        return requisitionDetailResponse({ quantidade_autorizada: "1.000" });
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/cancel/")) {
        cancelPayload = await request.json();
        return requisitionDetailResponse({}, { status: "cancelada" });
      }

      if (requestUrl(request).includes("/api/v1/requisitions/pending-fulfillments/")) {
        return pendingFulfillmentListResponse([]);
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderRoute("/requisicoes/101?contexto=atendimento");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancelar requisição autorizada" }));

    expect(await screen.findByText("Informe o motivo do cancelamento.")).toBeInTheDocument();
    expect(cancelPayload).toBeUndefined();

    fireEvent.change(screen.getByLabelText("Motivo do cancelamento operacional"), {
      target: { value: "Material indisponível no balcão" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Cancelar requisição autorizada" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("Cancelar requisição autorizada?");
    fireEvent.click(screen.getByRole("button", { name: "Confirmar cancelamento" }));

    await waitFor(() => {
      expect(cancelPayload).toEqual({
        motivo_cancelamento: "Material indisponível no balcão",
      });
      expect(container.ownerDocument.location.pathname).toBe("/atendimentos");
    });
  });

  it("redirects to login when cancel action returns 401", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn((request: Request) => {
          if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
            return sessionResponse(warehouseSession());
          }

          if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
            return requisitionDetailResponse({ quantidade_autorizada: "1.000" });
          }

          if (requestUrl(request).endsWith("/api/v1/requisitions/101/cancel/")) {
            return new Response(null, { status: 401, headers: jsonHeaders });
          }

          const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
        }),
      );

      const { container } = renderRoute("/requisicoes/101?contexto=atendimento");

      expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Cancelar requisição autorizada" }));
      fireEvent.change(screen.getByLabelText("Motivo do cancelamento operacional"), {
        target: { value: "Material indisponível no balcão" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Cancelar requisição autorizada" }));
      expect(await screen.findByRole("dialog")).toHaveTextContent("Cancelar requisição autorizada?");
      fireEvent.click(screen.getByRole("button", { name: "Confirmar cancelamento" }));

      expect(await screen.findByRole("heading", { name: "Entrar no piloto" })).toBeInTheDocument();
      expect(container.ownerDocument.location.pathname).toBe("/login");
      expect(container.ownerDocument.location.search).toBe(
        "?redirect=%2Frequisicoes%2F101%3Fcontexto%3Datendimento",
      );
    },
  );

  it("preserves authorization page when queue request expires", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).includes("/api/v1/requisitions/pending-approvals/")) {
          return unauthenticatedForbiddenResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/autorizacoes?page=2");

    expect(await screen.findByRole("heading", { name: "Entrar no piloto" })).toBeInTheDocument();
    expect(container.ownerDocument.location.pathname).toBe("/login");
    expect(container.ownerDocument.location.search).toBe("?redirect=%2Fautorizacoes%3Fpage%3D2");
  });

  it("does not render empty state while redirecting authorization queue auth error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).includes("/api/v1/requisitions/pending-approvals/")) {
          return unauthenticatedForbiddenResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/autorizacoes");

    expect(await screen.findByRole("heading", { name: "Entrar no piloto" })).toBeInTheDocument();
    expect(screen.queryByText("Nenhuma autorização pendente")).not.toBeInTheDocument();
  });

  it("keeps permission denied queue errors inside the page", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).includes("/api/v1/requisitions/pending-approvals/")) {
          return forbiddenResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/autorizacoes");

    expect(await screen.findByText("Permissão negada.")).toBeInTheDocument();
    expect(container.ownerDocument.location.pathname).toBe("/autorizacoes");
  });

  it("requires inline justification for partial authorization", async () => {
    let authorizePayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(chefeSession());
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
        return pendingApprovalDetailResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/authorize/")) {
        authorizePayload = await request.json();
        return requisitionDetailResponse({ quantidade_autorizada: "1.000" });
      }

      if (requestUrl(request).includes("/api/v1/requisitions/pending-approvals/")) {
        return pendingApprovalListResponse([]);
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderRoute("/requisicoes/101?contexto=autorizacao");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Quantidade autorizada para Papel sulfite A4"), {
      target: { value: "1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Autorizar conforme ajustes" }));

    expect(await screen.findByText("Informe justificativa para autorização parcial ou zerada.")).toBeInTheDocument();
    expect(authorizePayload).toBeUndefined();

    fireEvent.change(screen.getByLabelText("Justificativa para Papel sulfite A4"), {
      target: { value: "Saldo parcial" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Autorizar conforme ajustes" }));

    await waitFor(() => {
      expect(authorizePayload).toEqual({
        itens: [
          {
            item_id: 501,
            quantidade_autorizada: "1",
            justificativa_autorizacao_parcial: "Saldo parcial",
          },
        ],
      });
    });
  });

  it("normalizes comma decimal separator before sending authorization payload", async () => {
    let authorizePayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(chefeSession());
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
        return pendingApprovalDetailResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/authorize/")) {
        authorizePayload = await request.json();
        return requisitionDetailResponse({ quantidade_autorizada: "1.500" });
      }

      if (requestUrl(request).includes("/api/v1/requisitions/pending-approvals/")) {
        return pendingApprovalListResponse([]);
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderRoute("/requisicoes/101?contexto=autorizacao");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Quantidade autorizada para Papel sulfite A4"), {
      target: { value: "1,5" },
    });
    fireEvent.change(screen.getByLabelText("Justificativa para Papel sulfite A4"), {
      target: { value: "Saldo parcial" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Autorizar conforme ajustes" }));

    await waitFor(() => {
      expect(authorizePayload).toEqual({
        itens: [
          {
            item_id: 501,
            quantidade_autorizada: "1.5",
            justificativa_autorizacao_parcial: "Saldo parcial",
          },
        ],
      });
    });
  });

  it("refuses a requisition only with a reason", async () => {
    let refusePayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(chefeSession());
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
        return pendingApprovalDetailResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/refuse/")) {
        refusePayload = await request.json();
        return requisitionDetailResponse();
      }

      if (requestUrl(request).includes("/api/v1/requisitions/pending-approvals/")) {
        return pendingApprovalListResponse([]);
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderRoute("/requisicoes/101?contexto=autorizacao");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Recusar requisição" }));

    expect(await screen.findByText("Informe o motivo da recusa.")).toBeInTheDocument();
    expect(refusePayload).toBeUndefined();

    fireEvent.change(screen.getByLabelText("Motivo da recusa"), {
      target: { value: "Pedido fora do escopo do setor" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Recusar requisição" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("Recusar requisição?");
    fireEvent.click(screen.getByRole("button", { name: "Confirmar recusa" }));

    await waitFor(() => {
      expect(refusePayload).toEqual({
        motivo_recusa: "Pedido fora do escopo do setor",
      });
      expect(container.ownerDocument.location.pathname).toBe("/autorizacoes");
    });
  });

  it("keeps user on detail when authorization action returns domain error", async () => {
    const writeText = vi.fn(() => Promise.resolve());
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return pendingApprovalDetailResponse();
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/authorize/")) {
          return new Response(
            JSON.stringify({
              error: {
                code: "domain_conflict",
                message: "Saldo atual insuficiente.",
                details: {},
                trace_id: "trace-domain",
              },
            }),
            { status: 409, headers: jsonHeaders },
          );
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/requisicoes/101?contexto=autorizacao");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Autorizar tudo como solicitado" }));

    expect(await screen.findByText("Saldo atual insuficiente.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Copiar detalhes para suporte" }));
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith("trace_id: trace-domain");
    });
    expect(await screen.findByText("Detalhes copiados.")).toBeInTheDocument();
    expect(container.ownerDocument.location.pathname).toBe("/requisicoes/101");
  });

  it("handles clipboard rejection when copying support details", async () => {
    const clipboardError = new Error("clipboard blocked");
    const writeText = vi.fn(() => Promise.reject(clipboardError));
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return pendingApprovalDetailResponse();
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/authorize/")) {
          return new Response(
            JSON.stringify({
              error: {
                code: "domain_conflict",
                message: "Saldo atual insuficiente.",
                details: {},
                trace_id: "trace-domain",
              },
            }),
            { status: 409, headers: jsonHeaders },
          );
        }

        const notificationsResponse = maybeNotificationsRequest(request);
        if (notificationsResponse) return notificationsResponse;
        throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/requisicoes/101?contexto=autorizacao");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Autorizar tudo como solicitado" }));

    expect(await screen.findByText("Saldo atual insuficiente.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Copiar detalhes para suporte" }));
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith("trace_id: trace-domain");
      expect(consoleError).toHaveBeenCalledWith(
        "Não foi possível copiar detalhes para suporte.",
        clipboardError,
      );
    });
    expect(await screen.findByText("Não foi possível copiar.")).toBeInTheDocument();
  });

  it("redirects to login when authorize returns unauthenticated error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return pendingApprovalDetailResponse();
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/authorize/")) {
          return unauthenticatedResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/requisicoes/101?contexto=autorizacao&page=2");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Autorizar tudo como solicitado" }));

    expect(await screen.findByRole("heading", { name: "Entrar no piloto" })).toBeInTheDocument();
    expect(container.ownerDocument.location.pathname).toBe("/login");
    expect(container.ownerDocument.location.search).toBe(
      "?redirect=%2Frequisicoes%2F101%3Fcontexto%3Dautorizacao%26page%3D2",
    );
  });

  it("redirects to login when refuse returns unauthenticated error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse(chefeSession());
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return pendingApprovalDetailResponse();
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/refuse/")) {
          return unauthenticatedForbiddenResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/requisicoes/101?contexto=autorizacao&page=2");

    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Motivo da recusa"), {
      target: { value: "Sessão expirou antes da decisão" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Recusar requisição" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("Recusar requisição?");
    fireEvent.click(screen.getByRole("button", { name: "Confirmar recusa" }));

    expect(await screen.findByRole("heading", { name: "Entrar no piloto" })).toBeInTheDocument();
    expect(container.ownerDocument.location.pathname).toBe("/login");
    expect(container.ownerDocument.location.search).toBe(
      "?redirect=%2Frequisicoes%2F101%3Fcontexto%3Dautorizacao%26page%3D2",
    );
  });

  it("creates draft requisition for the current user", async () => {
    let createdPayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse();
      }

      if (
        requestUrl(request).includes("/api/v1/materials/") &&
        requestSearchParam(request, "search") === "papel"
      ) {
        return materialListResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/") && request.method === "POST") {
        createdPayload = await request.json();
        return draftRequisitionDetailResponse({
          itens: [
            {
              id: 501,
              material: {
                id: 301,
                codigo_completo: "010.001.001",
                nome: "Papel sulfite A4",
                unidade_medida: "UN",
              },
              unidade_medida: "UN",
              quantidade_solicitada: "3.000",
              quantidade_autorizada: "0.000",
              quantidade_entregue: "0.000",
              justificativa_autorizacao_parcial: "",
              justificativa_atendimento_parcial: "",
              observacao: "",
            },
          ],
        });
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderRoute("/requisicoes/nova");

    expect(await screen.findByRole("heading", { name: "Nova requisição" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Próximo: itens" }));
    expect(await screen.findByRole("heading", { name: "Itens" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Buscar material"), {
      target: { value: "papel" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Adicionar Papel sulfite A4" }));
    fireEvent.change(screen.getByLabelText("Quantidade solicitada"), {
      target: { value: "3" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salvar rascunho" }));

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/requisicoes/101");
    });
    expect(window.sessionStorage.getItem("wms-saep:draft:v1:user:10:new")).toBeNull();
    expect(createdPayload).toEqual({
      beneficiario_id: 10,
      observacao: "",
      itens: [
        {
          material_id: 301,
          quantidade_solicitada: "3",
          observacao: "",
        },
      ],
    });
  });

  it("navigates draft wizard steps without losing selected data", async () => {
    let createdPayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse();
      }

      if (
        requestUrl(request).includes("/api/v1/materials/") &&
        requestSearchParam(request, "search") === "papel"
      ) {
        return materialListResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/") && request.method === "POST") {
        createdPayload = await request.json();
        return draftRequisitionDetailResponse();
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderRoute("/requisicoes/nova?etapa=beneficiario");

    expect(await screen.findByRole("heading", { name: "Nova requisição" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Beneficiário" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Próximo: itens" }));

    expect(await screen.findByRole("heading", { name: "Itens" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Buscar material"), {
      target: { value: "papel" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Adicionar Papel sulfite A4" }));
    fireEvent.change(screen.getByLabelText("Quantidade solicitada"), {
      target: { value: "1,5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Próximo: revisão" }));

    expect(await screen.findByRole("heading", { name: "Revisão" })).toBeInTheDocument();
    expect(screen.getAllByText("Usuario Piloto (91003)").length).toBeGreaterThan(0);
    expect(screen.getAllByText("010.001.001 - Papel sulfite A4").length).toBeGreaterThan(0);
    expect(screen.getByText("1,5 UN")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Próximo: envio" }));

    expect(await screen.findByRole("heading", { name: "Envio" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Salvar rascunho" }));

    await waitFor(() => {
      expect(createdPayload).toEqual({
        beneficiario_id: 10,
        observacao: "",
        itens: [
          {
            material_id: 301,
            quantidade_solicitada: "1.5",
            observacao: "",
          },
        ],
      });
    });
  });

  it("rejects quantities with dot decimal separator before saving a draft", async () => {
    let createdPayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse();
      }

      if (
        requestUrl(request).includes("/api/v1/materials/") &&
        requestSearchParam(request, "search") === "papel"
      ) {
        return materialListResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/") && request.method === "POST") {
        createdPayload = await request.json();
        return requisitionDetailResponse();
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderRoute("/requisicoes/nova");

    expect(await screen.findByRole("heading", { name: "Nova requisição" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Próximo: itens" }));
    expect(await screen.findByRole("heading", { name: "Itens" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Buscar material"), {
      target: { value: "papel" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Adicionar Papel sulfite A4" }));
    fireEvent.change(screen.getByLabelText("Quantidade solicitada"), {
      target: { value: "1.5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salvar rascunho" }));

    expect(
      await screen.findByText(
        "Quantidade inválida no item 010.001.001 - Papel sulfite A4: use um número válido maior que zero.",
      ),
    ).toBeInTheDocument();
    expect(createdPayload).toBeUndefined();
  });

  it("keeps failed draft save visible and recoverable from session storage", async () => {
    const fetchMock = vi.fn((request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse();
      }

      if (
        requestUrl(request).includes("/api/v1/materials/") &&
        requestSearchParam(request, "search") === "papel"
      ) {
        return materialListResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/") && request.method === "POST") {
        return new Response(
          JSON.stringify({
            error: {
              code: "network_error",
              message: "Falha temporária de conexão.",
              details: {},
              trace_id: null,
            },
          }),
          { status: 503, headers: jsonHeaders },
        );
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderRoute("/requisicoes/nova?etapa=itens");

    expect(await screen.findByRole("heading", { name: "Itens" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Buscar material"), {
      target: { value: "papel" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Adicionar Papel sulfite A4" }));
    fireEvent.change(screen.getByLabelText("Quantidade solicitada"), {
      target: { value: "2,5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salvar rascunho" }));

    expect(await screen.findByText("Falha temporária de conexão.")).toBeInTheDocument();
    expect(screen.getByLabelText("Quantidade solicitada")).toHaveValue("2,5");
    expect(window.sessionStorage.getItem("wms-saep:draft:v1:user:10:new")).toContain("2,5");
  });

  it("preserves the current wizard step after the first draft save", async () => {
    let createdPayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse();
      }

      if (
        requestUrl(request).includes("/api/v1/materials/") &&
        requestSearchParam(request, "search") === "papel"
      ) {
        return materialListResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/") && request.method === "POST") {
        createdPayload = await request.json();
        return requisitionDetailResponse();
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderRoute("/requisicoes/nova?etapa=itens");

    expect(await screen.findByRole("heading", { name: "Itens" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Buscar material"), {
      target: { value: "papel" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Adicionar Papel sulfite A4" }));
    fireEvent.click(screen.getByRole("button", { name: "Salvar rascunho" }));

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/requisicoes/101");
      expect(container.ownerDocument.location.search).toBe("?etapa=itens");
    });
    expect(createdPayload).toEqual({
      beneficiario_id: 10,
      observacao: "",
      itens: [
        {
          material_id: 301,
          quantidade_solicitada: "1",
          observacao: "",
        },
      ],
    });
  });

  it("recovers a local draft snapshot and can discard that copy", async () => {
    window.sessionStorage.setItem(
      "wms-saep:draft:v1:user:10:new",
      JSON.stringify({
        beneficiaryMode: "self",
        beneficiaryId: "10",
        beneficiaryLabel: "Usuario Piloto (91003)",
        beneficiarySearch: "",
        materialSearch: "",
        observacao: "Recuperada localmente",
        itens: [
          {
            materialId: "301",
            materialLabel: "010.001.001 - Papel sulfite A4",
            materialCode: "010.001.001",
            unidadeMedida: "UN",
            saldoDisponivel: 12,
            quantidadeSolicitada: "4,5",
            observacao: "Item local",
          },
        ],
      }),
    );
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
        if (notificationsResponse) return notificationsResponse;
        throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/requisicoes/nova?etapa=revisao");

    expect(await screen.findByText("Rascunho local recuperado")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Recuperada localmente")).toBeInTheDocument();
    expect(screen.getByText("4,5 UN")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Descartar cópia local" }));

    expect(screen.queryByText("Rascunho local recuperado")).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem("wms-saep:draft:v1:user:10:new")).toBeNull();
  });

  it("creates draft requisition for a third-party beneficiary when allowed", async () => {
    let createdPayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(authSession("auxiliar_setor"));
      }

      if (requestUrl(request).includes("/api/v1/users/beneficiary-lookup/")) {
        return beneficiaryLookupResponse();
      }

      if (
        requestUrl(request).includes("/api/v1/materials/") &&
        requestSearchParam(request, "search") === "papel"
      ) {
        return materialListResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/") && request.method === "POST") {
        createdPayload = await request.json();
        return requisitionDetailResponse();
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderRoute("/requisicoes/nova");

    expect(await screen.findByRole("heading", { name: "Nova requisição" })).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Para terceiro"));
    fireEvent.change(screen.getByLabelText("Buscar beneficiário"), {
      target: { value: "Beneficiario" },
    });
    fireEvent.click(await screen.findByRole("button", { name: /Beneficiario Terceiro/ }));
    fireEvent.click(screen.getByRole("button", { name: "Próximo: itens" }));
    expect(await screen.findByRole("heading", { name: "Itens" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Buscar material"), {
      target: { value: "papel" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Adicionar Papel sulfite A4" }));
    fireEvent.click(screen.getByRole("button", { name: "Salvar rascunho" }));

    await waitFor(() => {
      expect(createdPayload).toEqual({
        beneficiario_id: 11,
        observacao: "",
        itens: [
          {
            material_id: 301,
            quantidade_solicitada: "1",
            observacao: "",
          },
        ],
      });
    });
  });

  it("requires selecting a beneficiary after switching from self to third-party", async () => {
    let createdPayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(authSession("auxiliar_setor"));
      }

      if (
        requestUrl(request).includes("/api/v1/materials/") &&
        requestSearchParam(request, "search") === "papel"
      ) {
        return materialListResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/") && request.method === "POST") {
        createdPayload = await request.json();
        return requisitionDetailResponse();
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderRoute("/requisicoes/nova");

    expect(await screen.findByRole("heading", { name: "Nova requisição" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Próximo: itens" }));
    expect(await screen.findByRole("heading", { name: "Itens" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Buscar material"), {
      target: { value: "papel" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Adicionar Papel sulfite A4" }));
    fireEvent.click(screen.getByRole("button", { name: "Voltar etapa" }));
    expect(await screen.findByRole("heading", { name: "Beneficiário" })).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Para terceiro"));
    fireEvent.click(screen.getByRole("button", { name: "Salvar rascunho" }));

    await waitFor(() => {
      expect(screen.getAllByText("Informe beneficiário.").length).toBeGreaterThan(0);
    });
    expect(createdPayload).toBeUndefined();
  });

  it("clears stale global validation banners after beneficiary and item corrections", async () => {
    const fetchMock = vi.fn((request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(authSession("auxiliar_setor"));
      }

      if (requestUrl(request).includes("/api/v1/users/beneficiary-lookup/")) {
        return beneficiaryLookupResponse();
      }

      if (
        requestUrl(request).includes("/api/v1/materials/") &&
        requestSearchParam(request, "search") === "papel"
      ) {
        return materialListResponse();
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderRoute("/requisicoes/nova");

    expect(await screen.findByRole("heading", { name: "Nova requisição" })).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Para terceiro"));
    fireEvent.click(screen.getByRole("button", { name: "Salvar rascunho" }));

    expect((await screen.findAllByText("Informe beneficiário.")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByLabelText("Para mim"));
    await waitFor(() => {
      expect(screen.queryByText("Informe beneficiário.")).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText("Para terceiro"));
    fireEvent.click(screen.getByRole("button", { name: "Salvar rascunho" }));
    expect((await screen.findAllByText("Informe beneficiário.")).length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Buscar beneficiário"), {
      target: { value: "benef" },
    });
    fireEvent.click(await screen.findByRole("button", { name: /Beneficiario Terceiro/ }));
    await waitFor(() => {
      expect(screen.queryByText("Informe beneficiário.")).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Próximo: itens" }));
    expect(await screen.findByRole("heading", { name: "Itens" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Salvar rascunho" }));

    expect((await screen.findAllByText("Adicione ao menos um item.")).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Buscar material"), {
      target: { value: "papel" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Adicionar Papel sulfite A4" }));
    await waitFor(() => {
      expect(screen.queryByText("Adicione ao menos um item.")).not.toBeInTheDocument();
    });
  });

  it("updates an existing draft with full replacement payload", async () => {
    let updatedPayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
        return draftRequisitionDetailResponse();
      }

      if (
        requestUrl(request).includes("/api/v1/materials/") &&
        requestSearchParam(request, "search") === "010.001.001"
      ) {
        return materialListResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/draft/")) {
        updatedPayload = await request.json();
        return draftRequisitionDetailResponse({ observacao: "Observacao nova" });
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderRoute("/requisicoes/101?etapa=itens");

    expect(await screen.findByRole("heading", { name: "Editar rascunho" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Itens" })).toBeInTheDocument();
    expect(screen.getByLabelText("Quantidade solicitada")).toHaveValue("2");
    expect(screen.queryByText(/Saldo não exibido/)).not.toBeInTheDocument();
    expect(await screen.findByText("Saldo 12 UN")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Observação geral"), {
      target: { value: "Observacao nova" },
    });
    fireEvent.change(screen.getByLabelText("Quantidade solicitada"), {
      target: { value: "4" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salvar rascunho" }));

    await waitFor(() => {
      expect(updatedPayload).toEqual({
        beneficiario_id: 10,
        observacao: "Observacao nova",
        itens: [
          {
            material_id: 301,
            quantidade_solicitada: "4",
            observacao: "Item antigo",
          },
        ],
      });
    });
    expect(container.ownerDocument.location.pathname).toBe("/requisicoes/101");
  });

  it("redirects draft detail to login when session refresh expires", async () => {
    let sessionRequests = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          sessionRequests += 1;
          return sessionRequests === 1 ? sessionResponse() : unauthenticatedResponse();
        }

        if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
          return draftRequisitionDetailResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
        if (notificationsResponse) return notificationsResponse;
        throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    const { container } = renderRoute("/requisicoes/101?etapa=itens");

    expect(await screen.findByRole("heading", { name: "Entrar no piloto" })).toBeInTheDocument();
    expect(container.ownerDocument.location.pathname).toBe("/login");
    expect(container.ownerDocument.location.search).toBe("?redirect=%2Frequisicoes%2F101");
  });

  it("confirms and submits a draft to authorization", async () => {
    let updatedPayload: unknown;
    let submitCalled = false;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
        return draftRequisitionDetailResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/draft/")) {
        updatedPayload = await request.json();
        return draftRequisitionDetailResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/submit/")) {
        submitCalled = true;
        return requisitionDetailResponse();
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderRoute("/requisicoes/101");

    expect(await screen.findByRole("heading", { name: "Editar rascunho" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Enviar para autorização" }));
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("Enviar rascunho para autorização?");
    expect(screen.getByRole("button", { name: "Voltar ao rascunho" })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Confirmar envio" }));

    await waitFor(() => {
      expect(updatedPayload).toEqual({
        beneficiario_id: 10,
        observacao: "Observacao antiga",
        itens: [
          {
            material_id: 301,
            quantidade_solicitada: "2",
            observacao: "Item antigo",
          },
        ],
      });
      expect(submitCalled).toBe(true);
    });
    expect(await screen.findByRole("heading", { name: "REQ-2026-000101" })).toBeInTheDocument();
  });

  it("discards an unnumbered draft", async () => {
    let discardCalled = false;
    const fetchMock = vi.fn((request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
        return draftRequisitionDetailResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/discard/")) {
        discardCalled = true;
        return new Response(null, { status: 204 });
      }

      if (requestUrl(request).includes("/api/v1/requisitions/mine/")) {
        return requisitionListResponse([]);
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.sessionStorage.setItem(
      "wms-saep:draft:v1:user:10:draft:101",
      JSON.stringify({ observacao: "Rascunho a descartar" }),
    );

    const { container } = renderRoute("/requisicoes/101");

    expect(await screen.findByRole("heading", { name: "Editar rascunho" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Observação geral"), {
      target: { value: "Rascunho sujo" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Descartar rascunho" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("Descartar rascunho?");
    fireEvent.click(screen.getByRole("button", { name: "Confirmar descarte" }));

    await waitFor(() => {
      expect(discardCalled).toBe(true);
      expect(container.ownerDocument.location.pathname).toBe("/minhas-requisicoes");
    });
    expect(window.sessionStorage.getItem("wms-saep:draft:v1:user:10:draft:101")).toBeNull();
  });

  it("cancels a numbered draft instead of discarding it", async () => {
    let cancelPayload: unknown;
    const fetchMock = vi.fn(async (request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/")) {
        return draftRequisitionDetailResponse({ numero_publico: "REQ-2026-000050" });
      }

      if (requestUrl(request).endsWith("/api/v1/requisitions/101/cancel/")) {
        cancelPayload = await request.json();
        return requisitionDetailResponse({}, { status: "cancelada" });
      }

      if (requestUrl(request).includes("/api/v1/requisitions/mine/")) {
        return requisitionListResponse([]);
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.sessionStorage.setItem(
      "wms-saep:draft:v1:user:10:draft:101",
      JSON.stringify({ observacao: "Rascunho numerado" }),
    );

    const { container } = renderRoute("/requisicoes/101");

    expect(await screen.findByRole("heading", { name: "Editar rascunho" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Observação geral"), {
      target: { value: "Cancelamento sujo" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Cancelar requisição" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("Cancelar requisição?");
    fireEvent.click(screen.getByRole("button", { name: "Confirmar cancelamento" }));

    await waitFor(() => {
      expect(cancelPayload).toEqual({ motivo_cancelamento: "" });
      expect(container.ownerDocument.location.pathname).toBe("/minhas-requisicoes");
    });
    expect(window.sessionStorage.getItem("wms-saep:draft:v1:user:10:draft:101")).toBeNull();
  });

  it("shows material stock and blocks adding material without positive stock", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        if (
          requestUrl(request).includes("/api/v1/materials/") &&
          requestSearchParam(request, "search") === "caneta"
        ) {
          return materialListResponse([
            {
              id: 302,
              codigo_completo: "010.001.002",
              nome: "Caneta sem estoque",
              descricao: "Caneta azul",
              unidade_medida: "UN",
              saldo_disponivel: 0,
            },
          ]);
        }

        const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/requisicoes/nova");

    expect(await screen.findByRole("heading", { name: "Nova requisição" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Próximo: itens" }));
    expect(await screen.findByRole("heading", { name: "Itens" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Buscar material"), {
      target: { value: "caneta" },
    });

    const addButton = await screen.findByRole("button", { name: "Adicionar Caneta sem estoque" });
    expect(addButton).toBeDisabled();
    expect(screen.getByText(/saldo 0 UN/i)).toBeInTheDocument();
    expect(screen.getAllByText("Nenhum material adicionado.").length).toBeGreaterThan(0);
  });

  it("shows recent materials only when local data has enough entries", async () => {
    window.sessionStorage.setItem(
      "wms-saep:recent-materials:v1:user:10",
      JSON.stringify([
        {
          id: 301,
          codigo_completo: "010.001.001",
          nome: "Papel sulfite A4",
          descricao: "Pacote com 500 folhas",
          unidade_medida: "UN",
          saldo_disponivel: 12,
        },
        {
          id: 302,
          codigo_completo: "010.001.002",
          nome: "Caneta azul",
          descricao: "Caneta esferográfica",
          unidade_medida: "UN",
          saldo_disponivel: 8,
        },
      ]),
    );
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
        if (notificationsResponse) return notificationsResponse;
        throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/requisicoes/nova?etapa=itens");

    expect(await screen.findByRole("heading", { name: "Itens" })).toBeInTheDocument();
    expect(screen.getByText("Materiais recentes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Adicionar Papel sulfite A4" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Adicionar Caneta azul" })).toBeInTheDocument();
  });

  it("ignores malformed draft and recent-material snapshots from session storage", async () => {
    window.sessionStorage.setItem(
      "wms-saep:draft:v1:user:10:new",
      JSON.stringify({
        beneficiaryMode: "third_party",
        beneficiaryId: 123,
        beneficiaryLabel: ["invalido"],
        observacao: null,
        itens: [null, "quebrado", { materialId: 301, saldoDisponivel: "12" }],
      }),
    );
    window.sessionStorage.setItem(
      "wms-saep:recent-materials:v1:user:10",
      JSON.stringify([null, "quebrado", { id: 301, nome: "Sem codigo" }]),
    );
    vi.stubGlobal(
      "fetch",
      vi.fn((request: Request) => {
        if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
          return sessionResponse();
        }

        const notificationsResponse = maybeNotificationsRequest(request);
        if (notificationsResponse) return notificationsResponse;
        throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/requisicoes/nova");

    expect(await screen.findByRole("heading", { name: "Nova requisição" })).toBeInTheDocument();
    expect(screen.getByText("Rascunho local recuperado")).toBeInTheDocument();
    expect(screen.getByText("Selecionado:")).toBeInTheDocument();
    expect(screen.queryByText("Sem codigo")).not.toBeInTheDocument();
  });

  it("renders notifications counter and collective badge in app shell", async () => {
    const fetchMock = vi.fn((request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(authSession("solicitante"));
      }

      if (requestUrl(request).includes("/api/v1/notifications/unread-count/")) {
        return notificationUnreadCountResponse(2);
      }

      if (
        requestUrl(request).includes("/api/v1/notifications/") &&
        request.method === "GET" &&
        !requestUrl(request).includes("/mark-read/")
      ) {
        return notificationListResponse([
          notificationListItem({
            id: 910,
            destino: { tipo: "papel", usuario_id: null, papel: "chefe_setor" },
            leitura_suportada: false,
            tipo: "requisicao_autorizada",
            titulo: "Aviso coletivo",
          }),
          notificationListItem({
            id: 911,
            titulo: "Aviso individual",
            leitura_suportada: true,
            destino: { tipo: "usuario", usuario_id: 10, papel: null },
          }),
        ]);
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderRoute("/minhas-requisicoes");

    expect(await screen.findByText("Notificações")).toBeInTheDocument();
    expect(await screen.findByText("2")).toBeInTheDocument();
    expect(
      await screen.findByText("Aviso coletivo", { selector: ".notification-badge" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Marcar como lida" })).toBeInTheDocument();
  });

  it("marks individual notification as read and refreshes unread counter", async () => {
    let unreadCount = 1;
    let notificationsRead = false;

    const fetchMock = vi.fn((request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(authSession("solicitante"));
      }

      if (requestUrl(request).includes("/api/v1/notifications/unread-count/")) {
        return notificationUnreadCountResponse(unreadCount);
      }

      if (
        requestUrl(request).includes("/api/v1/notifications/") &&
        request.method === "GET" &&
        !requestUrl(request).includes("/mark-read/")
      ) {
        return notificationListResponse([
          notificationListItem({
            id: 920,
            lida: notificationsRead,
            lida_em: notificationsRead ? "2026-05-02T09:35:00Z" : null,
            leitura_suportada: true,
          }),
        ]);
      }

      if (requestUrl(request).includes("/api/v1/notifications/920/mark-read/")) {
        unreadCount = 0;
        notificationsRead = true;
        return new Response(
          JSON.stringify(
            notificationListItem({
              id: 920,
              lida: true,
              lida_em: "2026-05-02T09:35:00Z",
              leitura_suportada: true,
            }),
          ),
          { status: 200, headers: jsonHeaders },
        );
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderRoute("/minhas-requisicoes");

    const markReadButton = await screen.findByRole("button", { name: "Marcar como lida" });
    fireEvent.click(markReadButton);

    await waitFor(() => {
      expect(screen.getByText("0")).toBeInTheDocument();
    });

    expect(
      fetchMock.mock.calls.some(([request]) =>
        requestUrl(request).includes("/api/v1/notifications/920/mark-read/"),
      ),
    ).toBe(true);
  });

  it("builds requisition link with operational context from notification type", async () => {
    const fetchMock = vi.fn((request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(authSession("chefe_setor"));
      }

      if (requestUrl(request).includes("/api/v1/notifications/unread-count/")) {
        return notificationUnreadCountResponse(1);
      }

      if (
        requestUrl(request).includes("/api/v1/notifications/") &&
        request.method === "GET" &&
        !requestUrl(request).includes("/mark-read/")
      ) {
        return notificationListResponse([
          notificationListItem({
            id: 930,
            tipo: "requisicao_enviada_autorizacao",
            leitura_suportada: true,
            objeto_relacionado: {
              tipo: "requisicao",
              id: 101,
              numero_publico: "REQ-2026-000101",
              status: "aguardando_autorizacao",
            },
          }),
        ]);
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderRoute("/minhas-requisicoes");

    const link = await screen.findByRole("link", { name: "Abrir requisição" });
    expect(link).toHaveAttribute("href", "/requisicoes/101?contexto=autorizacao");
    expect(screen.getByText("Fila de autorizações", { selector: ".notification-context" })).toBeInTheDocument();
  });

  it("logs out from authenticated shell and returns to login", async () => {
    let loggedIn = true;
    const fetchMock = vi.fn((request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return loggedIn ? sessionResponse(authSession("solicitante")) : unauthenticatedResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/auth/csrf/")) {
        return csrfResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/auth/logout/")) {
        loggedIn = false;
        return new Response(null, { status: 204 });
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderRoute("/minhas-requisicoes");

    expect(await screen.findByText("Usuario Piloto")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sair" }));

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/login");
    });
  });

  it("shows logout error when the backend rejects logout", async () => {
    const fetchMock = vi.fn((request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(authSession("solicitante"));
      }

      if (requestUrl(request).endsWith("/api/v1/auth/csrf/")) {
        return csrfResponse();
      }

      if (requestUrl(request).endsWith("/api/v1/auth/logout/")) {
        return new Response(
          JSON.stringify({
            error: {
              code: "logout_failed",
              message: "Não foi possível encerrar a sessão.",
              details: {},
              trace_id: null,
            },
          }),
          { status: 500, headers: jsonHeaders },
        );
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderRoute("/minhas-requisicoes");

    expect(await screen.findByText("Usuario Piloto")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sair" }));

    expect(await screen.findByText("Não foi possível encerrar a sessão.")).toBeInTheDocument();
    expect(container.ownerDocument.location.pathname).toBe("/minhas-requisicoes");
  });

  it("does not post logout when csrf preparation fails", async () => {
    let logoutCalled = false;
    const fetchMock = vi.fn((request: Request) => {
      if (requestUrl(request).endsWith("/api/v1/auth/me/")) {
        return sessionResponse(authSession("solicitante"));
      }

      if (requestUrl(request).endsWith("/api/v1/auth/csrf/")) {
        return new Response(
          JSON.stringify({
            error: {
              code: "csrf_unavailable",
              message: "CSRF indisponível.",
              details: {},
              trace_id: null,
            },
          }),
          { status: 503, headers: jsonHeaders },
        );
      }

      if (requestUrl(request).endsWith("/api/v1/auth/logout/")) {
        logoutCalled = true;
        return new Response(null, { status: 204 });
      }

      const notificationsResponse = maybeNotificationsRequest(request);
      if (notificationsResponse) return notificationsResponse;
      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderRoute("/minhas-requisicoes");

    expect(await screen.findByText("Usuario Piloto")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sair" }));

    expect(await screen.findByText("CSRF indisponível.")).toBeInTheDocument();
    expect(logoutCalled).toBe(false);
    expect(container.ownerDocument.location.pathname).toBe("/minhas-requisicoes");
  });
});
