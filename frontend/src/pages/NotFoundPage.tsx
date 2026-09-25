import { Link } from "react-router";
import { EmptyState } from "../components/ui";

export function NotFoundPage() {
  return (
    <EmptyState
      title="Página não encontrada"
      hint="O endereço pode estar errado, ou a página não está disponível para o seu perfil."
      action={
        <Link to="/" className="text-sm font-medium text-accent hover:underline">
          Voltar para o início
        </Link>
      }
    />
  );
}
