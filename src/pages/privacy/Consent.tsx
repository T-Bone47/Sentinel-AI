import React from 'react';
import { FileBadge } from 'lucide-react';
import { EntityWorkspace } from '../../components/org/EntityWorkspace';
import { MetricTile } from '../../components/common/MetricCard';
import { SectionCard } from '../../components/common/SectionCard';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { ProgressBar } from '../../components/ui/Progress';
import { RelationChain } from '../../components/cyber/InvestigationChain';
import { StackedBarsChart } from '../../components/charts/ChartPrimitives';
import { MetaStat } from '../../components/layout/PageHeader';
import { type Column, type TableFilter } from '../../components/ui/DataTable';
import { getConsents } from '../../services/api';
import { useApiResource } from '../../hooks/useApiResource';
import { AsyncSection } from '../../components/common/AsyncSection';
import { formatRelative } from '../../utils/format';
import type { ConsentRecord } from '../../types/domain';

const statusTone = {
  valid: 'success',
  partial: 'warning',
  violation: 'danger'
} as const;

const columns: Column<ConsentRecord>[] = [
{
  id: 'purpose',
  header: 'Purpose',
  accessor: (c) => c.purpose,
  width: 210,
  sticky: true,
  hideable: false,
  cell: (c) =>
  <div className="min-w-0">
        <p className="truncate font-medium">{c.purpose}</p>
        <p className="truncate text-2xs text-muted-foreground">{c.application}</p>
      </div>

},
{
  id: 'principals',
  header: 'Data principals',
  accessor: (c) => c.principals,
  width: 140,
  align: 'right',
  cell: (c) =>
  <span className="font-mono text-[13px]">{c.principals.toLocaleString()}</span>

},
{
  id: 'coverage',
  header: 'Consent coverage',
  accessor: (c) => c.coverage,
  width: 190,
  cell: (c) =>
  <ProgressBar
    value={c.coverage}
    size="sm"
    tone={c.coverage >= 95 ? 'success' : c.coverage >= 80 ? 'warning' : 'danger'}
    showValue />


},
{
  id: 'basis',
  header: 'Lawful basis',
  accessor: (c) => c.basis,
  width: 152,
  cell: (c) => <Badge tone="neutral">{c.basis}</Badge>
},
{
  id: 'status',
  header: 'Status',
  accessor: (c) => c.status,
  width: 118,
  cell: (c) =>
  <Badge tone={statusTone[c.status]} dot>
        {c.status}
      </Badge>

},
{
  id: 'withdrawal',
  header: 'Withdrawal rate',
  accessor: (c) => c.withdrawalRate,
  width: 148,
  align: 'right',
  cell: (c) =>
  <span
    className={
    c.withdrawalRate > 5 ?
    'font-mono text-[13px] font-semibold text-warning' :
    'font-mono text-[13px] text-muted-foreground'
    }>
    
        {c.withdrawalRate}%
      </span>

},
{
  id: 'updated',
  header: 'Updated',
  accessor: (c) => c.lastUpdated,
  width: 124,
  cell: (c) =>
  <span className="font-mono text-2xs text-muted-foreground">
        {formatRelative(c.lastUpdated)}
      </span>

}];


const buildFilters = (rows: ConsentRecord[]): TableFilter<ConsentRecord>[] => [
{
  id: 'status',
  label: 'Status',
  options: [
  { value: 'valid', label: 'Valid' },
  { value: 'partial', label: 'Partial' },
  { value: 'violation', label: 'Violation' }],

  predicate: (row, value) => row.status === value
},
{
  id: 'basis',
  label: 'Lawful basis',
  options: [
  { value: 'Consent', label: 'Consent' },
  { value: 'Contract', label: 'Contract' },
  { value: 'Legal Obligation', label: 'Legal obligation' }],

  predicate: (row, value) => row.basis === value
}];


