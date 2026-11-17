import { motion } from 'framer-motion';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { cn } from '../../utils/cn';
import type { TrustDomain } from '../../types/domain';

const barTone: Record<TrustDomain['status'], string> = {
  trusted: 'bg-success',
  warning: 'bg-warning',
  critical: 'bg-risk-critical'
};

const valueTone: Record<TrustDomain['status'], string> = {
  trusted: 'text-success',
  warning: 'text-warning',
  critical: 'text-risk-critical'
};

/** Dense posture readout — one compact row per domain, no card explosion. */
export function TrustPosture({
  domains,
  className



}: {domains: TrustDomain[];className?: string;}) {
  return (
    <ul className={cn('divide-y divide-border/70', className)}>
      {domains.map((domain, i) => {
        const Trend =
        domain.delta > 0 ? ArrowUpRight : domain.delta < 0 ? ArrowDownRight : Minus;
        return (
          <motion.li
            key={domain.id}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22, delay: i * 0.03 }}
            className="group grid grid-cols-[104px_1fr_auto] items-center gap-3 py-2.5">
            
            <div className="min-w-0">
              <p className="truncate text-[13px] font-medium">{domain.label}</p>
              <p className="truncate text-2xs text-muted-foreground">{domain.detail}</p>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-surface-3">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${domain.score}%` }}
                transition={{ duration: 0.7, delay: 0.1 + i * 0.03, ease: [0.22, 1, 0.36, 1] }}
                className={cn('h-full rounded-full', barTone[domain.status])} />
              
            </div>
            <div className="flex items-center gap-2 justify-self-end">
              <span
                className={cn(
                  'font-mono text-sm font-semibold tabular-nums',
                  valueTone[domain.status]
                )}>
                
                {domain.score}
              </span>
              <span
                className={cn(
                  'flex w-12 items-center justify-end gap-0.5 font-mono text-2xs',
                  domain.delta >= 0 ? 'text-success' : 'text-risk-critical'
                )}>
                
                <Trend className="h-3 w-3" aria-hidden />
                {Math.abs(domain.delta).toFixed(1)}
              </span>
            </div>
          </motion.li>);

      })}
    </ul>);

}