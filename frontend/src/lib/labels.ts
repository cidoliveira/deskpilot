import type { SlaStatus, TicketPriority, TicketStatus, UserRole } from "../types/api";

export const STATUS_LABEL: Record<TicketStatus, string> = {
  OPEN: "Aberto",
  IN_PROGRESS: "Em andamento",
  WAITING_USER: "Aguardando usuário",
  RESOLVED: "Resolvido",
  CLOSED: "Fechado",
  CANCELLED: "Cancelado",
};

export const PRIORITY_LABEL: Record<TicketPriority, string> = {
  LOW: "Baixa",
  MEDIUM: "Média",
  HIGH: "Alta",
  CRITICAL: "Crítica",
};

export const SLA_LABEL: Record<SlaStatus, string> = {
  ON_TRACK: "No prazo",
  AT_RISK: "Em risco",
  BREACHED: "Violado",
  MET: "Cumprido",
};

export const ROLE_LABEL: Record<UserRole, string> = {
  USER: "Usuário",
  TECHNICIAN: "Técnico",
  ADMIN: "Administrador",
};

/** Verb shown on the button that moves a ticket to each status. */
export const TRANSITION_LABEL: Record<TicketStatus, string> = {
  OPEN: "Reabrir",
  IN_PROGRESS: "Iniciar atendimento",
  WAITING_USER: "Aguardar usuário",
  RESOLVED: "Resolver",
  CLOSED: "Confirmar e fechar",
  CANCELLED: "Cancelar chamado",
};

export const STATUSES = Object.keys(STATUS_LABEL) as TicketStatus[];
export const PRIORITIES = Object.keys(PRIORITY_LABEL) as TicketPriority[];
export const SLA_STATUSES = Object.keys(SLA_LABEL) as SlaStatus[];
