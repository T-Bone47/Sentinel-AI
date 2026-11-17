import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Check, FileText, Loader2, Sparkles, Upload } from 'lucide-react';
import { EntityWorkspace } from '../components/org/EntityWorkspace';
import { MetricTile } from '../components/common/MetricCard';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PolicyStatusBadge } from '../components/common/StatusPills';
import { RelationChain } from '../components/cyber/InvestigationChain';
import { MetaStat } from '../components/layout/PageHeader';
import { type Column, type TableFilter } from '../components/ui/DataTable';
const policyPipeline = [
{ id: 'upload', label: 'Upload', detail: 'Document received · SHA-256 recorded' },
{ id: 'analyzing', label: 'Analyzing', detail: 'Sentinel parsing clauses and obligations' },
{ id: 'controls', label: 'Controls extracted', detail: '18 candidate controls identified' },
{ id: 'mapped', label: 'Requirements mapped', detail: 'Mapped to ISO 27001 · SOC 2 · DPDP' },
{ id: 'evidence', label: 'Evidence identified', detail: '11 evidence requirements generated' }];

import { getControls, getPolicies } from '../services/api';
import { PolicyAnalysisPanel } from '../components/intelligence/PolicyAnalysisPanel';
import { useApiResource } from '../hooks/useApiResource';
import { AsyncSection } from '../components/common/AsyncSection';
import { formatDate } from '../utils/format';
import { cn } from '../utils/cn';
import type { Policy } from '../types/domain';

const columns: Column<Policy>[] = [
{
  id: 'name',
  header: 'Policy',
  accessor: (p) => p.name,
  width: 260,
  sticky: true,
  hideable: false,
  cell: (p) =>
  <div className="min-w-0">
        <p className="flex items-center gap-2 truncate font-medium">
          {p.name}
          {p.aiGenerated &&
      <Badge tone="ai">
              <Sparkles className="h-2.5 w-2.5" aria-hidden />
              AI
            </Badge>
      }
        </p>
        <p className="truncate font-mono text-2xs text-muted-foreground">{p.id}</p>
      </div>

},
{
  id: 'framework',
  header: 'Framework',
  accessor: (p) => p.framework,
  width: 150,
  cell: (p) => <Badge tone="neutral">{p.framework}</Badge>
},
{ id: 'owner', header: 'Owner', accessor: (p) => p.owner, width: 176 },
{
  id: 'controls',
  header: 'Controls',
  accessor: (p) => p.controls ?? 0,
  width: 100,
  align: 'right',
  cell: (p) => <span className="font-mono text-[13px]">{p.controls}</span>
},
{
  id: 'status',
  header: 'Status',
  accessor: (p) => p.status,
  width: 124,
  cell: (p) => <PolicyStatusBadge status={p.status} />
},
{
  id: 'lastReviewed',
  header: 'Last reviewed',
  accessor: (p) => p.lastReviewed,
  width: 140,
  cell: (p) =>
  <span className="font-mono text-2xs text-muted-foreground">
        {formatDate(p.lastReviewed, 'MMM d, yyyy')}
      </span>

},
{
  id: 'nextReview',
  header: 'Next review',
  accessor: (p) => p.nextReview,
  width: 140,
  cell: (p) =>
  <span className="font-mono text-2xs text-muted-foreground">
        {p.nextReview === '—' ? '—' : formatDate(p.nextReview, 'MMM d, yyyy')}
      </span>

}];


const buildFilters = (rows: Policy[]): TableFilter<Policy>[] => [
  {
    id: 'status',
    label: 'Status',
    options: [
      { value: 'published', label: 'Published' },
      { value: 'in-review', label: 'In review' },
      { value: 'draft', label: 'Draft' },
      { value: 'archived', label: 'Archived' },
    ],
    predicate: (row, value) => row.status === value,
  },
  {
    id: 'framework',
    label: 'Framework',
    options: Array.from(new Set(rows.map((p) => p.framework))).map((f) => ({
      value: f,
      label: f,
    })),
    predicate: (row, value) => row.framework === value,
  },
  {
    id: 'origin',
    label: 'Origin',
    options: [
      { value: 'ai', label: 'AI generated' },
      { value: 'human', label: 'Human authored' },
    ],
    predicate: (row, value) =>
      value === 'ai' ? row.aiGenerated : !row.aiGenerated,
  },
];


