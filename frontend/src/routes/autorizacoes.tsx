import { useEffect, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
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
  formatDateTime,
  pendingApprovalsQueryOptions,
  queryErrorMessage,
  statusLabel,
  type RequisicaoPendingApprovalItem,
} from "../features/requisitions/requisitions";

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
    <div className="empty-state">
      <p className="eyebrow">Sem pendências</p>
      <h2>Nenhuma autorização pendente</h2>
      <p>A fila mostra requisições aguardando decisão do chefe do setor responsável.</p>
    </div>
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
            <p className="mt-2 text-xs uppercase tracking-[0.18em] text-[var(--ink-muted)]">
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
        id: "actions",
        header: "",
        cell: ({ row }) => (
          <Link
            className="action-link compact-action"
            params={{ id: String(row.original.id) }}
            search={{ contexto: "autorizacao", page: currentPage === 1 ? undefined : currentPage }}
            to="/requisicoes/$id"
          >
            Abrir
          </Link>
        ),
      },
    ],
    [currentPage],
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

      {listQuery.isError && !authError ? (
        <div className="error-panel">
          {queryErrorMessage(listQuery.error, "Não foi possível carregar autorizações pendentes.")}
        </div>
      ) : null}

      {!listQuery.isError || authError ? (
        <div className="table-frame">
          {listQuery.isPending ? (
            <div className="loading-state">Carregando autorizações...</div>
          ) : rows.length === 0 ? (
            <EmptyState />
          ) : (
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
          )}
        </div>
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
