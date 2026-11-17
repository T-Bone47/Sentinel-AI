import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { cn } from '../../utils/cn';
import { useCountUp } from '../../hooks/useCountUp';
import { formatNumber } from '../../utils/format';
import type { Kpi } from '../../types/domain';
import { Card } from '../ui/Card';
import { Sparkline } from '../charts/ChartPrimitives';

export function KpiCard({ kpi, index = 0 }: {kpi: Kpi;index?: number;}) {
  const decimals = Number.isInteger(kpi.value) ? 0 : 1;
  const animated = useCountUp(kpi.value, 900, decimals);
  const good =
  kpi.direction === 'flat' ?
  true :
  kpi.direction === 'up' === kpi.positiveIsGood;
  const TrendIcon =
  kpi.direction === 'up' ? ArrowUpRight : kpi.direction === 'down' ? ArrowDownRight : Minus;

  return (
    <Card
      interactive
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: index * 0.05, ease: [0.22, 1, 0.36, 1] }}
      className="p-5">
      
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium text-muted-foreground">{kpi.label}</p>
        <span
          className={cn(
            'inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 text-2xs font-semibold',
            good ? 'bg-success/12 text-success' : 'bg-destructive/12 text-destructive'
          )}>
          
          <TrendIcon className="h-3 w-3" aria-hidden />
          {kpi.delta > 0 ? '+' : ''}
          {formatNumber(kpi.delta, 1)}
          {kpi.id === 'posture' || kpi.id === 'risk' ? '%' : ''}
        </span>
      </div>
      <div className="mt-3 flex items-end justify-between gap-3">
        <p className="font-mono text-[28px] font-semibold leading-none tracking-tight">
          {kpi.prefix}
          {formatNumber(animated, decimals)}
          {kpi.suffix}
        </p>
        <Sparkline
          values={kpi.spark}
          color={good ? 'var(--success)' : 'var(--destructive)'} />
        
      </div>
      <p className="mt-3 text-2xs text-muted-foreground">{kpi.caption}</p>
    </Card>);

}