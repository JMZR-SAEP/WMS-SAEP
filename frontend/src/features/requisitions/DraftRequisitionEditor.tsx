import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
} from "react";
import { useFieldArray, useForm, useWatch, type FieldPath } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";

import { authQueryKeys, isAuthError, type AuthSession } from "../auth/session";
import type { DraftStep } from "./draftSteps";
import {
  cancelDraftRequisition,
  createDraftRequisition,
  discardDraftRequisition,
  displayRequisitionIdentifier,
  draftBeneficiariesQueryOptions,
  draftMaterialsQueryOptions,
  fetchMaterialsForDraft,
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
const DRAFT_STEPS: Array<{ key: DraftStep; label: string }> = [
  { key: "beneficiario", label: "Beneficiário" },
  { key: "itens", label: "Itens" },
  { key: "revisao", label: "Revisão" },
  { key: "envio", label: "Envio" },
];

type DraftRequisitionEditorProps = {
  activeStep?: DraftStep;
  initialRequisition?: RequisicaoDetail;
  onStepChange?: (step: DraftStep) => void;
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

function beneficiaryLabel(
  beneficiary: Pick<BeneficiaryLookupItem, "matricula_funcional" | "nome_completo">,
) {
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
        quantidadeSolicitada: quantityInputValue(item.quantidade_solicitada),
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

function quantityInputValue(value: string) {
  const trimmedValue = value.trim();
  if (!trimmedValue.includes(".")) {
    return trimmedValue;
  }
  return trimmedValue.replace(/0+$/, "").replace(/\.$/, "").replace(".", ",");
}

function isPositiveQuantity(value: string) {
  if (!/^\d+(,\d+)?$/.test(value.trim())) {
    return false;
  }
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

function draftStorageKey(sessionId: number, draftId: number | undefined) {
  return draftId
    ? `wms-saep:draft:v1:user:${sessionId}:draft:${draftId}`
    : `wms-saep:draft:v1:user:${sessionId}:new`;
}

function recentMaterialsStorageKey(sessionId: number) {
  return `wms-saep:recent-materials:v1:user:${sessionId}`;
}

function safeReadJson<T>(key: string): T | null {
  try {
    const rawValue = window.sessionStorage.getItem(key);
    return rawValue ? (JSON.parse(rawValue) as T) : null;
  } catch {
    return null;
  }
}

function safeWriteJson(key: string, value: unknown) {
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Draft recovery is best-effort and must never block editing.
  }
}

function safeRemoveStorage(key: string) {
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    // Ignore unavailable storage.
  }
}

function normalizeSnapshot(values: DraftFormValues): DraftFormValues {
  return {
    beneficiaryMode: values.beneficiaryMode === "third_party" ? "third_party" : "self",
    beneficiaryId: values.beneficiaryId ?? "",
    beneficiaryLabel: values.beneficiaryLabel ?? "",
    beneficiarySearch: "",
    materialSearch: "",
    observacao: values.observacao ?? "",
    itens: Array.isArray(values.itens)
      ? values.itens.map((item) => ({
          materialId: item.materialId ?? "",
          materialLabel: item.materialLabel ?? "",
          materialCode: item.materialCode ?? "",
          unidadeMedida: item.unidadeMedida ?? "",
          saldoDisponivel: item.saldoDisponivel ?? null,
          quantidadeSolicitada: item.quantidadeSolicitada ?? "",
          observacao: item.observacao ?? "",
        }))
      : [],
  };
}

function sameDraftValues(first: DraftFormValues, second: DraftFormValues) {
  return JSON.stringify(normalizeSnapshot(first)) === JSON.stringify(normalizeSnapshot(second));
}

function quantityErrorMessage(itemLabel: string | number) {
  return `Quantidade inválida no item ${itemLabel}: use um número válido maior que zero.`;
}

function quantityFieldName(index: number): `itens.${number}.quantidadeSolicitada` {
  return `itens.${index}.quantidadeSolicitada`;
}

function draftFieldError(
  values: DraftFormValues,
  session: AuthSession,
): { name: FieldPath<DraftFormValues>; message: string } | null {
  const selectedBeneficiaryId = Number.parseInt(values.beneficiaryId, 10);
  if (
    !values.beneficiaryId ||
    !Number.isFinite(selectedBeneficiaryId) ||
    selectedBeneficiaryId <= 0 ||
    (values.beneficiaryMode === "third_party" && selectedBeneficiaryId === session.id)
  ) {
    return { name: "beneficiaryId", message: "Informe beneficiário." };
  }
  if (values.itens.length === 0) {
    return { name: "itens", message: "Adicione ao menos um item." };
  }
  const invalidItemIndex = values.itens.findIndex(
    (item) => !isPositiveQuantity(item.quantidadeSolicitada),
  );
  if (invalidItemIndex >= 0) {
    const item = values.itens[invalidItemIndex];
    return {
      name: `itens.${invalidItemIndex}.quantidadeSolicitada`,
      message: quantityErrorMessage(item.materialLabel || invalidItemIndex + 1),
    };
  }
  return null;
}

function stepIndex(step: DraftStep) {
  return DRAFT_STEPS.findIndex((candidate) => candidate.key === step);
}

function nextStep(step: DraftStep) {
  return DRAFT_STEPS[Math.min(stepIndex(step) + 1, DRAFT_STEPS.length - 1)].key;
}

function previousStep(step: DraftStep) {
  return DRAFT_STEPS[Math.max(stepIndex(step) - 1, 0)].key;
}

function StepSection({
  activeStep,
  children,
  step,
}: {
  activeStep: DraftStep;
  children: ReactNode;
  step: DraftStep;
}) {
  return (
    <section className="draft-step-panel" hidden={activeStep !== step}>
      {children}
    </section>
  );
}

export function DraftRequisitionEditor({
  activeStep: activeStepProp = "beneficiario",
  initialRequisition,
  onStepChange,
  session,
}: DraftRequisitionEditorProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<ConfirmAction | null>(null);
  const [localStep, setLocalStep] = useState<DraftStep>(activeStepProp);
  const [recentMaterials, setRecentMaterials] = useState<MaterialListItem[]>(() =>
    safeReadJson<MaterialListItem[]>(recentMaterialsStorageKey(session.id)) ?? [],
  );
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const cancelConfirmationButtonRef = useRef<HTMLButtonElement | null>(null);
  const pendingRef = useRef(false);
  const suppressNextPersistRef = useRef(false);
  const storageKey = draftStorageKey(session.id, initialRequisition?.id);
  const baseValues = useMemo(
    () => formValuesFromRequisition(initialRequisition, session),
    [initialRequisition, session],
  );
  const recoveredValues = useMemo(
    () => safeReadJson<DraftFormValues>(storageKey),
    [storageKey],
  );
  const hasRecoveredSnapshot = Boolean(recoveredValues && !sameDraftValues(recoveredValues, baseValues));
  const [showRecoveredDraft, setShowRecoveredDraft] = useState(hasRecoveredSnapshot);
  const [hasDraftSnapshot, setHasDraftSnapshot] = useState(hasRecoveredSnapshot);
  const form = useForm<DraftFormValues>({
    defaultValues:
      recoveredValues && !sameDraftValues(recoveredValues, baseValues)
        ? normalizeSnapshot(recoveredValues)
        : baseValues,
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
  const watchedValues = useWatch({ control: form.control });
  const isDraftDirty = form.formState.isDirty;
  const activeStep = onStepChange ? activeStepProp : localStep;
  const isEdit = Boolean(initialRequisition);
  const title = isEdit ? "Editar rascunho" : "Nova requisição";
  const identifier = initialRequisition
    ? (displayRequisitionIdentifier(initialRequisition) ?? statusLabel(initialRequisition.status))
    : "Novo rascunho";
  const beneficiaryQuery = useQuery({
    ...draftBeneficiariesQueryOptions(beneficiarySearch),
    enabled:
      beneficiaryMode === "third_party" &&
      canRequestForThirdParty(session) &&
      beneficiarySearch.length >= 3,
  });
  const materialsQuery = useQuery({
    ...draftMaterialsQueryOptions(materialSearch),
    enabled: materialSearch.length >= 2,
  });
  useEffect(() => {
    if (suppressNextPersistRef.current) {
      suppressNextPersistRef.current = false;
      return;
    }
    if (isDraftDirty || hasDraftSnapshot) {
      safeWriteJson(storageKey, normalizeSnapshot(form.getValues()));
      return;
    }
    safeRemoveStorage(storageKey);
  }, [form, hasDraftSnapshot, isDraftDirty, storageKey, watchedValues]);

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
      const self = currentUserBeneficiary(session);
      form.setValue("beneficiaryId", String(self.id));
      form.setValue("beneficiaryLabel", beneficiaryLabel(self));
    } else if (previousBeneficiaryModeRef.current === "self") {
      form.setValue("beneficiaryId", "");
      form.setValue("beneficiaryLabel", "");
    }
    previousBeneficiaryModeRef.current = beneficiaryMode;
  }, [beneficiaryMode, form, session]);

  function clearDraftStorage() {
    safeRemoveStorage(storageKey);
    setShowRecoveredDraft(false);
    setHasDraftSnapshot(false);
  }

  function afterMutationSuccess(requisition: RequisicaoDetail) {
    suppressNextPersistRef.current = true;
    clearDraftStorage();
    queryClient.setQueryData(requisitionsQueryKeys.detail(requisition.id), requisition);
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
        const currentItems = form.getValues("itens");
        const nextValues = formValuesFromRequisition(requisition, session);
        nextValues.itens = nextValues.itens.map((item) => ({
          ...item,
          saldoDisponivel:
            currentItems.find((currentItem) => currentItem.materialId === item.materialId)?.saldoDisponivel ??
            item.saldoDisponivel,
        }));
        form.reset(nextValues);
      }
      if (!initialRequisition) {
        await navigate({
          to: "/requisicoes/$id",
          params: { id: String(requisition.id) },
          search: { etapa: activeStep },
        });
      }
    },
    onError: handleMutationError,
  });
  const submitMutation = useMutation({
    mutationFn: async (input: RequisicaoDraftInput) => {
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
      clearDraftStorage();
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
  const displayedMaterials = materialSearch ? materials : recentMaterials.length >= 2 ? recentMaterials : [];
  const beneficiaries = beneficiaryQuery.data ?? [];
  const missingStockSignature = selectedItems
    .filter((item) => item.saldoDisponivel === null)
    .map((item) => `${item.materialId}:${item.materialCode}`)
    .join("|");

  useEffect(() => {
    pendingRef.current = pending;
  }, [pending]);

  useEffect(() => {
    if (!initialRequisition || !missingStockSignature) {
      return;
    }
    const itemsToHydrate = form
      .getValues("itens")
      .map((item, index) => ({ item, index }))
      .filter(({ item }) => item.saldoDisponivel === null);

    if (itemsToHydrate.length === 0) {
      return;
    }

    let ignore = false;

    void Promise.all(
      itemsToHydrate.map(async ({ item, index }) => {
        try {
          const materialPage = await fetchMaterialsForDraft(item.materialCode);
          const material = materialPage.results.find(
            (candidate) => candidate.id === Number.parseInt(item.materialId, 10),
          );
          if (!ignore && material) {
            form.setValue(`itens.${index}.saldoDisponivel`, material.saldo_disponivel, {
              shouldDirty: false,
            });
          }
        } catch {
          // Best effort: saved drafts still work if stock lookup is temporarily unavailable.
        }
      }),
    );

    return () => {
      ignore = true;
    };
  }, [form, initialRequisition, missingStockSignature]);

  const selectedMaterialIds = useMemo(
    () => new Set(selectedItems.map((item) => Number.parseInt(item.materialId, 10))),
    [selectedItems],
  );

  function goToStep(step: DraftStep) {
    if (onStepChange) {
      onStepChange(step);
      return;
    }
    setLocalStep(step);
  }

  function storeRecentMaterial(material: MaterialListItem) {
    const nextMaterials = [
      material,
      ...recentMaterials.filter((candidate) => candidate.id !== material.id),
    ].slice(0, 5);
    setRecentMaterials(nextMaterials);
    safeWriteJson(recentMaterialsStorageKey(session.id), nextMaterials);
  }

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
    form.clearErrors("itens");
    setFormError(null);
    storeRecentMaterial(material);
    form.setValue("materialSearch", "");
  }

  function chooseBeneficiary(beneficiary: BeneficiaryLookupItem) {
    if (pending) {
      return;
    }
    form.setValue("beneficiaryId", String(beneficiary.id), { shouldDirty: true });
    form.setValue("beneficiaryLabel", beneficiaryLabel(beneficiary), { shouldDirty: true });
    form.setValue("beneficiarySearch", "");
    form.clearErrors("beneficiaryId");
    setFormError(null);
  }

  function chooseBeneficiaryMode(mode: DraftFormValues["beneficiaryMode"]) {
    if (pending) {
      return;
    }
    form.setValue("beneficiaryMode", mode, { shouldDirty: true });
    if (mode === "self") {
      const self = currentUserBeneficiary(session);
      form.setValue("beneficiaryId", String(self.id), { shouldDirty: true });
      form.setValue("beneficiaryLabel", beneficiaryLabel(self), { shouldDirty: true });
      form.setValue("beneficiarySearch", "");
      form.clearErrors("beneficiaryId");
      setFormError(null);
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

  async function validateDraft({ focus = true }: { focus?: boolean } = {}) {
    form.clearErrors();
    const values = form.getValues();
    const validationError = draftFieldError(values, session);
    if (validationError) {
      form.setError(validationError.name, { type: "manual", message: validationError.message }, {
        shouldFocus: focus,
      });
      setFormError(validationError.message);
      return false;
    }
    const fieldNames = values.itens.map((_item, index) => quantityFieldName(index));
    const valid = await form.trigger(fieldNames, { shouldFocus: focus });
    if (!valid) {
      return false;
    }
    setFormError(null);
    return true;
  }

  async function advanceStep() {
    if (activeStep === "beneficiario") {
      const validBeneficiary = await validateDraftStep("beneficiario");
      if (!validBeneficiary) {
        return;
      }
    }
    if (activeStep === "itens") {
      const validItems = await validateDraftStep("itens");
      if (!validItems) {
        return;
      }
    }
    goToStep(nextStep(activeStep));
  }

  async function validateDraftStep(step: DraftStep) {
    form.clearErrors();
    const values = form.getValues();
    if (step === "beneficiario") {
      const selectedBeneficiaryId = Number.parseInt(values.beneficiaryId, 10);
      if (
        !values.beneficiaryId ||
        !Number.isFinite(selectedBeneficiaryId) ||
        selectedBeneficiaryId <= 0 ||
        (values.beneficiaryMode === "third_party" && selectedBeneficiaryId === session.id)
      ) {
        form.setError("beneficiaryId", { type: "manual", message: "Informe beneficiário." }, {
          shouldFocus: true,
        });
        setFormError("Informe beneficiário.");
        return false;
      }
      setFormError(null);
      return true;
    }
    if (step === "itens") {
      if (values.itens.length === 0) {
        form.setError("itens", { type: "manual", message: "Adicione ao menos um item." });
        setFormError("Adicione ao menos um item.");
        return false;
      }
      return validateDraft();
    }
    return true;
  }

  async function saveDraft(valuesToSave: DraftFormValues) {
    if (!(await validateDraft())) {
      return;
    }
    saveMutation.mutate(payloadFromValues(valuesToSave));
  }

  async function requestSubmitDraft(valuesToSubmit: DraftFormValues) {
    if (!(await validateDraft())) {
      return;
    }
    setConfirmAction({ type: "submit", values: valuesToSubmit });
  }

  function requestDiscardOrCancel() {
    setConfirmAction({ type: initialRequisition?.numero_publico ? "cancel" : "discard" });
  }

  function discardLocalCopy() {
    clearDraftStorage();
    form.reset(baseValues);
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
  const itemError = form.formState.errors.itens?.message;
  const showRecentMaterials = !materialSearch && recentMaterials.length >= 2;

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

      <div className="draft-stepper" aria-label="Etapas do rascunho">
        {DRAFT_STEPS.map((step) => (
          <button
            aria-current={activeStep === step.key ? "step" : undefined}
            className={activeStep === step.key ? "draft-step active" : "draft-step"}
            disabled={pending}
            key={step.key}
            onClick={() => goToStep(step.key)}
            type="button"
          >
            {step.label}
          </button>
        ))}
      </div>

      {showRecoveredDraft ? (
        <div className="draft-recovery-banner">
          <div>
            <strong>Rascunho local recuperado</strong>
            <p>Encontramos dados salvos nesta aba. Continue ou descarte a cópia local.</p>
          </div>
          <div className="draft-recovery-actions">
            <button
              className="preview-button draft-primary"
              onClick={() => setShowRecoveredDraft(false)}
              type="button"
            >
              Continuar
            </button>
            <button className="action-link compact-action" onClick={discardLocalCopy} type="button">
              Descartar cópia local
            </button>
          </div>
        </div>
      ) : null}

      {formError ? <div className="error-panel">{formError}</div> : null}

      <form
        className="draft-editor"
        onSubmit={(event) => {
          void form.handleSubmit(saveDraft)(event);
        }}
      >
        <StepSection activeStep={activeStep} step="beneficiario">
          <section className="detail-panel draft-section">
            <h2>Beneficiário</h2>
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
              {canRequestForThirdParty(session) ? (
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
            {form.formState.errors.beneficiaryId?.message ? (
              <p className="field-error">{form.formState.errors.beneficiaryId.message}</p>
            ) : null}
            {beneficiaryMode === "third_party" && canRequestForThirdParty(session) ? (
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
        </StepSection>

        <StepSection activeStep={activeStep} step="itens">
          <section className="detail-panel draft-section">
            <h2>Itens</h2>
            <label className="preview-label">
              Buscar material
              <input
                className="preview-input"
                disabled={pending}
                placeholder="Código, nome ou descrição"
                {...form.register("materialSearch")}
              />
            </label>
            {materialsQuery.isLoading ? (
              <div className="worklist-skeleton" aria-label="Carregando materiais">
                <span className="worklist-skeleton-line wide" />
                <span className="worklist-skeleton-line medium" />
              </div>
            ) : null}
            {materialsQuery.isError ? (
              <p className="helper-text">{queryErrorMessage(materialsQuery.error, "Erro na busca.")}</p>
            ) : null}
            {showRecentMaterials ? <p className="eyebrow">Materiais recentes</p> : null}
            <div className="lookup-results">
              {displayedMaterials.map((material) => {
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
            <h2>Itens solicitados</h2>
            {itemError ? <p className="field-error">{itemError}</p> : null}
            {fields.length === 0 ? (
              <p className="helper-text">Nenhum material adicionado.</p>
            ) : (
              <div className="draft-items">
                {fields.map((field, index) => {
                  const item = selectedItems[index] ?? field;
                  return (
                    <article className="draft-item-card" key={field.id}>
                      <div>
                        <h3>{field.materialLabel}</h3>
                        <p>
                          {item.saldoDisponivel === null
                            ? "Saldo carregando..."
                            : `Saldo ${formatQuantity(String(item.saldoDisponivel))} ${field.unidadeMedida}`}
                        </p>
                      </div>
                      <div className="draft-item-fields">
                        <label className="preview-label">
                          Quantidade solicitada
                          <input
                            className="preview-input"
                            disabled={pending}
                            inputMode="decimal"
                            {...form.register(`itens.${index}.quantidadeSolicitada`, {
                              validate: (value) =>
                                isPositiveQuantity(value) ||
                                quantityErrorMessage(field.materialLabel),
                            })}
                          />
                        </label>
                        {form.formState.errors.itens?.[index]?.quantidadeSolicitada?.message ? (
                          <p className="field-error">
                            {form.formState.errors.itens[index]?.quantidadeSolicitada?.message}
                          </p>
                        ) : null}
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
                  );
                })}
              </div>
            )}
          </section>
        </StepSection>

        <StepSection activeStep={activeStep} step="revisao">
          <section className="detail-panel draft-section">
            <h2>Revisão</h2>
            <dl className="info-list">
              <div>
                <dt>Beneficiário</dt>
                <dd>{beneficiaryLabelValue}</dd>
              </div>
              <div>
                <dt>Total de itens</dt>
                <dd>{selectedItems.length}</dd>
              </div>
            </dl>
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
            <h2>Resumo dos itens</h2>
            {selectedItems.length === 0 ? (
              <p className="helper-text">Nenhum material adicionado.</p>
            ) : (
              <div className="draft-review-list">
                {selectedItems.map((item) => (
                  <article className="draft-review-item" key={item.materialId}>
                    <div>
                      <strong>{item.materialLabel}</strong>
                      {item.observacao ? <p>{item.observacao}</p> : null}
                    </div>
                    <span>
                      {item.quantidadeSolicitada} {item.unidadeMedida}
                    </span>
                  </article>
                ))}
              </div>
            )}
          </section>
        </StepSection>

        <StepSection activeStep={activeStep} step="envio">
          <section className="detail-panel draft-section">
            <h2>Envio</h2>
            <p className="helper-text">
              Salvar mantém o rascunho editável. Enviar confirma o rascunho no backend e encaminha
              para autorização.
            </p>
            <dl className="info-list">
              <div>
                <dt>Beneficiário</dt>
                <dd>{beneficiaryLabelValue}</dd>
              </div>
              <div>
                <dt>Itens</dt>
                <dd>{selectedItems.length}</dd>
              </div>
            </dl>
          </section>
        </StepSection>

        <div className="draft-actions draft-sticky-actions">
          {activeStep !== "beneficiario" ? (
            <button
              className="action-link compact-action"
              disabled={pending}
              onClick={() => goToStep(previousStep(activeStep))}
              type="button"
            >
              Voltar etapa
            </button>
          ) : null}
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
          {activeStep !== "envio" ? (
            <button
              className="preview-button draft-primary"
              disabled={pending}
              onClick={() => void advanceStep()}
              type="button"
            >
              {activeStep === "beneficiario"
                ? "Próximo: itens"
                : activeStep === "itens"
                  ? "Próximo: revisão"
                  : "Próximo: envio"}
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
