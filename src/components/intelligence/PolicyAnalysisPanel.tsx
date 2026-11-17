import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileSearch, Loader2, ShieldAlert, ShieldCheck } from 'lucide-react';
import { SectionCard } from '../common/SectionCard';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { MetricTile } from '../common/MetricCard';
import { analyzePolicyText, type PolicyAnalysis, type PolicyRequirement } from '../../services/api';
import { cn } from '../../utils/cn';

const GAP_TONE: Record<string, string> = {
  none: 'text-success',
  partial: 'text-warning',
  unverified: 'text-warning',
  no_evidence: 'text-risk-high',
  unmapped: 'text-muted-foreground'
};

const GAP_LABEL: Record<string, string> = {
  none: 'Satisfied',
  partial: 'Partially satisfied',
  unverified: 'Evidence unverified',
  no_evidence: 'No evidence',
  unmapped: 'No control mapping'
};

const SAMPLE = `All privileged accounts must use multi-factor authentication before accessing production systems.
Personal data must be encrypted at rest and in transit.
Access reviews shall be performed quarterly for all privileged users.
Vendors must complete a security due diligence assessment prior to onboarding.`;

/**
 * "Analyze Policy" workflow.
 *
 * Paste policy text, get structured requirements mapped onto controls that
 * actually exist, each with its current compliance state read from real
 * evidence and findings.
 *
 * The engine label is shown prominently and honestly: this is deterministic
 * rule-based extraction, not a language model, and the backend says so in
 * every response (`llm_used: false`). Requirements the matcher cannot place
 * render their `mapping_note` — "No verified control mapping found." — rather
 * than being hidden or padded with a nearest guess.
 */
export function PolicyAnalysisPanel() {
  const [text, setText] = useState('');
  const [analysis, setAnalysis] = useState<PolicyAnalysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    const value = text.trim();
    if (value.length < 20 || busy) return;
    setBusy(true);
    setError(null);
    try {
      setAnalysis(await analyzePolicyText(value, 'Uploaded policy'));
    } catch (cause) {
      setAnalysis(null);
      setError(
        cause instanceof Error ? cause.message : 'Policy analysis failed.'
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <SectionCard
      title="Analyze policy"
      description="Extract obligations and map them to controls that exist in your estate">

      <div className="space-y-4">
        <div>
          <label htmlFor="policy-text" className="sr-only">
            Policy text
          </label>
          <textarea
            id="policy-text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={6}
            placeholder="Paste policy text here..."
            className="w-full resize-y rounded-lg border border-border bg-surface-2/60 px-3.5 py-3 text-[13px] leading-relaxed outline-none transition focus:border-border-strong" />

          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Button
              variant="ai"
              size="sm"
              onClick={run}
              disabled={busy || text.trim().length < 20}
              iconLeft={
              busy ?
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> :
              <FileSearch className="h-3.5 w-3.5" />
              }>

              {busy ? 'Analyzing...' : 'Analyze'}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setText(SAMPLE)}>
              Use sample
            </Button>
            <span className="font-mono text-2xs text-muted-foreground">
              Rule-based extraction · no language model
            </span>
          </div>
        </div>

        {error &&
        <p
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/[0.05] px-3.5 py-2.5 text-xs text-destructive">

            {error}
          </p>
        }

        {analysis &&
        <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <MetricTile label="Requirements" value={analysis.requirements_found} index={0} />
              <MetricTile label="Mapped to controls" value={analysis.requirements_mapped} index={1} />
              <MetricTile
              label="Unmapped"
              value={analysis.requirements_unmapped}
              tone={analysis.requirements_unmapped ? 'warning' : undefined}
              index={2} />
            
              <MetricTile
              label="Satisfied"
              value={`${analysis.compliance_percentage}%`}
              tone={analysis.compliance_percentage >= 70 ? 'success' : 'critical'}
              index={3} />
            
            </div>

            {/* Engine disclosure, not buried in a tooltip. */}
            <p className="rounded-lg border border-border bg-surface-2/40 px-3 py-2 font-mono text-2xs leading-relaxed text-muted-foreground">
              {analysis.engine} · llm_used: {String(analysis.llm_used)} — {analysis.engine_note}
            </p>

            <ul className="space-y-2.5">
              {analysis.requirements.map((requirement, index) =>
            <RequirementRow key={requirement.requirement_id} requirement={requirement} index={index} />
            )}
            </ul>

            <p className="font-mono text-2xs text-muted-foreground">
              {analysis.compliance_formula}
            </p>
          </div>
        }
      </div>
    </SectionCard>);

}

function RequirementRow({
  requirement,
  index
}: {
  requirement: PolicyRequirement;
  index: number;
}) {
  const mapped = requirement.mapped_controls.length > 0;
  const top = requirement.mapped_controls[0];

  return (
    <motion.li
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, delay: Math.min(index, 8) * 0.04 }}
      className="rounded-lg border border-border bg-surface-2/50 px-3.5 py-3">

      <div className="flex items-start justify-between gap-3">
        <p className="min-w-0 flex-1 text-[13px] leading-relaxed">{requirement.requirement}</p>
        <span className="flex shrink-0 items-center gap-2">
          <Badge tone={requirement.obligation === 'mandatory' ? 'danger' : 'neutral'}>
            {requirement.obligation}
          </Badge>
          <span
            className={cn(
              'flex items-center gap-1 text-2xs font-semibold uppercase tracking-label',
              GAP_TONE[requirement.gap] ?? 'text-muted-foreground'
            )}>

            {requirement.gap === 'none' ?
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden /> :
            <ShieldAlert className="h-3.5 w-3.5" aria-hidden />
            }
            {GAP_LABEL[requirement.gap] ?? requirement.gap}
          </span>
        </span>
      </div>

      <div className="mt-2 space-y-1.5 border-l-2 border-border pl-3">
        {mapped ?
        <>
            <p className="text-2xs text-muted-foreground">
              Mapped to{' '}
              <span className="font-mono text-foreground">{top.control_id}</span>{' '}
              {top.control_name}
              {top.framework ? ` · ${top.framework}` : ''}
              {/* Match score is published so a reviewer can judge the mapping. */}
              <span className="ml-1.5 font-mono">
                (
                {requirement.mapping_source === 'database_foreign_key' ?
              'verified foreign key' :
              `match ${top.match_score}`}
                )
              </span>
            </p>
            <p className="text-2xs leading-relaxed text-muted-foreground">
              {requirement.current_state}
            </p>
            <p className="text-2xs leading-relaxed text-ai">
              {requirement.recommended_action}
            </p>
          </> :

        <p className="text-2xs leading-relaxed text-muted-foreground">
            {/* The honesty guarantee — rendered, never filtered out. */}
            <span className="font-medium text-warning">{requirement.mapping_note}</span>{' '}
            {requirement.recommended_action}
          </p>
        }
      </div>
    </motion.li>);

}
