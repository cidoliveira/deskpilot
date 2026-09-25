// Types mirroring the backend response schemas (app/schemas/*.py).

export type UserRole = "USER" | "TECHNICIAN" | "ADMIN";

export type TicketStatus =
  | "OPEN"
  | "IN_PROGRESS"
  | "WAITING_USER"
  | "RESOLVED"
  | "CLOSED"
  | "CANCELLED";

export type TicketPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type SlaStatus = "ON_TRACK" | "AT_RISK" | "BREACHED" | "MET";

export type TicketAction =
  | "CREATED"
  | "ASSIGNED"
  | "STATUS_CHANGED"
  | "PRIORITY_CHANGED"
  | "CATEGORY_CHANGED"
  | "RESOLVED"
  | "CLOSED"
  | "REOPENED";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface UserSummary {
  id: number;
  name: string;
}

export interface User extends UserSummary {
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Token {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface Category {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TicketSummary {
  id: number;
  title: string;
  status: TicketStatus;
  priority: TicketPriority;
  category: { id: number; name: string };
  created_by: UserSummary;
  assigned_to: UserSummary | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  sla_due_at: string;
  sla_status: SlaStatus | null;
}

export interface TicketActions {
  can_edit: boolean;
  can_claim: boolean;
  can_assign: boolean;
  can_change_priority: boolean;
  can_comment: boolean;
  allowed_transitions: TicketStatus[];
}

export interface TicketDetail extends TicketSummary {
  description: string;
  resolution: string | null;
  closed_at: string | null;
  allowed_actions: TicketActions;
}

export interface TicketEvent {
  id: number;
  action: TicketAction;
  changed_by: UserSummary;
  old_value: string | null;
  new_value: string | null;
  old_label: string | null;
  new_label: string | null;
  created_at: string;
}

export interface Comment {
  id: number;
  ticket_id: number;
  author: UserSummary;
  message: string;
  created_at: string;
}

export interface DashboardMetrics {
  total: number;
  by_status: Record<TicketStatus, number>;
  by_priority: Record<TicketPriority, number>;
  by_category: { category_id: number; name: string; count: number }[];
  sla: {
    at_risk: number;
    breached_open: number;
    breached_resolved: number;
    met: number;
    compliance_rate: number | null;
  };
  avg_resolution_hours: number | null;
  by_technician: { technician: UserSummary; open: number; resolved: number }[];
}

/** Error body returned by the API for every failure. */
export interface ApiErrorBody {
  error: string;
  message: string;
  details?: { field: string; message: string }[];
}
