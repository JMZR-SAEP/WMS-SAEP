import { queryOptions } from "@tanstack/react-query";

import { ensureCsrfCookie, ApiError, type AuthSession, type ErrorResponse } from "../auth/session";
import { apiClient } from "../../shared/api/client";
import type { components } from "../../shared/api/schema";

export type PushConfig = components["schemas"]["PushConfigOutput"];
export type PushSubscriptionOutput = components["schemas"]["PushSubscriptionOutput"];
type PushEventDiagnosticStatus = components["schemas"]["DiagnosticStatusEnum"];
export type PushDiagnosticStatus = PushEventDiagnosticStatus | "aguardando_config";
export type PushClientEventType = components["schemas"]["EventTypeEnum"];
export type PushClientEventInput = components["schemas"]["PushClientEventInput"];
export type PushClientEventOutput = components["schemas"]["PushClientEventOutput"];
export type PushCapabilities = Pick<
  PushClientEventInput,
  | "notification_supported"
  | "service_worker_supported"
  | "push_manager_supported"
  | "badging_supported"
  | "standalone_display"
>;

export type PushDiagnostic = {
  status: PushDiagnosticStatus;
  label: string;
  description: string;
  nextAction: string;
  canActivate: boolean;
  eventType?: PushClientEventType;
  capabilities: PushCapabilities;
};

export const pushQueryKeys = {
  config: ["notifications", "push", "config"] as const,
};

const PUSH_ONBOARDING_PREFIX = "wms-saep:push-onboarding:v1";
const PUSH_EVENT_PREFIX = "wms-saep:push-event:v1";
const fallbackOnboardingState = new Set<string>();
const fallbackReportedEvents = new Set<string>();

function getLocalStorage() {
  try {
    const storage = window.localStorage;
    if (
      typeof storage?.getItem === "function" &&
      typeof storage.setItem === "function"
    ) {
      return storage;
    }
  } catch {
    return null;
  }

  return null;
}

export function isPushOnboardingPapel(papel: string) {
  return papel === "chefe_setor" || papel === "chefe_almoxarifado";
}

export function pushOnboardingStorageKey(session: Pick<AuthSession, "id">) {
  return `${PUSH_ONBOARDING_PREFIX}:user:${session.id}`;
}

export function hasSeenPushOnboarding(session: Pick<AuthSession, "id">) {
  const key = pushOnboardingStorageKey(session);
  try {
    return getLocalStorage()?.getItem(key) === "seen" || fallbackOnboardingState.has(key);
  } catch {
    return fallbackOnboardingState.has(key);
  }
}

export function markPushOnboardingSeen(session: Pick<AuthSession, "id">) {
  const key = pushOnboardingStorageKey(session);
  const storage = getLocalStorage();

  if (storage) {
    try {
      storage.setItem(key, "seen");
      return;
    } catch {
      fallbackOnboardingState.add(key);
      return;
    }
  }

  fallbackOnboardingState.add(key);
}

export function resetPushOnboardingStateForTests() {
  fallbackOnboardingState.clear();
  fallbackReportedEvents.clear();

  try {
    const storage = getLocalStorage();
    if (!storage) {
      return;
    }

    const keysToRemove: string[] = [];
    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index);
      if (key?.startsWith(PUSH_ONBOARDING_PREFIX) || key?.startsWith(PUSH_EVENT_PREFIX)) {
        keysToRemove.push(key);
      }
    }

    keysToRemove.forEach((key) => storage.removeItem(key));
  } catch {
    // Test environments may expose a partial localStorage shim.
  }
}

function messageFromError(error: ErrorResponse | undefined, fallback: string) {
  return error?.error?.message || fallback;
}

export async function fetchPushConfig() {
  const { data, error, response } = await apiClient.GET("/api/v1/notifications/push/config/");

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível carregar configuração de alertas."),
      response.status,
      error,
    );
  }

  return data;
}

export const pushConfigQueryOptions = queryOptions({
  queryKey: pushQueryKeys.config,
  queryFn: fetchPushConfig,
  retry: false,
});

export function isPushSupported() {
  return (
    "Notification" in window &&
    "serviceWorker" in navigator &&
    "PushManager" in window
  );
}

