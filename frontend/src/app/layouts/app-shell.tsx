import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useLocation, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import saepLogoUrl from "../../assets/saep-logo.webp";
import { authQueryKeys, logoutSession, meQueryOptions } from "../../features/auth/session";
import {
  formatNotificationDate,
  markNotificationRead,
  notificationListQueryOptions,
  notificationOperationalContext,
  notificationOperationalLabel,
  notificationUnreadCountQueryOptions,
  notificationsQueryKeys,
} from "../../features/notifications/notifications";
import {
  getPushDiagnostic,
  hasSeenPushOnboarding,
  isPushOnboardingPapel,
  pushConfigQueryOptions,
  reportBadgeUnavailableIfNeeded,
  reportPushDiagnosticIfNeeded,
  updateAppBadge,
} from "../../features/pwa/push";
import { PushStatusWarning } from "../../features/pwa/PushStatusWarning";
import { pendingApprovalsQueryOptions } from "../../features/requisitions/requisitions";
import { navigationItems } from "../../shared/config/navigation";
import { SupportErrorPanel } from "../../shared/ui/support-error";

const PAPEL_LABEL: Record<string, string> = {
  solicitante: "Solicitante",
  auxiliar_setor: "Auxiliar de setor",
  chefe_setor: "Chefe de setor",
  auxiliar_almoxarifado: "Auxiliar de almoxarifado",
  chefe_almoxarifado: "Chefe de almoxarifado",
};

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sessionQuery = useQuery(meQueryOptions);
  const session = sessionQuery.data;
  const pushRole = Boolean(session && isPushOnboardingPapel(session.papel));
  const pushConfigQuery = useQuery({
    ...pushConfigQueryOptions,
    enabled: pushRole,
  });
  const pendingApprovalsBadgeQuery = useQuery({
    ...pendingApprovalsQueryOptions({ page: 1, pageSize: 1 }),
    enabled: pushRole && location.pathname !== "/alertas",
    refetchInterval: 60_000,
  });
  const logoutMutation = useMutation({
    mutationFn: logoutSession,
    retry: false,
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: authQueryKeys.me });
      queryClient.removeQueries({ queryKey: notificationsQueryKeys.all });
      await navigate({ to: "/login", search: { redirect: undefined } });
    },
  });
  const notificationsQuery = useQuery({
    ...notificationListQueryOptions({ page: 1, pageSize: 6 }),
    enabled: Boolean(session),
  });
  const unreadCountQuery = useQuery({
    ...notificationUnreadCountQueryOptions,
    enabled: Boolean(session),
  });
  const markReadMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: notificationsQueryKeys.all }),
        queryClient.invalidateQueries({ queryKey: notificationsQueryKeys.unreadCount }),
      ]);
    },
  });
  const notifications = notificationsQuery.data?.results ?? [];
  const unreadCount = unreadCountQuery.data?.unread_count ?? 0;
  const pushDiagnostic =
    pushRole && pushConfigQuery.isSuccess ? getPushDiagnostic(pushConfigQuery.data) : null;
  const pushUnsupported = pushDiagnostic?.status === "sem_suporte";
  const [notificationsOpen, setNotificationsOpen] = useState(true);

  useEffect(() => {
    if (
      session &&
      isPushOnboardingPapel(session.papel) &&
      location.pathname !== "/alertas" &&
      !hasSeenPushOnboarding(session)
    ) {
      void navigate({ to: "/alertas" });
    }
  }, [location.pathname, navigate, session]);

  useEffect(() => {
    if (!session || !pushDiagnostic || pushDiagnostic.status === "ativo") {
      return;
    }

    void reportPushDiagnosticIfNeeded(session, pushDiagnostic).catch(() => undefined);
  }, [pushDiagnostic, session]);

  useEffect(() => {
    if (!session || !pushRole || !pendingApprovalsBadgeQuery.isSuccess) {
      return;
    }

    void updateAppBadge(pendingApprovalsBadgeQuery.data.count)
      .then((updated) => {
        if (!updated) {
          void reportBadgeUnavailableIfNeeded(session).catch(() => undefined);
        }
        return undefined;
      })
      .catch(() => {
        void reportBadgeUnavailableIfNeeded(session).catch(() => undefined);
      });
  }, [
    pendingApprovalsBadgeQuery.data?.count,
    pendingApprovalsBadgeQuery.isSuccess,
    pushRole,
    session,
  ]);

  if (location.pathname === "/login") {
    return (
      <div className="min-h-screen bg-[var(--page-bg)] px-3 py-3 text-[var(--ink-strong)] sm:px-6 sm:py-6">
        <main className="mx-auto w-full max-w-5xl">
          <Outlet />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--page-bg)] text-[var(--ink-strong)]">
      <div className="mx-auto flex min-h-screen max-w-[1440px] flex-col gap-4 px-3 py-3 sm:px-4 lg:flex-row lg:px-6">
        <aside className="glass-panel mb-4 w-full shrink-0 overflow-hidden lg:mb-0 lg:w-[320px]">
          <div className="border-b border-[var(--line-soft)] px-4 py-3 sm:px-6 sm:py-5">
            <img className="brand-logo" src={saepLogoUrl} alt="SAEP" />
            <h1 className="mt-3 text-xl font-bold leading-tight sm:text-2xl">WMS-SAEP</h1>
            <p className="mt-1 hidden max-w-[30ch] text-sm text-[var(--ink-soft)] sm:block">
              Almoxarifado do piloto para requisições, autorizações e atendimento.
            </p>
          </div>

          <nav className="space-y-1 px-3 py-3 sm:px-4" aria-label="Navegação principal">
            {navigationItems
              .filter((item) => {
                if (item.visibleFor && !(session && item.visibleFor.includes(session.papel))) {
                  return false;
                }
                if (item.to === "/alertas" && pushUnsupported) {
                  return false;
                }
                return true;
              })
              .map((item) => {
                const active = item.matches(location.pathname);
                const className = active ? "nav-link nav-link-active" : "nav-link nav-link-idle";
                return (
                  <Link
                    key={item.label}
                    to={item.to}
                    className={className}
                    aria-current={active ? "page" : undefined}
                  >
                    <span className="text-sm font-semibold text-[var(--ink-strong)]">
                      {item.label}
                    </span>
                  </Link>
                );
              })}
          </nav>

          <div className="border-t border-[var(--line-soft)] px-3 py-3 sm:px-4 sm:py-4">
            {session ? (
              <div className="space-y-3">
                {pushDiagnostic ? <PushStatusWarning diagnostic={pushDiagnostic} /> : null}
                <div className="notifications-panel">
                  <button
                    aria-expanded={notificationsOpen}
                    className="notifications-header"
                    onClick={() => setNotificationsOpen((o) => !o)}
                    type="button"
                  >
                    <p className="notifications-header-label text-xs font-bold uppercase text-[var(--ink-muted)]">
                      Notificações
                    </p>
                    <div className="flex items-center gap-2">
                      <span className="notifications-count">{unreadCount}</span>
                      <svg
                        aria-hidden="true"
                        className={notificationsOpen ? "notifications-chevron open" : "notifications-chevron"}
                        fill="none"
                        height="12"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        viewBox="0 0 12 12"
                        width="12"
                      >
                        <path d="M2 4l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                  </button>

                  {notificationsOpen ? (
                    <div className="mt-2">
                      {notificationsQuery.isLoading || unreadCountQuery.isLoading ? (
                        <p className="notifications-empty">Carregando notificações...</p>
                      ) : null}

                      {notificationsQuery.isError || unreadCountQuery.isError ? (
                        <SupportErrorPanel
                          error={notificationsQuery.error ?? unreadCountQuery.error}
                          fallback="Não foi possível carregar notificações."
                        />
                      ) : null}

                      {!notificationsQuery.isLoading &&
                      !unreadCountQuery.isLoading &&
                      !notificationsQuery.isError &&
                      !unreadCountQuery.isError &&
                      notifications.length === 0 ? (
                        <p className="notifications-empty">Sem notificações no momento.</p>
                      ) : null}

                      {!notificationsQuery.isLoading &&
                      !unreadCountQuery.isLoading &&
                      !notificationsQuery.isError &&
                      !unreadCountQuery.isError &&
                      notifications.length > 0 ? (
                        <ul className="notifications-list">
                          {notifications.map((notification) => {
                            const relatedObject = notification.objeto_relacionado;
                            const context = notificationOperationalContext(notification.tipo);
                            const contextLabel = notificationOperationalLabel(notification.tipo);

                            return (
                              <li className="notification-item" key={notification.id}>
                                <div className="notification-meta">
                                  <strong>{notification.titulo}</strong>
                                  <span>{formatNotificationDate(notification.created_at)}</span>
                                </div>
                                <p className="notification-message">{notification.mensagem}</p>

                                {notification.destino.tipo === "papel" ? (
                                  <span className="notification-badge">Aviso coletivo</span>
                                ) : null}

                                {relatedObject?.tipo === "requisicao" ? (
                                  <div className="notification-links">
                                    <Link
                                      className="notification-link"
                                      params={{ id: String(relatedObject.id) }}
                                      search={
                                        context
                                          ? {
                                              contexto: context,
                                            }
                                          : undefined
                                      }
                                      to="/requisicoes/$id"
                                    >
                                      Abrir requisição
                                    </Link>
                                    {contextLabel ? (
                                      <span className="notification-context">{contextLabel}</span>
                                    ) : null}
                                  </div>
                                ) : null}

                                {notification.leitura_suportada && !notification.lida ? (
                                  <button
                                    className="notification-read-button"
                                    disabled={markReadMutation.isPending}
                                    onClick={() => {
                                      markReadMutation.reset();
                                      markReadMutation.mutate(notification.id);
                                    }}
                                    type="button"
                                  >
                                    Marcar como lida
                                  </button>
                                ) : null}
                              </li>
                            );
                          })}
                        </ul>
                      ) : null}

                      {markReadMutation.isError ? (
                        <SupportErrorPanel
                          error={markReadMutation.error}
                          fallback="Não foi possível marcar notificação como lida."
                        />
                      ) : null}
                    </div>
                  ) : null}
                </div>
                <div className="session-footer">
                  <div>
                    <p className="text-xs font-bold uppercase text-[var(--ink-muted)]">
                      Sessão atual
                    </p>
                    <p className="mt-1 text-sm font-semibold text-[var(--ink-strong)]">
                      {session.nome_completo}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-1">
                      <span className="session-role-badge">
                        {PAPEL_LABEL[session.papel] ?? session.papel}
                      </span>
                      {session.setor ? (
                        <span className="text-xs text-[var(--ink-muted)]">{session.setor.nome}</span>
                      ) : null}
                    </div>
                  </div>
                  <button
                    className="sidebar-logout"
                    disabled={logoutMutation.isPending}
                    onClick={() => logoutMutation.mutate()}
                    type="button"
                  >
                    {logoutMutation.isPending ? "Saindo..." : "Sair"}
                  </button>
                  {logoutMutation.isError ? (
                    <SupportErrorPanel
                      error={logoutMutation.error}
                      fallback="Não foi possível sair. Tente novamente."
                    />
                  ) : null}
                </div>
              </div>
            ) : (
              <>
                <p className="text-xs font-bold uppercase text-[var(--ink-muted)]">
                  Acesso operacional
                </p>
                <ul className="mt-3 space-y-2 text-sm text-[var(--ink-soft)]">
                  <li>Entre com matrícula funcional e senha.</li>
                  <li>O menu é ajustado pelo papel operacional da sessão.</li>
                </ul>
              </>
            )}
          </div>
        </aside>

        <main className="flex-1">
          <div className="glass-panel min-h-full overflow-hidden">
            <div className="border-b border-[var(--line-soft)] px-4 py-5 sm:px-6">
              <p className="eyebrow">Piloto operacional</p>
              <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <h2 className="text-2xl font-bold leading-tight text-[var(--ink-strong)]">
                    Requisições de materiais
                  </h2>
                  <p className="mt-2 max-w-[52ch] text-sm text-[var(--ink-soft)]">
                    Use as filas do seu papel para criar, autorizar ou atender requisições.
                  </p>
                </div>
                <div className="status-chip">
                  <span className="status-dot" />
                  Tema SAEP
                </div>
              </div>
            </div>

            <div className="p-4 sm:p-6">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
