import { PRIORITY_LABEL, STATUS_LABEL } from "./labels";
import type { TicketEvent, TicketPriority, TicketStatus } from "../types/api";

const status = (value: string | null) => STATUS_LABEL[value as TicketStatus] ?? value;
const priority = (value: string | null) => PRIORITY_LABEL[value as TicketPriority] ?? value;

/** One readable sentence per audit event (the actor's name is shown separately). */
export function describeEvent(event: TicketEvent): string {
  switch (event.action) {
    case "CREATED":
      return "abriu o chamado";
    case "ASSIGNED":
      if (event.new_value === String(event.changed_by.id)) return "assumiu o chamado";
      return event.old_value
        ? `transferiu de ${event.old_label} para ${event.new_label}`
        : `atribuiu a ${event.new_label}`;
    case "STATUS_CHANGED":
      return `mudou de ${status(event.old_value)} para ${status(event.new_value)}`;
    case "PRIORITY_CHANGED":
      return `mudou a prioridade de ${priority(event.old_value)} para ${priority(event.new_value)}`;
    case "CATEGORY_CHANGED":
      return `mudou a categoria de ${event.old_label} para ${event.new_label}`;
    case "RESOLVED":
      return "resolveu o chamado";
    case "CLOSED":
      return "confirmou a solução e fechou o chamado";
    case "REOPENED":
      return "reabriu o chamado";
  }
}
