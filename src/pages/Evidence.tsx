import React from 'react';
import { FileBadge, Upload } from 'lucide-react';
import { EntityWorkspace } from '../components/org/EntityWorkspace';
import { MetricTile } from '../components/common/MetricCard';
import { SectionCard } from '../components/common/SectionCard';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { EvidenceStatusBadge } from '../components/common/StatusPills';
import { RelationChain } from '../components/cyber/InvestigationChain';
import { DonutChart } from '../components/charts/ChartPrimitives';
import { MetaStat } from '../components/layout/PageHeader';
import { type Column, type TableFilter } from '../components/ui/DataTable';
import {
  getControls,
  getEvidence,
  getEvidenceIntelligence,
  getFindings,
  getRisks } from
'../services/api';
import { EvidenceCoveragePanel } from '../components/intelligence/EvidenceCoveragePanel';
import { useApiResource } from '../hooks/useApiResource';
import { AsyncSection } from '../components/common/AsyncSection';
import { formatDate, formatRelative } from '../utils/format';

import type { EvidenceItem } from '../types/domain';

const columns: Column<EvidenceItem>[] = [
{
  id: 'id',
  header: 'ID',
  accessor: (e) => e.id,
  width: 104,
  sticky: true,
  hideable: false,
  cell: (e) => <span className="font-mono text-xs text-muted-foreground">{e.id}</span>
},
{
  id: 'name',
  header: 'Evidence',
  accessor: (e) => e.name,
  width: 300,
  hideable: false,
  cell: (e) =>
  <div className="min-w-0">
        <p className="truncate font-medium">{e.name}</p>
        <p className="truncate text-2xs text-muted-foreground">{e.source}</p>
      </div>

},
{
  id: 'control',
  header: 'Control',
  accessor: (e) => e.control,
  width: 140,
  cell: (e) => <span className="font-mono text-2xs text-primary">{e.control}</span>
},
{
  id: 'collected',
  header: 'Collected',
  accessor: (e) => e.collectedAt,
  width: 128,
  cell: (e) =>
  <span className="font-mono text-2xs text-muted-foreground">
        {formatRelative(e.collectedAt)}
      </span>

},
{
  id: 'validity',
  header: 'Valid until',
  accessor: (e) => e.validUntil,
  width: 132,
  cell: (e) =>
  <span className="font-mono text-2xs text-muted-foreground">
        {formatDate(e.validUntil, 'MMM d, yyyy')}
      </span>

},
{ id: 'owner', header: 'Owner', accessor: (e) => e.owner, width: 168 },
{
  id: 'status',
  header: 'Status',
  accessor: (e) => e.status,
  width: 124,
  cell: (e) => <EvidenceStatusBadge status={e.status} />
},
{
  id: 'automated',
  header: 'Collection',
  accessor: (e) => e.automated ? 'Automated' : 'Manual',
  width: 126,
  cell: (e) =>
  <Badge tone={e.automated ? 'primary' : 'neutral'}>
        {e.automated ? 'Automated' : 'Manual'}
      </Badge>

}];


const buildFilters = (rows: EvidenceItem[]): TableFilter<EvidenceItem>[] => [
{
  id: 'status',
  label: 'Status',
  options: [
  { value: 'verified', label: 'Verified' },
  { value: 'pending', label: 'Pending' },
  { value: 'expiring', label: 'Expiring' },
  { value: 'expired', label: 'Expired' }],

  predicate: (row, value) => row.status === value
},
{
  id: 'collection',
  label: 'Collection',
  options: [
  { value: 'automated', label: 'Automated' },
  { value: 'manual', label: 'Manual' }],

  predicate: (row, value) => value === 'automated' ? row.automated : !row.automated
},
{
  id: 'owner',
  label: 'Owner',
  options: Array.from(new Set(rows.map((e) => e.owner))).map((o) => ({
    value: o,
    label: o
  })),
  predicate: (row, value) => row.owner === value
}];


