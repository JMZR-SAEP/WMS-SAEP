import { createFileRoute } from "@tanstack/react-router";

import { requireSession } from "../features/auth/guards";

export const Route = createFileRoute("/unknown-role")({
  beforeLoad: ({ context, location }) =>
    requireSession({
      queryClient: context.queryClient,
      locationHref: location.href,
    }),
  component: UnknownRolePage,
});

function UnknownRolePage() {
  return (
    <section className="glass-inset space-y-4 p-6">
      <p className="eyebrow">Sessão sem home operacional</p>
      <h3 className="font-title text-4xl leading-none tracking-[-0.04em]">
        Papel operacional não mapeado
      </h3>
      <p className="max-w-[58ch] text-base leading-7 text-[var(--ink-soft)]">
        Sua sessão está ativa, mas o papel recebido ainda não tem uma rota inicial no piloto.
        Peça ao administrador para revisar o cadastro ou alinhar o novo papel ao frontend.
      </p>
    </section>
  );
}
