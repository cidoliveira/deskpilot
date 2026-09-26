import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  categoriesApi,
  dashboardApi,
  ticketsApi,
  usersApi,
  type TicketListParams,
} from "../services/api";

/** Query keys in one place, so mutations know exactly what to refresh. */
export const keys = {
  tickets: ["tickets"] as const,
  ticketList: (params: TicketListParams) => ["tickets", "list", params] as const,
  ticket: (id: number) => ["tickets", "detail", id] as const,
  history: (id: number) => ["tickets", "detail", id, "history"] as const,
  comments: (id: number) => ["tickets", "detail", id, "comments"] as const,
  categories: (includeInactive: boolean) => ["categories", { includeInactive }] as const,
  users: (params: object) => ["users", params] as const,
  dashboard: ["dashboard"] as const,
};

export function useTicketList(params: TicketListParams) {
  return useQuery({
    queryKey: keys.ticketList(params),
    queryFn: () => ticketsApi.list(params),
    // Keep showing the previous page while the next one loads (no flashing table).
    placeholderData: keepPreviousData,
  });
}

export function useTicket(id: number) {
  return useQuery({ queryKey: keys.ticket(id), queryFn: () => ticketsApi.get(id) });
}

export function useTicketHistory(id: number) {
  return useQuery({ queryKey: keys.history(id), queryFn: () => ticketsApi.history(id) });
}

export function useComments(id: number) {
  return useQuery({ queryKey: keys.comments(id), queryFn: () => ticketsApi.comments(id) });
}

export function useCategories(includeInactive = false) {
  return useQuery({
    queryKey: keys.categories(includeInactive),
    queryFn: () => categoriesApi.list(includeInactive),
    staleTime: 5 * 60_000,
  });
}

export function useStaff(enabled: boolean) {
  const params = { role: "TECHNICIAN", is_active: true, page_size: 100 } as const;
  return useQuery({
    queryKey: keys.users(params),
    queryFn: () => usersApi.list(params),
    enabled,
  });
}

export function useDashboard() {
  return useQuery({ queryKey: keys.dashboard, queryFn: dashboardApi.metrics });
}
