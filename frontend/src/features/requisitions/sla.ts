export type SlaStatus = "normal" | "atencao" | "atrasada";

export const SLA_ATENCAO_MINUTES = 90;
export const SLA_ATRASADA_MINUTES = 240;

export function calcSlaStatus(dataEnvio: string | null): SlaStatus | null {
  if (!dataEnvio) return null;
  const sent = new Date(dataEnvio);
  if (isNaN(sent.getTime())) return null;
  const elapsed = (Date.now() - sent.getTime()) / 60_000;
  if (elapsed < SLA_ATENCAO_MINUTES) return "normal";
  if (elapsed < SLA_ATRASADA_MINUTES) return "atencao";
  return "atrasada";
}

export function slaLabel(status: SlaStatus): string {
  if (status === "normal") return "No prazo";
  if (status === "atencao") return "Atenção";
  return "Atrasada";
}
