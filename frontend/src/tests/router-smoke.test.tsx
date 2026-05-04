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

function mockCurrentSession(papel = "solicitante") {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      new Response(
        JSON.stringify({
          id: 10,
          matricula_funcional: "91003",
          nome_completo: "Usuario Piloto",
          papel,
          setor: {
            id: 1,
            nome: "Operacao",
          },
          is_authenticated: true,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    ),
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

  it("logs in with matricula and sends chefe de setor to authorization queue", async () => {
    const fetchMock = vi.fn((request: Request) => {
      if (request.url.endsWith("/api/v1/auth/me/")) {
        return new Response(
          JSON.stringify({
            error: {
              code: "not_authenticated",
              message: "Autenticação necessária.",
              details: {},
              trace_id: null,
            },
          }),
          { status: 401, headers: { "Content-Type": "application/json" } },
        );
      }

      if (request.url.endsWith("/api/v1/auth/csrf/")) {
        return new Response(JSON.stringify({ csrf_token: "csrf-token" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (request.url.endsWith("/api/v1/auth/login/")) {
        return new Response(
          JSON.stringify({
            id: 20,
            matricula_funcional: "91003",
            nome_completo: "Chefe Piloto",
            papel: "chefe_setor",
            setor: {
              id: 2,
              nome: "Manutencao",
            },
            is_authenticated: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      throw new Error(`Unexpected request: ${request.url}`);
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
        if (request.url.endsWith("/api/v1/auth/me/")) {
          return new Response(JSON.stringify({ error: { code: "not_authenticated" } }), {
            status: 401,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (request.url.endsWith("/api/v1/auth/csrf/")) {
          return new Response(JSON.stringify({ csrf_token: "csrf-token" }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
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
          { status: 401, headers: { "Content-Type": "application/json" } },
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
          { status: 401, headers: { "Content-Type": "application/json" } },
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
    const fetchMock = vi.fn((request: Request) => {
      if (request.url.endsWith("/api/v1/auth/me/")) {
        return new Response(
          JSON.stringify({
            id: 10,
            matricula_funcional: "91003",
            nome_completo: "Usuario Piloto",
            papel: "solicitante",
            setor: {
              id: 1,
              nome: "Operacao",
            },
            is_authenticated: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      if (request.url.endsWith("/api/v1/auth/csrf/")) {
        return new Response(JSON.stringify({ csrf_token: "csrf-token" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (request.url.endsWith("/api/v1/auth/logout/")) {
        return new Response(null, { status: 204 });
      }

      throw new Error(`Unexpected request: ${request.url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderRoute("/minhas-requisicoes");

    expect(await screen.findByText("Usuario Piloto")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sair" }));

    await waitFor(() => {
      expect(container.ownerDocument.location.pathname).toBe("/login");
    });
  });
});
