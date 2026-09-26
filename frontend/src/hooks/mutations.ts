import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ticketsApi, type TicketInput } from "../services/api";
import type { TicketDetail, TicketPriority, TicketStatus } from "../types/api";
import { keys } from "./queries";

/**
 * After any change to a ticket: put the fresh ticket returned by the API in the cache
 * (no extra request for the detail) and mark lists, history and metrics as stale.
 */
function useTicketUpdater() {
  const queryClient = useQueryClient();
  return (ticket: TicketDetail) => {
    queryClient.setQueryData(keys.ticket(ticket.id), ticket);
    void queryClient.invalidateQueries({ queryKey: keys.tickets });
    void queryClient.invalidateQueries({ queryKey: keys.dashboard });
  };
}

export function useCreateTicket() {
  const onSuccess = useTicketUpdater();
  return useMutation({ mutationFn: (data: TicketInput) => ticketsApi.create(data), onSuccess });
}

export function useUpdateTicket(id: number) {
  const onSuccess = useTicketUpdater();
  return useMutation({
    mutationFn: (data: Partial<TicketInput>) => ticketsApi.update(id, data),
    onSuccess,
  });
}

export function useChangeStatus(id: number) {
  const onSuccess = useTicketUpdater();
  return useMutation({
    mutationFn: ({ status, resolution }: { status: TicketStatus; resolution?: string }) =>
      ticketsApi.setStatus(id, status, resolution),
    onSuccess,
  });
}

export function useAssign(id: number) {
  const onSuccess = useTicketUpdater();
  return useMutation({
    mutationFn: (assigneeId: number) => ticketsApi.assign(id, assigneeId),
    onSuccess,
  });
}

export function useChangePriority(id: number) {
  const onSuccess = useTicketUpdater();
  return useMutation({
    mutationFn: (priority: TicketPriority) => ticketsApi.setPriority(id, priority),
    onSuccess,
  });
}

export function useAddComment(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (message: string) => ticketsApi.addComment(id, message),
    // A comment can change the ticket too (author answering WAITING_USER resumes it).
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.ticket(id) }),
  });
}
