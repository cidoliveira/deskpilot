import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { routes } from "../routes/router";
import { tokenStorage } from "../services/http";
import type { User } from "../types/api";

export interface Reply {
  status: number;
  body: unknown;
}

/** A non-200 answer, e.g. reply(404, { error: "ticket_not_found", message: "..." }). */
export const reply = (status: number, body: unknown): Reply => ({ status, body });

type Handler = unknown | Reply | ((request: RecordedRequest) => unknown | Reply);

export interface RecordedRequest {
  method: string;
  path: string;
  query: URLSearchParams;
  body: unknown;
}

/**
 * Fake API: handlers are keyed by "METHOD /path" (path without /api/v1 and without the
 * query string). Unknown routes answer 404, so a missing handler is visible in the test.
 */
export function mockApi(handlers: Record<string, Handler>) {
  const requests: RecordedRequest[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = new URL(String(input), "http://localhost");
    const path = url.pathname.replace(/^\/api\/v1/, "");
    const method = (init.method ?? "GET").toUpperCase();
    let body: unknown = init.body;
    if (typeof body === "string") body = JSON.parse(body);
    else if (body instanceof URLSearchParams) body = Object.fromEntries(body);
    const request = { method, path, query: url.searchParams, body };
    requests.push(request);

    const handler = handlers[`${method} ${path}`];
    const result = typeof handler === "function" ? handler(request) : handler;
    const { status, body: payload } =
      result === undefined
        ? reply(404, { error: "not_found", message: `No mock for ${method} ${path}` })
        : result && typeof result === "object" && "status" in result && "body" in result
          ? (result as Reply)
          : { status: 200, body: result };
    return new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);

  return {
    requests,
    /** Requests matching "METHOD /path", most recent last. */
    calls: (key: string) => requests.filter((r) => `${r.method} ${r.path}` === key),
  };
}

/** Renders the whole app (routes, guards, providers) at `path`, optionally signed in. */
export function renderApp(path: string, options: { user?: User; api?: Record<string, Handler> }) {
  const api = mockApi({
    ...(options.user ? { "GET /auth/me": options.user } : {}),
    ...options.api,
  });
  if (options.user) tokenStorage.set("test-token");

  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>,
  );
  return { api, router };
}
