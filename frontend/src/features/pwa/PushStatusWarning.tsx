import { Link } from "@tanstack/react-router";

import type { PushDiagnostic } from "./push";

export function PushStatusWarning({ diagnostic }: { diagnostic: PushDiagnostic }) {
  if (diagnostic.status === "ativo") {
    return null;
  }

  return (
    <div className="push-warning" role="status">
      <div>
        <p className="text-xs font-bold uppercase text-[var(--warning)]">
          Alertas: {diagnostic.label}
        </p>
        <p className="mt-1 text-sm text-[var(--ink-soft)]">{diagnostic.nextAction}</p>
      </div>
      <Link className="notification-link" to="/alertas">
        Ver diagnóstico
      </Link>
    </div>
  );
}
