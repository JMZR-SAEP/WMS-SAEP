import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: "html",
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "on-first-retry",
    serviceWorkers: "block",
  },
  projects: [
    {
      name: "desktop-chromium",
      use: {
        ...devices["Desktop Chrome"],
      },
    },
    {
      name: "mobile-chrome",
      grep: /@qa-final/,
      use: {
        ...devices["Pixel 5"],
      },
    },
    {
      name: "mobile-safari-webkit",
      grep: /@qa-final/,
      use: {
        ...devices["iPhone 12"],
      },
    },
  ],
  webServer: [
    {
      name: "backend",
      command:
        "WEB_PUSH_VAPID_PUBLIC_KEY='BElxQaFinalMobilePilot_abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJK' uv run python manage.py runserver 127.0.0.1:8000 --noreload",
      cwd: "..",
      url: "http://127.0.0.1:8000/api/v1/auth/csrf/",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: "ignore",
      stderr: "pipe",
    },
    {
      name: "frontend",
      command: "./node_modules/.bin/vite --host 127.0.0.1 --port 4173",
      url: "http://127.0.0.1:4173",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: "ignore",
      stderr: "pipe",
    },
  ],
});
