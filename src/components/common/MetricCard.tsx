import { motion } from 'framer-motion';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { cn } from '../../utils/cn';
import { useCountUp } from '../../hooks/useCountUp';
import { Sparkline } from '../charts/ChartPrimitives';
import type { Kpi, PostureStatus } from '../../types/domain';

const statusBar: Record<PostureStatus, string> = {
  trusted: 'bg-success',
  warning: 'bg-warning',
  critical: 'bg-risk-critical'
};

const statusSpark: Record<PostureStatus, string> = {
  trusted: 'var(--success)',
  warning: 'var(--warning)',
  critical: 'var(--risk-critical)'
};

/** Compact executive KPI — number, label, trend, status. Deliberately small. */
export function MetricCard({ kpi, index = 0 }: {kpi: Kpi;index?: number;}) {
  const decimals = Number.isInteger(kpi.value) ? 0 : 1;
  const animated = useCountUp(kpi.value, 900, decimals);
  const good = kpi.direction === 'up' === kpi.positiveIsGood;

  const Trend =
  kpi.direction === 'up' ? ArrowUpRight : kpi.direction === 'down' ? ArrowDownRight : Minus;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.26, delay: index * 0.05, ease: [0.22, 1, 0.36, 1] }}
      className="group relative overflow-hidden rounded-xl border border-border bg-card/80 backdrop-blur-xl px-4 py-3.5 transition-colors duration-180 hover:border-border-strong">
      
      <span
        className={cn('absolute inset-x-0 top-0 h-px', statusBar[kpi.status])}
        aria-hidden />
      
      <p className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
        {kpi.label}
      </p>
      <div className="mt-2 flex items-end justify-between gap-2">
        <p className="font-mono text-[30px] font-semibold leading-none tracking-tight">
          {kpi.prefix}
          {animated.toFixed(decimals)}
          {kpi.suffix}
        </p>
        <Sparkline values={kpi.spark} color={statusSpark[kpi.status]} width={64} height={22} />
      </div>
      <div className="mt-2.5 flex items-center justify-between gap-2">
        <span className="truncate text-2xs text-muted-foreground">{kpi.caption}</span>
        <span
          className={cn(
            'flex shrink-0 items-center gap-0.5 font-mono text-2xs font-semibold',
            good ? 'text-success' : 'text-risk-critical'
          )}>
          
          <Trend className="h-3 w-3" aria-hidden />
          {kpi.delta > 0 ? '+' : ''}
          {kpi.delta}
          {kpi.suffix === '%' ? 'pt' : ''}
        </span>
      </div>
    </motion.div>);

}

/** Even denser variant for domain metric strips (IAM, privacy, devices). */
export function MetricTile({
  label,
  value,
  suffix,
  caption,
  tone = 'default',
  index = 0







}: {label: string;value: number | string;suffix?: string;caption?: string;tone?: 'default' | 'critical' | 'warning' | 'success';index?: number;}) {
  const toneClass = {
    default: 'text-foreground',
    critical: 'text-risk-critical',
    warning: 'text-warning',
    success: 'text-success'
  }[tone];

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, delay: index * 0.04 }}
      className="rounded-xl border border-border bg-card/80 backdrop-blur-xl px-4 py-3">
      
      <p className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
        {label}
      </p>
      <p className={cn('mt-1.5 font-mono text-2xl font-semibold leading-none', toneClass)}>
        {value}
        {suffix && <span className="text-base font-normal text-muted-foreground">{suffix}</span>}
      </p>
      {caption && <p className="mt-1.5 text-2xs text-muted-foreground">{caption}</p>}
    </motion.div>);

}