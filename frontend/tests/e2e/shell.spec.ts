import { expect, test, type Page } from "@playwright/test";

// Keep aligned with apps/requisitions/seed_pilot_minimo.py (SEED_PASSWORD).
const SEED_PASSWORD = "piloto-minimo";

async function expectNoHorizontalOverflow(page: Page) {
  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);
}

async function skipPushOnboarding(page: Page) {
  await page.addInitScript(() => {
    const originalGetItem = Object.getOwnPropertyDescriptor(Storage.prototype, "getItem")
      ?.value as Storage["getItem"];
    Storage.prototype.getItem = function getItem(key: string) {
      if (key.startsWith("wms-saep:push-onboarding:v1:user:")) {
        return "seen";
      }
      return Reflect.apply(originalGetItem, this, [key]);
    };
  });
}

async function forcePushDeniedCapabilities(page: Page) {
  await page.addInitScript(() => {
    Object.defineProperty(window, "Notification", {
      configurable: true,
      value: {
        permission: "denied",
        requestPermission: () => Promise.resolve("denied"),
      },
    });
    Object.defineProperty(window, "PushManager", {
      configurable: true,
      value: function PushManager() {},
    });
    Object.defineProperty(navigator, "serviceWorker", {
      configurable: true,
      value: {
        register: () => Promise.resolve({}),
        ready: Promise.resolve({ pushManager: {} }),
      },
    });
  });
}

async function loginAs(
  page: Page,
  matricula: string,
  expectedPath: RegExp,
  options: { skipPushOnboarding?: boolean } = {},
) {
  if (options.skipPushOnboarding) {
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
    skipPushOnboarding: true,
  });
  await expect(page.getByRole("heading", { name: "Fila de autorizações" })).toBeVisible();
  await expect(page.getByText("Wagner Fonseca")).toBeVisible();

  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login(?:\?.*)?$/);
  await expect(page.getByRole("heading", { name: "Entrar no piloto" })).toBeVisible();
});

