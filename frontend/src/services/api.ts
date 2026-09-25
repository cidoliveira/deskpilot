import type {
  Category,
  Comment,
  DashboardMetrics,
  Page,
  TicketDetail,
  TicketEvent,
  TicketPriority,
  TicketStatus,
  TicketSummary,
  Token,
  User,
  UserRole,
} from "../types/api";
import { request } from "./http";

export interface TicketListParams {
  page?: number;
  page_size?: number;
  status?: TicketStatus[];
  priority?: TicketPriority[];
  category_id?: number;
  assignee?: "me" | "none" | string;
  created_by_id?: number;
  sla_status?: string;
  q?: string;
  sort?: string;
}

export interface TicketInput {
  title: string;
  description: string;
  category_id: number;
  priority?: TicketPriority;
}

export const authApi = {
  login: (email: string, password: string) =>
    request<Token>("/auth/login", {
      method: "POST",
      form: { username: email, password },
    }),
  register: (data: { name: string; email: string; password: string }) =>
    request<User>("/auth/register", { method: "POST", json: data }),
  me: () => request<User>("/auth/me"),
};

export const ticketsApi = {
  list: (params: TicketListParams) =>
    request<Page<TicketSummary>>("/tickets", { query: { ...params } }),
  get: (id: number) => request<TicketDetail>(`/tickets/${id}`),
  create: (data: TicketInput) => request<TicketDetail>("/tickets", { method: "POST", json: data }),
  update: (id: number, data: Partial<TicketInput>) =>
    request<TicketDetail>(`/tickets/${id}`, { method: "PATCH", json: data }),
  setStatus: (id: number, status: TicketStatus, resolution?: string) =>
    request<TicketDetail>(`/tickets/${id}/status`, {
      method: "PATCH",
      json: resolution ? { status, resolution } : { status },
    }),
  assign: (id: number, assigneeId: number) =>
    request<TicketDetail>(`/tickets/${id}/assignee`, {
      method: "PUT",
      json: { assignee_id: assigneeId },
    }),
  setPriority: (id: number, priority: TicketPriority) =>
    request<TicketDetail>(`/tickets/${id}/priority`, { method: "PATCH", json: { priority } }),
  history: (id: number) => request<TicketEvent[]>(`/tickets/${id}/history`),
  comments: (id: number) => request<Comment[]>(`/tickets/${id}/comments`),
  addComment: (id: number, message: string) =>
    request<Comment>(`/tickets/${id}/comments`, { method: "POST", json: { message } }),
};

export const categoriesApi = {
  list: (includeInactive = false) =>
    request<Category[]>("/categories", { query: { include_inactive: includeInactive } }),
  create: (data: { name: string; description?: string }) =>
    request<Category>("/categories", { method: "POST", json: data }),
  update: (id: number, data: Partial<Pick<Category, "name" | "description" | "is_active">>) =>
    request<Category>(`/categories/${id}`, { method: "PATCH", json: data }),
};

export const usersApi = {
  list: (params: { role?: UserRole; is_active?: boolean; page?: number; page_size?: number }) =>
    request<Page<User>>("/users", { query: { ...params } }),
  create: (data: { name: string; email: string; password: string; role: UserRole }) =>
    request<User>("/users", { method: "POST", json: data }),
  update: (id: number, data: Partial<Pick<User, "name" | "role" | "is_active">>) =>
    request<User>(`/users/${id}`, { method: "PATCH", json: data }),
};

export const dashboardApi = {
  metrics: () => request<DashboardMetrics>("/dashboard/metrics"),
};
