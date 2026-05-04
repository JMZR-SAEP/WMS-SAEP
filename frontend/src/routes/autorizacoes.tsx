import { createFileRoute } from "@tanstack/react-router";

import { requireSession } from "../features/auth/guards";
import { FeaturePlaceholder } from "../shared/ui/feature-placeholder";

export const Route = createFileRoute("/autorizacoes")({
  beforeLoad: ({ context, location }) =>
    requireSession({ queryClient: context.queryClient, locationHref: location.href }),
  component: AutorizacoesPlaceholderPage,
});

function AutorizacoesPlaceholderPage() {
  return (
    <FeaturePlaceholder
      kicker="Authorization queue"
      title="Fila de autorizações"
      summary="Fila especializada para chefia de setor. O scaffold já reserva densidade operacional maior e ligação direta com o detalhe em `?contexto=autorizacao`."
      nextSlice="#40 — fila e decisões de autorização"
      contracts={[
        "GET /api/v1/requisitions/pending-approvals/",
        "GET /api/v1/requisitions/{id}/",
      ]}
      bullets={[
        "Ordenação por pendências mais antigas primeiro.",
        "Ação rápida só depois da leitura do detalhe canônico.",
        "Nada de capability inventada para auxiliar de setor.",
      ]}
      preview={
        <div className="preview-panel">
          <div className="preview-row">
            <span>REQ-2026-0011</span>
            <span className="preview-meta">setor manutenção</span>
          </div>
          <div className="preview-row">
            <span>REQ-2026-0013</span>
            <span className="preview-meta">2 itens pendentes</span>
          </div>
          <div className="preview-badge">contexto=autorizacao</div>
        </div>
      }
    />
  );
}