/** The document â†’ controls ingestion pipeline, animated stage by stage. */
function IngestionPipeline({ open, onClose }: {open: boolean;onClose: () => void;}) {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (!open) {
      setStage(0);
      return;
    }
    const timer = window.setInterval(() => {
      setStage((s) => s >= policyPipeline.length ? s : s + 1);
    }, 900);
    return () => window.clearInterval(timer);
  }, [open]);

  const done = stage >= policyPipeline.length;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Upload policy"
      description="Preview of the Phase 2 policy ingestion flow. This walkthrough is illustrative — it does not read a real document or write to the database yet."
      footer={
      <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="ai" disabled={!done} iconLeft={<Sparkles className="h-4 w-4" />}>
            {done ? 'Publish 18 controls' : 'Analyzing...'}
          </Button>
        </>
      }>
      
      <div className="space-y-5">
        {/* Scanning document surface */}
        <div className="relative overflow-hidden rounded-xl border border-ai-border/50 bg-ai-surface/20 p-5">
          <div className="absolute inset-0 cyber-grid-fine opacity-40" aria-hidden />
          {!done &&
          <div
            className="pointer-events-none absolute inset-y-0 -left-1/3 w-1/3 bg-gradient-to-r from-transparent via-ai/25 to-transparent motion-safe:animate-sweep"
            aria-hidden />

          }
          <div className="relative flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-ai-border/60 bg-ai-surface/60 text-ai">
              <FileText className="h-5 w-5" aria-hidden />
            </span>
            <div className="min-w-0">
              <p className="truncate text-[13px] font-medium">
                Information-Security-Policy-v5.pdf
              </p>
              <p className="font-mono text-2xs text-muted-foreground">
                412 KB · sha256:7c41...9e2b · 34 pages
              </p>
            </div>
          </div>
        </div>

        {/* Stage list */}
        <ol className="space-y-2.5" aria-live="polite">
          {policyPipeline.map((step, i) => {
            const complete = stage > i;
            const current = stage === i;
            return (
              <motion.li
                key={step.id}
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: i * 0.04 }}
                className={cn(
                  'flex items-center gap-3 rounded-lg border px-3.5 py-2.5 transition-colors duration-180',
                  complete ?
                  'border-success/35 bg-success/[0.06]' :
                  current ?
                  'border-ai-border/60 bg-ai-surface/30' :
                  'border-border bg-surface-2/40 opacity-60'
                )}>
                
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-current/20">
                  {complete ?
                  <Check className="h-3.5 w-3.5 text-success" strokeWidth={3} aria-hidden /> :
                  current ?
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-ai" aria-hidden /> :

                  <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground" aria-hidden />
                  }
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-[13px] font-medium">{step.label}</span>
                  <span className="block truncate text-2xs text-muted-foreground">
                    {step.detail}
                  </span>
                </span>
              </motion.li>);

          })}
        </ol>
      </div>
    </Modal>);

}

