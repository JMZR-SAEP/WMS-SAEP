import { afterEach, describe, expect, it, vi } from "vitest";

import { registerServiceWorker } from "../features/pwa/service-worker";

const originalServiceWorkerDescriptor = Object.getOwnPropertyDescriptor(navigator, "serviceWorker");

afterEach(() => {
  vi.restoreAllMocks();
  if (originalServiceWorkerDescriptor) {
    Object.defineProperty(navigator, "serviceWorker", originalServiceWorkerDescriptor);
  } else {
    Reflect.deleteProperty(navigator, "serviceWorker");
  }
});

describe("PWA bootstrap", () => {
  it("registra o service worker publico da SPA", async () => {
    const register = vi.fn().mockResolvedValue({});

    Object.defineProperty(navigator, "serviceWorker", {
      configurable: true,
      value: {
        register,
      },
    });

    await registerServiceWorker();

    expect(register).toHaveBeenCalledWith("/sw.js");
  });

  it("retorna null quando navigator.serviceWorker não existe", async () => {
    Reflect.deleteProperty(navigator, "serviceWorker");

    await expect(registerServiceWorker()).resolves.toBeNull();
  });
});
