import { QueryClient } from "@tanstack/react-query";

import { isAuthError } from "../features/auth/session";

export function createAppQueryClient() {
  return new QueryClient({
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
