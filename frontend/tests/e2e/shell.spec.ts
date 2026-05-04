import { expect, test } from "@playwright/test";

test("loads frontend shell", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Fundação da SPA")).toBeVisible();
  await expect(page.getByText("Repositório pronto para #37 e #42")).toBeVisible();
  await expect(page.locator('nav a[href="/login"]').first()).toBeVisible();
});
