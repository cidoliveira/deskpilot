import { useEffect, useState } from "react";
import { useCategories } from "../hooks/queries";
import type { ListFilters, useListParams } from "../hooks/useListParams";
import {
  ACTIVE_STATUSES,
  PRIORITIES,
  PRIORITY_LABEL,
  SLA_LABEL,
  SLA_STATUSES,
  STATUSES,
  STATUS_LABEL,
} from "../lib/labels";
import { FilterSelect } from "./fields";

const SORTS: [string, string][] = [
  ["-created_at", "Mais recentes"],
  ["created_at", "Mais antigos"],
  ["sla_due_at", "Prazo mais próximo"],
  ["-priority", "Maior prioridade"],
  ["-updated_at", "Atualizados recentemente"],
];

type Params = ReturnType<typeof useListParams>;

interface TicketFiltersProps {
  filters: ListFilters;
  setFilter: Params["setFilter"];
  clearFilters: Params["clearFilters"];
  hasFilters: boolean;
  /** Presets (like queue views) may fix the status; then the status filter is hidden. */
  showStatus?: boolean;
}

export function TicketFilters({
  filters,
  setFilter,
  clearFilters,
  hasFilters,
  showStatus = true,
}: TicketFiltersProps) {
  const categories = useCategories();
  const [search, setSearch] = useState(filters.q);
  const [syncedQ, setSyncedQ] = useState(filters.q);

  // The URL can change `q` from outside (clear filters, back button): follow it, unless it
  // is just the debounced version of what is being typed (don't eat a trailing space).
  if (filters.q !== syncedQ) {
    setSyncedQ(filters.q);
    if (filters.q !== search.trim()) setSearch(filters.q);
  }

  // Search as you type, but only after a short pause (one request, not one per key).
  useEffect(() => {
    if (search === filters.q) return;
    const timer = setTimeout(() => setFilter("q", search.trim()), 350);
    return () => clearTimeout(timer);
  }, [search, filters.q, setFilter]);

  return (
    <div className="flex flex-wrap items-end gap-3 border-b border-line px-4 py-3">
      <label className="flex min-w-48 flex-1 flex-col gap-1">
        <span className="label-caps">Buscar</span>
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Título ou descrição"
          className="rounded-md border border-line bg-surface px-2.5 py-1.5 text-sm focus:border-accent focus:outline-none"
        />
      </label>
      {showStatus && (
        <FilterSelect
          label="Status"
          value={filters.status}
          onChange={(event) => setFilter("status", event.target.value)}
        >
          <option value="">Todos</option>
          <option value={ACTIVE_STATUSES.join(",")}>Em aberto (todos os ativos)</option>
          {STATUSES.map((status) => (
            <option key={status} value={status}>
              {STATUS_LABEL[status]}
            </option>
          ))}
        </FilterSelect>
      )}
      <FilterSelect
        label="Prioridade"
        value={filters.priority}
        onChange={(event) => setFilter("priority", event.target.value)}
      >
        <option value="">Todas</option>
        {PRIORITIES.map((priority) => (
          <option key={priority} value={priority}>
            {PRIORITY_LABEL[priority]}
          </option>
        ))}
      </FilterSelect>
      <FilterSelect
        label="Categoria"
        value={filters.category_id}
        onChange={(event) => setFilter("category_id", event.target.value)}
      >
        <option value="">Todas</option>
        {categories.data?.map((category) => (
          <option key={category.id} value={category.id}>
            {category.name}
          </option>
        ))}
      </FilterSelect>
      <FilterSelect
        label="SLA"
        value={filters.sla_status}
        onChange={(event) => setFilter("sla_status", event.target.value)}
      >
        <option value="">Qualquer</option>
        {SLA_STATUSES.map((status) => (
          <option key={status} value={status}>
            {SLA_LABEL[status]}
          </option>
        ))}
      </FilterSelect>
      <FilterSelect
        label="Ordenar"
        value={filters.sort}
        onChange={(event) => setFilter("sort", event.target.value)}
      >
        {SORTS.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </FilterSelect>
      {hasFilters && (
        <button
          type="button"
          onClick={clearFilters}
          className="pb-2 text-sm text-accent hover:underline"
        >
          Limpar filtros
        </button>
      )}
    </div>
  );
}