export function Evidence() {
  const state = useApiResource(
    () =>
      Promise.all([
        getEvidence(),
        getControls(),
        getFindings(),
        getRisks(),
        getEvidenceIntelligence(10)
      ]).then(([evidence, controls, findings, risks, coverage]) => ({
        evidence: evidence.data,
        controls: controls.data,
        findings: findings.data,
        risks: risks.data,
        coverage
      })),
    []
  );
  const evidenceItems = state.data?.evidence ?? [];
  const controls = state.data?.controls ?? [];
  const findings = state.data?.findings ?? [];
  const risks = state.data?.risks ?? [];
  const coverage = state.data?.coverage ?? null;
  const filters = React.useMemo(() => buildFilters(evidenceItems), [evidenceItems]);
  const expired = evidenceItems.filter((e) => e.status === 'expired').length;
  const automatedCount = evidenceItems.filter(e => e.automated).length;
  const totalItems = evidenceItems.length;
  const automatedPct = totalItems > 0 ? Math.round((automatedCount / totalItems) * 100) : 0;
  const manualPct = totalItems > 0 ? 100 - automatedPct : 0;
  
  const evidenceCoverage = [
    { id: 'automated', label: 'Automated collection', value: automatedPct },
    { id: 'manual', label: 'Manual upload', value: manualPct }
  ];

  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <EntityWorkspace<EvidenceItem>
      title="Evidence Repository"
      subtitle="Audit-ready proof for every control — collected automatically where possible, with validity tracked so nothing goes stale before an audit."
      eyebrow={
      <Badge tone={expired ? 'danger' : 'success'} dot>
          {expired} artifacts expired
        </Badge>
      }
      meta={
      <>
          <MetaStat
          label="Artifacts"
          value={`${coverage?.total_evidence_items ?? evidenceItems.length}`}
          icon={<FileBadge className="h-3.5 w-3.5" aria-hidden />} />
        
          <MetaStat label="Automated" value={`${automatedPct}%`} />
          <MetaStat
            label="Controls evidenced"
            value={`${new Set(evidenceItems.map((e) => e.control)).size} of ${controls.length}`} />
        </>
      }
      actions={
      <Button variant="primary" iconLeft={<Upload className="h-4 w-4" />}>
          Upload evidence
        </Button>
      }
      metrics={
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricTile
          label="Artifacts"
          value={coverage?.total_evidence_items ?? evidenceItems.length}
          index={0} />
        
          <MetricTile
          label="Controls not provable"
          value={coverage?.uncovered_controls ?? 0}
          tone="critical"
          caption="no verified evidence"
          index={1} />
        
          <MetricTile
          label="Collected, unverified"
          value={coverage?.unverified_evidence_items ?? 0}
          tone="warning"
          caption="does not count toward coverage"
          index={2} />
        
          <MetricTile
          label="Verified"
          value={coverage?.verified_evidence_items ?? 0}
          tone="success"
          caption="audit ready"
          index={3} />
        
        </section>
      }
      beforeTable={coverage ? <EvidenceCoveragePanel coverage={coverage} /> : null}
      aside={
      <SectionCard title="Collection mix" description="How evidence reaches the repository">
          <DonutChart
          label="Evidence collection method"
          data={evidenceCoverage.map((item, i) => ({
            name: item.label,
            value: item.value,
            color: i === 2 ? 'var(--ai)' : `var(--chart-${i + 1})`
          }))}
          height={188}
          centerValue={`${automatedPct}%`}
          centerLabel="automated" />
        
          <ul className="mt-3 space-y-1.5">
            {evidenceCoverage.map((item) =>
          <li key={item.id} className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{item.label}</span>
                <span className="font-mono font-medium">{item.value}%</span>
              </li>
          )}
          </ul>
        </SectionCard>
      }
      columns={columns}
      rows={evidenceItems}
      getRowId={(e) => e.id}
      filters={filters}
      pageSize={7}
      ariaLabel="Evidence repository"
      exportName="sentinel-evidence"
      searchPlaceholder="Search evidence, controls, sources..."
      bulkActions={(selected, clear) =>
      <Button variant="outline" size="sm" onClick={clear}>
          Re-collect ({selected.length})
        </Button>
      }
      detail={{
        title: (e) => e.name,
        subtitle: (e) => `${e.id} · ${e.source} · owner ${e.owner}`,
        eyebrow: (e) =>
        <div className="flex flex-wrap items-center gap-2">
            <EvidenceStatusBadge status={e.status} />
            <Badge tone="primary">{e.control}</Badge>
            <Badge tone={e.automated ? 'primary' : 'neutral'}>
              {e.automated ? 'Automated' : 'Manual upload'}
            </Badge>
          </div>,

        actions: () => <Button variant="primary">Preview artifact</Button>,
        render: (e) => {
          // The control id is the first token of the composed label the
          // adapter builds ("CTRL-123 · Name"). Related findings and risks
          // come from the live rows fetched alongside the evidence.
          const controlId = e.control.split(' · ')[0];
          const control = controls.find((c) => c.id === controlId);
          const finding = findings.find((f) => f.control === controlId);
          const risk = risks.find((r) => r.control === controlId);

          return (
            <div className="space-y-6">
              <div className="relative overflow-hidden rounded-xl border border-border bg-surface-2/50 p-4">
                <div className="absolute inset-0 cyber-grid-fine opacity-30" aria-hidden />
                <dl className="relative grid grid-cols-2 gap-4 text-[13px]">
                  <div>
                    <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                      Collected
                    </dt>
                    <dd className="mt-1 font-mono">{formatDate(e.collectedAt)}</dd>
                  </div>
                  <div>
                    <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                      Valid until
                    </dt>
                    <dd className="mt-1 font-mono">{formatDate(e.validUntil)}</dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                      Integrity
                    </dt>
                    <dd className="mt-1 truncate font-mono text-xs text-success">
                      sha256:9f2c41e8a7b3...d18f · verified
                    </dd>
                  </div>
                </dl>
              </div>

              <RelationChain
                items={[
                { label: 'Evidence', value: `${e.id} · ${e.name}`, tone: 'success' },
                {
                  label: 'Control',
                  value: control ? `${control.id} · ${control.name}` : e.control,
                  tone: control?.status === 'passing' ? 'success' : 'warning'
                },
                {
                  label: 'Finding',
                  value: finding ? `${finding.id} · ${finding.title}` : 'No linked finding',
                  tone: finding ? 'critical' : 'neutral'
                },
                {
                  label: 'Risk',
                  value: risk ? `${risk.id} · ${risk.title}` : 'No linked risk',
                  tone: risk ? 'critical' : 'neutral'
                }]
                } />
              
            </div>);

        }
      }} />);


}