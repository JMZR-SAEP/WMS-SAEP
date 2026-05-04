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
          return new Response(JSON.stringify({ error: { code: "not_authenticated" } }), {
            status: 401,
            headers: jsonHeaders,
          });
        }

        if (requestUrl(request).endsWith("/api/v1/auth/csrf/")) {
          return csrfResponse();
        }

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

  it("redirects protected routes without session to login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        new Response(
          JSON.stringify({
            error: {
              code: "not_authenticated",
              message: "Autenticação necessária.",
              details: {},
              trace_id: null,
            },
          }),
          { status: 401, headers: jsonHeaders },
        ),
      ),
    );

    const { container } = renderRoute("/minhas-requisicoes");

    expect(await screen.findByRole("heading", { name: "Entrar no piloto" })).toBeInTheDocument();
    expect(container.ownerDocument.location.pathname).toBe("/login");
    expect(container.ownerDocument.location.search).toBe("?redirect=%2Fminhas-requisicoes");
  });

  it("renders minhas requisicoes placeholder", async () => {
    mockCurrentSession();
    renderRoute("/minhas-requisicoes");

    expect(
      await screen.findByRole("heading", { name: "Minhas requisições" }),
    ).toBeInTheDocument();
    expect(screen.getByText("GET /api/v1/requisitions/?page=&page_size=&search=&status=")).toBeInTheDocument();
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
});
