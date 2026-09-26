import { fieldMessage } from "../lib/validation";
import type { ApiErrorBody } from "../types/api";

const API_BASE = "/api/v1";
const TOKEN_KEY = "deskpilot.token";

/** Error with the backend's `{ error, message, details }` contract. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ApiErrorBody["details"];

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.error;
    this.details = body.details;
  }

  /** Validation message for one field (in PT-BR), if the API reported one. */
  fieldError(field: string): string | undefined {
    const detail = this.details?.find((item) => item.field === field);
    return detail && fieldMessage(detail);
  }
}

// [PORTFOLIO] The token lives in localStorage for simplicity. In production an
// httpOnly cookie (plus CSRF protection) keeps it out of reach of injected scripts.
export const tokenStorage = {
  get: (): string | null => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

let onUnauthorized: () => void = () => {};

/** Called by the auth layer: what to do when the API says the session is over. */
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

type Query = Record<string, string | number | boolean | string[] | undefined | null>;

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH";
  json?: unknown;
  form?: Record<string, string>;
  query?: Query;
}

function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === null || value === "") continue;
    for (const item of Array.isArray(value) ? value : [value]) params.append(key, String(item));
  }
  const search = params.toString();
  return `${API_BASE}${path}${search ? `?${search}` : ""}`;
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    return new ApiError(response.status, (await response.json()) as ApiErrorBody);
  } catch {
    // Not our JSON contract (e.g. proxy error page): still return a usable message.
    return new ApiError(response.status, {
      error: "network_error",
      message: "Não foi possível falar com o servidor. Tente novamente em instantes.",
    });
  }
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = tokenStorage.get();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  } else if (options.form) {
    body = new URLSearchParams(options.form);
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), {
      method: options.method ?? "GET",
      headers,
      body,
    });
  } catch {
    throw new ApiError(0, {
      error: "network_error",
      message: "Sem conexão com o servidor. Verifique sua rede.",
    });
  }

  if (!response.ok) {
    const error = await parseError(response);
    if (response.status === 401 && token) onUnauthorized();
    throw error;
  }
  return (await response.json()) as T;
}
