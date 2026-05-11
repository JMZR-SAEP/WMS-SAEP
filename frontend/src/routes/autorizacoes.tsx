import { useCallback, useEffect, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { z } from "zod";

import { requireOperationalPapel } from "../features/auth/guards";
import { authQueryKeys, isUnauthenticatedError } from "../features/auth/session";
import {
  authorizeRequisition,
  formatDateTime,
  pendingApprovalsQueryOptions,
  queryErrorMessage,
  requisitionDetailQueryOptions,
  requisitionsQueryKeys,
  statusLabel,
  type RequisicaoPendingApprovalItem,
} from "../features/requisitions/requisitions";
import { calcSlaStatus, slaLabel, type SlaStatus } from "../features/requisitions/sla";
import {
  ResponsiveWorklistFrame,
  WorklistEmptyState,
  WorklistErrorState,
} from "../shared/ui/worklist";

const DEFAULT_PAGE_SIZE = 20;

const authorizationSearchSchema = z.object({
  page: z.coerce.number().int().min(1).optional().catch(undefined),
});

export const Route = createFileRoute("/autorizacoes")({
  validateSearch: authorizationSearchSchema,
  beforeLoad: ({ context, location }) =>
    requireOperationalPapel({
      allowedPapeis: ["chefe_setor", "chefe_almoxarifado"],
      queryClient: context.queryClient,
      locationHref: location.href,
    }),
  component: AutorizacoesPage,
});

function EmptyState() {
  return (
    <WorklistEmptyState
      description="A fila mostra requisições aguardando decisão do chefe do setor responsável."
      eyebrow="Sem pendências"
      title="Nenhuma autorização pendente"
    />
  );
}

function SlaBadge({ status }: { status: SlaStatus | null }) {
  if (!status) return null;
  const label = slaLabel(status);
  const icon = status === "atrasada" ? "⚠" : status === "atencao" ? "◉" : "●";
  return (
    <span aria-label={`SLA: ${label}`} className={`sla-badge sla-badge-${status}`}>
      {icon} {label}
    </span>
  );
}

function AutorizacaoCard({
  anyMutationPending,
  currentPage,
  isBeingAuthorized,
  onQuickAuthorize,
  quickAuthorizeError,
  requisicao,
}: {
  anyMutationPending: boolean;
  currentPage: number;
  isBeingAuthorized: boolean;
  onQuickAuthorize: (id: number) => void;
  quickAuthorizeError: string | null;
  requisicao: RequisicaoPendingApprovalItem;
}) {
  const slaStatus = calcSlaStatus(requisicao.data_envio_autorizacao);

  return (
    <article className="worklist-card">
      <div className="worklist-card-main">
        <div>
          <span className="font-semibold text-[var(--ink-strong)]">
            {requisicao.numero_publico ?? `#${requisicao.id}`}
          </span>
          <p className="mt-2 text-xs font-bold uppercase text-[var(--ink-muted)]">
            {requisicao.total_itens} {requisicao.total_itens === 1 ? "item" : "itens"}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`req-status req-status-${requisicao.status}`}>
            {statusLabel(requisicao.status)}
          </span>
          <SlaBadge status={slaStatus} />
        </div>
      </div>

      <dl className="worklist-card-details">
        <div>
          <dt>Beneficiário</dt>
          <dd>{requisicao.beneficiario.nome_completo}</dd>
        </div>
        <div>
          <dt>Setor</dt>
          <dd>{requisicao.setor_beneficiario.nome}</dd>
        </div>
        <div>
          <dt>Criador</dt>
          <dd>{requisicao.criador.nome_completo}</dd>
        </div>
        <div>
          <dt>Envio</dt>
          <dd>{formatDateTime(requisicao.data_envio_autorizacao)}</dd>
        </div>
      </dl>

      {quickAuthorizeError ? (
        <div className="error-panel compact-error">{quickAuthorizeError}</div>
      ) : null}

      <div className="worklist-card-footer">
        {slaStatus === "normal" ? (
          <button
            className="action-link compact-action"
            disabled={anyMutationPending}
            onClick={() => onQuickAuthorize(requisicao.id)}
            type="button"
          >
            {isBeingAuthorized ? "Autorizando..." : "Autorizar tudo"}
          </button>
        ) : null}
        <Link
          className="action-link compact-action"
          params={{ id: String(requisicao.id) }}
          search={{ contexto: "autorizacao", page: currentPage === 1 ? undefined : currentPage }}
          to="/requisicoes/$id"
        >
          Abrir
        </Link>
      </div>
    </article>
  );
}

