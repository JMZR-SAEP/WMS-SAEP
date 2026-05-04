import { createFileRoute } from "@tanstack/react-router";

import { FeaturePlaceholder } from "../shared/ui/feature-placeholder";

export const Route = createFileRoute("/login")({
  component: LoginPlaceholderPage,
});

function LoginPlaceholderPage() {
  return (
    <FeaturePlaceholder
      kicker="Auth shell"
      title="Entrar no piloto"
      summary="Tela-base pronta para receber fluxo de sessão Django + CSRF. Nesta fatia, o formulário ainda não autentica nem resolve home por papel."
      nextSlice="#37 — login e bootstrap de sessão"
      contracts={[
        "GET /api/v1/auth/csrf/",
        "POST /api/v1/auth/login/",
        "POST /api/v1/auth/logout/",
        "GET /api/v1/auth/me/",
      ]}
      bullets={[
        "Capturar matrícula funcional e senha sem inventar auth paralela.",
        "Redirecionar por papel operacional principal depois do bootstrap.",
        "Tratar sessão expirada com retorno previsível para /login.",
      ]}
      preview={
        <div className="preview-panel space-y-4">
          <label className="preview-label">
            Matrícula funcional
            <input className="preview-input" disabled value="91003" />
          </label>
          <label className="preview-label">
            Senha
            <input className="preview-input" disabled type="password" value="123456" />
          </label>
          <button className="preview-button" disabled type="button">
            Autenticação chega em #37
          </button>
        </div>
      }
    />
  );
}
