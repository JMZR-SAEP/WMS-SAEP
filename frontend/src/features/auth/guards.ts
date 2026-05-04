import type { QueryClient } from "@tanstack/react-query";
import { redirect } from "@tanstack/react-router";

import { ApiError, authQueryKeys, meQueryOptions } from "./session";

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
    if (error instanceof ApiError && error.status === 401) {
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
