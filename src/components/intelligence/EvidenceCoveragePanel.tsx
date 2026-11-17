import { motion } from 'framer-motion';
import { ShieldAlert, ShieldCheck } from 'lucide-react';
import { SectionCard } from '../common/SectionCard';
import { Badge } from '../ui/Badge';
import { MetricTile } from '../common/MetricCard';
import type { EvidenceCoverage, EvidenceGap } from '../../services/api';
import { cn } from '../../utils/cn';

const GAP_TONE: Record<string, string> = {
  Critical: 'text-risk-critical',
  High: 'text-risk-high',
  Medium: 'text-warning',
  Low: 'text-muted-foreground'
};

/**
 * "Can we prove our controls are actually working?"
 *
 * Renders the backend's evidence coverage verbatim, including the two things
 * that make the number trustworthy: the formula it was computed with, and the
 * explicit statement that evidence freshness is *not* assessed. Both ship in
 * the API response; neither is invented here.
 */
export function EvidenceCoveragePanel({
  coverage,
  onSelectGap
}: {
  coverage: EvidenceCoverage;
  onSelectGap?: (gap: EvidenceGap) => void;
}) {
  const gaps = coverage.top_gaps ?? coverage.evidence_gaps ?? [];

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricTile
          label="Provable controls"
          value={`${coverage.coverage_percentage}%`}
          index={0} />

        <MetricTile
          label="No evidence at all"
          value={coverage.controls_with_no_evidence}
          index={1} />

        <MetricTile
          label="Collected but unverified"
          value={coverage.controls_with_unverified_evidence_only}
          index={2} />

        <MetricTile
          label="Critical gaps"
          value={coverage.critical_gaps}
          index={3} />

      </div>

      <SectionCard
        title="Evidence coverage"
        description={`${coverage.covered_controls} of ${coverage.total_controls} controls have at least one verified evidence item`}>

        <div className="space-y-4">
          <div>
            <div className="h-2 overflow-hidden rounded-full bg-surface-3">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${coverage.coverage_percentage}%` }}
                transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                className={cn(
                  'h-full rounded-full',
                  coverage.coverage_percentage >= 80 ?
                  'bg-success' :
                  coverage.coverage_percentage >= 60 ?
                  'bg-warning' :
                  'bg-risk-critical'
                )} />

            </div>
            {/* The formula travels with the number so it can be checked. */}
            <p className="mt-2 font-mono text-2xs leading-relaxed text-muted-foreground">
              {coverage.formula}
            </p>
          </div>

          <ul className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
            {coverage.by_framework.map((framework) =>
            <li
              key={framework.framework}
              className="rounded-lg border border-border bg-surface-2/50 px-3 py-2.5">

                <p className="truncate text-[13px] font-medium">{framework.framework}</p>
                <p className="font-mono text-sm text-foreground">
                  {framework.coverage_percentage}%
                </p>
                <p className="font-mono text-2xs text-muted-foreground">
                  {framework.covered_controls}/{framework.total_controls} controls
                </p>
              </li>
            )}
          </ul>

          {/* Stated plainly rather than quietly omitted: the dataset has no
              validity period, so nothing here claims evidence has gone stale. */}
          <p className="rounded-lg border border-border bg-surface-2/40 px-3 py-2 text-2xs leading-relaxed text-muted-foreground">
            {coverage.freshness_note}
          </p>
        </div>
      </SectionCard>

      <SectionCard
        title="Evidence gaps"
        description="Controls that cannot currently be proven, worst first">

        {gaps.length === 0 ?
        <p className="flex items-center gap-2 text-[13px] text-success">
            <ShieldCheck className="h-4 w-4" aria-hidden />
            Every control has verified evidence.
          </p> :

        <ul className="space-y-2">
            {gaps.slice(0, 10).map((gap, index) =>
          <motion.li
            key={gap.control_id}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22, delay: index * 0.04 }}>

                <button
              type="button"
              onClick={() => onSelectGap?.(gap)}
              className="w-full rounded-lg border border-border bg-surface-2/50 px-3.5 py-3 text-left transition hover:border-border-strong hover:bg-surface-2">

                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-[13px] font-medium">
                        {gap.control_name}
                      </p>
                      <p className="font-mono text-2xs text-muted-foreground">
                        {gap.control_id}
                        {gap.framework ? ` · ${gap.framework}` : ''}
                        {gap.mandatory_policy ? ' · mandatory policy' : ''}
                      </p>
                    </div>
                    <span className="flex shrink-0 items-center gap-2">
                      {gap.open_findings > 0 &&
                  <Badge tone="danger">{gap.open_findings} open</Badge>
                  }
                      <span
                    className={cn(
                      'flex items-center gap-1 text-2xs font-semibold uppercase tracking-label',
                      GAP_TONE[gap.gap_severity]
                    )}>

                        <ShieldAlert className="h-3.5 w-3.5" aria-hidden />
                        {gap.gap_severity}
                      </span>
                    </span>
                  </div>
                  {/* `why` is generated by the backend from real counts. */}
                  <p className="mt-1.5 text-2xs leading-relaxed text-muted-foreground">
                    {gap.why}
                  </p>
                </button>
              </motion.li>
          )}
          </ul>
        }
      </SectionCard>
    </div>);

}
