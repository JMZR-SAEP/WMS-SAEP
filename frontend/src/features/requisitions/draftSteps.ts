import { z } from "zod";

export const draftStepSchema = z.enum(["beneficiario", "itens", "revisao", "envio"]);
export type DraftStep = z.infer<typeof draftStepSchema>;
