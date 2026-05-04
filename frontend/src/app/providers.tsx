import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { type PropsWithChildren } from "react";

import { appQueryClient } from "./query-client";

type AppProvidersProps = PropsWithChildren<{
  queryClient?: QueryClient;
}>;

export function AppProviders({ children, queryClient = appQueryClient }: AppProvidersProps) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
