import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  SLA_ATENCAO_MINUTES,
  SLA_ATRASADA_MINUTES,
  calcSlaStatus,
  slaLabel,
} from "../features/requisitions/sla";

const MINUTE_MS = 60_000;

function minutesAgo(minutes: number): string {
  return new Date(Date.now() - minutes * MINUTE_MS).toISOString();
}

describe("calcSlaStatus", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns null for null input", () => {
    expect(calcSlaStatus(null)).toBeNull();
  });

  it("returns null for invalid date string", () => {
    expect(calcSlaStatus("not-a-date")).toBeNull();
  });

  it("returns 'normal' when elapsed < atencao threshold", () => {
    expect(calcSlaStatus(minutesAgo(SLA_ATENCAO_MINUTES - 1))).toBe("normal");
  });

  it("returns 'normal' when just sent (0 min elapsed)", () => {
    expect(calcSlaStatus(new Date().toISOString())).toBe("normal");
  });

  it("returns 'atencao' when elapsed equals atencao threshold", () => {
    expect(calcSlaStatus(minutesAgo(SLA_ATENCAO_MINUTES))).toBe("atencao");
  });

  it("returns 'atencao' when elapsed is between atencao and atrasada thresholds", () => {
    const midpoint = Math.floor((SLA_ATENCAO_MINUTES + SLA_ATRASADA_MINUTES) / 2);
    expect(calcSlaStatus(minutesAgo(midpoint))).toBe("atencao");
  });

  it("returns 'atencao' when elapsed is one minute before atrasada threshold", () => {
    expect(calcSlaStatus(minutesAgo(SLA_ATRASADA_MINUTES - 1))).toBe("atencao");
  });

  it("returns 'atrasada' when elapsed equals atrasada threshold", () => {
    expect(calcSlaStatus(minutesAgo(SLA_ATRASADA_MINUTES))).toBe("atrasada");
  });

  it("returns 'atrasada' when elapsed exceeds atrasada threshold", () => {
    expect(calcSlaStatus(minutesAgo(SLA_ATRASADA_MINUTES + 60))).toBe("atrasada");
  });
});

describe("slaLabel", () => {
  it("labels normal status", () => {
    expect(slaLabel("normal")).toBe("No prazo");
  });

  it("labels atencao status", () => {
    expect(slaLabel("atencao")).toBe("Atenção");
  });

  it("labels atrasada status", () => {
    expect(slaLabel("atrasada")).toBe("Atrasada");
  });
});
