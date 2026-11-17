import React from 'react';
import { ShieldCheck, Sparkles } from 'lucide-react';
import { EntityWorkspace } from '../components/org/EntityWorkspace';
import { MetricTile } from '../components/common/MetricCard';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { ControlStatusBadge } from '../components/common/StatusPills';
import { RelationChain } from '../components/cyber/InvestigationChain';
import { MetaStat } from '../components/layout/PageHeader';
import { type Column, type TableFilter } from '../components/ui/DataTable';
import { getControls, getEvidence, getFindings, getRisks } from '../services/api';
import { useApiResource } from '../hooks/useApiResource';
import { AsyncSection } from '../components/common/AsyncSection';

import { formatRelative } from '../utils/format';
import type { Control } from '../types/domain';

const columns: Column<Control>[] = [
{
  id: 'id',
  header: 'Control ID',
  accessor: (c) => c.id,
  width: 132,
  sticky: true,
  hideable: false,
  cell: (c) => <span className="font-mono text-xs text-primary">{c.id}</span>
},
{
  id: 'name',
  header: 'Control',
  accessor: (c) => c.name,
  width: 340,
  hideable: false,
  cell: (c) =>
  <div className="min-w-0">
        <p className="truncate font-medium">{c.name}</p>
        <p className="truncate text-2xs text-muted-foreground">{c.policy}</p>
      </div>

},
{
  id: 'framework',
  header: 'Framework',
  accessor: (c) => c.framework,
  width: 148,
  cell: (c) => <Badge tone="neutral">{c.framework}</Badge>
},
{
  id: 'status',
  header: 'Status',
  accessor: (c) => c.status,
  width: 124,
  cell: (c) => <ControlStatusBadge status={c.status} />
},
{
  id: 'evidence',
  header: 'Evidence',
  accessor: (c) => c.evidence,
  width: 100,
  align: 'right',
  cell: (c) => <span className="font-mono text-[13px]">{c.evidence}</span>
},
{
  id: 'findings',
  header: 'Findings',
  accessor: (c) => c.findings,
  width: 100,
  align: 'right',
  cell: (c) =>
  <span
    className={
    c.findings > 0 ?
    'font-mono text-[13px] font-semibold text-risk-critical' :
    'font-mono text-[13px] text-muted-foreground'
    }>
    
        {c.findings}
      </span>

},
{ id: 'owner', header: 'Owner', accessor: (c) => c.owner, width: 168 },
{
  id: 'automated',
  header: 'Testing',
  accessor: (c) => c.automated ? 'Automated' : 'Manual',
  width: 122,
  cell: (c) =>
  <Badge tone={c.automated ? 'primary' : 'neutral'}>
        {c.automated ? 'Automated' : 'Manual'}
      </Badge>

},
{
  id: 'lastTested',
  header: 'Last tested',
  accessor: (c) => c.lastTested,
  width: 128,
  cell: (c) =>
  <span className="font-mono text-2xs text-muted-foreground">
        {formatRelative(c.lastTested)}
      </span>

}];


const buildFilters = (rows: Control[]): TableFilter<Control>[] => [
{
  id: 'status',
  label: 'Status',
  options: [
  { value: 'passing', label: 'Passing' },
  { value: 'failing', label: 'Failing' },
  { value: 'partial', label: 'Partial' },
  { value: 'not-tested', label: 'Not tested' }],

  predicate: (row, value) => row.status === value
},
{
  id: 'framework',
  label: 'Framework',
  options: Array.from(new Set(rows.map((c) => c.framework))).map((f) => ({
    value: f,
    label: f
  })),
  predicate: (row, value) => row.framework === value
},
{
  id: 'testing',
  label: 'Testing',
  options: [
  { value: 'automated', label: 'Automated' },
  { value: 'manual', label: 'Manual' }],

  predicate: (row, value) => value === 'automated' ? row.automated : !row.automated
},
{
  id: 'owner',
  label: 'Owner',
  options: Array.from(new Set(rows.map((c) => c.owner))).map((o) => ({
    value: o,
    label: o
  })),
  predicate: (row, value) => row.owner === value
}];


