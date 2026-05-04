import { createBrowserHistory, createRouter } from "@tanstack/react-router";

import { routeTree } from "../routeTree.gen";
import { appQueryClient } from "./query-client";

export function buildRouter({ queryClient = appQueryClient } = {}) {
  return createRouter({
    routeTree,
    defaultPreload: "intent",
    history: createBrowserHistory(),
    context: {
      queryClient,
    },
  });
}

export type AppRouter = ReturnType<typeof buildRouter>;

export const router = buildRouter();

declare module "@tanstack/react-router" {
  interface Register {
    router: AppRouter;
  }
}
