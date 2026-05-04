import { createFileRoute } from "@tanstack/react-router";

import { requireSession } from "../../features/auth/guards";
import { FeaturePlaceholder } from "../../shared/ui/feature-placeholder";

export const Route = createFileRoute("/requisicoes/$id")({
  beforeLoad: ({ context, location }) =>
    requireSession({ queryClient: context.queryClient, locationHref: location.href }),
  component: DetalhePlaceholderPage,
});

function DetalhePlaceholderPage() {
  const { id } = Route.useParams();

  return (
    <FeaturePlaceholder
      kicker="Canonical detail"
      title={`Requisição ${id}`}
      summary="Superfície canônica do piloto. Cabeçalho, itens, status e resumo de eventos já têm lugar definido, mas as ações contextuais reais entram nas próximas slices."
      nextSlice="#38 + #40 + #41"
      contracts={[
        "GET /api/v1/requisitions/{id}/",
        "query param contexto=autorizacao|atendimento",
      ]}
      bullets={[
        "Corpo comum para qualquer entrada.",
        "Ações mudam por contexto, não por rota duplicada.",
        "Timeline e divergências visuais chegam nas fatias funcionais.",
      ]}
      preview={
        <div className="preview-panel space-y-3">
          <div className="preview-row">
            <span>Status</span>
            <span className="preview-meta">aguardando autorização</span>
          </div>
          <div className="preview-row">
            <span>Itens</span>
            <span className="preview-meta">solicitado / autorizado / entregue</span>
          </div>
          <div className="preview-row">
            <span>Eventos</span>
            <span className="preview-meta">timeline resumida</span>
          </div>
        </div>
      }
    />
  );
}
