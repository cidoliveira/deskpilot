import type {
  Category,
  Comment,
  DashboardMetrics,
  Page,
  TicketActions,
  TicketDetail,
  TicketEvent,
  TicketSummary,
  User,
  UserRole,
} from "../types/api";

const hoursAgo = (hours: number) => new Date(Date.now() - hours * 3_600_000).toISOString();
const inHours = (hours: number) => new Date(Date.now() + hours * 3_600_000).toISOString();

export function makeUser(role: UserRole, overrides: Partial<User> = {}): User {
  const names = { USER: "Ana Souza", TECHNICIAN: "Carla Mendes", ADMIN: "Admin" };
  return {
    id: { USER: 1, TECHNICIAN: 2, ADMIN: 3 }[role],
    name: names[role],
    email: `${role.toLowerCase()}@example.com`,
    role,
    is_active: true,
    created_at: hoursAgo(100),
    updated_at: hoursAgo(100),
    ...overrides,
  };
}

export const ana = makeUser("USER");
export const carla = makeUser("TECHNICIAN");
export const admin = makeUser("ADMIN");

export const categories: Category[] = [
  {
    id: 10,
    name: "Hardware",
    description: "Equipamentos",
    is_active: true,
    created_at: hoursAgo(500),
    updated_at: hoursAgo(500),
  },
  {
    id: 11,
    name: "Network",
    description: "Rede e VPN",
    is_active: true,
    created_at: hoursAgo(500),
    updated_at: hoursAgo(500),
  },
];

export function makeTicket(overrides: Partial<TicketSummary> = {}): TicketSummary {
  return {
    id: 42,
    title: "VPN não conecta",
    status: "OPEN",
    priority: "HIGH",
    category: { id: 11, name: "Network" },
    created_by: { id: ana.id, name: ana.name },
    assigned_to: null,
    created_at: hoursAgo(2),
    updated_at: hoursAgo(1),
    resolved_at: null,
    sla_due_at: inHours(6),
    sla_status: "ON_TRACK",
    ...overrides,
  };
}

const NO_ACTIONS: TicketActions = {
  can_edit: false,
  can_claim: false,
  can_assign: false,
  can_change_priority: false,
  can_comment: true,
  allowed_transitions: [],
};

export function makeDetail(
  overrides: Partial<TicketDetail> = {},
  actions: Partial<TicketActions> = {},
): TicketDetail {
  return {
    ...makeTicket(),
    description: "Erro 809 ao conectar de casa.",
    resolution: null,
    closed_at: null,
    ...overrides,
    allowed_actions: { ...NO_ACTIONS, ...actions },
  };
}

export function page<T>(items: T[], overrides: Partial<Page<T>> = {}): Page<T> {
  return { items, total: items.length, page: 1, page_size: 15, pages: 1, ...overrides };
}

export const history: TicketEvent[] = [
  {
    id: 1,
    action: "CREATED",
    changed_by: { id: ana.id, name: ana.name },
    old_value: null,
    new_value: "OPEN",
    old_label: null,
    new_label: null,
    created_at: hoursAgo(2),
  },
  {
    id: 2,
    action: "ASSIGNED",
    changed_by: { id: carla.id, name: carla.name },
    old_value: null,
    new_value: String(carla.id),
    old_label: null,
    new_label: carla.name,
    created_at: hoursAgo(1),
  },
];

export const comments: Comment[] = [
  {
    id: 1,
    ticket_id: 42,
    author: { id: carla.id, name: carla.name },
    message: "Pode mandar um print?",
    created_at: hoursAgo(1),
  },
];

export const metrics: DashboardMetrics = {
  total: 9,
  by_status: { OPEN: 2, IN_PROGRESS: 2, WAITING_USER: 1, RESOLVED: 1, CLOSED: 2, CANCELLED: 1 },
  by_priority: { LOW: 2, MEDIUM: 3, HIGH: 3, CRITICAL: 1 },
  by_category: [{ category_id: 11, name: "Network", count: 4 }],
  sla: { at_risk: 1, breached_open: 1, breached_resolved: 1, met: 2, compliance_rate: 0.6667 },
  avg_resolution_hours: 6,
  by_technician: [{ technician: { id: carla.id, name: carla.name }, open: 2, resolved: 1 }],
};
