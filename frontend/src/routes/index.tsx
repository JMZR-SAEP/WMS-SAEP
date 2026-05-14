import { Link, createFileRoute, redirect } from "@tanstack/react-router";

import { requireSession } from "../features/auth/guards";
import { homePathForPapel } from "../features/auth/session";
import { navigationItems } from "../shared/config/navigation";

export const Route = createFileRoute("/")({
  beforeLoad: async ({ context, location }) => {
    const session = await requireSession({
      queryClient: context.queryClient,
      locationHref: location.href,
    });

    // eslint-disable-next-line @typescript-eslint/only-throw-error
    throw redirect({ to: homePathForPapel(session.papel) });
  },
  component: HomePage,
});

function HomePage() {
  return (
    <section className="space-y-8">
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_340px]">
        <article className="glass-inset p-6">
          <p className="eyebrow">Piloto SAEP</p>
          <h3 className="mt-3 text-3xl font-bold leading-tight">
            Operação do almoxarifado
          </h3>
          <p className="mt-4 max-w-[58ch] text-base leading-7 text-[var(--ink-soft)]">
            Acesse as filas e ações disponíveis ao seu papel para acompanhar requisições,
            autorizações e atendimentos.
          </p>
        </article>

        <article className="glass-inset p-6">
          <p className="eyebrow">Orientação</p>
          <ul className="mt-4 space-y-3 text-sm text-[var(--ink-soft)]">
            <li>Use o menu lateral para navegar entre listas de trabalho.</li>
            <li>A home inicial é definida pelo papel operacional da sessão.</li>
            <li>Em caso de bloqueio, confirme cadastro e permissões com o administrador.</li>
          </ul>
        </article>
      </div>

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {navigationItems.map((item) => (
          <Link key={item.label} to={item.to} className="route-card">
            <h4 className="text-2xl font-bold leading-tight">{item.label}</h4>
            <p className="mt-4 text-sm leading-6 text-[var(--ink-soft)]">
              Abra esta área para trabalhar com as permissões disponíveis ao seu papel.
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}
