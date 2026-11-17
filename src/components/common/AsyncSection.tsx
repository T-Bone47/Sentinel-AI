import { CloudOff, Inbox } from 'lucide-react';
import { EmptyState, ErrorState } from '../ui/States';
import { SkeletonCard, SkeletonTable } from '../ui/Skeleton';
import type { AsyncState } from '../../hooks/useApiResource';
import { ApiError } from '../../services/http';

/**
 * Renders the four states every data-backed screen needs: loading, error,
 * empty and success.
 *
 * The error copy distinguishes "backend unreachable" from "backend returned
 * an error", because during a demo those need very different reactions —
 * one means start the API, the other means look at the response.
 */
export function AsyncSection<T>({
  state,
  isEmpty,
  emptyTitle = 'No records found',
  emptyDescription = 'No rows in the database match the current filters.',
  skeleton,
  children
}: {
  state: AsyncState<T>;
  isEmpty?: (data: T) => boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  skeleton?: React.ReactNode;
  children: (data: T) => React.ReactNode;
}) {
  if (state.status === 'loading') {
    return <>{skeleton ?? <DefaultSkeleton />}</>;
  }

  if (state.status === 'error' || !state.data) {
    const offline = state.error instanceof ApiError && state.error.isOffline;
    return (
      <ErrorState
        title={offline ? 'Backend unreachable' : 'Could not load this data'}
        description={
          offline
            ? 'The Sentinel AI API is not responding. Start the backend with `uvicorn app.main:app --reload` and retry — this screen shows live database records only, never sample data.'
            : (state.error?.message ??
              'The API returned an error. Check the backend logs and retry.')
        }
        onRetry={state.reload}
      />
    );
  }

  if (isEmpty?.(state.data)) {
    return (
      <EmptyState
        icon={<Inbox className="h-5 w-5" aria-hidden />}
        title={emptyTitle}
        description={emptyDescription}
      />
    );
  }

  return <>{children(state.data)}</>;
}

function DefaultSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
      <SkeletonTable rows={6} />
    </div>
  );
}

/** Small inline banner for screens that keep rendering while refetching. */
export function OfflineNotice({ error, onRetry }: { error: Error | null; onRetry: () => void }) {
  if (!error) return null;
  const offline = error instanceof ApiError && error.isOffline;
  return (
    <div
      role="alert"
      className="flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/[0.05] px-4 py-2.5 text-xs text-destructive"
    >
      <CloudOff className="h-4 w-4 shrink-0" aria-hidden />
      <span className="flex-1">
        {offline ? 'Live data unavailable — backend unreachable.' : error.message}
      </span>
      <button type="button" onClick={onRetry} className="font-semibold underline underline-offset-2">
        Retry
      </button>
    </div>
  );
}
