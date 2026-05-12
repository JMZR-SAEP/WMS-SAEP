import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getPushDiagnostic,
  hasSeenPushOnboarding,
  markPushOnboardingSeen,
  reportPushDiagnosticIfNeeded,
  resetPushOnboardingStateForTests,
  updateAppBadge,
} from "../features/pwa/push";
import { registerServiceWorker } from "../features/pwa/service-worker";

const originalServiceWorkerDescriptor = Object.getOwnPropertyDescriptor(navigator, "serviceWorker");
const originalLocalStorageDescriptor = Object.getOwnPropertyDescriptor(window, "localStorage");
const originalUserAgent = navigator.userAgent;
const originalSetAppBadgeDescriptor = Object.getOwnPropertyDescriptor(navigator, "setAppBadge");
const originalClearAppBadgeDescriptor = Object.getOwnPropertyDescriptor(navigator, "clearAppBadge");

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  resetPushOnboardingStateForTests();
  if (originalServiceWorkerDescriptor) {
    Object.defineProperty(navigator, "serviceWorker", originalServiceWorkerDescriptor);
  } else {
    Reflect.deleteProperty(navigator, "serviceWorker");
  }
  if (originalLocalStorageDescriptor) {
    Object.defineProperty(window, "localStorage", originalLocalStorageDescriptor);
  }
  Object.defineProperty(navigator, "userAgent", {
    configurable: true,
    value: originalUserAgent,
  });
  if (originalSetAppBadgeDescriptor) {
    Object.defineProperty(navigator, "setAppBadge", originalSetAppBadgeDescriptor);
  } else {
    Reflect.deleteProperty(navigator, "setAppBadge");
  }
  if (originalClearAppBadgeDescriptor) {
    Object.defineProperty(navigator, "clearAppBadge", originalClearAppBadgeDescriptor);
  } else {
    Reflect.deleteProperty(navigator, "clearAppBadge");
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

  it("diagnostica push bloqueado por permissao negada", () => {
    vi.stubGlobal("Notification", {
      permission: "denied",
      requestPermission: vi.fn(),
    });
    vi.stubGlobal("PushManager", function PushManager() {});
    Object.defineProperty(navigator, "serviceWorker", {
      configurable: true,
      value: {},
    });

    const diagnostic = getPushDiagnostic({ enabled: true });

    expect(diagnostic.status).toBe("bloqueado");
    expect(diagnostic.eventType).toBe("push_permission_denied");
    expect(diagnostic.canActivate).toBe(false);
  });

  it("diagnostica falta de suporte do navegador", () => {
    Reflect.deleteProperty(navigator, "serviceWorker");

    const diagnostic = getPushDiagnostic({ enabled: true });

    expect(diagnostic.status).toBe("sem_suporte");
    expect(diagnostic.eventType).toBe("push_unavailable");
  });

  it("mantem diagnostico neutro enquanto configuracao nao carregou", () => {
    const diagnostic = getPushDiagnostic(null);

    expect(diagnostic.status).toBe("aguardando_config");
    expect(diagnostic.eventType).toBeUndefined();
    expect(diagnostic.canActivate).toBe(false);
  });

  it("diagnostica iOS fora do modo PWA instalado", () => {
    Object.defineProperty(navigator, "userAgent", {
      configurable: true,
      value: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
    });
    vi.stubGlobal("Notification", {
      permission: "default",
      requestPermission: vi.fn(),
    });
    vi.stubGlobal("PushManager", function PushManager() {});
    Object.defineProperty(navigator, "serviceWorker", {
      configurable: true,
      value: {},
    });
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => ({
        matches: false,
        media: "(display-mode: standalone)",
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    );

    const diagnostic = getPushDiagnostic({ enabled: true });

    expect(diagnostic.status).toBe("requer_instalacao_pwa");
    expect(diagnostic.eventType).toBe("push_requires_pwa");
  });

  it("atualiza badge quando API do navegador existe", async () => {
    const setAppBadge = vi.fn().mockResolvedValue(undefined);
    const clearAppBadge = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "setAppBadge", {
      configurable: true,
      value: setAppBadge,
    });
    Object.defineProperty(navigator, "clearAppBadge", {
      configurable: true,
      value: clearAppBadge,
    });

    await expect(updateAppBadge(3)).resolves.toBe(true);
    await expect(updateAppBadge(0)).resolves.toBe(true);

    expect(setAppBadge).toHaveBeenCalledWith(3);
    expect(clearAppBadge).toHaveBeenCalled();
  });

  it("registra evento de diagnostico uma vez por dia", async () => {
    const postedBodies: unknown[] = [];
    Object.defineProperty(navigator, "userAgent", {
      configurable: true,
      value: "Mozilla/5.0 desktop",
    });
    vi.stubGlobal("fetch", async (request: Request) => {
      if (request.url.includes("/api/v1/auth/csrf/")) {
        return new Response(JSON.stringify({ csrf_token: "token" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (request.url.includes("/api/v1/notifications/push/events/")) {
        postedBodies.push(await request.json());
        return new Response(
          JSON.stringify({
            event_type: "push_unavailable",
            diagnostic_status: "sem_suporte",
            notification_supported: false,
            service_worker_supported: false,
            push_manager_supported: false,
            badging_supported: false,
            standalone_display: false,
            event_date: "2026-05-12",
            updated_at: "2026-05-12T10:00:00Z",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response("Not found", { status: 404 });
    });

    const diagnostic = getPushDiagnostic({ enabled: false });
    await reportPushDiagnosticIfNeeded({ id: 88 }, diagnostic);
    await reportPushDiagnosticIfNeeded({ id: 88 }, diagnostic);

    expect(postedBodies).toHaveLength(1);
    expect(postedBodies[0]).toMatchObject({
      event_type: "push_unavailable",
      diagnostic_status: "sem_suporte",
      service_worker_supported: false,
      badging_supported: false,
      standalone_display: false,
    });
  });

  it("evita duplicidade concorrente e reverte marca local quando registro falha", async () => {
    let requestCount = 0;
    let failRequest = false;
    vi.stubGlobal("fetch", (request: Request) => {
      if (request.url.includes("/api/v1/auth/csrf/")) {
        return new Response(JSON.stringify({ csrf_token: "token" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (request.url.includes("/api/v1/notifications/push/events/")) {
        requestCount += 1;
        if (failRequest) {
          return new Response(JSON.stringify({ error: { message: "falhou" } }), {
            status: 503,
            headers: { "Content-Type": "application/json" },
          });
        }
        return new Response(
          JSON.stringify({
            event_type: "push_unavailable",
            diagnostic_status: "sem_suporte",
            notification_supported: false,
            service_worker_supported: false,
            push_manager_supported: false,
            badging_supported: false,
            standalone_display: false,
            event_date: "2026-05-12",
            updated_at: "2026-05-12T10:00:00Z",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response("Not found", { status: 404 });
    });

    const diagnostic = getPushDiagnostic({ enabled: false });
    await Promise.all([
      reportPushDiagnosticIfNeeded({ id: 89 }, diagnostic),
      reportPushDiagnosticIfNeeded({ id: 89 }, diagnostic),
    ]);

    expect(requestCount).toBe(1);

    resetPushOnboardingStateForTests();
    requestCount = 0;
    failRequest = true;
    await expect(reportPushDiagnosticIfNeeded({ id: 89 }, diagnostic)).rejects.toThrow();

    failRequest = false;
    await reportPushDiagnosticIfNeeded({ id: 89 }, diagnostic);

    expect(requestCount).toBe(2);
  });
});
