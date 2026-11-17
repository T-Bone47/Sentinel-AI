import { motion } from 'framer-motion';
import {
  AlertTriangle,
  Boxes,
  FileBadge,
  FileText,
  Lightbulb,
  ShieldCheck,
  Target } from
'lucide-react';
import { cn } from '../../utils/cn';
import type { RiskItem } from '../../types/domain';

type Step = {
  key: keyof RiskItem['chain'];
  label: string;
  icon: React.ElementType;
  tone: 'neutral' | 'warning' | 'critical' | 'ai' | 'success';
};

const steps: Step[] = [
{ key: 'policy', label: 'Policy', icon: FileText, tone: 'neutral' },
{ key: 'control', label: 'Control', icon: ShieldCheck, tone: 'warning' },
{ key: 'finding', label: 'Finding', icon: AlertTriangle, tone: 'critical' },
{ key: 'asset', label: 'Affected asset', icon: Boxes, tone: 'neutral' },
{ key: 'evidence', label: 'Evidence', icon: FileBadge, tone: 'success' },
{ key: 'impact', label: 'Business impact', icon: Target, tone: 'critical' },
{ key: 'recommendation', label: 'Recommendation', icon: Lightbulb, tone: 'ai' }];


const toneStyles = {
  neutral: { node: 'border-border bg-surface-2', icon: 'text-muted-foreground' },
  warning: { node: 'border-warning/40 bg-warning/[0.06]', icon: 'text-warning' },
  critical: {
    node: 'border-risk-critical/40 bg-risk-critical/[0.06]',
    icon: 'text-risk-critical'
  },
  success: { node: 'border-success/40 bg-success/[0.06]', icon: 'text-success' },
  ai: { node: 'border-ai-border/60 bg-ai-surface/40', icon: 'text-ai' }
};

/**
 * The investigation spine: POLICY â†’ CONTROL â†’ FINDING â†’ ASSET â†’ EVIDENCE â†’
 * IMPACT â†’ RECOMMENDATION, rendered as connected nodes.
 */
export function InvestigationChain({
  chain,
  className



}: {chain: RiskItem['chain'];className?: string;}) {
  return (
    <ol className={cn('relative', className)}>
      <span
        className="absolute left-[15px] top-4 h-[calc(100%-32px)] w-px bg-gradient-to-b from-border via-border-strong to-border"
        aria-hidden />
      
      {steps.map((step, i) => {
        const tone = toneStyles[step.tone];
        const Icon = step.icon;
        return (
          <motion.li
            key={step.key}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.26, delay: i * 0.06 }}
            className="relative flex gap-4 pb-5 last:pb-0">
            
            <span
              className={cn(
                'relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border',
                tone.node
              )}
              aria-hidden>
              
              <Icon className={cn('h-4 w-4', tone.icon)} />
            </span>
            <div className="min-w-0 flex-1 pt-1">
              <p className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                {step.label}
              </p>
              <p
                className={cn(
                  'mt-1 text-[13px] leading-relaxed',
                  step.key === 'recommendation' ? 'text-foreground' : 'text-foreground/90'
                )}>
                
                {chain[step.key]}
              </p>
            </div>
          </motion.li>);

      })}
    </ol>);

}

/** Compact relationship chain for vendors, controls and privacy records. */
export function RelationChain({
  items,
  className



}: {items: {label: string;value: string;tone?: keyof typeof toneStyles;}[];className?: string;}) {
  return (
    <ol className={cn('relative', className)}>
      <span className="absolute left-[11px] top-3 h-[calc(100%-24px)] w-px bg-border" aria-hidden />
      {items.map((item, i) => {
        const tone = toneStyles[item.tone ?? 'neutral'];
        return (
          <motion.li
            key={item.label}
            initial={{ opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.22, delay: i * 0.05 }}
            className="relative flex items-start gap-3 pb-3.5 last:pb-0">
            
            <span
              className={cn(
                'relative z-10 mt-0.5 h-[22px] w-[22px] shrink-0 rounded-md border',
                tone.node
              )}
              aria-hidden />
            
            <div className="min-w-0 flex-1">
              <p className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                {item.label}
              </p>
              <p className="mt-0.5 text-[13px] leading-snug">{item.value}</p>
            </div>
          </motion.li>);

      })}
    </ol>);

}