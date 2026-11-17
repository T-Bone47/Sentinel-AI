import { motion } from 'framer-motion';
import { ArrowUpRight, Radar } from 'lucide-react';
import { cn } from '../../utils/cn';
import { useCountUp } from '../../hooks/useCountUp';
import type { TrustDomain } from '../../types/domain';

const statusRing: Record<TrustDomain['status'], string> = {
  trusted: 'bg-success',
  warning: 'bg-warning',
  critical: 'bg-risk-critical'
};

const statusText: Record<TrustDomain['status'], string> = {
  trusted: 'text-success',
  warning: 'text-warning',
  critical: 'text-risk-critical'
};

/**
 * One integrated trust visualization: radial score, animated scanning ring and
 * the nine posture domains orbiting the score. No per-domain cards.
 */
export function TrustScore({
  score,
  max = 100,
  band,
  delta,
  domains,
  signals,
  size = 300








}: {score: number;max?: number;band: string;delta?: number;domains: TrustDomain[];signals: number;size?: number;}) {
  const animated = useCountUp(score, 1100);
  const thickness = 12;
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.max(0, Math.min(1, score / max));
  const orbit = size / 2 + 56;

  return (
    <div className="flex flex-col items-center">
      <div
        className="relative flex items-center justify-center"
        style={{ width: size + 112, height: size + 112 }}>
        
        {/* Orbiting domain chips (wide screens only — the posture panel repeats them) */}
        {domains.map((domain, i) => {
          const angle = i / domains.length * 2 * Math.PI - Math.PI / 2;
          const x = Math.cos(angle) * orbit;
          const y = Math.sin(angle) * orbit;
          return (
            <motion.div
              key={domain.id}
              initial={{ opacity: 0, scale: 0.9, x: `calc(-50% + ${x}px)`, y: `calc(-50% + ${y}px)` }}
              animate={{ opacity: 1, scale: 1, x: `calc(-50% + ${x}px)`, y: `calc(-50% + ${y}px)` }}
              transition={{ duration: 0.3, delay: 0.35 + i * 0.05 }}
              className="absolute top-1/2 left-1/2 hidden xl:flex z-20">
              
              <span className="group relative flex items-center gap-2.5 whitespace-nowrap rounded-sm border border-border-strong border-l-2 bg-card/80 px-3 py-1.5 backdrop-blur-md shadow-[0_4px_20px_oklch(0_0_0/0.4)] overflow-hidden transition-all duration-300 hover:border-ai/50 hover:bg-card/95"
                    style={{ borderLeftColor: `oklch(var(--${domain.status === 'trusted' ? 'success' : domain.status === 'warning' ? 'warning' : 'risk-critical'}))` }}>
                {/* Tactical grid background overlay */}
                <div className="absolute inset-0 cyber-grid opacity-20 pointer-events-none" />
                <div className="absolute inset-0 bg-gradient-to-r from-background/40 to-transparent pointer-events-none" />
                
                <span
                  className={cn('relative z-10 h-1.5 w-1.5 shadow-[0_0_8px_currentColor]', statusRing[domain.status], statusText[domain.status])}
                  style={{ borderRadius: '1px' }}
                  aria-hidden />
                
                <span className="relative z-10 text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground group-hover:text-foreground transition-colors">
                  {domain.label}
                </span>
                <span className="relative z-10 font-mono text-[13px] font-bold text-foreground">
                  {domain.score}
                </span>
                
                {/* Decorative tech accent */}
                <span className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-border opacity-50" />
                <span className="absolute top-0 left-0 w-1 h-1 bg-muted-foreground/30" />
              </span>
            </motion.div>);

        })}

        {/* Rotating scan sweep */}
        <div
          className="absolute animate-scan-slow motion-reduce:animate-none"
          style={{ width: size + 40, height: size + 40 }}
          aria-hidden>
          
          <svg width={size + 40} height={size + 40} className="overflow-visible">
            <defs>
              <linearGradient id="scan-sweep" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" style={{ stopColor: 'oklch(var(--cyan))', stopOpacity: 0 }} />
                <stop offset="100%" style={{ stopColor: 'oklch(var(--cyan))', stopOpacity: 0.9 }} />
              </linearGradient>
            </defs>
            <circle
              cx={(size + 40) / 2}
              cy={(size + 40) / 2}
              r={(size + 40) / 2 - 2}
              fill="none"
              style={{ stroke: 'oklch(var(--border))' }}
              strokeWidth={1}
              strokeDasharray="2 8" />
            
            <line
              x1={(size + 40) / 2}
              y1={(size + 40) / 2}
              x2={size + 38}
              y2={(size + 40) / 2}
              style={{ stroke: 'url(#scan-sweep)' }}
              strokeWidth={1.5} />
            
          </svg>
        </div>

        {/* Score dial */}
        <svg width={size} height={size} className="relative -rotate-90">
          <defs>
            <linearGradient id="trust-arc" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" style={{ stopColor: 'oklch(var(--cyan))' }} />
              <stop offset="55%" style={{ stopColor: 'oklch(var(--primary))' }} />
              <stop offset="100%" style={{ stopColor: 'oklch(var(--ai))' }} />
            </linearGradient>
          </defs>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={thickness}
            style={{ stroke: 'oklch(var(--surface-3))' }} />
          
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={thickness}
            strokeLinecap="round"
            stroke="url(#trust-arc)"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: circumference * (1 - pct) }}
            transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
            style={{ filter: 'drop-shadow(0 0 10px oklch(var(--primary) / 0.55))' }} />
          
          {/* Tick marks every 10 points */}
          {Array.from({ length: 40 }).map((_, i) => {
            const angle = i / 40 * 2 * Math.PI;
            const inner = radius - thickness - 6;
            const outer = i % 5 === 0 ? inner - 7 : inner - 3;
            return (
              <line
                key={i}
                x1={size / 2 + Math.cos(angle) * inner}
                y1={size / 2 + Math.sin(angle) * inner}
                x2={size / 2 + Math.cos(angle) * outer}
                y2={size / 2 + Math.sin(angle) * outer}
                style={{ stroke: 'oklch(var(--border-strong))' }}
                strokeWidth={i % 5 === 0 ? 1.4 : 0.8}
                opacity={i / 40 <= pct ? 0.95 : 0.35} />);
          })}
        </svg>

        {/* Center readout */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <div className="absolute inset-0 rounded-full bg-gradient-to-b from-transparent to-primary/10 opacity-60 blur-2xl pointer-events-none" />
          <p className="relative z-10 text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground/80">
            Organization Trust
          </p>
          <p className="relative z-10 mt-1 flex items-baseline gap-1 font-mono text-[72px] font-bold leading-none tracking-tight text-white drop-shadow-[0_0_20px_oklch(var(--ai)/0.5)]">
            {Math.round(animated)}
            <span className="text-2xl font-medium text-white/40 drop-shadow-none">/ {max}</span>
          </p>
          <p className={cn(
            "relative z-10 mt-3 rounded-full px-3 py-1 text-xs font-bold uppercase tracking-widest border shadow-[0_0_15px_currentColor] backdrop-blur-md",
            band === 'Healthy' ? 'bg-success/10 text-success border-success/30' : 'bg-risk-critical/10 text-risk-critical border-risk-critical/30'
          )}>
            {band}
          </p>
          {delta !== undefined &&
          <p className="relative z-10 mt-2 flex items-center gap-1 text-xs font-medium text-success drop-shadow-sm">
              <ArrowUpRight className="h-3.5 w-3.5" aria-hidden />
              +{delta}% this week
            </p>
          }
        </div>
      </div>

      <p className="mt-1 flex items-center gap-1.5 font-mono text-2xs text-muted-foreground">
        <Radar className="h-3 w-3 text-cyan" aria-hidden />
        {signals.toLocaleString()} signals evaluated · continuous
      </p>

      {/* Compact domain legend for narrow viewports */}
      <ul className="mt-4 flex flex-wrap justify-center gap-x-3 gap-y-1.5 xl:hidden">
        {domains.map((domain) =>
        <li key={domain.id} className="flex items-center gap-1.5">
            <span
            className={cn('h-1.5 w-1.5 rounded-full', statusRing[domain.status])}
            aria-hidden />
          
            <span className="text-2xs text-muted-foreground">{domain.label}</span>
            <span className={cn('font-mono text-2xs font-semibold', statusText[domain.status])}>
              {domain.score}
            </span>
          </li>
        )}
      </ul>
    </div>);

}