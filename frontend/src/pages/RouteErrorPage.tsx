import { isRouteErrorResponse, Link, useRouteError } from "react-router";
import { Brand } from "../components/AppLayout";

/**
 * Shown when a screen throws while rendering. The rest of the app is not lost: the user
 * can reload or go back to the start, instead of staring at a blank page.
 */
export function RouteErrorPage() {
  const error = useRouteError();
  const notFound = isRouteErrorResponse(error) && error.status === 404;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center">
      <Brand />
      <div>
        <h1 className="font-display text-2xl font-semibold">
          {notFound ? "Página não encontrada" : "Esta tela parou de funcionar"}
        </h1>
        <p className="mx-auto mt-2 max-w-md text-sm text-ink-soft">
          {notFound
            ? "O endereço pode estar errado."
            : "Seus dados estão salvos. Recarregue a página; se o problema continuar, avise o suporte."}
        </p>
      </div>
      <div className="flex gap-2">
        {!notFound && (
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="rounded-md bg-accent px-3.5 py-2 text-sm font-medium text-white hover:bg-accent-strong"
          >
            Recarregar
          </button>
        )}
        <Link
          to="/"
          className="rounded-md border border-line bg-surface px-3.5 py-2 text-sm font-medium hover:border-ink/30"
        >
          Ir para o início
        </Link>
      </div>
    </div>
  );
}
