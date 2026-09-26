import { Link } from "react-router";
import { useAuth } from "../auth/useAuth";
import { TicketListView } from "../components/TicketListView";
import { PageHeader } from "../components/ui";
import { useListParams } from "../hooks/useListParams";

const newTicketLink = (
  <Link
    to="/tickets/new"
    className="inline-flex rounded-md bg-accent px-3.5 py-2 text-sm font-medium text-white hover:bg-accent-strong"
  >
    Abrir chamado
  </Link>
);

export function MyTicketsPage() {
  const { user } = useAuth();
  const list = useListParams();
  if (!user) return null;

  return (
    <>
      <PageHeader eyebrow="Acompanhamento" title="Meus chamados" />
      <TicketListView
        list={list}
        preset={{ created_by_id: user.id }}
        showAuthor={false}
        empty={{
          title: "Você ainda não abriu nenhum chamado",
          hint: "Quando algo não funcionar, abra um chamado e acompanhe o atendimento por aqui.",
          action: newTicketLink,
        }}
      />
    </>
  );
}
