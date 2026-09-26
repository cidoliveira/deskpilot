import { useState, type FormEvent } from "react";
import { useAddComment } from "../../hooks/mutations";
import { useComments } from "../../hooks/queries";
import { formatDateTime } from "../../lib/format";
import type { TicketDetail, User } from "../../types/api";
import { Button, ErrorBanner, Spinner } from "../ui";

interface CommentThreadProps {
  ticket: TicketDetail;
  currentUser: User;
}

export function CommentThread({ ticket, currentUser }: CommentThreadProps) {
  const comments = useComments(ticket.id);
  const addComment = useAddComment(ticket.id);
  const [message, setMessage] = useState("");
  const waitingForMe = ticket.status === "WAITING_USER" && ticket.created_by.id === currentUser.id;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = message.trim();
    if (!text) return;
    addComment.mutate(text, { onSuccess: () => setMessage("") });
  }

  return (
    <section aria-labelledby="conversation-title">
      <h2 id="conversation-title" className="label-caps mb-3">
        Conversa
      </h2>
      {comments.isPending && <Spinner />}
      <ErrorBanner error={comments.error} />
      {comments.data?.length === 0 && (
        <p className="mb-4 text-sm text-ink-soft">Nenhuma mensagem ainda.</p>
      )}
      <ul className="space-y-3">
        {comments.data?.map((comment) => {
          const fromAuthor = comment.author.id === ticket.created_by.id;
          return (
            <li
              key={comment.id}
              className={`rounded-lg border px-4 py-3 ${
                fromAuthor ? "border-line bg-surface" : "border-accent/20 bg-accent-soft/60"
              }`}
            >
              <p className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
                <span className="font-medium">
                  {comment.author.name}
                  {!fromAuthor && <span className="ml-2 text-xs text-ink-soft">suporte</span>}
                </span>
                <time
                  dateTime={comment.created_at}
                  className="font-mono text-[11px] text-ink-faint"
                >
                  {formatDateTime(comment.created_at)}
                </time>
              </p>
              <p className="mt-1 text-sm whitespace-pre-line text-ink">{comment.message}</p>
            </li>
          );
        })}
      </ul>

      {ticket.allowed_actions.can_comment ? (
        <form onSubmit={handleSubmit} className="mt-4 space-y-2">
          {waitingForMe && (
            <p className="rounded-md border border-sla-risk/40 bg-sla-risk/10 px-3 py-2 text-sm text-ink">
              O técnico aguarda a sua resposta. Ao responder, o atendimento é retomado.
            </p>
          )}
          <label htmlFor="comment" className="sr-only">
            Nova mensagem
          </label>
          <textarea
            id="comment"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            rows={3}
            maxLength={5000}
            placeholder="Escreva uma mensagem…"
            className="w-full resize-y rounded-md border border-line bg-surface px-3 py-2 text-sm focus:border-accent focus:outline-none"
          />
          <ErrorBanner error={addComment.error} />
          <div className="flex justify-end">
            <Button type="submit" busy={addComment.isPending} disabled={!message.trim()}>
              Enviar mensagem
            </Button>
          </div>
        </form>
      ) : (
        <p className="mt-4 text-sm text-ink-soft">Chamado encerrado: não recebe novas mensagens.</p>
      )}
    </section>
  );
}
