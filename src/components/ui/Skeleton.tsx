import { cn } from '../../utils/cn';

export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden
      className={cn(
        'relative overflow-hidden rounded-md bg-muted',
        'after:absolute after:inset-0 after:-translate-x-full after:animate-shimmer after:bg-gradient-to-r after:from-transparent after:via-foreground/[0.06] after:to-transparent',
        className
      )}
      {...props} />);


}

export function SkeletonText({ lines = 3, className }: {lines?: number;className?: string;}) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) =>
      <Skeleton
        key={i}
        className={cn('h-3', i === lines - 1 ? 'w-2/3' : 'w-full')} />

      )}
    </div>);

}

export function SkeletonCard({ className }: {className?: string;}) {
  return (
    <div className={cn('rounded-xl border border-border bg-card p-5', className)}>
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-4 h-8 w-32" />
      <Skeleton className="mt-4 h-2.5 w-full" />
    </div>);

}

export function SkeletonTable({ rows = 6, cols = 5 }: {rows?: number;cols?: number;}) {
  return (
    <div role="status" aria-label="Loading table data" className="divide-y divide-border">
      {Array.from({ length: rows }).map((_, r) =>
      <div key={r} className="flex items-center gap-4 px-4 py-3.5">
          {Array.from({ length: cols }).map((_, c) =>
        <Skeleton
          key={c}
          className={cn('h-3', c === 0 ? 'w-1/4' : 'flex-1')}
          style={{ opacity: 1 - r * 0.08 }} />

        )}
        </div>
      )}
    </div>);

}