import { RouterProvider } from "@tanstack/react-router";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppProviders } from "../app/providers";
import { buildRouter } from "../app/router";

function renderRoute(pathname: string) {
  window.history.replaceState({}, "", pathname);
  const router = buildRouter();

  return render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );
}

describe("frontend scaffold router", () => {
  it("renders login placeholder", async () => {
    renderRoute("/login");

    expect(await screen.findByRole("heading", { name: "Entrar no piloto" })).toBeInTheDocument();
    expect(screen.getByText("#37 — login e bootstrap de sessão")).toBeInTheDocument();
  });

  it("renders minhas requisicoes placeholder", async () => {
    renderRoute("/minhas-requisicoes");

    expect(
      await screen.findByRole("heading", { name: "Minhas requisições" }),
    ).toBeInTheDocument();
    expect(screen.getByText("GET /api/v1/requisitions/?page=&page_size=&search=&status=")).toBeInTheDocument();
  });
});
