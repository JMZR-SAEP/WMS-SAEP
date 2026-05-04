import type { QueryClient } from "@tanstack/react-query";
import { redirect } from "@tanstack/react-router";

import { authQueryKeys, isAuthError, meQueryOptions } from "./session";

export async function requireSession({
  queryClient,
  locationHref,
}: {
  queryClient: QueryClient;
  locationHref: string;
}) {
  try {
    return await queryClient.ensureQueryData(meQueryOptions);
  } catch (error) {
    if (isAuthError(error)) {
      queryClient.removeQueries({ queryKey: authQueryKeys.me });
      // eslint-disable-next-line @typescript-eslint/only-throw-error
      throw redirect({
        to: "/login",
        search: {
          redirect: locationHref,
        },
      });
    }

    throw error;
  }
}