function isStandaloneDisplay() {
  const navigatorWithStandalone = navigator as Navigator & { standalone?: boolean };
  return (
    navigatorWithStandalone.standalone === true ||
    window.matchMedia?.("(display-mode: standalone)")?.matches === true
  );
}

function isLikelyIos() {
  return /iPad|iPhone|iPod/.test(navigator.userAgent);
}

export function getPushCapabilities(): PushCapabilities {
  return {
    notification_supported: "Notification" in window,
    service_worker_supported: "serviceWorker" in navigator,
    push_manager_supported: "PushManager" in window,
    badging_supported: "setAppBadge" in navigator && "clearAppBadge" in navigator,
    standalone_display: isStandaloneDisplay(),
  };
}

export function getPushDiagnostic(config?: Pick<PushConfig, "enabled"> | null): PushDiagnostic {
  const capabilities = getPushCapabilities();

  if (config == null) {
    return {
      status: "aguardando_config",
      label: "Verificando",
      description: "A configuração de alertas ainda está sendo carregada.",
      nextAction: "Aguarde a verificação dos alertas neste navegador.",
      canActivate: false,
      capabilities,
    };
  }

  if (isLikelyIos() && !capabilities.standalone_display) {
    return {
      status: "requer_instalacao_pwa",
      label: "Requer instalação PWA",
      description: "No iPhone/iPad, os alertas funcionam pelo app instalado na Tela de Início.",
      nextAction: "Instale o WMS-SAEP na Tela de Início e volte a esta tela.",
      canActivate: false,
      eventType: "push_requires_pwa",
      capabilities,
    };
  }

  if (!config.enabled || !isPushSupported()) {
    return {
      status: "sem_suporte",
      label: "Sem suporte",
      description: "Este navegador ou servidor não oferece Web Push completo para o piloto.",
      nextAction: "Use Chrome Android atual ou Safari iOS com PWA instalado.",
      canActivate: false,
      eventType: "push_unavailable",
      capabilities,
    };
  }

  if (Notification.permission === "denied") {
    return {
      status: "bloqueado",
      label: "Bloqueado",
      description: "A permissão de notificações foi negada neste navegador.",
      nextAction: "Libere notificações nas configurações do navegador para este site.",
      canActivate: false,
      eventType: "push_permission_denied",
      capabilities,
    };
  }

  if (Notification.permission === "granted") {
    return {
      status: "ativo",
      label: "Ativo",
      description: "Este navegador pode receber alertas de autorização.",
      nextAction: "Nenhuma ação necessária.",
      canActivate: false,
      capabilities,
    };
  }

  return {
    status: "requer_ativacao",
    label: "Requer ativação",
    description: "Alertas ainda não foram ativados neste navegador.",
    nextAction: "Ative alertas para receber novas autorizações pendentes.",
    canActivate: true,
    capabilities,
  };
}

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

function pushEventStorageKey(
  session: Pick<AuthSession, "id">,
  eventType: PushClientEventType,
) {
  return `${PUSH_EVENT_PREFIX}:user:${session.id}:${eventType}:${todayKey()}`;
}

function hasReportedPushEvent(
  session: Pick<AuthSession, "id">,
  eventType: PushClientEventType,
) {
  const key = pushEventStorageKey(session, eventType);
  try {
    return getLocalStorage()?.getItem(key) === "sent" || fallbackReportedEvents.has(key);
  } catch {
    return fallbackReportedEvents.has(key);
  }
}

function markPushEventReported(
  session: Pick<AuthSession, "id">,
  eventType: PushClientEventType,
) {
  const key = pushEventStorageKey(session, eventType);
  const storage = getLocalStorage();
  if (storage) {
    try {
      storage.setItem(key, "sent");
      return;
    } catch {
      fallbackReportedEvents.add(key);
      return;
    }
  }
  fallbackReportedEvents.add(key);
}

function unmarkPushEventReported(
  session: Pick<AuthSession, "id">,
  eventType: PushClientEventType,
) {
  const key = pushEventStorageKey(session, eventType);
  fallbackReportedEvents.delete(key);

  try {
    getLocalStorage()?.removeItem(key);
  } catch {
    // Keep rollback best-effort when storage is unavailable.
  }
}

