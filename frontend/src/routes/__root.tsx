import { createRootRoute } from "@tanstack/react-router";

import { AppShell } from "../app/layouts/app-shell";

export const Route = createRootRoute({
  component: AppShell,
});
