import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';

export type FlowStatus = 'trusted' | 'warning' | 'critical' | 'neutral' | 'ai';

export interface FlowNode {
  id: string;
  label: string;
  value?: string;
  detail?: string;
  status?: FlowStatus;
  icon?: React.ReactNode;
}

const nodeTone: Record<FlowStatus, string> = {
  trusted: 'border-success/40 bg-success/[0.07] text-success',
  warning: 'border-warning/40 bg-warning/[0.07] text-warning',
  critical: 'border-risk-critical/45 bg-risk-critical/[0.08] text-risk-critical',
  neutral: 'border-border bg-surface-2/70 text-muted-foreground',
  ai: 'border-ai-border/60 bg-ai-surface/40 text-ai'
};

/**
 * Data-flow / relationship chain used for the topology preview, investigation
 * chains and privacy data flows. Connectors animate as telemetry paths.
 */
export function FlowChain({
  nodes,
  orientation = 'horizontal',
  className,
  onSelect,
  activeId






}: {nodes: FlowNode[];orientation?: 'horizontal' | 'vertical';className?: string;onSelect?: (node: FlowNode) => void;activeId?: string;}) {
  const horizontal = orientation === 'horizontal';

  return (
    <div
      className={cn(
        horizontal ?
        'scrollbar-none flex items-stretch gap-0 overflow-x-auto pb-1' :
        'flex flex-col',
        className
      )}>
      
      {nodes.map((node, i) => {
        const status = node.status ?? 'neutral';
        const active = activeId === node.id;
        return (
          <React.Fragment key={node.id}>
            <motion.button
              type="button"
              disabled={!onSelect}
              onClick={() => onSelect?.(node)}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22, delay: i * 0.05 }}
              className={cn(
                'relative rounded-lg border px-3 py-2.5 text-left transition-all duration-180',
                nodeTone[status],
                horizontal ? 'min-w-[124px] shrink-0' : 'w-full',
                onSelect && 'hover:border-primary/50 hover:bg-primary/[0.06]',
                active && 'border-primary/70 bg-primary/[0.10] glow-primary'
              )}>
              
              <span className="flex items-center gap-1.5">
                {node.icon}
                <span className="text-2xs font-semibold uppercase tracking-label">
                  {node.label}
                </span>
              </span>
              {node.value &&
              <span className="mt-1 block font-mono text-[13px] font-semibold text-foreground">
                  {node.value}
                </span>
              }
              {node.detail &&
              <span className="mt-1 block text-2xs leading-relaxed text-muted-foreground">
                  {node.detail}
                </span>
              }
            </motion.button>

            {i < nodes.length - 1 &&
            <span
              className={cn(
                'flex shrink-0 items-center justify-center',
                horizontal ? 'w-6' : 'h-5 w-full pl-4'
              )}
              aria-hidden>
              
                <svg
                width={horizontal ? 24 : 2}
                height={horizontal ? 2 : 20}
                className="overflow-visible">
                
                  <line
                  x1={0}
                  y1={horizontal ? 1 : 0}
                  x2={horizontal ? 24 : 1}
                  y2={horizontal ? 1 : 20}
                  style={{ stroke: 'oklch(var(--border-strong))' }}
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  className="motion-safe:animate-dash-flow" />
                
                </svg>
              </span>
            }
          </React.Fragment>);

      })}
    </div>);

}