function recordsLabelForList({
  count,
  hasError,
  isLoading,
}: {
  count: number | undefined;
  hasError: boolean;
  isLoading: boolean;
}) {
  if (isLoading) {
    return "Carregando...";
  }

  if (hasError) {
    return "Erro ao carregar";
  }

  if (typeof count === "number") {
    return `${count} ${count === 1 ? "registro" : "registros"}`;
  }

  return "0 registros";
}

function AutorizacoesPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate({ from: "/autorizacoes" });
  const searchParams = Route.useSearch();
  const currentPage = searchParams.page ?? 1;
  const listQuery = useQuery(
    pendingApprovalsQueryOptions({
      page: currentPage,
      pageSize: DEFAULT_PAGE_SIZE,
    }),
  );
  const authError = listQuery.isError && isUnauthenticatedError(listQuery.error);
  const rows = listQuery.data?.results ?? [];
  const recordsLabel = recordsLabelForList({
    count: listQuery.data?.count,
    hasError: listQuery.isError && !listQuery.data,
    isLoading: listQuery.isLoading,
  });

  const quickAuthorizeMutation = useMutation({
    mutationFn: async (id: number) => {
      const detail = await queryClient.fetchQuery(requisitionDetailQueryOptions(id));
      return authorizeRequisition(id, {
        itens: detail.itens.map((item) => ({
          item_id: item.id,
          quantidade_autorizada: item.quantidade_solicitada,
          justificativa_autorizacao_parcial: "",
        })),
      });
    },
    onSuccess: async (_data, id) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: requisitionsQueryKeys.pendingApprovalsAll }),
        queryClient.invalidateQueries({ queryKey: requisitionsQueryKeys.detail(id) }),
      ]);
    },
    onError: (error) => {
      if (isUnauthenticatedError(error)) {
        queryClient.removeQueries({ queryKey: authQueryKeys.me });
        void navigate({
          to: "/login",
          search: { redirect: currentPage === 1 ? "/autorizacoes" : `/autorizacoes?page=${currentPage}` },
        });
      }
    },
  });

  const {
    error: quickAuthorizeErrorObj,
    isError: quickAuthorizeIsError,
    isPending: quickAuthorizing,
    mutate: quickAuthorize,
    variables: quickAuthorizingId,
  } = quickAuthorizeMutation;

  const handleQuickAuthorize = useCallback(
    (id: number) => quickAuthorize(id),
    [quickAuthorize],
  );

  const columns = useMemo<ColumnDef<RequisicaoPendingApprovalItem>[]>(
    () => [
      {
        id: "identifier",
        header: "Requisição",
        cell: ({ row }) => (
          <div className="min-w-[11rem]">
            <span className="font-semibold text-[var(--ink-strong)]">
              {row.original.numero_publico ?? `#${row.original.id}`}
            </span>
            <p className="mt-2 text-xs font-bold uppercase text-[var(--ink-muted)]">
              {row.original.total_itens} {row.original.total_itens === 1 ? "item" : "itens"}
            </p>
          </div>
        ),
      },
      {
        id: "status",
        header: "Status",
        cell: ({ row }) => (
          <span className={`req-status req-status-${row.original.status}`}>
            {statusLabel(row.original.status)}
          </span>
        ),
      },
      {
        id: "beneficiario",
        header: "Beneficiário",
        cell: ({ row }) => (
          <div>
            <p className="font-semibold">{row.original.beneficiario.nome_completo}</p>
            <p className="mt-1 text-sm text-[var(--ink-soft)]">
              {row.original.setor_beneficiario.nome}
            </p>
          </div>
        ),
      },
      {
        id: "criador",
        header: "Criador",
        cell: ({ row }) => <span>{row.original.criador.nome_completo}</span>,
      },
      {
        id: "sent_at",
        header: "Envio",
        cell: ({ row }) => (
          <span className="text-sm text-[var(--ink-soft)]">
            {formatDateTime(row.original.data_envio_autorizacao)}
          </span>
        ),
      },
      {
        id: "sla",
        header: "SLA",
        cell: ({ row }) => (
          <SlaBadge status={calcSlaStatus(row.original.data_envio_autorizacao)} />
        ),
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => {
          const slaStatus = calcSlaStatus(row.original.data_envio_autorizacao);
          const isBeingAuthorized = quickAuthorizing && quickAuthorizingId === row.original.id;
          const rowError =
            quickAuthorizeIsError && quickAuthorizingId === row.original.id
              ? queryErrorMessage(quickAuthorizeErrorObj, "Não foi possível autorizar.")
              : null;
          return (
            <div className="flex items-center gap-2">
              {rowError ? (
                <div className="error-panel compact-error">{rowError}</div>
              ) : null}
              {slaStatus === "normal" ? (
                <button
                  className="action-link compact-action"
                  disabled={quickAuthorizing}
                  onClick={() => handleQuickAuthorize(row.original.id)}
                  type="button"
                >
                  {isBeingAuthorized ? "Autorizando..." : "Autorizar tudo"}
                </button>
              ) : null}
              <Link
                className="action-link compact-action"
                params={{ id: String(row.original.id) }}
                search={{ contexto: "autorizacao", page: currentPage === 1 ? undefined : currentPage }}
                to="/requisicoes/$id"
              >
                Abrir
              </Link>
            </div>
          );
        },
      },
    ],
    [currentPage, handleQuickAuthorize, quickAuthorizeErrorObj, quickAuthorizeIsError, quickAuthorizing, quickAuthorizingId],
  );
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    columns,
    data: rows,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    rowCount: listQuery.data?.count ?? 0,
    state: {
      pagination: {
        pageIndex: currentPage - 1,
        pageSize: DEFAULT_PAGE_SIZE,
      },
    },
  });

  function goToPage(page: number) {
    void navigate({
      search: {
        page: page === 1 ? undefined : page,
      },
    });
  }

  useEffect(() => {
    if (!authError) {
      return;
    }
    queryClient.removeQueries({ queryKey: authQueryKeys.me });
    void navigate({
      to: "/login",
      search: {
        redirect: currentPage === 1 ? "/autorizacoes" : `/autorizacoes?page=${currentPage}`,
      },
    });
  }, [authError, currentPage, navigate, queryClient]);

  if (authError) {
    return null;
  }

  return (
    <section className="space-y-6">
      <div className="worklist-header">
        <div>
          <p className="eyebrow">Worklist operacional</p>
          <h1>Fila de autorizações</h1>
          <p>Requisições aguardando decisão da chefia do setor responsável.</p>
        </div>
        <div className="status-chip">
          <span className="status-dot" />
          {recordsLabel}
        </div>
      </div>

      {listQuery.isError ? (
        <WorklistErrorState>
          {queryErrorMessage(listQuery.error, "Não foi possível carregar autorizações pendentes.")}
        </WorklistErrorState>
      ) : null}

      {!listQuery.isError ? (
        <ResponsiveWorklistFrame
          desktop={
            <table className="operational-table">
              <thead>
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th key={header.id}>
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                  <tr key={row.id}>
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          }
          empty={<EmptyState />}
          isEmpty={rows.length === 0}
          isPending={listQuery.isPending}
          mobile={
            <div aria-label="Cards da fila de autorizações" className="worklist-card-list">
              {rows.map((requisicao) => (
                <AutorizacaoCard
                  anyMutationPending={quickAuthorizing}
                  currentPage={currentPage}
                  isBeingAuthorized={quickAuthorizing && quickAuthorizingId === requisicao.id}
                  key={requisicao.id}
                  onQuickAuthorize={handleQuickAuthorize}
                  quickAuthorizeError={
                    quickAuthorizeIsError && quickAuthorizingId === requisicao.id
                      ? queryErrorMessage(quickAuthorizeErrorObj, "Não foi possível autorizar.")
                      : null
                  }
                  requisicao={requisicao}
                />
              ))}
            </div>
          }
          skeletonLabel="Carregando autorizações"
        />
      ) : null}

      <div className="pagination-bar">
        <button
          className="action-link compact-action"
          disabled={currentPage <= 1 || listQuery.isPending}
          onClick={() => goToPage(currentPage - 1)}
          type="button"
        >
          Anterior
        </button>
        <span>
          Página {listQuery.data?.page ?? currentPage} de {listQuery.data?.total_pages ?? 1}
        </span>
        <button
          className="action-link compact-action"
          disabled={
            listQuery.isPending ||
            !listQuery.data ||
            currentPage >= listQuery.data.total_pages
          }
          onClick={() => goToPage(currentPage + 1)}
          type="button"
        >
          Próxima
        </button>
      </div>
    </section>
  );
}
