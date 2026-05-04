import { createBrowserHistory, createRouter } from "@tanstack/react-router";

import { routeTree } from "../routeTree.gen";

export function buildRouter() {
  return createRouter({
    routeTree,
    defaultPreload: "intent",
    history: createBrowserHistory(),
  });
}

export type AppRouter = ReturnType<typeof buildRouter>;

export const router = buildRouter();

declare module "@tanstack/react-router" {
  interface Register {
    router: AppRouter;
  }
}
