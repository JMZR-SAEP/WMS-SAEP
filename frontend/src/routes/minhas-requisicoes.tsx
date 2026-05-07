import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";
import { z } from "zod";

import { requireSession } from "../features/auth/guards";
import { authQueryKeys, isAuthError } from "../features/auth/session";
import {
  contextualDateLabel,
  formatDateTime,
  isThirdPartyBeneficiary,
  myRequisitionsQueryOptions,
  statusLabel,
  STATUS_OPTIONS,
  type RequisicaoListItem,
  type RequisicaoStatus,
} from "../features/requisitions/requisitions";

const DEFAULT_PAGE_SIZE = 20;

const STATUS_VALUES = STATUS_OPTIONS.map((option) => option.value) as [
  RequisicaoStatus,
  ...RequisicaoStatus[],
];

const requisitionsSearchSchema = z.object({
  page: z.coerce.number().int().min(1).optional().catch(undefined),
  search: z.string().optional().catch(undefined),
  status: z.enum(STATUS_VALUES).optional().catch(undefined),
});

export const Route = createFileRoute("/minhas-requisicoes")({
  validateSearch: requisitionsSearchSchema,
  beforeLoad: ({ context, location }) =>
    requireSession({ queryClient: context.queryClient, locationHref: location.href }),
  component: MinhasRequisicoesPage,
});

function queryErrorMessage(error: unknown) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Não foi possível carregar os dados.";
}

function StatusBadge({ status }: { status: RequisicaoStatus }) {
  return <span className={`req-status req-status-${status}`}>{statusLabel(status)}</span>;
}

function IdentifierCell({ requisicao }: { requisicao: RequisicaoListItem }) {
  if (requisicao.numero_publico) {
    return <span className="font-semibold text-[var(--ink-strong)]">{requisicao.numero_publico}</span>;
  }

  return <span className="draft-badge">Rascunho</span>;
}

function EmptyState() {
  return (
    <div className="empty-state">
      <p className="eyebrow">Sem resultados</p>
      <h2>Nenhuma requisição encontrada</h2>
      <p>Ajuste busca ou status para voltar à lista operacional.</p>
    </div>
  );
}

function MinhasRequisicoesPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate({ from: "/minhas-requisicoes" });
  const searchParams = Route.useSearch();
  const currentPage = searchParams.page ?? 1;
  const currentSearch = searchParams.search ?? "";
  const [searchDraft, setSearchDraft] = useState(currentSearch);
  const listQuery = useQuery(
    myRequisitionsQueryOptions({
      page: currentPage,
      pageSize: DEFAULT_PAGE_SIZE,
      search: currentSearch.trim() || undefined,
      status: searchParams.status,
    }),
  );
  const authError = listQuery.isError && isAuthError(listQuery.error);

  useEffect(() => {
    setSearchDraft(currentSearch);
  }, [currentSearch]);

  const rows = listQuery.data?.results ?? [];
  const columns = useMemo<ColumnDef<RequisicaoListItem>[]>(
    () => [
      {
        id: "identifier",
        header: "Requisição",
        cell: ({ row }) => (
          <div className="min-w-[11rem]">
            <IdentifierCell requisicao={row.original} />
            <p className="mt-2 text-xs uppercase tracking-[0.18em] text-[var(--ink-muted)]">
              {row.original.total_itens} {row.original.total_itens === 1 ? "item" : "itens"}
            </p>
          </div>
        ),
      },
      {
        id: "status",
        header: "Status",
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        id: "beneficiario",
        header: "Beneficiário",
        cell: ({ row }) => {
          const thirdParty = isThirdPartyBeneficiary(row.original);

          return (
            <div>
              <p className="font-semibold">{row.original.beneficiario.nome_completo}</p>
              <p className="mt-1 text-sm text-[var(--ink-soft)]">
                {row.original.setor_beneficiario.nome}
              </p>
              {thirdParty ? <span className="third-party-badge">Beneficiário terceiro</span> : null}
            </div>
          );
        },
      },
      {
        id: "updated_at",
        header: "Atualização",
        cell: ({ row }) => (
          <div className="text-sm text-[var(--ink-soft)]">
            <p>{contextualDateLabel(row.original)}</p>
            <p className="mt-1 text-xs uppercase tracking-[0.16em] text-[var(--ink-muted)]">
              criada em {formatDateTime(row.original.data_criacao)}
            </p>
          </div>
        ),
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => (
          <Link
            className="action-link compact-action"
            params={{ id: String(row.original.id) }}
            to="/requisicoes/$id"
          >
            Abrir
          </Link>
        ),
      },
    ],
    [],
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

  async function updateSearch(nextSearch: string, nextStatus: RequisicaoStatus | undefined) {
    await navigate({
      search: (previous) => ({
        ...previous,
        page: undefined,
        search: nextSearch.trim() || undefined,
        status: nextStatus,
      }),
    });
  }

  async function goToPage(page: number) {
    await navigate({
      search: (previous) => ({
        ...previous,
        page: page === 1 ? undefined : page,
      }),
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
        redirect: "/minhas-requisicoes",
      },
    });
  }, [authError, navigate, queryClient]);

  return (
    <section className="space-y-6">
      <div className="worklist-header">
        <div>
          <p className="eyebrow">Worklist operacional</p>
          <h1>Minhas requisições</h1>
          <p>
            Lista única de rascunhos e requisições formais criadas por você ou em que você é
            beneficiário.
          </p>
        </div>
        <div className="status-chip">
          <span className="status-dot" />
          {listQuery.data ? `${listQuery.data.count} registro(s)` : "Carregando"}
        </div>
      </div>

      <form
        className="filters-bar"
        onSubmit={(event) => {
          event.preventDefault();
          void updateSearch(searchDraft, searchParams.status);
        }}
      >
        <label className="preview-label">
          Busca
          <input
            className="preview-input"
            name="search"
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder="Número público, beneficiário ou criador"
            value={searchDraft}
          />
        </label>
        <label className="preview-label">
          Status
          <select
            className="preview-input"
            name="status"
            onChange={(event) => {
              const status = event.target.value
                ? (event.target.value as RequisicaoStatus)
                : undefined;
              void updateSearch(currentSearch, status);
            }}
            value={searchParams.status ?? ""}
          >
            <option value="">Todos</option>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <button className="preview-button filters-submit" type="submit">
          Filtrar
        </button>
      </form>

      {listQuery.isError && !authError ? (
        <div className="error-panel">{queryErrorMessage(listQuery.error)}</div>
      ) : null}

      <div className="table-frame">
        {listQuery.isPending ? (
          <div className="loading-state">Carregando requisições...</div>
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

      <div className="pagination-bar">
        <button
          className="action-link compact-action"
          disabled={currentPage <= 1 || listQuery.isPending}
          onClick={() => void goToPage(currentPage - 1)}
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
          onClick={() => void goToPage(currentPage + 1)}
          type="button"
        >
          Próxima
        </button>
      </div>
    </section>
  );
}
