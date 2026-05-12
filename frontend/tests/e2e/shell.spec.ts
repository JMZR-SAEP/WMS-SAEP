import { expect, test, type Page } from "@playwright/test";

// Keep aligned with apps/requisitions/seed_pilot_minimo.py (SEED_PASSWORD).
const SEED_PASSWORD = "piloto-minimo";

async function skipPushOnboarding(page: Page) {
  await page.addInitScript(() => {
    const originalGetItem = window.localStorage.getItem.bind(window.localStorage);
    Storage.prototype.getItem = function getItem(key: string) {
      if (key.startsWith("wms-saep:push-onboarding:v1:user:")) {
        return "seen";
      }
      return originalGetItem(key);
    };
  });
}

async function loginAs(
  page: Page,
  matricula: string,
  expectedPath: RegExp,
  options: { afterOnboardingPath?: string } = {},
) {
  if (options.afterOnboardingPath) {
    await skipPushOnboarding(page);
  }
  await page.goto("/login");
  await page.getByLabel("Matrícula funcional").fill(matricula);
  await page.getByLabel("Senha").fill(SEED_PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(expectedPath);
}

function expectDetailContextUrl(
  rawUrl: string,
  contexto: "autorizacao" | "atendimento",
  allowPageParam = true,
) {
  const url = new URL(rawUrl);

  expect(url.pathname).toMatch(/^\/requisicoes\/\d+$/);
  expect(url.searchParams.get("contexto")).toBe(contexto);

  const pageParam = url.searchParams.get("page");
  if (!allowPageParam) {
    expect(pageParam).toBeNull();
    return;
  }
  if (pageParam !== null) {
    expect(pageParam).toMatch(/^\d+$/);
  }
}

test("logs in and logs out through real backend", async ({ page }) => {
  await loginAs(page, "chefe-setor", /\/autorizacoes(?:\?.*)?$/, {
    afterOnboardingPath: "/autorizacoes",
  });
  await expect(page.getByRole("heading", { name: "Fila de autorizações" })).toBeVisible();
  await expect(page.getByText("Wagner Fonseca")).toBeVisible();

  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login(?:\?.*)?$/);
  await expect(page.getByRole("heading", { name: "Entrar no piloto" })).toBeVisible();
});

test("login fits mobile viewport with SAEP identity", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/login");

  await expect(page.getByRole("img", { name: "SAEP" }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Entrar no piloto" })).toBeVisible();
  await expect(page.getByText(/scaffold/i)).toHaveCount(0);

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);

  for (let index = 0; index < 12; index += 1) {
    if (await page.getByLabel("Matrícula funcional").evaluate((element) => element === document.activeElement)) {
      break;
    }
    await page.keyboard.press("Tab");
  }
  await expect(page.getByLabel("Matrícula funcional")).toBeFocused();
});

test("opens minhas requisicoes and canonical detail with real data", async ({ page }) => {
  await loginAs(page, "solicitante1", /\/minhas-requisicoes(?:\?.*)?$/);

  await expect(page.getByRole("heading", { name: "Minhas requisições" })).toBeVisible();
  const formalRow = page.locator("tbody tr").filter({ hasText: /REQ-\d{4}-\d+/ }).first();
  await expect(formalRow).toBeVisible();
  await formalRow.getByRole("link", { name: "Abrir" }).click();

  await expect(page).toHaveURL(/\/requisicoes\/\d+$/);
  await expect(page.getByRole("heading", { name: /REQ-\d{4}-\d+/ })).toBeVisible();
});

test("creates draft and submits to authorization using seed scenario", async ({ page }) => {
  await loginAs(page, "91002", /\/minhas-requisicoes(?:\?.*)?$/);

  await page.goto("/requisicoes/nova");
  await expect(page.getByRole("heading", { name: "Nova requisição" })).toBeVisible();

  await page.getByLabel("Para terceiro").click();
  await page.getByLabel("Buscar beneficiário").fill("Ped");
  await page.getByRole("button", { name: /Pedro Nunes/i }).click();
  await page.getByRole("button", { name: "Próximo: itens" }).click();
  await expect(page.getByRole("heading", { name: "Itens", exact: true })).toBeVisible();

  await page.getByLabel("Buscar material").fill("Papel sulfite");
  await page.getByRole("button", { name: /Adicionar Papel sulfite A4/i }).click();
  await page.getByLabel("Quantidade solicitada").fill("2");

  await page.getByRole("button", { name: "Salvar rascunho" }).click();
  await expect(page).toHaveURL(/\/requisicoes\/\d+\?etapa=itens$/);
  await expect(page.getByRole("heading", { name: "Editar rascunho" })).toBeVisible();

  await page.getByRole("button", { name: "Enviar para autorização" }).click();
  await page.getByRole("button", { name: "Confirmar envio" }).click();

  await expect(page.getByRole("heading", { name: /REQ-\d{4}-\d+/ })).toBeVisible();
  await expect(page.getByText("Aguardando autorização")).toBeVisible();
});

test("draft wizard fits mobile viewport with sticky actions", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await loginAs(page, "91002", /\/minhas-requisicoes(?:\?.*)?$/);

  await page.goto("/requisicoes/nova?etapa=beneficiario");
  await expect(page.getByRole("heading", { name: "Nova requisição" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Próximo: itens" })).toBeVisible();

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);
});

test("authorizes pending requisition from worklist", async ({ page }) => {
  await loginAs(page, "chefe-setor", /\/autorizacoes(?:\?.*)?$/, {
    afterOnboardingPath: "/autorizacoes",
  });

  await expect(page.getByRole("heading", { name: "Fila de autorizações" })).toBeVisible();
  const approvalRows = page.locator("tbody tr");
  await expect(approvalRows).not.toHaveCount(0);
  const approvalRow = approvalRows.first();
  await expect(approvalRow).toBeVisible();
  await approvalRow.getByRole("link", { name: "Abrir" }).click();

  await expect(page).toHaveURL(/\/requisicoes\/\d+\?/);
  expectDetailContextUrl(page.url(), "autorizacao");
  await page.getByRole("button", { name: "Autorizar tudo como solicitado" }).click();
  await expect(page).toHaveURL(/\/autorizacoes(?:\?.*)?$/);
  await expect(page.getByRole("heading", { name: "Fila de autorizações" })).toBeVisible();
});

test("fulfills authorized requisition from worklist", async ({ page }) => {
  await loginAs(page, "auxiliar-almox", /\/atendimentos(?:\?.*)?$/);

  await expect(page.getByRole("heading", { name: "Fila de atendimento" })).toBeVisible();
  const fulfillmentRows = page.locator("tbody tr");
  await expect(fulfillmentRows).not.toHaveCount(0);
  const fulfillmentRow = fulfillmentRows.first();
  await expect(fulfillmentRow).toBeVisible();
  await fulfillmentRow.getByRole("link", { name: "Abrir" }).click();

  await expect(page).toHaveURL(/\/requisicoes\/\d+\?/);
  expectDetailContextUrl(page.url(), "atendimento");
  await page.getByRole("button", { name: "Preencher entrega completa" }).click();
  await page.getByLabel("Retirante físico").fill("Servidor piloto E2E");
  await page.getByRole("button", { name: "Registrar atendimento" }).click();
  await expect(page).toHaveURL(/\/atendimentos(?:\?.*)?$/);
  await expect(page.getByRole("heading", { name: "Fila de atendimento" })).toBeVisible();
});
