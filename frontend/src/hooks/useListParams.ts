import { useSearchParams } from "react-router";
import type { TicketListParams } from "../services/api";
import type { TicketPriority, TicketStatus } from "../types/api";

/** Filters that live in the URL, so a filtered list can be reloaded or shared as a link. */
export interface ListFilters {
  q: string;
  status: string;
  priority: string;
  category_id: string;
  sla_status: string;
  sort: string;
  page: number;
}

const FILTER_KEYS = ["q", "status", "priority", "category_id", "sla_status", "sort"] as const;

export function useListParams(defaultSort = "-created_at") {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters: ListFilters = {
    q: searchParams.get("q") ?? "",
    status: searchParams.get("status") ?? "",
    priority: searchParams.get("priority") ?? "",
    category_id: searchParams.get("category_id") ?? "",
    sla_status: searchParams.get("sla_status") ?? "",
    sort: searchParams.get("sort") ?? defaultSort,
    page: Number(searchParams.get("page") ?? 1) || 1,
  };

  /** Change one filter; any filter change goes back to page 1. */
  function setFilter(key: (typeof FILTER_KEYS)[number] | "page", value: string) {
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (value) next.set(key, value);
        else next.delete(key);
        if (key !== "page") next.delete("page");
        return next;
      },
      { replace: true },
    );
  }

  function clearFilters() {
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        FILTER_KEYS.forEach((key) => next.delete(key));
        next.delete("page");
        return next;
      },
      { replace: true },
    );
  }

  const hasFilters = FILTER_KEYS.some((key) => key !== "sort" && filters[key] !== "");

  const apiParams: TicketListParams = {
    page: filters.page,
    page_size: 15,
    q: filters.q || undefined,
    // Comma-separated, so one URL value can mean "any active status".
    status: filters.status ? (filters.status.split(",") as TicketStatus[]) : undefined,
    priority: filters.priority ? [filters.priority as TicketPriority] : undefined,
    category_id: filters.category_id ? Number(filters.category_id) : undefined,
    sla_status: filters.sla_status || undefined,
    sort: filters.sort,
  };

  return { filters, apiParams, setFilter, clearFilters, hasFilters, searchParams, setSearchParams };
}
