import { useState } from 'react';
import { motion } from 'framer-motion';
import { ScanSearch, Sparkles } from 'lucide-react';
import { PageHeader, MetaStat } from '../components/layout/PageHeader';
import { SectionCard } from '../components/common/SectionCard';
import { Button } from '../components/ui/Button';
import { Badge, RiskBadge } from '../components/ui/Badge';
import { Tabs } from '../components/ui/Tabs';
import { InvestigationChain } from '../components/cyber/InvestigationChain';
import { ConfidenceMeter, RiskStatusBadge } from '../components/common/StatusPills';
import { getRisks } from '../services/api';
import { useApiResource } from '../hooks/useApiResource';
import { AsyncSection } from '../components/common/AsyncSection';
import { formatRelative } from '../utils/format';
import { cn } from '../utils/cn';

const scopes = [
{ id: 'active', label: 'Active' },
{ id: 'critical', label: 'Critical only' },
{ id: 'closed', label: 'Closed' }];


export function Investigations() {
  const [scope, setScope] = useState('active');
  const [activeId, setActiveId] = useState<string | null>(null);
  const state = useApiResource(() => getRisks(), []);

  const risks = state.data?.data ?? [];
  const filtered = risks.filter((r) =>
  scope === 'critical' ?
  r.severity === 'critical' :
  scope === 'closed' ?
  r.status === 'closed' :
  r.status !== 'closed'
  );
  const active = filtered.find((r) => r.id === activeId) ?? filtered[0];

  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow={
        <Badge tone="primary" dot>
            {risks.filter((r) => r.status === 'investigating').length} investigations in progress
          </Badge>
        }
        title="Investigations"
        subtitle="Trace any exposure from the policy it breaks to the evidence that proves it — the full chain in one workspace."
        meta={
        <>
            <MetaStat
            label="Open cases"
            value={String(risks.filter((r) => r.status !== 'closed').length)}
            icon={<ScanSearch className="h-3.5 w-3.5" aria-hidden />} />
          
            <MetaStat
            label="Critical"
            value={String(risks.filter((r) => r.severity === 'critical').length)} />
          
            <MetaStat
            label="Mapped to a control"
            value={String(risks.filter((r) => r.assetType === 'Control').length)} />
          </>
        }
        actions={
        <Button variant="ai" iconLeft={<Sparkles className="h-4 w-4" />}>
            Open AI analyst
          </Button>
        } />
      

      <Tabs items={scopes} value={scope} onChange={setScope} ariaLabel="Investigation scope" />

      <div className="grid gap-4 xl:grid-cols-12">
        {/* Case list */}
        <section
          aria-label="Cases"
          className="overflow-hidden rounded-xl border border-border bg-card xl:col-span-4">
          
          <p className="border-b border-border px-4 py-2.5 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
            Cases · {filtered.length}
          </p>
          <ul className="max-h-[640px] divide-y divide-border overflow-y-auto">
            {filtered.map((risk) => {
              const selected = active?.id === risk.id;
              return (
                <li key={risk.id}>
                  <button
                    type="button"
                    onClick={() => setActiveId(risk.id)}
                    aria-current={selected}
                    className={cn(
                      'w-full px-4 py-3 text-left transition-colors duration-150',
                      selected ? 'bg-primary/[0.07]' : 'hover:bg-accent/50'
                    )}>
                    
                    <span className="flex items-center justify-between gap-2">
                      <RiskBadge level={risk.severity} withDot={false} />
                      <span className="font-mono text-2xs text-muted-foreground">
                        {formatRelative(risk.updatedAt)}
                      </span>
                    </span>
                    <span className="mt-1.5 block truncate text-[13px] font-medium">
                      {risk.title}
                    </span>
                    <span className="mt-0.5 flex items-center gap-2 truncate font-mono text-2xs text-muted-foreground">
                      {risk.id} · {risk.owner}
                    </span>
                  </button>
                </li>);

            })}
          </ul>
        </section>

        {/* Case detail */}
        {active &&
        <div className="space-y-4 xl:col-span-8">
            <motion.section
            key={active.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.24 }}
            aria-label="Case summary"
            className="scanlines relative overflow-hidden rounded-xl border border-border bg-card p-5">
            
              <div className="absolute inset-0 cyber-grid-fine opacity-30" aria-hidden />
              <div className="relative flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <RiskBadge level={active.severity} />
                    <RiskStatusBadge status={active.status} />
                    <Badge tone="primary">{active.control}</Badge>
                    <Badge tone="neutral">{active.framework}</Badge>
                  </div>
                  <h2 className="mt-3 text-lg font-semibold leading-snug">{active.title}</h2>
                  <p className="mt-1 font-mono text-2xs text-muted-foreground">
                    {active.id} · {active.assetType} · {active.asset} · {active.owner}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                    Risk score
                  </p>
                  <p
                  className={cn(
                    'font-mono text-5xl font-semibold leading-none tracking-tight',
                    active.score >= 90 ?
                    'text-risk-critical' :
                    active.score >= 75 ?
                    'text-risk-high' :
                    'text-risk-medium'
                  )}>
                  
                    {active.score}
                  </p>
                  <div className="mt-2 flex justify-end">
                    <ConfidenceMeter value={active.aiConfidence ?? 0} />
                  </div>
                </div>
              </div>
              <div className="relative mt-5 flex flex-wrap gap-2">
                <Button variant="primary" size="sm">
                  Assign owner
                </Button>
                <Button variant="ai" size="sm" iconLeft={<Sparkles className="h-3.5 w-3.5" />}>
                  Draft remediation
                </Button>
                <Button variant="outline" size="sm">
                  Export case file
                </Button>
              </div>
            </motion.section>

            <SectionCard
            title="Investigation chain"
            description="Policy â†’ control â†’ finding â†’ asset â†’ evidence â†’ impact â†’ recommendation"
            delay={0.05}>
            
              <InvestigationChain chain={active.chain} />
            </SectionCard>
          </div>
        }
      </div>
    </div>);

}