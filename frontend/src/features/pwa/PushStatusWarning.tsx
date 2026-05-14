import { Link } from "@tanstack/react-router";

import type { PushDiagnostic } from "./push";

export function PushStatusWarning({ diagnostic }: { diagnostic: PushDiagnostic }) {
  if (diagnostic.status === "ativo") {
    return null;
  }

  return (
    <div className="push-warning" role="status">
      <p className="text-xs font-bold uppercase text-[var(--warning)]">
        Alertas sem suporte
      </p>
      <p className="text-xs text-[var(--ink-soft)]">
        Use Chrome Android ou Safari iOS com PWA instalado.
      </p>
      <Link className="notification-link text-xs" to="/alertas">
        Ver diagnóstico
      </Link>
    </div>
  );
}
