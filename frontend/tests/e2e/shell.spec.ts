import { expect, test } from "@playwright/test";

test("logs in and logs out through pilot shell", async ({ page }) => {
  let authenticated = false;

  await page.route("**/api/v1/auth/me/", async (route) => {
    if (!authenticated) {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "not_authenticated",
            message: "Autenticação necessária.",
            details: {},
            trace_id: null,
          },
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
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
    });
  });
  await page.route("**/api/v1/auth/csrf/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ csrf_token: "csrf-token" }),
    });
  });
  await page.route("**/api/v1/auth/login/", async (route) => {
    authenticated = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
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
    });
  });
  await page.route("**/api/v1/auth/logout/", async (route) => {
    authenticated = false;
    await route.fulfill({ status: 204 });
  });

  await page.goto("/login");

  await page.getByLabel("Matrícula funcional").fill("91003");
  await page.getByLabel("Senha").fill("senha-segura-123");
  await page.getByRole("button", { name: "Entrar" }).click();

  await expect(page).toHaveURL(/\/autorizacoes$/);
  await expect(page.getByText("Chefe Piloto")).toBeVisible();

  await page.getByRole("button", { name: "Sair" }).click();

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Entrar no piloto" })).toBeVisible();
});
