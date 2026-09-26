import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { SelectField, TextArea, TextField } from "../components/fields";
import { Button, Card, ErrorBanner, PageHeader } from "../components/ui";
import { useCreateTicket } from "../hooks/mutations";
import { useCategories } from "../hooks/queries";
import { PRIORITIES, PRIORITY_LABEL } from "../lib/labels";
import { ApiError } from "../services/http";
import type { TicketPriority } from "../types/api";

// Mirrors the backend SLA table, so people know what each priority means before choosing.
const SLA_HINT: Record<TicketPriority, string> = {
  LOW: "resolução em até 48 h",
  MEDIUM: "resolução em até 24 h",
  HIGH: "resolução em até 8 h",
  CRITICAL: "resolução em até 4 h: use quando o trabalho está parado",
};

type Errors = Partial<Record<"title" | "description" | "category_id", string>>;

function validate(form: FormData): Errors {
  const errors: Errors = {};
  if (String(form.get("title")).trim().length < 5) errors.title = "Use pelo menos 5 caracteres.";
  if (String(form.get("description")).trim().length < 10) {
    errors.description = "Conte um pouco mais: o que acontece e desde quando.";
  }
  if (!form.get("category_id")) errors.category_id = "Escolha uma categoria.";
  return errors;
}

export function NewTicketPage() {
  const navigate = useNavigate();
  const categories = useCategories();
  const createTicket = useCreateTicket();
  const [errors, setErrors] = useState<Errors>({});
  const [priority, setPriority] = useState<TicketPriority>("MEDIUM");

  const apiError = createTicket.error instanceof ApiError ? createTicket.error : null;
  const fieldError = (field: keyof Errors) => errors[field] ?? apiError?.fieldError(field);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    createTicket.mutate(
      {
        title: String(form.get("title")).trim(),
        description: String(form.get("description")).trim(),
        category_id: Number(form.get("category_id")),
        priority,
      },
      { onSuccess: (ticket) => navigate(`/tickets/${ticket.id}`) },
    );
  }

  return (
    <>
      <PageHeader eyebrow="Novo chamado" title="Abrir chamado" />
      <Card className="max-w-2xl p-6">
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {createTicket.isError && apiError?.code !== "validation_error" && (
            <ErrorBanner error={createTicket.error} />
          )}
          <TextField
            label="Resumo do problema"
            name="title"
            placeholder="Ex.: VPN não conecta fora do escritório"
            maxLength={200}
            error={fieldError("title")}
          />
          <div className="grid gap-5 sm:grid-cols-2">
            <SelectField
              label="Categoria"
              name="category_id"
              defaultValue=""
              error={fieldError("category_id")}
            >
              <option value="" disabled>
                Escolha…
              </option>
              {categories.data?.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </SelectField>
            <SelectField
              label="Prioridade"
              name="priority"
              value={priority}
              onChange={(event) => setPriority(event.target.value as TicketPriority)}
              hint={SLA_HINT[priority]}
            >
              {PRIORITIES.map((value) => (
                <option key={value} value={value}>
                  {PRIORITY_LABEL[value]}
                </option>
              ))}
            </SelectField>
          </div>
          <TextArea
            label="Descrição"
            name="description"
            rows={6}
            placeholder="O que acontece, desde quando, e o que você já tentou."
            error={fieldError("description")}
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => navigate(-1)}>
              Voltar
            </Button>
            <Button type="submit" busy={createTicket.isPending}>
              Abrir chamado
            </Button>
          </div>
        </form>
      </Card>
    </>
  );
}
