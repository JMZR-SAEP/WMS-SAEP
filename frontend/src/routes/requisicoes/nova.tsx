import { createFileRoute } from "@tanstack/react-router";

import { requireSession } from "../../features/auth/guards";
import { FeaturePlaceholder } from "../../shared/ui/feature-placeholder";

export const Route = createFileRoute("/requisicoes/nova")({
  beforeLoad: ({ context, location }) =>
    requireSession({ queryClient: context.queryClient, locationHref: location.href }),
  component: NovaRequisicaoPlaceholderPage,
});

function NovaRequisicaoPlaceholderPage() {
  return (
    <FeaturePlaceholder
      kicker="Draft editor"
      title="Nova requisição"
      summary="Tela-base reservada para criação e edição do mesmo rascunho. O scaffold não envia nada ainda, mas fixa o espaço para fluxo único de draft."
      nextSlice="#39 — criação, edição e envio de rascunho"
      contracts={[
        "GET /api/v1/users/beneficiary-lookup/?q=...",
        "PUT /api/v1/requisitions/{id}/draft/",
      ]}
      bullets={[
        "Beneficiário por busca curta, nunca diretório infinito.",
        "Mesma tela para criar, salvar e editar rascunho.",
        "Substituição completa de itens no update explícito.",
      ]}
      preview={
        <div className="preview-panel space-y-3">
          <div className="preview-row">
            <span>Beneficiário</span>
            <span className="preview-meta">lookup por nome</span>
          </div>
          <div className="preview-row">
            <span>Itens</span>
            <span className="preview-meta">replace total no draft</span>
          </div>
          <button className="preview-button" disabled type="button">
            Salvar rascunho chega em #39
          </button>
        </div>
      }
    />
  );
}