export function Consent() {
  const state = useApiResource(() => getConsents(), []);
  const consentRecords = state.data?.data ?? [];
  const filters = React.useMemo(() => buildFilters(consentRecords), [consentRecords]);
  const violations = consentRecords.filter((c) => c.status === 'violation').length;
  const chartData = consentRecords.map((c) => ({
    purpose: c.purpose,
    covered: c.coverage,
    gap: 100 - c.coverage
  }));


  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <EntityWorkspace<ConsentRecord>
      title="Consent Management"
      subtitle="Lawful basis for every processing purpose, with live coverage against the data principals actually in each dataset."
      eyebrow={
      <Badge tone="danger" dot>
          {violations} purposes processing without valid consent
        </Badge>
      }
      meta={
      <>
          <MetaStat
          label="Purposes"
          value={String(consentRecords.length)}
          icon={<FileBadge className="h-3.5 w-3.5" aria-hidden />} />
        
          <MetaStat label="Coverage" value="94%" />
          <MetaStat label="Requests fulfilled in SLA" value="100%" />
        </>
      }
      metrics={
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricTile label="Processing purposes" value={consentRecords.length} index={0} />
          <MetricTile
          label="Violations"
          value={violations}
          tone="critical"
          caption="legal review required"
          index={1} />
        
          <MetricTile
          label="Partial coverage"
          value={consentRecords.filter((c) => c.status === 'partial').length}
          tone="warning"
          caption="re-collection recommended"
          index={2} />
        
          <MetricTile
          label="Valid"
          value={consentRecords.filter((c) => c.status === 'valid').length}
          tone="success"
          caption="fully documented basis"
          index={3} />
        
        </section>
      }
      aside={
      <SectionCard title="Coverage by purpose" description="Consented versus gap">
          <StackedBarsChart
          label="Consent coverage by purpose"
          data={chartData}
          xKey="purpose"
          layout="vertical"
          height={260}
          series={[
          { key: 'covered', name: 'Consented', color: 'var(--success)' },
          { key: 'gap', name: 'Gap', color: 'var(--risk-critical)' }]
          }
          showLegend />
        
        </SectionCard>
      }
      columns={columns}
      rows={consentRecords}
      getRowId={(c) => c.id}
      filters={filters}
      pageSize={7}
      ariaLabel="Consent register"
      exportName="sentinel-consent"
      searchPlaceholder="Search purposes, applications, basis..."
      detail={{
        title: (c) => c.purpose,
        subtitle: (c) =>
        `${c.id} · ${c.application} · ${c.principals.toLocaleString()} data principals`,
        eyebrow: (c) =>
        <div className="flex flex-wrap items-center gap-2">
            <Badge tone={statusTone[c.status]} dot>
              {c.status}
            </Badge>
            <Badge tone="neutral">{c.basis}</Badge>
          </div>,

        actions: () => <Button variant="primary">Re-collect consent</Button>,
        render: (c) =>
        <div className="space-y-6">
            <div className="rounded-xl border border-border bg-surface-2/50 p-4">
              <p className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                Consent coverage
              </p>
              <p className="mt-1 font-mono text-4xl font-semibold leading-none">
                {c.coverage}
                <span className="text-base font-normal text-muted-foreground">%</span>
              </p>
              <p className="mt-2 text-xs text-muted-foreground">
                {Math.round(c.principals * (100 - c.coverage) / 100).toLocaleString()} data
                principals lack a recorded basis for this purpose.
              </p>
            </div>
            <RelationChain
            items={[
            { label: 'Purpose', value: c.purpose },
            { label: 'Application', value: c.application },
            { label: 'Lawful basis', value: c.basis },
            {
              label: 'Coverage',
              value: `${c.coverage}% of ${c.principals.toLocaleString()} principals`,
              tone: c.coverage >= 95 ? 'success' : 'critical'
            },
            {
              label: 'Control',
              value: 'CTL-DPDP-6 · Valid consent captured for every processing purpose',
              tone: 'warning'
            },
            {
              label: 'Withdrawal',
              value: `${c.withdrawalRate}% withdrawal rate`,
              tone: c.withdrawalRate > 5 ? 'warning' : 'neutral'
            }]
            } />
          
          </div>

      }} />);


}