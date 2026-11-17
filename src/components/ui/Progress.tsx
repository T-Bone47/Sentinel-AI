import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';

export type ProgressTone = 'primary' | 'success' | 'warning' | 'danger' | 'ai';

const barTone: Record<ProgressTone, string> = {
  primary: 'bg-primary',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-destructive',
  ai: 'ai-gradient'
};

export function ProgressBar({
  value,
  tone = 'primary',
  label,
  showValue = false,
  className,
  size = 'md'







}: {value: number;tone?: ProgressTone;label?: string;showValue?: boolean;className?: string;size?: 'sm' | 'md';}) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className={cn('w-full', className)}>
      {(label || showValue) &&
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
          {label &&
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        }
          {showValue &&
        <span className="font-mono text-xs font-medium text-foreground">
              {clamped.toFixed(0)}%
            </span>
        }
        </div>
      }
      <div
        role="progressbar"
        aria-valuenow={Math.round(clamped)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ?? 'Progress'}
        className={cn(
          'w-full overflow-hidden rounded-full bg-muted',
          size === 'sm' ? 'h-1' : 'h-1.5'
        )}>
        
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${clamped}%` }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className={cn('h-full rounded-full', barTone[tone])} />
        
      </div>
    </div>);

}

const strokeTone: Record<ProgressTone, string> = {
  primary: 'stroke-primary',
  success: 'stroke-success',
  warning: 'stroke-warning',
  danger: 'stroke-destructive',
  ai: 'stroke-ai'
};

export function RadialGauge({
  value,
  size = 132,
  thickness = 10,
  tone = 'primary',
  caption,
  children







}: {value: number;size?: number;thickness?: number;tone?: ProgressTone;caption?: string;children?: React.ReactNode;}) {
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, value));
  const offset = circumference - clamped / 100 * circumference;

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${caption ?? 'Score'}: ${clamped.toFixed(0)} percent`}>
      
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={thickness}
          className="stroke-muted" />
        
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={thickness}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          className={strokeTone[tone]} />
        
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {children}
      </div>
    </div>);

}