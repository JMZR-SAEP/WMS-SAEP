import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";

import { requireSession } from "../../features/auth/guards";
import { meQueryOptions } from "../../features/auth/session";
import { DraftRequisitionEditor } from "../../features/requisitions/DraftRequisitionEditor";

export const Route = createFileRoute("/requisicoes/nova")({
  beforeLoad: ({ context, location }) =>
    requireSession({ queryClient: context.queryClient, locationHref: location.href }),
  component: NovaRequisicaoPage,
});

function NovaRequisicaoPage() {
  const sessionQuery = useQuery(meQueryOptions);

  if (!sessionQuery.data) {
    return <div className="loading-state">Carregando sessão...</div>;
  }

  return <DraftRequisitionEditor session={sessionQuery.data} />;
}
