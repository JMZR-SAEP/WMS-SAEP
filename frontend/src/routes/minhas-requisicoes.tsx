import { createFileRoute } from "@tanstack/react-router";

import { FeaturePlaceholder } from "../shared/ui/feature-placeholder";

export const Route = createFileRoute("/minhas-requisicoes")({
  component: MinhasRequisicoesPlaceholderPage,
});

function MinhasRequisicoesPlaceholderPage() {
  return (
    <FeaturePlaceholder
      kicker="Worklist read model"
      title="Minhas requisições"
      summary="Worklist canônica do solicitante e do auxiliar de setor. Estrutura visual já reservada para lista única, destaque de terceiro e filtros mínimos."
      nextSlice="#38 — minhas requisições + detalhe canônico"
      contracts={[
        "GET /api/v1/requisitions/?page=&page_size=&search=&status=",
        "GET /api/v1/requisitions/{id}/",
      ]}
      bullets={[
        "Lista única com rascunhos e formais.",
        "Destaque visual quando beneficiário != usuário logado.",
        "Entrada no detalhe canônico sem telas paralelas.",
      ]}
      preview={
        <div className="preview-panel">
          <div className="preview-row">
            <span>Rascunho</span>
            <span className="preview-meta">beneficiário terceiro</span>
          </div>
          <div className="preview-row">
            <span>REQ-2026-0001</span>
            <span className="preview-meta">aguardando autorização</span>
          </div>
          <div className="preview-row">
            <span>REQ-2026-0002</span>
            <span className="preview-meta">atendida parcialmente</span>
          </div>
        </div>
      }
    />
  );
}
