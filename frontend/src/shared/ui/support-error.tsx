import { useEffect, useState } from "react";

import { queryErrorMessage, supportDetailsFromError } from "../api/errors";

type SupportErrorPanelProps = {
  error: unknown;
  fallback: string;
  onRetry?: () => void;
  retryLabel?: string;
};

export function SupportErrorPanel({
  error,
  fallback,
  onRetry,
  retryLabel,
}: SupportErrorPanelProps) {
  const [copyFeedback, setCopyFeedback] = useState("");
  const supportDetails = supportDetailsFromError(error);
  const canCopySupportDetails = Boolean(
    supportDetails &&
      navigator.clipboard &&
      typeof navigator.clipboard.writeText === "function",
  );

  useEffect(() => {
    let isCurrent = true;

    queueMicrotask(() => {
      if (isCurrent) {
        setCopyFeedback("");
      }
    });

    return () => {
      isCurrent = false;
    };
  }, [supportDetails]);

  async function copySupportDetails() {
    if (!supportDetails || !canCopySupportDetails) {
      setCopyFeedback("Copie os detalhes manualmente.");
      return;
    }

    try {
      await navigator.clipboard.writeText(supportDetails);
      setCopyFeedback("Detalhes copiados.");
    } catch (copyError) {
      console.error("Não foi possível copiar detalhes para suporte.", copyError);
      setCopyFeedback("Não foi possível copiar.");
    }
  }

  return (
    <div className="error-panel compact-error detail-error-state" role="alert">
      <p>{queryErrorMessage(error, fallback)}</p>
      <div className="detail-error-actions">
        {onRetry ? (
          <button className="action-link compact-action" onClick={onRetry} type="button">
            {retryLabel ?? "Tentar novamente"}
          </button>
        ) : null}
        {canCopySupportDetails ? (
          <button
            className="action-link compact-action"
            onClick={() => void copySupportDetails()}
            type="button"
          >
            Copiar detalhes para suporte
          </button>
        ) : null}
      </div>
      {supportDetails && !canCopySupportDetails ? (
        <p className="helper-text">
          Copie estes detalhes para suporte: <code>{supportDetails}</code>
        </p>
      ) : null}
      {copyFeedback ? (
        <p aria-live="polite" className="helper-text" role="status">
          {copyFeedback}
        </p>
      ) : null}
    </div>
  );
}