export async function recordPushClientEvent(input: PushClientEventInput) {
  await ensureCsrfCookie();
  const { data, error, response } = await apiClient.POST("/api/v1/notifications/push/events/", {
    body: input,
  });

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível registrar diagnóstico de alertas."),
      response.status,
      error,
    );
  }

  return data;
}

export async function reportPushDiagnosticIfNeeded(
  session: Pick<AuthSession, "id">,
  diagnostic: PushDiagnostic,
) {
  if (
    !diagnostic.eventType ||
    diagnostic.status === "aguardando_config" ||
    hasReportedPushEvent(session, diagnostic.eventType)
  ) {
    return;
  }

  markPushEventReported(session, diagnostic.eventType);
  try {
    await recordPushClientEvent({
      event_type: diagnostic.eventType,
      diagnostic_status: diagnostic.status,
      ...diagnostic.capabilities,
    });
  } catch (error) {
    unmarkPushEventReported(session, diagnostic.eventType);
    throw error;
  }
}

export async function reportBadgeUnavailableIfNeeded(
  session: Pick<AuthSession, "id">,
  capabilities = getPushCapabilities(),
) {
  const eventType: PushClientEventType = "push_badge_unavailable";
  if (hasReportedPushEvent(session, eventType)) {
    return;
  }

  markPushEventReported(session, eventType);
  try {
    await recordPushClientEvent({
      event_type: eventType,
      diagnostic_status: capabilities.badging_supported ? "ativo" : "sem_suporte",
      ...capabilities,
    });
  } catch (error) {
    unmarkPushEventReported(session, eventType);
    throw error;
  }
}

type NavigatorWithBadging = Navigator & {
  setAppBadge?: (contents?: number) => Promise<void>;
  clearAppBadge?: () => Promise<void>;
};

export async function updateAppBadge(count: number) {
  const badgeNavigator = navigator as NavigatorWithBadging;
  if (
    typeof badgeNavigator.setAppBadge !== "function" ||
    typeof badgeNavigator.clearAppBadge !== "function"
  ) {
    return false;
  }

  if (count > 0) {
    await badgeNavigator.setAppBadge(count);
    return true;
  }

  await badgeNavigator.clearAppBadge();
  return true;
}

function base64UrlToUint8Array(value: string) {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const base64 = `${value}${padding}`.replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const output = new Uint8Array(rawData.length);

  for (let index = 0; index < rawData.length; index += 1) {
    output[index] = rawData.charCodeAt(index);
  }

  return output;
}

function applicationServerKeysMatch(
  existingKey: ArrayBuffer | null | undefined,
  expectedKey: Uint8Array,
) {
  if (!existingKey) {
    return false;
  }

  const existingBytes = new Uint8Array(existingKey);
  if (existingBytes.byteLength !== expectedKey.byteLength) {
    return false;
  }

  return existingBytes.every((byte, index) => byte === expectedKey[index]);
}

export async function registerPushSubscription(publicKey: string) {
  if (!isPushSupported()) {
    throw new Error("Este navegador não oferece suporte a push.");
  }

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("Permissão de push negada.");
  }

  const registration = await navigator.serviceWorker.ready;
  const existingSubscription = await registration.pushManager.getSubscription();
  const applicationServerKey = base64UrlToUint8Array(publicKey);
  let subscription = existingSubscription;

  if (
    existingSubscription &&
    !applicationServerKeysMatch(
      existingSubscription.options?.applicationServerKey,
      applicationServerKey,
    )
  ) {
    await existingSubscription.unsubscribe();
    subscription = null;
  }

  if (!subscription) {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey,
    });
  }
  const subscriptionJson = subscription.toJSON();

  if (!subscriptionJson.endpoint || !subscriptionJson.keys?.p256dh || !subscriptionJson.keys.auth) {
    throw new Error("Assinatura push incompleta.");
  }

  await ensureCsrfCookie();
  const { data, error, response } = await apiClient.POST(
    "/api/v1/notifications/push/subscriptions/",
    {
      body: {
        endpoint: subscriptionJson.endpoint,
        keys: {
          p256dh: subscriptionJson.keys.p256dh,
          auth: subscriptionJson.keys.auth,
        },
      },
    },
  );

  if (error || !data) {
    throw new ApiError(
      messageFromError(error, "Não foi possível ativar alertas neste navegador."),
      response.status,
      error,
    );
  }

  return data;
}
