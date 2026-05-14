import { z } from "zod";

import type { AuthSession } from "../auth/session";

export const draftStepSchema = z.enum(["beneficiario", "itens", "revisao", "envio"]);
export type DraftStep = z.infer<typeof draftStepSchema>;

export function canRequestForThirdParty(session: AuthSession) {
  return session.papel !== "solicitante";
}
