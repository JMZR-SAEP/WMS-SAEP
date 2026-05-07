import { RouterProvider } from "@tanstack/react-router";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../app/providers";
import { createAppQueryClient } from "../app/query-client";
import { buildRouter } from "../app/router";

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
  vi.unstubAllGlobals();
});

const jsonHeaders = { "Content-Type": "application/json" };

function requestUrl(request: Request) {
  return request.url;
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

function requisitionDetailResponse() {
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
    }),
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

      throw new Error(`Unexpected request: ${requestUrl(request)}`);
    }),
  );
}

describe("frontend scaffold router", () => {
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
          return new Response(JSON.stringify({ detail: "Falha no backend" }), {
            status: 422,
            headers: jsonHeaders,
          });
        }

        throw new Error(`Unexpected request: ${requestUrl(request)}`);
      }),
    );

    renderRoute("/minhas-requisicoes");

    expect(await screen.findByText("Erro ao carregar")).toBeInTheDocument();
    expect(screen.getByText("Não foi possível carregar requisições.")).toBeInTheDocument();
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
