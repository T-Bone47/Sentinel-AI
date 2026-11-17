/**
 * Low-level HTTP client for the Sentinel AI backend.
 *
 * Design rule that matters most here: **this layer never falls back to seed
 * data.** A failed request throws. The previous implementation swallowed
 * errors and quietly returned curated mock rows, which meant a dead backend
 * looked exactly like a healthy one — the worst possible failure mode during
 * a live demo. Callers now surface a real connection state instead.
 *
 * Every backend response uses the same envelope:
 *   list   { data: [...], meta: { page, page_size, total, total_pages }, error: null }
 *   detail { data: {...}, error: null }
 *   error  { data: null,  error: { code, message } }
 */

export const API_BASE_URL =
  ((import.meta as any).env?.VITE_API_URL as string | undefined) || '/api/v1';

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly endpoint: string;

  constructor(message: string, status: number, code: string, endpoint: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.endpoint = endpoint;
  }

  /** True when the backend could not be reached at all (vs. returning an error). */
  get isOffline() {
    return this.status === 0;
  }
}

export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface Paged<T> {
  data: T[];
  meta: PageMeta;
}

export interface QueryParams {
  page?: number;
  page_size?: number;
  search?: string;
  sort?: string;
  [key: string]: string | number | boolean | undefined | null;
}

function buildQuery(params?: QueryParams): string {
  if (!params) return '';
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue;
    if (value === 'all') continue; // the UI's "no filter" sentinel
    search.append(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

/* ---------------------------------------------------------------- session */

export const ACCESS_TOKEN_KEY = 'sentinel.access_token';
const REFRESH_TOKEN_KEY = 'sentinel.refresh_token';

/** Fired on `window` when the server has ended the session and it cannot be renewed. */
export const SESSION_ENDED_EVENT = 'sentinel:session-ended';

/**
 * Tokens live in localStorage (see docs/DECISIONS.md, ADR-002). What limits the
 * damage if one is stolen is on the server: access tokens last 15 minutes,
 * refresh tokens are single-use, and reusing one ends the session.
 */
export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS_TOKEN_KEY, access);
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
};

type RefreshOutcome = 'renewed' | 'rejected' | 'offline';

/**
 * Exchange the refresh token for a new pair. Refresh tokens are single-use and
 * presenting one twice ends the session, so this must never run twice for the
 * same token — neither from parallel requests nor from another tab. The Web
 * Locks API serialises it across both; whoever enters second finds the token
 * already replaced and simply carries on.
 */
async function renewSession(staleAccess: string): Promise<RefreshOutcome> {
  const renew = async (): Promise<RefreshOutcome> => {
    if (tokenStore.access && tokenStore.access !== staleAccess) return 'renewed';
    const refresh = tokenStore.refresh;
    if (!refresh) return 'rejected';
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh })
      });
    } catch {
      return 'offline';
    }
    const body = response.ok ? await response.json().catch(() => null) : null;
    if (!body?.data?.access_token || !body.data.refresh_token) return 'rejected';
    tokenStore.set(body.data.access_token, body.data.refresh_token);
    return 'renewed';
  };
  return navigator.locks ? navigator.locks.request('sentinel.session-renew', renew) : renew();
}

async function request<T>(
  endpoint: string,
  init: RequestInit = {},
  isRetry = false
): Promise<{ data: T; meta?: PageMeta }> {
  const sentToken = tokenStore.access;
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(sentToken ? { Authorization: `Bearer ${sentToken}` } : {}),
        ...(init.headers as Record<string, string> | undefined)
      }
    });
  } catch (cause) {
    throw new ApiError(
      'Cannot reach the Sentinel AI backend. Check that the API is running.',
      0,
      'network_error',
      endpoint
    );
  }

  let body: any = null;
  try {
    body = await response.json();
  } catch {
    // Non-JSON body (proxy error page, 502 HTML, etc.)
  }

  if (!response.ok) {
    // A 401 on a request that carried a token means the access token expired
    // or the session was ended. Try once to renew; if the server refuses, the
    // session is over and the app returns to the sign-in screen. (A 401 from
    // the sign-in form itself carries no token and is just a wrong password.)
    if (response.status === 401 && sentToken && !isRetry) {
      const outcome = await renewSession(sentToken);
      if (outcome === 'renewed') return request<T>(endpoint, init, true);
      if (outcome === 'offline') {
        throw new ApiError(
          'Cannot reach the Sentinel AI backend. Check that the API is running.',
          0,
          'network_error',
          endpoint
        );
      }
      tokenStore.clear();
      window.dispatchEvent(new Event(SESSION_ENDED_EVENT));
    }
    throw new ApiError(
      body?.error?.message ?? `Request failed with status ${response.status}`,
      response.status,
      body?.error?.code ?? `http_${response.status}`,
      endpoint
    );
  }

  return { data: (body?.data ?? body) as T, meta: body?.meta };
}

export async function getList<T>(
  resource: string,
  params?: QueryParams
): Promise<Paged<T>> {
  const { data, meta } = await request<T[]>(`${resource}${buildQuery(params)}`);
  const rows = Array.isArray(data) ? data : [];
  return {
    data: rows,
    meta:
      meta ??
      { page: 1, page_size: rows.length, total: rows.length, total_pages: 1 }
  };
}

export async function getOne<T>(resource: string, id: string): Promise<T> {
  const { data } = await request<T>(`${resource}/${encodeURIComponent(id)}`);
  return data;
}

export async function getRaw<T>(endpoint: string, params?: QueryParams): Promise<T> {
  const { data } = await request<T>(`${endpoint}${buildQuery(params)}`);
  return data;
}

export async function post<T>(endpoint: string, payload: unknown): Promise<T> {
  const { data } = await request<T>(endpoint, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
  return data;
}

/**
 * Fetch every page of a resource. Used only for the small reference tables
 * (policies, controls, findings, evidence — a few hundred rows each) that the
 * UI needs in full to compute joins the backend does not pre-join. Never call
 * this on audit_logs: it has 10,000 rows and the list endpoint paginates for
 * a reason.
 */
export async function getAll<T>(
  resource: string,
  params?: QueryParams,
  cap = 2000
): Promise<T[]> {
  const pageSize = 200;
  const first = await getList<T>(resource, { ...params, page: 1, page_size: pageSize });
  const rows = [...first.data];
  const totalPages = Math.min(
    first.meta.total_pages,
    Math.ceil(cap / pageSize)
  );
  for (let page = 2; page <= totalPages; page += 1) {
    const next = await getList<T>(resource, { ...params, page, page_size: pageSize });
    rows.push(...next.data);
  }
  return rows;
}
