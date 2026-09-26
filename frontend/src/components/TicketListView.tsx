import type { ReactNode } from "react";
import { useTicketList } from "../hooks/queries";
import type { useListParams } from "../hooks/useListParams";
import type { TicketListParams } from "../services/api";
import { Pagination } from "./Pagination";
import { TicketFilters } from "./TicketFilters";
import { TicketTable } from "./TicketTable";
import { Card, EmptyState, ErrorBanner, Spinner } from "./ui";

interface TicketListViewProps {
  list: ReturnType<typeof useListParams>;
  /** Fixed parameters of the view (e.g. "assigned to me"), merged with the URL filters. */
  preset?: Partial<TicketListParams>;
  showAuthor?: boolean;
  empty: { title: string; hint?: string; action?: ReactNode };
}

export function TicketListView({ list, preset = {}, showAuthor, empty }: TicketListViewProps) {
  const params = { ...list.apiParams, ...preset };
  if (list.apiParams.status) params.status = list.apiParams.status; // explicit filter wins
  const query = useTicketList(params);

  return (
    <Card>
      <TicketFilters
        filters={list.filters}
        setFilter={list.setFilter}
        clearFilters={list.clearFilters}
        hasFilters={list.hasFilters}
      />
      {query.isPending && <Spinner />}
      {query.isError && (
        <div className="p-4">
          <ErrorBanner error={query.error} />
        </div>
      )}
      {query.data && query.data.items.length === 0 && (
        <EmptyState
          {...(list.hasFilters
            ? {
                title: "Nenhum chamado com esses filtros",
                hint: "Tente limpar ou mudar os filtros.",
              }
            : empty)}
        />
      )}
      {query.data && query.data.items.length > 0 && (
        <div className={query.isPlaceholderData ? "opacity-60 transition-opacity" : undefined}>
          <TicketTable tickets={query.data.items} showAuthor={showAuthor} />
          <Pagination
            page={query.data.page}
            pages={query.data.pages}
            total={query.data.total}
            onChange={(page) => list.setFilter("page", String(page))}
          />
        </div>
      )}
    </Card>
  );
}
