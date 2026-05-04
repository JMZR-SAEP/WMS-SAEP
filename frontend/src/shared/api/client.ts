import createClient from "openapi-fetch";

import type { paths } from "./schema";

const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function getCookie(name: string) {
  const cookies = document.cookie ? document.cookie.split(";") : [];

  for (const rawCookie of cookies) {
    const cookie = rawCookie.trim();

    if (cookie.startsWith(`${name}=`)) {
      return decodeURIComponent(cookie.slice(name.length + 1));
    }
  }

  return null;
}

export const apiClient = createClient<paths>({
  baseUrl: "/api/v1",
  credentials: "include",
});

apiClient.use({
  onRequest({ request }) {
    if (typeof document === "undefined") {
      return request;
    }

    if (!MUTATING_METHODS.has(request.method.toUpperCase())) {
      return request;
    }

    const csrfToken = getCookie("csrftoken");

    if (csrfToken) {
      request.headers.set("X-CSRFToken", csrfToken);
    }

    return request;
  },
});
