import { useMutation, useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect } from "react";

import { requireOperationalPapel } from "../features/auth/guards";
import { ApiError, meQueryOptions } from "../features/auth/session";
import {
  isPushSupported,
  markPushOnboardingSeen,
  pushConfigQueryOptions,
  registerPushSubscription,
} from "../features/pwa/push";

export const Route = createFileRoute("/alertas")({
  beforeLoad: async ({ context, location }) => {
    await requireOperationalPapel({
      allowedPapeis: ["chefe_setor", "chefe_almoxarifado"],
      queryClient: context.queryClient,
      locationHref: location.href,
    });
  },
  component: AlertasPage,
});

function messageFromError(error: unknown) {
  if (error instanceof ApiError) {
    return error.payload?.error.message || error.message;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Não foi possível configurar alertas.";
}

function AlertasPage() {
  const sessionQuery = useQuery(meQueryOptions);
  const pushConfigQuery = useQuery(pushConfigQueryOptions);
  const publicKey = pushConfigQuery.data?.vapid_public_key ?? "";
  const pushConfigReady = pushConfigQuery.isSuccess && Boolean(pushConfigQuery.data?.enabled);
  const pushMutation = useMutation({
    mutationFn: async () => {
      if (!publicKey) {
        throw new Error("Servidor de push não configurado.");
      }

      return registerPushSubscription(publicKey);
    },
  });
  const serverEnabled = pushConfigReady;
  const browserSupported = isPushSupported();
  const canActivate = pushConfigReady && browserSupported && !pushMutation.isPending;

  useEffect(() => {
    if (sessionQuery.data) {
      markPushOnboardingSeen(sessionQuery.data);
    }
  }, [sessionQuery.data]);

  return (
    <section className="space-y-5">
      <div className="glass-inset p-5 sm:p-6">
        <p className="eyebrow">Alertas do chefe</p>
        <h3 className="mt-3 text-3xl font-bold leading-tight">Alertas de autorização</h3>
        <p className="mt-4 max-w-[62ch] text-sm leading-6 text-[var(--ink-soft)]">
          Ative notificações neste navegador para receber novas requisições aguardando
          autorização. O alerta mostra apenas o beneficiário e abre o detalhe em contexto
          de autorização.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <article className="detail-panel">
          <p className="eyebrow">Estado</p>
          <h4 className="mt-3 text-xl font-bold">Diagnóstico de push</h4>

          {pushConfigQuery.isLoading ? (
            <p className="mt-4 text-sm text-[var(--ink-soft)]">Carregando configuração...</p>
          ) : null}

          {pushConfigQuery.isError ? (
            <p className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
              {messageFromError(pushConfigQuery.error)}
            </p>
          ) : null}

          {pushConfigQuery.isSuccess ? (
            <dl className="mt-4 grid gap-3 text-sm">
              <div className="notification-item">
                <dt className="font-bold text-[var(--ink-strong)]">Servidor</dt>
                <dd className="mt-1 text-[var(--ink-soft)]">
                  {serverEnabled ? "Push disponível" : "Push não configurado"}
                </dd>
              </div>
              <div className="notification-item">
                <dt className="font-bold text-[var(--ink-strong)]">Navegador</dt>
                <dd className="mt-1 text-[var(--ink-soft)]">
                  {browserSupported ? "Suporte detectado" : "Sem suporte a Web Push"}
                </dd>
              </div>
            </dl>
          ) : null}

          <button
            className="preview-button mt-5"
            disabled={!canActivate}
            onClick={() => pushMutation.mutate()}
            type="button"
          >
            {pushMutation.isPending ? "Ativando..." : "Ativar alertas neste navegador"}
          </button>

          {pushMutation.isSuccess ? (
            <p className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
              Alertas ativos neste navegador.
            </p>
          ) : null}

          {pushMutation.isError ? (
            <p className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
              {messageFromError(pushMutation.error)}
            </p>
          ) : null}
        </article>

        <aside className="detail-panel">
          <p className="eyebrow">Privacidade</p>
          <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">
            A notificação não mostra materiais nem setor na tela bloqueada. Se negar a
            permissão, a fila continua disponível.
          </p>
        </aside>
      </div>
    </section>
  );
}
