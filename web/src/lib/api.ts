import type { User } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const ACCESS = "prepiba:access";
const REFRESH = "prepiba:refresh";

export class ApiError extends Error {
  constructor(public status: number, public data: unknown) {
    super(messageOf(data) ?? `Request failed (${status})`);
  }
}

function messageOf(data: unknown): string | null {
  if (!data || typeof data !== "object") return null;
  const d = data as Record<string, unknown>;
  const first = d.detail ?? Object.values(d)[0];
  if (Array.isArray(first)) return String(first[0]);
  return typeof first === "string" ? first : null;
}

function read(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}
function write(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch { /* private mode */ }
}

export const tokens = {
  access: () => read(ACCESS),
  has: () => read(ACCESS) !== null,
  set: (access: string, refresh: string) => { write(ACCESS, access); write(REFRESH, refresh); },
  clear: () => { write(ACCESS, null); write(REFRESH, null); },
};

let refreshing: Promise<boolean> | null = null;

async function refreshAccess(): Promise<boolean> {
  const refresh = read(REFRESH);
  if (!refresh) return false;
  refreshing ??= fetch(buildUrl("/auth/refresh/"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  })
    .then(async (r) => {
      if (!r.ok) return false;
      const d = await r.json();
      tokens.set(d.access, d.refresh ?? refresh);
      return true;
    })
    .catch(() => false)
    .finally(() => { refreshing = null; });
  return refreshing;
}

type Query = Record<string, string | number | boolean | undefined | null>;

function buildUrl(path: string, query?: Query): URL {
  // A relative API_URL ("/api/v1") means "same origin as the page", which is how the Docker/nginx setup runs.
  const url = new URL(`${API_URL}${path}`, API_URL.startsWith("/") ? window.location.origin : undefined);
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
  }
  return url;
}

/** fetch() with the bearer token attached and one transparent refresh-and-retry on 401. */
export async function authedFetch(path: string, init: { method?: string; body?: unknown; query?: Query; signal?: AbortSignal } = {}) {
  const send = () =>
    fetch(buildUrl(path, init.query), {
      method: init.method ?? "GET",
      signal: init.signal,
      headers: {
        ...(init.body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(tokens.access() ? { Authorization: `Bearer ${tokens.access()}` } : {}),
      },
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    });
  let res = await send();
  if (res.status === 401 && (await refreshAccess())) res = await send();
  if (res.status === 401) tokens.clear();
  return res;
}

export async function api<T>(
  path: string,
  opts: { method?: string; body?: unknown; query?: Query; auth?: boolean } = {},
): Promise<T> {
  const res = opts.auth === false
    ? await fetch(buildUrl(path, opts.query), {
        method: opts.method ?? "GET",
        headers: opts.body !== undefined ? { "Content-Type": "application/json" } : {},
        body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      })
    : await authedFetch(path, opts);
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

export const get = <T,>(path: string, query?: Query) => api<T>(path, { query });
export const post = <T,>(path: string, body?: unknown) => api<T>(path, { method: "POST", body: body ?? {} });

export async function loginWith(path: "/auth/google/" | "/auth/dev-login/", body: unknown) {
  const d = await api<{ access: string; refresh: string; user: User }>(path, { method: "POST", body, auth: false });
  tokens.set(d.access, d.refresh);
  return d.user;
}
