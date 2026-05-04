import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";

type FeaturePlaceholderProps = {
  kicker: string;
  title: string;
  summary: string;
  nextSlice: string;
  contracts: string[];
  bullets: string[];
  preview?: ReactNode;
};

export function FeaturePlaceholder({
  kicker,
  title,
  summary,
  nextSlice,
  contracts,
  bullets,
  preview,
}: FeaturePlaceholderProps) {
  return (
    <section className="grid gap-5 lg:grid-cols-[minmax(0,1.2fr)_340px]">
      <div className="space-y-5">
        <div>
          <p className="eyebrow">{kicker}</p>
          <h3 className="mt-3 font-title text-4xl leading-none tracking-[-0.04em]">{title}</h3>
          <p className="mt-4 max-w-[58ch] text-base leading-7 text-[var(--ink-soft)]">
            {summary}
          </p>
        </div>

        <div className="glass-inset p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="eyebrow">Próxima slice</p>
              <p className="mt-2 text-lg font-semibold text-[var(--ink-strong)]">{nextSlice}</p>
            </div>
            <Link to="/" className="action-link">
              Voltar ao mapa
            </Link>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <article className="glass-inset p-5">
            <p className="eyebrow">Contrato backend</p>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-[var(--ink-soft)]">
              {contracts.map((contract) => (
                <li key={contract} className="border-l border-[var(--line-strong)] pl-3">
                  {contract}
                </li>
              ))}
            </ul>
          </article>

          <article className="glass-inset p-5">
            <p className="eyebrow">Meta da UI</p>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-[var(--ink-soft)]">
              {bullets.map((bullet) => (
                <li key={bullet} className="border-l border-[var(--line-strong)] pl-3">
                  {bullet}
                </li>
              ))}
            </ul>
          </article>
        </div>
      </div>

      <aside className="glass-inset overflow-hidden p-5">
        <p className="eyebrow">Preview scaffold</p>
        <div className="mt-4">{preview}</div>
      </aside>
    </section>
  );
}