test("login fits mobile viewport with SAEP identity @qa-final", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/login");

  await expect(page.getByRole("img", { name: "SAEP" }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Entrar no piloto" })).toBeVisible();
  await expect(page.getByText(/scaffold/i)).toHaveCount(0);

  await expectNoHorizontalOverflow(page);

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
  await page.getByRole("link", { name: "Abrir" }).first().click();

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

  await expectNoHorizontalOverflow(page);
});

test("qa final keeps P0 mobile worklists without horizontal overflow @qa-final", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await loginAs(page, "solicitante1", /\/minhas-requisicoes(?:\?.*)?$/);
  await expect(page.getByRole("heading", { name: "Minhas requisições" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await expect(page.getByRole("link", { name: "Abrir" }).first()).toBeVisible();

  await page.getByRole("button", { name: "Sair" }).click();
  await loginAs(page, "chefe-setor", /\/autorizacoes(?:\?.*)?$/, {
    skipPushOnboarding: true,
  });
  await expect(page.getByRole("heading", { name: "Fila de autorizações" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await expect(page.getByRole("link", { name: "Abrir" }).first()).toBeVisible();

  await page.getByRole("button", { name: "Sair" }).click();
  await loginAs(page, "auxiliar-almox", /\/atendimentos(?:\?.*)?$/);
  await expect(page.getByRole("heading", { name: "Fila de atendimento" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await expect(page.getByRole("link", { name: "Abrir" }).first()).toBeVisible();
});

test("qa final preserves local draft after failed save @qa-final", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await loginAs(page, "91002", /\/minhas-requisicoes(?:\?.*)?$/);

  await page.goto("/requisicoes/nova");
  await page.getByLabel("Para terceiro").click();
  await page.getByLabel("Buscar beneficiário").fill("Ped");
  await page.getByRole("button", { name: /Pedro Nunes/i }).click();
  await page.getByRole("button", { name: "Próximo: itens" }).click();
  await page.getByLabel("Buscar material").fill("Papel sulfite");
  await page.getByRole("button", { name: /Adicionar Papel sulfite A4/i }).click();
  await page.getByLabel("Quantidade solicitada").fill("2");

  await page.route(/\/api\/v1\/requisitions\/(?:\d+\/draft\/)?(?:\?.*)?$/, async (route, request) => {
    if (request.method() === "POST" || request.method() === "PUT") {
      await route.fulfill({
        contentType: "application/json",
        status: 503,
        body: JSON.stringify({
          error: {
            code: "service_unavailable",
            message: "Falha controlada para QA.",
            trace_id: "qa-final-draft",
          },
        }),
      });
      return;
    }
    await route.fallback();
  });

  await page.getByRole("button", { name: "Salvar rascunho" }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page.reload();

  await expect(page.getByRole("heading", { name: /Nova requisição|Editar rascunho/ })).toBeVisible();
  const continueLocalDraft = page.getByRole("button", { name: "Continuar" });
  if (await continueLocalDraft.isVisible()) {
    await continueLocalDraft.click();
  }
  await expect(page.getByRole("heading", { name: /Papel sulfite A4/ }).first()).toBeVisible();
  await expect(page.getByLabel("Quantidade solicitada")).toHaveValue("2");
});

test("qa final opens authorization detail from deep link @qa-final", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await loginAs(page, "chefe-setor", /\/autorizacoes(?:\?.*)?$/, {
    skipPushOnboarding: true,
  });

  await expect(page.getByRole("heading", { name: "Fila de autorizações" })).toBeVisible();
  await page.getByRole("link", { name: "Abrir" }).first().click();
  await expect(page).toHaveURL(/\/requisicoes\/\d+\?/);
  await expect(page.getByRole("heading", { name: /REQ-\d{4}-\d+/ })).toBeVisible();
  const deepLink = page.url();
  expectDetailContextUrl(deepLink, "autorizacao");

  const deepLinkUrl = new URL(deepLink);
  await page.goto(`${deepLinkUrl.pathname}${deepLinkUrl.search}`, { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: /REQ-\d{4}-\d+/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "Voltar" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("qa final push denied warning does not block authorization queue @qa-final", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await forcePushDeniedCapabilities(page);
  await loginAs(page, "chefe-setor", /\/autorizacoes(?:\?.*)?$/, {
    skipPushOnboarding: true,
  });

  await expect(page.getByRole("heading", { name: "Fila de autorizações" })).toBeVisible();
  await expect(page.getByRole("status").first()).toContainText(/Bloqueado|Sem suporte|Requer instalação PWA/);
  await expect(page.getByRole("link", { name: "Abrir" }).first()).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("qa final exposes support details on API failure @qa-final", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: () => Promise.resolve(undefined),
      },
    });
  });
  await page.route(/\/api\/v1\/requisitions\/mine\//, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      status: 500,
      body: JSON.stringify({
        error: {
          code: "server_error",
          message: "Falha controlada para QA.",
          trace_id: "qa-final-trace",
        },
      }),
    });
  });

  await loginAs(page, "solicitante1", /\/minhas-requisicoes(?:\?.*)?$/);
  await expect(page.getByRole("alert")).toContainText("Falha controlada para QA.");
  await page.getByRole("button", { name: "Copiar detalhes para suporte" }).click();
  await expect(page.getByRole("status")).toContainText("Detalhes copiados.");
});

test("authorizes pending requisition from worklist", async ({ page }) => {
  await loginAs(page, "chefe-setor", /\/autorizacoes(?:\?.*)?$/, {
    skipPushOnboarding: true,
  });

  await expect(page.getByRole("heading", { name: "Fila de autorizações" })).toBeVisible();
  await page.getByRole("link", { name: "Abrir" }).first().click();

  await expect(page).toHaveURL(/\/requisicoes\/\d+\?/);
  expectDetailContextUrl(page.url(), "autorizacao");
  await page.getByRole("button", { name: "Autorizar tudo como solicitado" }).click();
  await expect(page).toHaveURL(/\/autorizacoes(?:\?.*)?$/);
  await expect(page.getByRole("heading", { name: "Fila de autorizações" })).toBeVisible();
});

test("fulfills authorized requisition from worklist", async ({ page }) => {
  await loginAs(page, "auxiliar-almox", /\/atendimentos(?:\?.*)?$/);

  await expect(page.getByRole("heading", { name: "Fila de atendimento" })).toBeVisible();
  await page.getByRole("link", { name: "Abrir" }).first().click();

  await expect(page).toHaveURL(/\/requisicoes\/\d+\?/);
  expectDetailContextUrl(page.url(), "atendimento");
  await page.getByRole("button", { name: "Preencher entrega completa" }).click();
  await page.getByLabel("Retirante físico").fill("Servidor piloto E2E");
  await page.getByRole("button", { name: "Registrar atendimento" }).click();
  await expect(page).toHaveURL(/\/atendimentos(?:\?.*)?$/);
  await expect(page.getByRole("heading", { name: "Fila de atendimento" })).toBeVisible();
});
