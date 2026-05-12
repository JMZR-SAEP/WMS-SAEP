import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";

import { reportApiError } from "../features/analytics/analytics";
import { isAuthError } from "../features/auth/session";

export function createAppQueryClient() {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: reportApiError,
    }),
    mutationCache: new MutationCache({
      onError: reportApiError,
    }),
    defaultOptions: {
      queries: {
        retry: (failureCount, error) => {
          if (isAuthError(error)) {
            return false;
          }

          // Pilot default: one retry for transient non-auth failures, no noisy loops.
          return failureCount < 1;
        },
        refetchOnWindowFocus: false,
      },
    },
  });
}

export const appQueryClient = createAppQueryClient();
