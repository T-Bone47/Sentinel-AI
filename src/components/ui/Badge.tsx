import { cn } from '../../utils/cn';
import type { RiskLevel } from '../../types/domain';

export type BadgeTone =
'neutral' |
'primary' |
'success' |
'warning' |
'danger' |
'info' |
'ai';

const tones: Record<BadgeTone, string> = {
  neutral: 'bg-muted text-muted-foreground border-border',
  primary: 'bg-primary/12 text-primary border-primary/25',
  success: 'bg-success/12 text-success border-success/25',
  warning: 'bg-warning/14 text-warning border-warning/30',
  danger: 'bg-destructive/12 text-destructive border-destructive/25',
  info: 'bg-info/12 text-info border-info/25',
  ai: 'bg-ai/12 text-ai border-ai/30'
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  dot?: boolean;
}

export function Badge({
  className,
  tone = 'neutral',
  dot = false,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border px-2 py-0.5 text-2xs font-medium',
        tones[tone],
        className
      )}
      {...props}>
      
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />}
      {children}
    </span>);

}

const riskTone: Record<RiskLevel, string> = {
  critical: 'bg-risk-critical/14 text-risk-critical border-risk-critical/30',
  high: 'bg-risk-high/14 text-risk-high border-risk-high/30',
  medium: 'bg-risk-medium/16 text-risk-medium border-risk-medium/30',
  low: 'bg-risk-low/14 text-risk-low border-risk-low/30',
  info: 'bg-risk-none/14 text-risk-none border-risk-none/30'
};

export function RiskBadge({
  level,
  className,
  withDot = true




}: {level: RiskLevel;className?: string;withDot?: boolean;}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border px-2 py-0.5 text-2xs font-semibold uppercase tracking-wide',
        riskTone[level],
        className
      )}>
      
      {withDot && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />}
      {level}
    </span>);

}