export function Controls() {
  // The control drawer traces control -> evidence -> finding -> risk, so the
  // related rows are fetched alongside rather than read from seed arrays.
  const state = useApiResource(
    () =>
      Promise.all([getControls(), getEvidence(), getFindings(), getRisks()]).then(
        ([controls, evidence, findings, risks]) => ({
          controls: controls.data,
          evidenceItems: evidence.data,
          findings: findings.data,
          risks: risks.data
        })
      ),
    []
  );
  const controls = state.data?.controls ?? [];
  const evidenceItems = state.data?.evidenceItems ?? [];
  const findings = state.data?.findings ?? [];
  const risks = state.data?.risks ?? [];
  const filters = React.useMemo(() => buildFilters(controls), [controls]);
  const failing = controls.filter((c) => c.status === 'failing').length;


  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <EntityWorkspace<Control>
      title="Compliance Controls"
      subtitle="Controls are the spine of the platform — every policy obligation, evidence artifact, finding and risk resolves through them."
      eyebrow={
      <Badge tone="danger" dot>
          {failing} controls failing across {new Set(controls.map((c) => c.framework)).size} frameworks
        </Badge>
      }
      meta={
      <>
          <MetaStat
          label="Controls"
          value={String(controls.length)}
          icon={<ShieldCheck className="h-3.5 w-3.5" aria-hidden />} />
        
          <MetaStat
            label="Automatable"
            value={`${controls.length ? Math.round((controls.filter((c) => c.automated).length / controls.length) * 100) : 0}%`} />
          <MetaStat
            label="Evidence coverage"
            value={`${controls.length ? Math.round((controls.filter((c) => c.evidence > 0).length / controls.length) * 100) : 0}%`} />
        </>
      }
      actions={
      <Button variant="ai" iconLeft={<Sparkles className="h-4 w-4" />}>
          Map controls
        </Button>
      }
      metrics={
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricTile label="Total controls" value={controls.length} index={0} />
          <MetricTile
          label="Failing"
          value={failing}
          tone="critical"
          caption="require remediation"
          index={1} />
        
          <MetricTile
          label="Partial"
          value={controls.filter((c) => c.status === 'partial').length}
          tone="warning"
          caption="incomplete coverage"
          index={2} />
        
          <MetricTile
          label="Passing"
          value={controls.filter((c) => c.status === 'passing').length}
          tone="success"
          caption="evidence verified"
          index={3} />
        
        </section>
      }
      columns={columns}
      rows={controls}
      getRowId={(c) => c.id}
      filters={filters}
      ariaLabel="Control library"
      exportName="sentinel-controls"
      searchPlaceholder="Search controls, policies, owners..."
      bulkActions={(selected, clear) =>
      <Button
        variant="ai"
        size="sm"
        iconLeft={<Sparkles className="h-3.5 w-3.5" />}
        onClick={clear}>
        
          Test controls ({selected.length})
        </Button>
      }
      detail={{
        title: (c) => c.name,
        subtitle: (c) => `${c.id} · ${c.framework} · owner ${c.owner}`,
        eyebrow: (c) =>
        <div className="flex flex-wrap items-center gap-2">
            <ControlStatusBadge status={c.status} />
            <Badge tone="neutral">{c.framework}</Badge>
            <Badge tone={c.automated ? 'primary' : 'neutral'}>
              {c.automated ? 'Automated test' : 'Manual test'}
            </Badge>
          </div>,

        actions: () => <Button variant="primary">Run test</Button>,
        render: (c) => {
          const relatedEvidence = evidenceItems.filter((e) => e.control.startsWith(c.id));
          const relatedFindings = findings.filter((f) => f.control === c.id);
          const relatedRisk = risks.find((r) => r.control === c.id);

          return (
            <div className="space-y-6">
              <div className="grid grid-cols-3 gap-3">
                <Stat label="Evidence" value={c.evidence} />
                <Stat label="Findings" value={c.findings} tone="critical" />
                <Stat label="Last tested" value={formatRelative(c.lastTested)} small />
              </div>

              <RelationChain
                items={[
                { label: 'Policy', value: c.policy },
                {
                  label: 'Control',
                  value: `${c.id} · ${c.name}`,
                  tone: c.status === 'passing' ? 'success' : 'warning'
                },
                {
                  label: 'Evidence',
                  value: relatedEvidence.length ?
                  relatedEvidence.map((e) => e.id).join(', ') :
                  'No artifacts collected',
                  tone: relatedEvidence.length ? 'success' : 'critical'
                },
                {
                  label: 'Finding',
                  value: relatedFindings.length ?
                  relatedFindings[0].title :
                  'No open findings',
                  tone: relatedFindings.length ? 'critical' : 'success'
                },
                {
                  label: 'Risk',
                  value: relatedRisk ?
                  `${relatedRisk.id} · ${relatedRisk.title} (score ${relatedRisk.score})` :
                  'No linked risk',
                  tone: relatedRisk ? 'critical' : 'neutral'
                }]
                } />
              

              {relatedEvidence.length > 0 &&
              <div>
                  <p className="mb-2 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                    Evidence artifacts
                  </p>
                  <ul className="space-y-2">
                    {relatedEvidence.map((item) =>
                  <li
                    key={item.id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface-2/50 px-3.5 py-2.5">
                    
                        <span className="min-w-0">
                          <span className="block truncate text-[13px]">{item.name}</span>
                          <span className="block font-mono text-2xs text-muted-foreground">
                            {item.id} · {item.source}
                          </span>
                        </span>
                        <Badge tone={item.status === 'verified' ? 'success' : 'warning'}>
                          {item.status}
                        </Badge>
                      </li>
                  )}
                  </ul>
                </div>
              }
            </div>);

        }
      }} />);


}

function Stat({
  label,
  value,
  tone = 'default',
  small = false





}: {label: string;value: string | number;tone?: 'default' | 'critical';small?: boolean;}) {
  return (
    <div className="rounded-lg border border-border bg-surface-2/50 p-3.5">
      <p className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
        {label}
      </p>
      <p
        className={
        small ?
        'mt-1.5 font-mono text-[13px]' :
        tone === 'critical' && Number(value) > 0 ?
        'mt-1.5 font-mono text-2xl font-semibold text-risk-critical' :
        'mt-1.5 font-mono text-2xl font-semibold'
        }>
        
        {value}
      </p>
    </div>);

}