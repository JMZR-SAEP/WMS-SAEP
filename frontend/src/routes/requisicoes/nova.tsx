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

  if (sessionQuery.isLoading) {
    return <div className="loading-state">Carregando sessão...</div>;
  }

  if (sessionQuery.isError) {
    return (
      <div className="error-panel">
        <p>Erro carregando sessão.</p>
        <button className="compact-action" type="button" onClick={() => void sessionQuery.refetch()}>
          Tentar novamente
        </button>
      </div>
    );
  }

  if (!sessionQuery.data) {
    return <div className="error-panel">Sessão indisponível.</div>;
  }

  return <DraftRequisitionEditor session={sessionQuery.data} />;
}
