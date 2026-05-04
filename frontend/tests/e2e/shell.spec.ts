import { expect, test } from "@playwright/test";

test("loads frontend shell", async ({ page }) => {
  await page.goto("/");

  await expect(page.locator("aside.glass-panel")).toBeVisible();
  await expect(page.locator("main .status-chip")).toBeVisible();
  await expect(page.locator('nav a[href="/login"]').first()).toBeVisible();
});
