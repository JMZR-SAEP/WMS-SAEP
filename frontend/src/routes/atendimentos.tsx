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
  pendingFulfillmentsQueryOptions,
  queryErrorMessage,
  statusLabel,
  type RequisicaoPendingFulfillmentItem,
} from "../features/requisitions/requisitions";
import {
  ResponsiveWorklistFrame,
  WorklistEmptyState,
  WorklistErrorState,
} from "../shared/ui/worklist";

const DEFAULT_PAGE_SIZE = 20;

const fulfillmentSearchSchema = z.object({
  page: z.coerce.number().int().min(1).optional().catch(undefined),
});

export const Route = createFileRoute("/atendimentos")({
  validateSearch: fulfillmentSearchSchema,
  beforeLoad: ({ context, location }) =>
    requireOperationalPapel({
      allowedPapeis: ["auxiliar_almoxarifado", "chefe_almoxarifado"],
      queryClient: context.queryClient,
      locationHref: location.href,
    }),
  component: AtendimentosPage,
});

function EmptyState() {
  return (
    <WorklistEmptyState
      description="A fila mostra requisições autorizadas aguardando retirada pelo Almoxarifado."
      eyebrow="Sem pendências"
      title="Nenhum atendimento pendente"
    />
  );
}

function AtendimentoCard({
  currentPage,
  requisicao,
}: {
  currentPage: number;
  requisicao: RequisicaoPendingFulfillmentItem;
}) {
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
        <span className={`req-status req-status-${requisicao.status}`}>
          {statusLabel(requisicao.status)}
        </span>
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
          <dt>Autorizador</dt>
          <dd>{requisicao.chefe_autorizador.nome_completo}</dd>
        </div>
        <div>
          <dt>Autorização</dt>
          <dd>{formatDateTime(requisicao.data_autorizacao_ou_recusa)}</dd>
        </div>
      </dl>

      <div className="worklist-card-footer">
        <Link
          className="action-link compact-action"
          params={{ id: String(requisicao.id) }}
          search={{ contexto: "atendimento", page: currentPage === 1 ? undefined : currentPage }}
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

function AtendimentosPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate({ from: "/atendimentos" });
  const searchParams = Route.useSearch();
  const currentPage = searchParams.page ?? 1;
  const listQuery = useQuery(
    pendingFulfillmentsQueryOptions({
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
  const columns = useMemo<ColumnDef<RequisicaoPendingFulfillmentItem>[]>(
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
        id: "authorizer",
        header: "Autorizador",
        cell: ({ row }) => <span>{row.original.chefe_autorizador.nome_completo}</span>,
      },
      {
        id: "authorized_at",
        header: "Autorização",
        cell: ({ row }) => (
          <span className="text-sm text-[var(--ink-soft)]">
            {formatDateTime(row.original.data_autorizacao_ou_recusa)}
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
            search={{ contexto: "atendimento", page: currentPage === 1 ? undefined : currentPage }}
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
        redirect: currentPage === 1 ? "/atendimentos" : `/atendimentos?page=${currentPage}`,
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
          <h1>Fila de atendimento</h1>
          <p>Requisições autorizadas aguardando retirada pelo Almoxarifado.</p>
        </div>
        <div className="status-chip">
          <span className="status-dot" />
          {recordsLabel}
        </div>
      </div>

      {listQuery.isError ? (
        <WorklistErrorState>
          {queryErrorMessage(listQuery.error, "Não foi possível carregar atendimentos pendentes.")}
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
            <div aria-label="Cards da fila de atendimento" className="worklist-card-list">
              {rows.map((requisicao) => (
                <AtendimentoCard
                  currentPage={currentPage}
                  key={requisicao.id}
                  requisicao={requisicao}
                />
              ))}
            </div>
          }
          skeletonLabel="Carregando atendimentos"
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
