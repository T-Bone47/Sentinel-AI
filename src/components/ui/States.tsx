import { motion } from 'framer-motion';
import { AlertTriangle, RotateCw } from 'lucide-react';
import { cn } from '../../utils/cn';
import { Button } from './Button';

export function EmptyState({
  icon,
  title,
  description,
  action,
  secondaryAction,
  className,
  tone = 'default'








}: {icon: React.ReactNode;title: string;description: string;action?: React.ReactNode;secondaryAction?: React.ReactNode;className?: string;tone?: 'default' | 'ai';}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24 }}
      className={cn(
        'flex flex-col items-center justify-center px-6 py-16 text-center',
        className
      )}>
      
      <div
        className={cn(
          'grid-noise mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border',
          tone === 'ai' ?
          'border-ai-border/60 bg-ai-surface/50 text-ai' :
          'border-border bg-surface-2 text-muted-foreground'
        )}
        aria-hidden>
        
        {icon}
      </div>
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-muted-foreground">
        {description}
      </p>
      {(action || secondaryAction) &&
      <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
          {action}
          {secondaryAction}
        </div>
      }
    </motion.div>);

}

export function ErrorState({
  title = 'Something went wrong',
  description = 'We could not load this data. Your session is still secure — retry or contact your workspace administrator.',
  onRetry,
  className





}: {title?: string;description?: string;onRetry?: () => void;className?: string;}) {
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border border-destructive/30 bg-destructive/[0.04] px-6 py-14 text-center',
        className
      )}>
      
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-destructive/30 bg-destructive/10 text-destructive">
        <AlertTriangle className="h-5 w-5" aria-hidden />
      </div>
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-1.5 max-w-md text-sm text-muted-foreground">{description}</p>
      {onRetry &&
      <Button
        className="mt-5"
        variant="outline"
        size="sm"
        onClick={onRetry}
        iconLeft={<RotateCw className="h-3.5 w-3.5" />}>
        
          Retry
        </Button>
      }
    </div>);

}