export function Policies() {
  const [uploadOpen, setUploadOpen] = useState(false);
  const state = useApiResource(
    () =>
      Promise.all([getPolicies(), getControls()]).then(([p, c]) => ({
        policies: p.data,
        controls: c.data
      })),
    []
  );
  const policies = state.data?.policies ?? [];
  const controls = state.data?.controls ?? [];
  const filters = React.useMemo(() => buildFilters(policies), [policies]);


  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <>
      <EntityWorkspace<Policy>
        title="Policies"
        subtitle="Policy documents become machine-readable governance: Sentinel extracts obligations, maps them to controls and identifies the evidence each one needs."
        eyebrow={
        <Badge tone="ai">
            <Sparkles className="h-3 w-3" aria-hidden />
            4 policies authored with Sentinel
          </Badge>
        }
        meta={
        <>
            <MetaStat
            label="Policies"
            value={String(policies.length)}
            icon={<FileText className="h-3.5 w-3.5" aria-hidden />} />
          
            <MetaStat label="Mapped controls" value="126" />
            <MetaStat label="Reviews due 90 days" value="3" />
          </>
        }
        actions={
        <>
            <Button variant="outline">Review calendar</Button>
            <Button
            variant="primary"
            iconLeft={<Upload className="h-4 w-4" />}
            onClick={() => setUploadOpen(true)}>
            
              Upload policy
            </Button>
          </>
        }
        beforeTable={<PolicyAnalysisPanel />}
      metrics={
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricTile label="Policies" value={policies.length} index={0} />
            <MetricTile
            label="In review"
            value={policies.filter((p) => p.status === 'in-review').length}
            tone="warning"
            caption="awaiting approval"
            index={1} />
          
            <MetricTile
            label="Draft"
            value={policies.filter((p) => p.status === 'draft').length}
            caption="not yet effective"
            index={2} />
          
            <MetricTile
            label="Published"
            value={policies.filter((p) => p.status === 'published').length}
            tone="success"
            caption="in force"
            index={3} />
          
          </section>
        }
        columns={columns}
        rows={policies}
        getRowId={(p) => p.id}
        filters={filters}
        ariaLabel="Policy library"
        exportName="sentinel-policies"
        searchPlaceholder="Search policies, frameworks, owners..."
        detail={{
          title: (p) => p.name,
          subtitle: (p) => `${p.id} · ${p.framework} · owner ${p.owner}`,
          eyebrow: (p) =>
          <div className="flex flex-wrap items-center gap-2">
              <PolicyStatusBadge status={p.status} />
              <Badge tone="neutral">{p.controls} controls</Badge>
              {p.aiGenerated &&
            <Badge tone="ai">
                  <Sparkles className="h-2.5 w-2.5" aria-hidden />
                  AI drafted
                </Badge>
            }
            </div>,

          actions: () => <Button variant="primary">Open document</Button>,
          render: (p) => {
            const mapped = controls.filter((c) => c.policy === p.name);
            return (
              <div className="space-y-6">
                <dl className="grid grid-cols-2 gap-4 text-[13px]">
                  <div>
                    <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                      Last reviewed
                    </dt>
                    <dd className="mt-1 font-mono">{formatDate(p.lastReviewed)}</dd>
                  </div>
                  <div>
                    <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                      Next review
                    </dt>
                    <dd className="mt-1 font-mono">
                      {p.nextReview === '—' ? '—' : formatDate(p.nextReview)}
                    </dd>
                  </div>
                </dl>

                {mapped.length > 0 &&
                <div>
                    <p className="mb-2 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                      Mapped controls
                    </p>
                    <ul className="space-y-2">
                      {mapped.map((control) =>
                    <li
                      key={control.id}
                      className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface-2/50 px-3.5 py-2.5">
                      
                          <span className="min-w-0">
                            <span className="block font-mono text-2xs text-primary">
                              {control.id}
                            </span>
                            <span className="block truncate text-[13px]">{control.name}</span>
                          </span>
                          <Badge
                        tone={
                        control.status === 'passing' ?
                        'success' :
                        control.status === 'failing' ?
                        'danger' :
                        'warning'
                        }>
                        
                            {control.status}
                          </Badge>
                        </li>
                    )}
                    </ul>
                  </div>
                }

                <RelationChain
                  items={[
                  { label: 'Policy', value: `${p.name} · ${p.framework}` },
                  { label: 'Controls', value: `${p.controls} obligations mapped` },
                  {
                    label: 'Evidence',
                    value: 'Evidence requirements generated per control',
                    tone: 'success'
                  },
                  {
                    label: 'Status',
                    value:
                    p.status === 'published' ?
                    'In force across the organization' :
                    'Not yet effective',
                    tone: p.status === 'published' ? 'success' : 'warning'
                  }]
                  } />
                
              </div>);

          }
        }} />
      
      <IngestionPipeline open={uploadOpen} onClose={() => setUploadOpen(false)} />
    </>);

}
