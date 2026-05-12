import { queryOptions } from "@tanstack/react-query";

import { ensureCsrfCookie, ApiError, type AuthSession, type ErrorResponse } from "../auth/session";
import { apiClient } from "../../shared/api/client";
import type { components } from "../../shared/api/schema";

export type PushConfig = components["schemas"]["PushConfigOutput"];
export type PushSubscriptionOutput = components["schemas"]["PushSubscriptionOutput"];

export const pushQueryKeys = {
  config: ["notifications", "push", "config"] as const,
};

const PUSH_ONBOARDING_PREFIX = "wms-saep:push-onboarding:v1";
const fallbackOnboardingState = new Set<string>();

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
  return getLocalStorage()?.getItem(key) === "seen" || fallbackOnboardingState.has(key);
}

export function markPushOnboardingSeen(session: Pick<AuthSession, "id">) {
  const key = pushOnboardingStorageKey(session);
  const storage = getLocalStorage();

  if (storage) {
    storage.setItem(key, "seen");
    return;
  }

  fallbackOnboardingState.add(key);
}

export function resetPushOnboardingStateForTests() {
  fallbackOnboardingState.clear();

  try {
    const storage = getLocalStorage();
    if (!storage) {
      return;
    }

    const keysToRemove: string[] = [];
    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index);
      if (key?.startsWith(PUSH_ONBOARDING_PREFIX)) {
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

export async function registerPushSubscription(publicKey: string) {
  if (!isPushSupported()) {
    throw new Error("Este navegador não oferece suporte a push.");
  }

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("Permissão de push negada.");
  }

  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: base64UrlToUint8Array(publicKey),
  });
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
