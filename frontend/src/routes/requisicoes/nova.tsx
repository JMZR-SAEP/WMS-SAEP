import { useQuery } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { z } from "zod";

import { requireSession } from "../../features/auth/guards";
import { meQueryOptions } from "../../features/auth/session";
import { DraftRequisitionEditor } from "../../features/requisitions/DraftRequisitionEditor";
import { canRequestForThirdParty, draftStepSchema, type DraftStep } from "../../features/requisitions/draftSteps";
import { SupportErrorPanel } from "../../shared/ui/support-error";

const draftSearchSchema = z.object({
  etapa: draftStepSchema.optional().catch("beneficiario"),
});

export const Route = createFileRoute("/requisicoes/nova")({
  validateSearch: draftSearchSchema,
  beforeLoad: ({ context, location }) =>
    requireSession({ queryClient: context.queryClient, locationHref: location.href }),
  component: NovaRequisicaoPage,
});

function NovaRequisicaoPage() {
  const sessionQuery = useQuery(meQueryOptions);
  const { etapa = "beneficiario" } = Route.useSearch();
  const navigate = useNavigate({ from: "/requisicoes/nova" });

  function handleStepChange(step: DraftStep) {
    void navigate({ search: (prev) => ({ ...prev, etapa: step }) });
  }

  if (sessionQuery.isLoading) {
    return <div className="loading-state">Carregando sessão...</div>;
  }

  if (sessionQuery.isError) {
    return (
      <SupportErrorPanel
        error={sessionQuery.error}
        fallback="Erro carregando sessão."
        onRetry={() => void sessionQuery.refetch()}
        retryLabel="Tentar novamente"
      />
    );
  }

  if (!sessionQuery.data) {
    return <div className="error-panel">Sessão indisponível.</div>;
  }

  const resolvedEtapa =
    etapa === "beneficiario" && !canRequestForThirdParty(sessionQuery.data) ? "itens" : etapa;

  return (
    <DraftRequisitionEditor
      activeStep={resolvedEtapa}
      onStepChange={handleStepChange}
      session={sessionQuery.data}
    />
  );
}
