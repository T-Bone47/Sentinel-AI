import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../services/http';

export type AsyncStatus = 'loading' | 'success' | 'error';

export interface AsyncState<T> {
  data: T | null;
  status: AsyncStatus;
  error: ApiError | Error | null;
  reload: () => void;
  /** True while a background refetch is in flight over already-rendered data. */
  refreshing: boolean;
}

/**
 * Fetch-on-mount with explicit loading / success / error states and a retry.
 *
 * There is deliberately no seed-data fallback here. If the backend is
 * unreachable the screen shows a connection error, because a demo that
 * silently renders mock rows when the API is down is worse than one that
 * says so.
 *
 * `deps` controls refetching — pass the values the request depends on
 * (filters, page, id). Results from a superseded request are discarded.
 */
export function useApiResource<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = []
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<AsyncStatus>('loading');
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [nonce, setNonce] = useState(0);

  const requestId = useRef(0);
  const hasData = useRef(false);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    const id = ++requestId.current;
    let cancelled = false;

    if (hasData.current) setRefreshing(true);
    else setStatus('loading');

    fetcherRef
      .current()
      .then((result) => {
        if (cancelled || id !== requestId.current) return;
        hasData.current = true;
        setData(result);
        setError(null);
        setStatus('success');
      })
      .catch((cause: Error) => {
        if (cancelled || id !== requestId.current) return;
        setError(cause);
        setStatus('error');
      })
      .finally(() => {
        if (!cancelled && id === requestId.current) setRefreshing(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  return { data, status, error, reload, refreshing };
}
