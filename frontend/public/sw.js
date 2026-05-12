const STATIC_CACHE = "wms-saep-static-v1";
const STATIC_ASSETS = ["/manifest.webmanifest", "/saep-icon.svg", "/saep-logo.webp"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .catch(() => undefined),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== STATIC_CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("push", (event) => {
  let payload = {};

  if (event.data) {
    try {
      payload = event.data.json();
    } catch {
      payload = {};
    }
  }

  const title = payload.title || "WMS-SAEP";
  const options = {
    body: payload.body || "Nova notificação disponível.",
    tag: payload.tag || "wms-saep",
    data: {
      url: payload.url || "/",
    },
    icon: "/saep-icon.svg",
    badge: "/saep-icon.svg",
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const requestedUrl = event.notification.data?.url || "/";
  const parsedTarget = new URL(requestedUrl, self.location.origin);
  const targetUrl =
    parsedTarget.origin === self.location.origin
      ? parsedTarget.href
      : new URL("/", self.location.origin).href;

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if (client.url === targetUrl && "focus" in client) {
          return client.focus();
        }
      }

      return self.clients.openWindow(targetUrl);
    }),
  );
});
