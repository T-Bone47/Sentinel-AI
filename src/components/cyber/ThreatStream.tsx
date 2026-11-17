import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';
import type { RiskLevel, StreamEvent } from '../../types/domain';

const severityDot: Record<RiskLevel, string> = {
  critical: 'bg-risk-critical glow-critical',
  high: 'bg-risk-high',
  medium: 'bg-risk-medium',
  low: 'bg-risk-low',
  info: 'bg-muted-foreground'
};

const severityText: Record<RiskLevel, string> = {
  critical: 'text-risk-critical',
  high: 'text-risk-high',
  medium: 'text-risk-medium',
  low: 'text-risk-low',
  info: 'text-muted-foreground'
};

/** Live SOC-style severity timeline. */
export function ThreatStream({
  events,
  onSelect,
  className




}: {events: StreamEvent[];onSelect?: (event: StreamEvent) => void;className?: string;}) {
  return (
    <ol className={cn('relative', className)}>
      <span
        className="absolute left-[5.5px] top-2 h-[calc(100%-16px)] w-px bg-border"
        aria-hidden />
      
      {events.map((event, i) =>
      <motion.li
        key={event.id}
        initial={{ opacity: 0, x: -6 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.24, delay: i * 0.04 }}
        className="relative">
        
          <button
          type="button"
          onClick={() => onSelect?.(event)}
          className="group flex w-full items-start gap-3 rounded-lg px-2 py-2 pl-0 text-left transition-colors duration-150 hover:bg-accent/50">
          
            <span className="relative mt-1.5 flex h-3 w-3 shrink-0 items-center justify-center">
              {event.severity === 'critical' &&
            <span
              className="absolute h-3 w-3 rounded-full bg-risk-critical/40 motion-safe:animate-signal-ping"
              aria-hidden />

            }
              <span
              className={cn('h-2 w-2 rounded-full', severityDot[event.severity])}
              aria-hidden />
            
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex items-center gap-2">
                <span className="font-mono text-2xs text-muted-foreground">{event.time}</span>
                <span
                className={cn(
                  'font-mono text-2xs font-semibold uppercase tracking-label',
                  severityText[event.severity]
                )}>
                
                  {event.severity}
                </span>
              </span>
              <span className="mt-0.5 block truncate text-[13px] font-medium text-foreground group-hover:text-foreground">
                {event.title}
              </span>
              <span className="mt-0.5 block truncate text-2xs text-muted-foreground">
                {event.source}
              </span>
            </span>
          </button>
        </motion.li>
      )}
    </ol>);

}