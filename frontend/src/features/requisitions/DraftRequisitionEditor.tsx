import { useEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";

import { authQueryKeys, isAuthError, type AuthSession } from "../auth/session";
import {
  cancelDraftRequisition,
  createDraftRequisition,
  discardDraftRequisition,
  displayRequisitionIdentifier,
  draftBeneficiariesQueryOptions,
  draftMaterialsQueryOptions,
  formatQuantity,
  queryErrorMessage,
  requisitionsQueryKeys,
  statusLabel,
  submitDraftRequisition,
  updateDraftRequisition,
  type BeneficiaryLookupItem,
  type MaterialListItem,
  type RequisicaoDetail,
  type RequisicaoDraftInput,
} from "./requisitions";

type DraftItemForm = {
  materialId: string;
  materialLabel: string;
  materialCode: string;
  unidadeMedida: string;
  saldoDisponivel: number | null;
  quantidadeSolicitada: string;
  observacao: string;
};

type DraftFormValues = {
  beneficiaryMode: "self" | "third_party";
  beneficiaryId: string;
  beneficiaryLabel: string;
  beneficiarySearch: string;
  materialSearch: string;
  observacao: string;
  itens: DraftItemForm[];
};

const EMPTY_DRAFT_ITEMS: DraftItemForm[] = [];

type DraftRequisitionEditorProps = {
  initialRequisition?: RequisicaoDetail;
  session: AuthSession;
};

type ConfirmAction =
  | {
      type: "submit";
      values: DraftFormValues;
    }
  | {
      type: "discard" | "cancel";
    };

function currentUserBeneficiary(session: AuthSession) {
  return {
    id: session.id,
    nome_completo: session.nome_completo,
    matricula_funcional: session.matricula_funcional,
    setor: session.setor,
  };
}

function beneficiaryLabel(beneficiary: Pick<BeneficiaryLookupItem, "matricula_funcional" | "nome_completo">) {
  return `${beneficiary.nome_completo} (${beneficiary.matricula_funcional})`;
}

function materialLabel(material: MaterialListItem) {
  return `${material.codigo_completo} - ${material.nome}`;
}

function formValuesFromRequisition(
  requisition: RequisicaoDetail | undefined,
  session: AuthSession,
): DraftFormValues {
  const beneficiary = requisition?.beneficiario ?? currentUserBeneficiary(session);

  return {
    beneficiaryMode: beneficiary.id === session.id ? "self" : "third_party",
    beneficiaryId: String(beneficiary.id),
    beneficiaryLabel: beneficiaryLabel(beneficiary),
    beneficiarySearch: "",
    materialSearch: "",
    observacao: requisition?.observacao ?? "",
    itens:
      requisition?.itens.map((item) => ({
        materialId: String(item.material.id),
        materialLabel: materialLabel({
          id: item.material.id,
          codigo_completo: item.material.codigo_completo,
          nome: item.material.nome,
          descricao: "",
          unidade_medida: item.material.unidade_medida,
          saldo_disponivel: null,
        }),
        materialCode: item.material.codigo_completo,
        unidadeMedida: item.unidade_medida,
        saldoDisponivel: null,
        quantidadeSolicitada: item.quantidade_solicitada,
        observacao: item.observacao,
      })) ?? [],
  };
}

function canRequestForThirdParty(session: AuthSession) {
  return session.papel !== "solicitante";
}

function hasPositiveStock(material: MaterialListItem) {
  return material.saldo_disponivel !== null && material.saldo_disponivel > 0;
}

function normalizeQuantity(value: string) {
  return value.trim().replace(/,/g, ".");
}

function isPositiveQuantity(value: string) {
  const quantity = Number(normalizeQuantity(value));
  return Number.isFinite(quantity) && quantity > 0;
}

function selectedBeneficiary(values: DraftFormValues) {
  return Number.parseInt(values.beneficiaryId, 10);
}

function payloadFromValues(values: DraftFormValues): RequisicaoDraftInput {
  return {
    beneficiario_id: selectedBeneficiary(values),
    observacao: values.observacao.trim(),
    itens: values.itens.map((item) => ({
      material_id: Number.parseInt(item.materialId, 10),
      quantidade_solicitada: normalizeQuantity(item.quantidadeSolicitada),
      observacao: item.observacao.trim(),
    })),
  };
}

function mutationErrorMessage(error: unknown) {
  return queryErrorMessage(error, "Não foi possível concluir a ação.");
}

export function DraftRequisitionEditor({ initialRequisition, session }: DraftRequisitionEditorProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<ConfirmAction | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const cancelConfirmationButtonRef = useRef<HTMLButtonElement | null>(null);
  const pendingRef = useRef(false);
  const sessionSetorId = session.setor?.id ?? null;
  const sessionSetorNome = session.setor?.nome ?? null;
  const stableSession = useMemo(
    () =>
      ({
        id: session.id,
        matricula_funcional: session.matricula_funcional,
        nome_completo: session.nome_completo,
        papel: session.papel,
        setor: sessionSetorId !== null && sessionSetorNome !== null
          ? {
              id: sessionSetorId,
              nome: sessionSetorNome,
            }
          : null,
        is_authenticated: session.is_authenticated,
      }) satisfies AuthSession,
    [
      session.id,
      session.is_authenticated,
      session.matricula_funcional,
      session.nome_completo,
      session.papel,
      sessionSetorId,
      sessionSetorNome,
    ],
  );
  const form = useForm<DraftFormValues>({
    defaultValues: formValuesFromRequisition(initialRequisition, stableSession),
  });
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "itens",
  });
  const beneficiaryMode = useWatch({ control: form.control, name: "beneficiaryMode" }) ?? "self";
  const previousBeneficiaryModeRef = useRef(beneficiaryMode);
  const beneficiaryLabelValue = useWatch({ control: form.control, name: "beneficiaryLabel" });
  const beneficiarySearch =
    useWatch({ control: form.control, name: "beneficiarySearch" })?.trim() ?? "";
  const materialSearch = useWatch({ control: form.control, name: "materialSearch" })?.trim() ?? "";
  const selectedItems = useWatch({ control: form.control, name: "itens" }) ?? EMPTY_DRAFT_ITEMS;
  const isEdit = Boolean(initialRequisition);
  const title = isEdit ? "Editar rascunho" : "Nova requisição";
  const identifier = initialRequisition
    ? (displayRequisitionIdentifier(initialRequisition) ?? statusLabel(initialRequisition.status))
    : "Novo rascunho";
  const beneficiaryQuery = useQuery({
    ...draftBeneficiariesQueryOptions(beneficiarySearch),
    enabled:
      beneficiaryMode === "third_party" &&
      canRequestForThirdParty(stableSession) &&
      beneficiarySearch.length >= 3,
  });
  const materialsQuery = useQuery({
    ...draftMaterialsQueryOptions(materialSearch),
    enabled: materialSearch.length >= 2,
  });
  const resetIdentity = `${initialRequisition?.id ?? "new"}:${stableSession.id}`;
  const resetIdentityRef = useRef(resetIdentity);

  useEffect(() => {
    if (resetIdentityRef.current === resetIdentity) {
      return;
    }
    resetIdentityRef.current = resetIdentity;
    form.reset(formValuesFromRequisition(initialRequisition, stableSession));
  }, [form, initialRequisition, resetIdentity, stableSession]);

  useEffect(() => {
    if (!confirmAction) {
      return;
    }
    cancelConfirmationButtonRef.current?.focus();
  }, [confirmAction]);

  useEffect(() => {
    if (!confirmAction) {
      return undefined;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !pendingRef.current) {
        event.preventDefault();
        setConfirmAction(null);
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [confirmAction]);

  useEffect(() => {
    if (beneficiaryMode === "self") {
      const self = currentUserBeneficiary(stableSession);
      form.setValue("beneficiaryId", String(self.id));
      form.setValue("beneficiaryLabel", beneficiaryLabel(self));
    } else if (previousBeneficiaryModeRef.current === "self") {
      form.setValue("beneficiaryId", "");
      form.setValue("beneficiaryLabel", "");
    }
    previousBeneficiaryModeRef.current = beneficiaryMode;
  }, [beneficiaryMode, form, stableSession]);

  function afterMutationSuccess(requisition: RequisicaoDetail) {
    queryClient.setQueryData(requisitionsQueryKeys.detail(requisition.id), requisition);
    // Editor routes do not keep worklists mounted; inactive refetch avoids overwriting this detail cache.
    void queryClient.invalidateQueries({
      queryKey: requisitionsQueryKeys.all,
      refetchType: "inactive",
    });
  }

  function handleMutationError(error: unknown) {
    setConfirmAction(null);
    if (isAuthError(error)) {
      queryClient.removeQueries({ queryKey: authQueryKeys.me });
      void navigate({
        to: "/login",
        search: {
          redirect: isEdit && initialRequisition ? `/requisicoes/${initialRequisition.id}` : "/requisicoes/nova",
        },
      });
      return;
    }
    setFormError(mutationErrorMessage(error));
  }

  const saveMutation = useMutation({
    mutationFn: async (input: RequisicaoDraftInput) =>
      initialRequisition
        ? updateDraftRequisition(initialRequisition.id, input)
        : createDraftRequisition(input),
    onSuccess: async (requisition) => {
      setFormError(null);
      afterMutationSuccess(requisition);
      if (initialRequisition) {
        form.reset(formValuesFromRequisition(requisition, stableSession));
      }
      if (!initialRequisition) {
        await navigate({ to: "/requisicoes/$id", params: { id: String(requisition.id) } });
      }
    },
    onError: handleMutationError,
  });
  const submitMutation = useMutation({
    mutationFn: async (input: RequisicaoDraftInput) => {
      // Submit requires the latest draft persisted first; if submit fails, the saved draft remains retryable.
      const draft = initialRequisition
        ? await updateDraftRequisition(initialRequisition.id, input)
        : await createDraftRequisition(input);
      return submitDraftRequisition(draft.id);
    },
    onSuccess: async (requisition) => {
      setFormError(null);
      setConfirmAction(null);
      afterMutationSuccess(requisition);
      await navigate({ to: "/requisicoes/$id", params: { id: String(requisition.id) } });
    },
    onError: handleMutationError,
  });
  const discardMutation = useMutation<RequisicaoDetail | undefined, unknown, void>({
    mutationFn: async () => {
      if (!initialRequisition) {
        throw new Error("Rascunho ainda não salvo.");
      }
      if (initialRequisition.numero_publico) {
        return cancelDraftRequisition(initialRequisition.id);
      }
      await discardDraftRequisition(initialRequisition.id);
      return undefined;
    },
    onSuccess: async (requisition) => {
      setFormError(null);
      if (initialRequisition) {
        queryClient.removeQueries({
          queryKey: requisitionsQueryKeys.detail(initialRequisition.id),
        });
      }
      await queryClient.invalidateQueries({ queryKey: requisitionsQueryKeys.all });
      if (requisition) {
        queryClient.setQueryData(requisitionsQueryKeys.detail(requisition.id), requisition);
      }
      await navigate({ to: "/minhas-requisicoes" });
    },
    onError: handleMutationError,
  });
  const pending = saveMutation.isPending || submitMutation.isPending || discardMutation.isPending;
  const materials = materialsQuery.data?.results ?? [];
  const beneficiaries = beneficiaryQuery.data ?? [];

  useEffect(() => {
    pendingRef.current = pending;
  }, [pending]);

  const selectedMaterialIds = useMemo(
    () => new Set(selectedItems.map((item) => Number.parseInt(item.materialId, 10))),
    [selectedItems],
  );

  function addMaterial(material: MaterialListItem) {
    if (pending || !hasPositiveStock(material) || selectedMaterialIds.has(material.id)) {
      return;
    }
    append({
      materialId: String(material.id),
      materialLabel: materialLabel(material),
      materialCode: material.codigo_completo,
      unidadeMedida: material.unidade_medida,
      saldoDisponivel: material.saldo_disponivel,
      quantidadeSolicitada: "1",
      observacao: "",
    });
    form.setValue("materialSearch", "");
  }

  function chooseBeneficiary(beneficiary: BeneficiaryLookupItem) {
    if (pending) {
      return;
    }
    form.setValue("beneficiaryId", String(beneficiary.id));
    form.setValue("beneficiaryLabel", beneficiaryLabel(beneficiary));
    form.setValue("beneficiarySearch", "");
  }

  function chooseBeneficiaryMode(mode: DraftFormValues["beneficiaryMode"]) {
    if (pending) {
      return;
    }
    form.setValue("beneficiaryMode", mode, { shouldDirty: true });
    if (mode === "self") {
      const self = currentUserBeneficiary(stableSession);
      form.setValue("beneficiaryId", String(self.id), { shouldDirty: true });
      form.setValue("beneficiaryLabel", beneficiaryLabel(self), { shouldDirty: true });
      form.setValue("beneficiarySearch", "");
      return;
    }
    form.setValue("beneficiaryId", "", { shouldDirty: true });
    form.setValue("beneficiaryLabel", "", { shouldDirty: true });
  }

  function removeMaterial(index: number) {
    if (pending) {
      return;
    }
    remove(index);
  }

  function closeConfirmation() {
    if (!pending) {
      setConfirmAction(null);
    }
  }

  function validationErrorMessage(values: DraftFormValues) {
    const selectedBeneficiaryId = Number.parseInt(values.beneficiaryId, 10);
    if (
      !values.beneficiaryId ||
      !Number.isFinite(selectedBeneficiaryId) ||
      selectedBeneficiaryId <= 0 ||
      (values.beneficiaryMode === "third_party" && selectedBeneficiaryId === stableSession.id)
    ) {
      return "Informe beneficiário.";
    }
    if (values.itens.length === 0) {
      return "Adicione ao menos um item.";
    }
    const invalidItemIndex = values.itens.findIndex(
      (item) => !isPositiveQuantity(item.quantidadeSolicitada),
    );
    if (invalidItemIndex >= 0) {
      const item = values.itens[invalidItemIndex];
      return `Quantidade inválida no item ${item.materialLabel || invalidItemIndex + 1}: use um número válido maior que zero.`;
    }
    return null;
  }

  function saveDraft(valuesToSave: DraftFormValues) {
    const validationError = validationErrorMessage(valuesToSave);
    if (validationError) {
      setFormError(validationError);
      return;
    }
    saveMutation.mutate(payloadFromValues(valuesToSave));
  }

  function requestSubmitDraft(valuesToSubmit: DraftFormValues) {
    const validationError = validationErrorMessage(valuesToSubmit);
    if (validationError) {
      setFormError(validationError);
      return;
    }
    setConfirmAction({ type: "submit", values: valuesToSubmit });
  }

  function requestDiscardOrCancel() {
    setConfirmAction({ type: initialRequisition?.numero_publico ? "cancel" : "discard" });
  }

  function confirmSelectedAction() {
    if (!confirmAction) {
      return;
    }
    if (confirmAction.type === "submit") {
      submitMutation.mutate(payloadFromValues(confirmAction.values));
      return;
    }
    discardMutation.mutate();
  }

  function confirmationContent() {
    switch (confirmAction?.type) {
      case "submit":
        return {
          title: "Enviar rascunho para autorização?",
          message: "Após o envio, a requisição sai do modo rascunho e segue para avaliação do autorizador.",
          confirmLabel: "Confirmar envio",
        };
      case "cancel":
        return {
          title: "Cancelar requisição?",
          message: "A requisição numerada será encerrada e não poderá voltar ao modo rascunho.",
          confirmLabel: "Confirmar cancelamento",
        };
      case "discard":
        return {
          title: "Descartar rascunho?",
          message: "O rascunho ainda sem número será removido e os dados não salvos serão perdidos.",
          confirmLabel: "Confirmar descarte",
        };
      default:
        return null;
    }
  }

  function trapDialogFocus(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key !== "Tab" || !dialogRef.current) {
      return;
    }
    const focusableElements = dialogRef.current.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
    );
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    if (!firstElement || !lastElement) {
      return;
    }
    if (event.shiftKey && document.activeElement === firstElement) {
      event.preventDefault();
      lastElement.focus();
      return;
    }
    if (!event.shiftKey && document.activeElement === lastElement) {
      event.preventDefault();
      firstElement.focus();
    }
  }

  const confirmation = confirmationContent();

  return (
    <section className="space-y-6">
      <div className="worklist-header">
        <div>
          <p className="eyebrow">Rascunho operacional</p>
          <h1>{title}</h1>
          <p>{identifier}</p>
        </div>
        <Link className="action-link compact-action" to="/minhas-requisicoes">
          Voltar
        </Link>
      </div>

      {formError ? <div className="error-panel">{formError}</div> : null}

      <form
        className="draft-editor"
        onSubmit={(event) => {
          void form.handleSubmit(saveDraft)(event);
        }}
      >
        <section className="detail-panel draft-section">
          <p className="eyebrow">Beneficiário</p>
          <input type="hidden" {...form.register("beneficiaryMode")} />
          <input type="hidden" {...form.register("beneficiaryId")} />
          <input type="hidden" {...form.register("beneficiaryLabel")} />
          <div className="draft-choice-grid">
            <label className="draft-choice">
              <input
                checked={beneficiaryMode === "self"}
                disabled={pending}
                name="beneficiaryModeChoice"
                onChange={() => chooseBeneficiaryMode("self")}
                type="radio"
                value="self"
              />
              Para mim
            </label>
            {canRequestForThirdParty(stableSession) ? (
              <label className="draft-choice">
                <input
                  checked={beneficiaryMode === "third_party"}
                  disabled={pending}
                  name="beneficiaryModeChoice"
                  onChange={() => chooseBeneficiaryMode("third_party")}
                  type="radio"
                  value="third_party"
                />
                Para terceiro
              </label>
            ) : null}
          </div>
          <p className="selected-summary">Selecionado: {beneficiaryLabelValue}</p>
          {beneficiaryMode === "third_party" && canRequestForThirdParty(stableSession) ? (
            <div className="draft-lookup">
              <label className="preview-label">
                Buscar beneficiário
                <input
                  className="preview-input"
                  disabled={pending}
                  placeholder="Nome com ao menos 3 letras"
                  {...form.register("beneficiarySearch")}
                />
              </label>
              {beneficiarySearch.length > 0 && beneficiarySearch.length < 3 ? (
                <p className="helper-text">Digite ao menos 3 caracteres.</p>
              ) : null}
              <div className="lookup-results">
                {beneficiaries.map((beneficiary) => (
                  <button
                    className="lookup-result"
                    disabled={pending}
                    key={beneficiary.id}
                    onClick={() => chooseBeneficiary(beneficiary)}
                    type="button"
                  >
                    <strong>{beneficiary.nome_completo}</strong>
                    <span>
                      {beneficiary.matricula_funcional} - {beneficiary.setor.nome}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </section>

        <section className="detail-panel draft-section">
          <p className="eyebrow">Observação</p>
          <label className="preview-label">
            Observação geral
            <textarea
              className="preview-input draft-textarea"
              disabled={pending}
              rows={3}
              {...form.register("observacao")}
            />
          </label>
        </section>

        <section className="detail-panel draft-section">
          <p className="eyebrow">Materiais</p>
          <label className="preview-label">
            Buscar material
            <input
              className="preview-input"
              disabled={pending}
              placeholder="Código, nome ou descrição"
              {...form.register("materialSearch")}
            />
          </label>
          {materialsQuery.isError ? (
            <p className="helper-text">{queryErrorMessage(materialsQuery.error, "Erro na busca.")}</p>
          ) : null}
          <div className="lookup-results">
            {materials.map((material) => {
              const disabled = pending || !hasPositiveStock(material) || selectedMaterialIds.has(material.id);
              return (
                <button
                  aria-label={`Adicionar ${material.nome}`}
                  className="lookup-result"
                  disabled={disabled}
                  key={material.id}
                  onClick={() => addMaterial(material)}
                  type="button"
                >
                  <strong>{material.nome}</strong>
                  <span>
                    {material.codigo_completo} - saldo{" "}
                    {material.saldo_disponivel === null
                      ? "indisponível"
                      : formatQuantity(String(material.saldo_disponivel))}{" "}
                    {material.unidade_medida}
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        <section className="detail-panel draft-section">
          <p className="eyebrow">Itens solicitados</p>
          {fields.length === 0 ? (
            <p className="helper-text">Nenhum material adicionado.</p>
          ) : (
            <div className="draft-items">
              {fields.map((field, index) => (
                <article className="draft-item-card" key={field.id}>
                  <div>
                    <h2>{field.materialLabel}</h2>
                    <p>
                      Saldo{" "}
                      {field.saldoDisponivel === null
                        ? "não exibido"
                        : formatQuantity(String(field.saldoDisponivel))}{" "}
                      {field.unidadeMedida}
                    </p>
                  </div>
                  <div className="draft-item-fields">
                    <label className="preview-label">
                      Quantidade solicitada
                      <input
                        className="preview-input"
                        disabled={pending}
                        inputMode="decimal"
                        {...form.register(`itens.${index}.quantidadeSolicitada`)}
                      />
                    </label>
                    <label className="preview-label">
                      Observação do item
                      <input
                        className="preview-input"
                        disabled={pending}
                        {...form.register(`itens.${index}.observacao`)}
                      />
                    </label>
                    <button
                      aria-label={`Remover ${field.materialLabel}`}
                      className="action-link compact-action"
                      disabled={pending}
                      onClick={() => removeMaterial(index)}
                      type="button"
                    >
                      Remover
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <div className="draft-actions">
          {initialRequisition ? (
            <button
              className="action-link compact-action danger-action"
              disabled={pending}
              onClick={requestDiscardOrCancel}
              type="button"
            >
              {initialRequisition.numero_publico ? "Cancelar requisição" : "Descartar rascunho"}
            </button>
          ) : null}
          <button className="preview-button draft-primary" disabled={pending} type="submit">
            {saveMutation.isPending ? "Salvando..." : "Salvar rascunho"}
          </button>
          <button
            className="preview-button draft-primary"
            disabled={pending}
            onClick={(event) => {
              void form.handleSubmit(requestSubmitDraft)(event);
            }}
            type="button"
          >
            {submitMutation.isPending ? "Enviando..." : "Enviar para autorização"}
          </button>
        </div>
      </form>

      {confirmation ? (
        <div
          aria-labelledby="draft-submit-confirmation-title"
          aria-modal="true"
          className="draft-confirmation-backdrop"
          onClick={closeConfirmation}
          onKeyDown={trapDialogFocus}
          ref={dialogRef}
          role="dialog"
        >
          <section className="draft-confirmation-panel" onClick={(event) => event.stopPropagation()}>
            <p className="eyebrow">Confirmação</p>
            <h2 id="draft-submit-confirmation-title">{confirmation.title}</h2>
            <p>{confirmation.message}</p>
            <div className="draft-actions">
              <button
                className="action-link compact-action"
                disabled={pending}
                onClick={closeConfirmation}
                ref={cancelConfirmationButtonRef}
                type="button"
              >
                Voltar ao rascunho
              </button>
              <button
                className="preview-button draft-primary"
                disabled={pending}
                onClick={confirmSelectedAction}
                type="button"
              >
                {confirmation.confirmLabel}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
