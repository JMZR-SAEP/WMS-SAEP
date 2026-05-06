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

test("opens minhas requisicoes and canonical detail", async ({ page }) => {
  await page.route("**/api/v1/auth/me/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
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
    });
  });
  await page.route("**/api/v1/requisitions/mine/?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        count: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
        next: null,
        previous: null,
        results: [
          {
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
              nome_completo: "Beneficiario Terceiro",
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
          },
        ],
      }),
    });
  });
  await page.route("**/api/v1/requisitions/101/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 101,
        numero_publico: "REQ-2026-000101",
        status: "autorizada",
        criador: {
          id: 10,
          matricula_funcional: "91003",
          nome_completo: "Usuario Piloto",
        },
        beneficiario: {
          id: 11,
          matricula_funcional: "91004",
          nome_completo: "Beneficiario Terceiro",
        },
        setor_beneficiario: {
          id: 1,
          nome: "Operacao",
        },
        chefe_autorizador: null,
        responsavel_atendimento: null,
        data_criacao: "2026-05-01T10:00:00Z",
        data_envio_autorizacao: "2026-05-01T11:00:00Z",
        data_autorizacao_ou_recusa: "2026-05-01T12:00:00Z",
        motivo_recusa: "",
        motivo_cancelamento: "",
        data_finalizacao: null,
        retirante_fisico: "",
        observacao: "",
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
            observacao: "",
          },
        ],
        eventos: [],
      }),
    });
  });

  await page.goto("/minhas-requisicoes?search=REQ");

  await expect(page.getByRole("heading", { name: "Minhas requisições" })).toBeVisible();
  await expect(page.getByText("REQ-2026-000101")).toBeVisible();
  await expect(page.getByText("Beneficiário terceiro")).toBeVisible();

  await page.getByRole("link", { name: "Abrir" }).click();

  await expect(page).toHaveURL(/\/requisicoes\/101$/);
  await expect(page.getByRole("heading", { name: "REQ-2026-000101" })).toBeVisible();
  await expect(page.getByText("Papel sulfite A4")).toBeVisible();
});
