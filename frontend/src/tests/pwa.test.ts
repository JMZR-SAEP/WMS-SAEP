import { afterEach, describe, expect, it, vi } from "vitest";

import {
  hasSeenPushOnboarding,
  markPushOnboardingSeen,
  resetPushOnboardingStateForTests,
} from "../features/pwa/push";
import { registerServiceWorker } from "../features/pwa/service-worker";

const originalServiceWorkerDescriptor = Object.getOwnPropertyDescriptor(navigator, "serviceWorker");
const originalLocalStorageDescriptor = Object.getOwnPropertyDescriptor(window, "localStorage");

afterEach(() => {
  vi.restoreAllMocks();
  resetPushOnboardingStateForTests();
  if (originalServiceWorkerDescriptor) {
    Object.defineProperty(navigator, "serviceWorker", originalServiceWorkerDescriptor);
  } else {
    Reflect.deleteProperty(navigator, "serviceWorker");
  }
  if (originalLocalStorageDescriptor) {
    Object.defineProperty(window, "localStorage", originalLocalStorageDescriptor);
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

  it("mantem fallback em memoria quando localStorage falha", () => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: {
        getItem: vi.fn(() => {
          throw new Error("storage blocked");
        }),
        setItem: vi.fn(() => {
          throw new Error("quota exceeded");
        }),
      },
    });

    markPushOnboardingSeen({ id: 77 });

    expect(hasSeenPushOnboarding({ id: 77 })).toBe(true);
    expect(hasSeenPushOnboarding({ id: 78 })).toBe(false);
  });
});
