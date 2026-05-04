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
          <p className="eyebrow">Issue #36 concluída</p>
          <h3 className="mt-3 font-title text-4xl leading-none tracking-[-0.04em]">
            Shell editorial, contrato vivo, zero fluxo implícito
          </h3>
          <p className="mt-4 max-w-[58ch] text-base leading-7 text-[var(--ink-soft)]">
            Esta base existe para reduzir atrito nas próximas fatias. O frontend já sobe com
            Router file-based, Query provider, client tipado e superfícies canônicas nomeadas com o
            vocabulário do projeto.
          </p>
        </article>

        <article className="glass-inset p-6">
          <p className="eyebrow">Comandos oficiais</p>
          <ul className="mt-4 space-y-3 font-mono text-sm text-[var(--ink-soft)]">
            <li>`rtk make frontend-init`</li>
            <li>`rtk make frontend-gen-api`</li>
            <li>`rtk make frontend-dev`</li>
            <li>`rtk make frontend-build`</li>
            <li>`rtk make frontend-test`</li>
          </ul>
        </article>
      </div>

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {navigationItems
          .filter((item) => item.to !== "/")
          .map((item) => {
            const linkProps = item.params ? { to: item.to, params: item.params } : { to: item.to };
            const cardContent = (
              <>
                <p className="eyebrow">{item.tag}</p>
                <h4 className="mt-3 font-title text-2xl leading-none tracking-[-0.03em]">
                  {item.label}
                </h4>
                <p className="mt-4 text-sm leading-6 text-[var(--ink-soft)]">
                  Placeholder navegável. Mantém rota, vocabulário e contexto prontos para a
                  próxima fatia.
                </p>
                <span className="mt-5 inline-flex w-fit rounded-full border border-[var(--line-soft)] px-3 py-1 text-xs uppercase tracking-[0.22em] text-[var(--ink-muted)]">
                  {item.hint}
                </span>
              </>
            );

            return (
              <Link key={item.label} {...linkProps} className="route-card">
                {cardContent}
              </Link>
            );
          })}
      </div>
    </section>
  );
}
