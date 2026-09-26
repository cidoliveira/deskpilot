import { useState, type FormEvent } from "react";
import { useUpdateTicket } from "../../hooks/mutations";
import { useCategories } from "../../hooks/queries";
import type { TicketDetail } from "../../types/api";
import { SelectField, TextArea, TextField } from "../fields";
import { Button, ErrorBanner } from "../ui";

interface TicketEditFormProps {
  ticket: TicketDetail;
  onDone: () => void;
}

export function TicketEditForm({ ticket, onDone }: TicketEditFormProps) {
  const categories = useCategories();
  const update = useUpdateTicket(ticket.id);
  // Controlled on purpose: with defaultValue, the options arriving after the form opened
  // made the browser select the first category, silently changing it on save.
  const [categoryId, setCategoryId] = useState(ticket.category.id);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    update.mutate(
      {
        title: String(form.get("title")).trim(),
        description: String(form.get("description")).trim(),
        category_id: categoryId,
      },
      { onSuccess: onDone },
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorBanner error={update.error} />
      <TextField label="Resumo" name="title" defaultValue={ticket.title} maxLength={200} />
      <SelectField
        label="Categoria"
        name="category_id"
        value={categoryId}
        onChange={(event) => setCategoryId(Number(event.target.value))}
      >
        {/* Keep the current category listed even if it was deactivated meanwhile. */}
        {!categories.data?.some((category) => category.id === ticket.category.id) && (
          <option value={ticket.category.id}>{ticket.category.name}</option>
        )}
        {categories.data?.map((category) => (
          <option key={category.id} value={category.id}>
            {category.name}
          </option>
        ))}
      </SelectField>
      <TextArea label="Descrição" name="description" rows={6} defaultValue={ticket.description} />
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onDone}>
          Descartar
        </Button>
        <Button type="submit" busy={update.isPending}>
          Salvar alterações
        </Button>
      </div>
    </form>
  );
}
