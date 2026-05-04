import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useLocation, useNavigate } from "@tanstack/react-router";

import { ApiError, authQueryKeys, logoutSession, meQueryOptions } from "../../features/auth/session";
import { navigationItems } from "../../shared/config/navigation";

function messageFromLogoutError(error: unknown) {
  if (error instanceof ApiError) {
    return error.payload?.error.message || error.message;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Não foi possível sair. Tente novamente.";
}

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sessionQuery = useQuery(meQueryOptions);
  const session = sessionQuery.data;
  const logoutMutation = useMutation({
    mutationFn: logoutSession,
    retry: false,
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: authQueryKeys.me });
      await navigate({ to: "/login", search: { redirect: undefined } });
    },
  });

  return (
    <div className="min-h-screen bg-[var(--page-bg)] text-[var(--ink-strong)]">
      <div className="mx-auto flex min-h-screen max-w-[1440px] flex-col px-4 py-4 lg:flex-row lg:px-6">
        <aside className="glass-panel mb-4 w-full shrink-0 overflow-hidden lg:mb-0 lg:w-[320px]">
          <div className="border-b border-[var(--line-soft)] px-6 py-5">
            <p className="eyebrow">Scaffold</p>
            <h1 className="mt-3 font-title text-3xl leading-none tracking-[-0.03em]">
              SPA do piloto
            </h1>
            <p className="mt-3 max-w-[28ch] text-sm text-[var(--ink-soft)]">
              Base operacional do piloto, sem fluxos reais ainda. Backend segue dono de domínio,
              sessão, autorização e contratos.
            </p>
          </div>

          <nav className="space-y-2 px-4 py-4">
            {navigationItems.map((item) => {
              const active = item.matches(location.pathname);
              const className = active ? "nav-link nav-link-active" : "nav-link nav-link-idle";
              const linkProps = item.params ? { to: item.to, params: item.params } : { to: item.to };
              const navContent = (
                <>
                  <div>
                    <p className="text-[0.68rem] uppercase tracking-[0.28em] text-[var(--ink-muted)]">
                      {item.tag}
                    </p>
                    <p className="mt-1 text-base font-semibold text-[var(--ink-strong)]">
                      {item.label}
                    </p>
                  </div>
                  <span className="text-sm text-[var(--ink-soft)]">{item.hint}</span>
                </>
              );

              return (
                <Link key={item.label} {...linkProps} className={className}>
                  {navContent}
                </Link>
              );
            })}
          </nav>

          <div className="border-t border-[var(--line-soft)] px-6 py-5">
            {session ? (
              <div className="space-y-3">
                <p className="text-xs uppercase tracking-[0.28em] text-[var(--ink-muted)]">
                  Sessão atual
                </p>
                <div>
                  <p className="text-sm font-semibold text-[var(--ink-strong)]">
                    {session.nome_completo}
                  </p>
                  <p className="mt-1 text-xs uppercase tracking-[0.18em] text-[var(--ink-muted)]">
                    {session.papel}
                  </p>
                  {session.setor ? (
                    <p className="mt-2 text-sm text-[var(--ink-soft)]">{session.setor.nome}</p>
                  ) : null}
                </div>
                <button
                  className="preview-button w-full"
                  disabled={logoutMutation.isPending}
                  onClick={() => logoutMutation.mutate()}
                  type="button"
                >
                  {logoutMutation.isPending ? "Saindo..." : "Sair"}
                </button>
                {logoutMutation.isError ? (
                  <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
                    {messageFromLogoutError(logoutMutation.error)}
                  </p>
                ) : null}
              </div>
            ) : (
              <>
                <p className="text-xs uppercase tracking-[0.28em] text-[var(--ink-muted)]">
                  Bloco 0 consumido
                </p>
                <ul className="mt-3 space-y-2 text-sm text-[var(--ink-soft)]">
                  <li>`auth/csrf` `auth/login` `auth/logout` `auth/me`</li>
                  <li>`users/beneficiary-lookup`</li>
                  <li>`requisitions list/detail` + `draft update`</li>
                </ul>
              </>
            )}
          </div>
        </aside>

        <main className="flex-1 lg:pl-6">
          <div className="glass-panel min-h-full overflow-hidden">
            <div className="border-b border-[var(--line-soft)] px-6 py-5">
              <p className="eyebrow">Pilot SPA shell</p>
              <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <h2 className="font-title text-3xl tracking-[-0.03em] text-[var(--ink-strong)]">
                    Repositório pronto para próximas fatias
                  </h2>
                  <p className="mt-2 max-w-[52ch] text-sm text-[var(--ink-soft)]">
                    Router file-based, Query provider, client OpenAPI, smoke tests e comandos
                    operacionais já conectados ao `Makefile`.
                  </p>
                </div>
                <div className="status-chip">
                  <span className="status-dot" />
                  Fundação entregue
                </div>
              </div>
            </div>

            <div className="p-6">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
