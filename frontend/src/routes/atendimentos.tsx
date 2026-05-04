import { createFileRoute } from "@tanstack/react-router";

import { requireSession } from "../features/auth/guards";
import { FeaturePlaceholder } from "../shared/ui/feature-placeholder";

export const Route = createFileRoute("/atendimentos")({
  beforeLoad: ({ context, location }) =>
    requireSession({ queryClient: context.queryClient, locationHref: location.href }),
  component: AtendimentosPlaceholderPage,
});

function AtendimentosPlaceholderPage() {
  return (
    <FeaturePlaceholder
      kicker="Fulfillment queue"
      title="Fila de atendimento"
      summary="Fila operacional do Almoxarifado pronta para receber atendimento total, parcial e leitura contextual do detalhe. Ainda sem side effects reais nesta fatia."
      nextSlice="#41 — fila e fluxo de atendimento"
      contracts={[
        "GET /api/v1/requisitions/pending-fulfillments/",
        "GET /api/v1/requisitions/{id}/",
        "POST /api/v1/requisitions/{id}/fulfill/",
      ]}
      bullets={[
        "Fila global do Almoxarifado, não por setor individual.",
        "Detalhe entra em modo `contexto=atendimento`.",
        "Exceções operacionais ficam para o bloco funcional, não para o scaffold.",
      ]}
      preview={
        <div className="preview-panel">
          <div className="preview-row">
            <span>REQ-2026-0020</span>
            <span className="preview-meta">autorizada</span>
          </div>
          <div className="preview-row">
            <span>REQ-2026-0021</span>
            <span className="preview-meta">retirante pendente</span>
          </div>
          <div className="preview-badge">contexto=atendimento</div>
        </div>
      }
    />
  );
}
