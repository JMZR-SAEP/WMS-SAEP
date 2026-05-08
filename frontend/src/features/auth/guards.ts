import type { QueryClient } from "@tanstack/react-query";
import { redirect } from "@tanstack/react-router";

import {
  authQueryKeys,
  homePathForPapel,
  isAuthError,
  isPapelOperacional,
  meQueryOptions,
  type PapelOperacional,
} from "./session";

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

export async function requireOperationalPapel({
  allowedPapeis,
  locationHref,
  queryClient,
}: {
  allowedPapeis: PapelOperacional[];
  locationHref: string;
  queryClient: QueryClient;
}) {
  const session = await requireSession({ queryClient, locationHref });

  if (isPapelOperacional(session.papel) && allowedPapeis.includes(session.papel)) {
    return session;
  }

  // eslint-disable-next-line @typescript-eslint/only-throw-error
  throw redirect({ to: homePathForPapel(session.papel) });
}
