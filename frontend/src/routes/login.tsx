import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

import {
  ApiError,
  authQueryKeys,
  homePathForPapel,
  loginWithMatricula,
} from "../features/auth/session";
import { FeaturePlaceholder } from "../shared/ui/feature-placeholder";

function safeInternalRedirectPath(redirect: string | undefined) {
  if (!redirect || redirect.startsWith("//")) {
    return undefined;
  }

  try {
    const url = new URL(redirect, window.location.origin);

    if (url.origin !== window.location.origin || !url.pathname.startsWith("/")) {
      return undefined;
    }

    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return undefined;
  }
}

export const Route = createFileRoute("/login")({
  validateSearch: (search) => ({
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }),
  component: LoginPage,
});

function LoginPage() {
  const queryClient = useQueryClient();
  const navigate = Route.useNavigate();
  const { redirect } = Route.useSearch();
  const [matriculaFuncional, setMatriculaFuncional] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const loginMutation = useMutation({
    mutationFn: loginWithMatricula,
    retry: false,
    onSuccess: async (session) => {
      queryClient.setQueryData(authQueryKeys.me, session);
      // Trusted redirects win; otherwise fall back to the papel-derived home, including /unknown-role.
      await navigate({
        href: safeInternalRedirectPath(redirect) ?? homePathForPapel(session.papel),
        search: { redirect: undefined },
      });
    },
    onError: (error) => {
      if (error instanceof ApiError) {
        setErrorMessage(error.payload?.error.message || error.message);
        return;
      }

      setErrorMessage("Não foi possível entrar. Tente novamente.");
    },
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    loginMutation.mutate({
      matricula_funcional: matriculaFuncional,
      password,
    });
  }

  return (
    <FeaturePlaceholder
      kicker="Auth shell"
      title="Entrar no piloto"
      summary="Autenticação por sessão Django + CSRF. A matrícula funcional identifica o usuário e o papel operacional principal define a home inicial."
      nextSlice="#37 — login e bootstrap de sessão em execução"
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
        <form className="preview-panel space-y-4" onSubmit={handleSubmit}>
          {errorMessage ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
              {errorMessage}
            </div>
          ) : null}
          <label className="preview-label">
            Matrícula funcional
            <input
              className="preview-input"
              autoComplete="username"
              name="matricula_funcional"
              onChange={(event) => setMatriculaFuncional(event.target.value)}
              required
              value={matriculaFuncional}
            />
          </label>
          <label className="preview-label">
            Senha
            <input
              className="preview-input"
              autoComplete="current-password"
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          <button className="preview-button" disabled={loginMutation.isPending} type="submit">
            {loginMutation.isPending ? "Entrando..." : "Entrar"}
          </button>
        </form>
      }
    />
  );
}
