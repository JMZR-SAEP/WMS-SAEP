import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

import saepLogoUrl from "../assets/saep-logo.svg";
import {
  ApiError,
  authQueryKeys,
  homePathForPapel,
  loginWithMatricula,
} from "../features/auth/session";

function safeInternalRedirectPath(redirect: string | undefined) {
  if (!redirect || redirect.startsWith("//")) {
    return undefined;
  }

  try {
    const url = new URL(redirect, window.location.origin);

    if (url.origin !== window.location.origin || !url.pathname.startsWith("/")) {
      return undefined;
    }

    url.searchParams.delete("redirect");

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
    <section className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[minmax(0,1fr)_24rem] lg:items-start">
      <div className="glass-inset p-5 sm:p-6">
        <img className="brand-logo" src={saepLogoUrl} alt="SAEP" />
        <p className="eyebrow mt-6">Acesso ao piloto</p>
        <h3 className="mt-3 text-3xl font-bold leading-tight">Entrar no piloto</h3>
        <p className="mt-4 max-w-[58ch] text-base leading-7 text-[var(--ink-soft)]">
          Use sua matrícula funcional para acessar as filas e ações disponíveis ao seu papel.
        </p>
      </div>

      <aside className="glass-inset p-5">
        <p className="eyebrow">Identificação</p>
        <form className="preview-panel mt-4 space-y-4" onSubmit={handleSubmit}>
          {errorMessage ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
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
      </aside>
    </section>
  );
}
