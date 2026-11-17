import React, { useState } from 'react';
import { Flame, Plus, ShieldAlert, Sparkles, UserPlus } from 'lucide-react';
import { PageHeader, MetaStat } from '../components/layout/PageHeader';
import { SectionCard } from '../components/common/SectionCard';
import { DataTable, type Column, type TableFilter } from '../components/ui/DataTable';
import { Button } from '../components/ui/Button';
import { Badge, RiskBadge } from '../components/ui/Badge';
import { InvestigationDrawer } from '../components/risk/InvestigationDrawer';
import { ConfidenceMeter, RiskScore, RiskStatusBadge } from '../components/common/StatusPills';
import { StackedBarsChart } from '../components/charts/ChartPrimitives';

import { formatRelative } from '../utils/format';
import type { RiskItem } from '../types/domain';

const columns: Column<RiskItem>[] = [
  {
    id: 'id',
    header: 'ID',
    accessor: (r) => r.id,
    width: 104,
    sticky: true,
    hideable: false,
    cell: (r) => <span className="font-mono text-xs text-muted-foreground">{r.id}</span>
  },
  {
    id: 'title',
    header: 'Risk',
    accessor: (r) => r.title,
    width: 300,
    hideable: false,
    cell: (r) =>
      <div className="min-w-0">
        <p className="truncate font-medium">{r.title}</p>
        <p className="mt-0.5 truncate font-mono text-2xs text-muted-foreground">
          {r.assetType} · {r.asset}
        </p>
      </div>

  },
  {
    id: 'severity',
    header: 'Severity',
    accessor: (r) => r.score,
    width: 112,
    cell: (r) => <RiskBadge level={r.severity} withDot={false} />
  },
  {
    id: 'score',
    header: 'Score',
    accessor: (r) => r.score,
    width: 86,
    align: 'right',
    cell: (r) => <RiskScore score={r.score} />
  },
  {
    id: 'control',
    header: 'Control',
    accessor: (r) => r.control,
    width: 132,
    cell: (r) => <span className="font-mono text-2xs text-primary">{r.control}</span>
  },
  {
    id: 'framework',
    header: 'Framework',
    accessor: (r) => r.framework,
    width: 132,
    cell: (r) => <Badge tone="neutral">{r.framework}</Badge>
  },
  { id: 'owner', header: 'Owner', accessor: (r) => r.owner, width: 148 },
  { id: 'department', header: 'Department', accessor: (r) => r.department, width: 148 },
  {
    id: 'status',
    header: 'Status',
    accessor: (r) => r.status,
    width: 130,
    cell: (r) => <RiskStatusBadge status={r.status} />
  },
  {
    id: 'confidence',
    header: 'AI confidence',
    accessor: (r) => r.aiConfidence ?? 0,
    width: 148,
    cell: (r) => <ConfidenceMeter value={r.aiConfidence ?? 0} />
  },
  {
    id: 'updated',
    header: 'Updated',
    accessor: (r) => r.updatedAt,
    width: 124,
    cell: (r) =>
      <span className="font-mono text-2xs text-muted-foreground">
        {formatRelative(r.updatedAt)}
      </span>

  }];


const buildFilters = (rows: RiskItem[]): TableFilter<RiskItem>[] => [
  {
    id: 'severity',
    label: 'Severity',
    options: [
      { value: 'critical', label: 'Critical' },
      { value: 'high', label: 'High' },
      { value: 'medium', label: 'Medium' },
      { value: 'low', label: 'Low' }],

    predicate: (row, value) => row.severity === value
  },
  {
    id: 'status',
    label: 'Status',
    options: [
      { value: 'open', label: 'Open' },
      { value: 'investigating', label: 'Investigating' },
      { value: 'mitigating', label: 'Mitigating' },
      { value: 'accepted', label: 'Accepted' },
      { value: 'closed', label: 'Closed' }],

    predicate: (row, value) => row.status === value
  },
  {
    id: 'owner',
    label: 'Owner',
    options: Array.from(new Set(rows.map((r) => r.owner))).map((o) => ({
      value: o,
      label: o
    })),
    predicate: (row, value) => row.owner === value
  },
  {
    id: 'framework',
    label: 'Framework',
    options: Array.from(new Set(rows.map((r) => r.framework))).map((f) => ({
      value: f,
      label: f
    })),
    predicate: (row, value) => row.framework === value
  },
  {
    id: 'asset',
    label: 'Asset type',
    options: Array.from(new Set(rows.map((r) => r.assetType))).map((a) => ({
      value: a,
      label: a
    })),
    predicate: (row, value) => row.assetType === value
  },
  {
    id: 'department',
    label: 'Department',
    options: Array.from(new Set(rows.map((r) => r.department))).map((d) => ({
      value: d,
      label: d
    })),
    predicate: (row, value) => row.department === value
  }];


import { getRisks } from '../services/api';
import { useApiResource } from '../hooks/useApiResource';
import { AsyncSection } from '../components/common/AsyncSection';

export function RiskCenter() {
  const [active, setActive] = useState<RiskItem | null>(null);
  const state = useApiResource(() => getRisks(), []);

  const items = state.data?.data ?? [];
  const filters = React.useMemo(() => buildFilters(items), [items]);
  const critical = items.filter((r) => r.severity === 'critical').length;
  const open = items.filter((r) => r.status !== 'closed').length;
  const highestScore = items.reduce((max, r) => Math.max(max, r.score), 0);
  // Charts below are computed from the live rows, not from a seeded series.
  const riskByDomain = React.useMemo(() => aggregateBy(items, (r) => r.department, 'domain'), [items]);
  const riskByStatus = React.useMemo(() => aggregateBy(items, (r) => r.status, 'status'), [items]);

  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow={
          <Badge tone="danger" dot>
            {critical} critical risks require action
          </Badge>
        }
        title="Risk Center"
        subtitle="Every exposure across identity, devices, cloud, applications, vendors and privacy — scored continuously and traced to a control."
        meta={
          <>
            <MetaStat
              label="Open"
              value={String(open)}
              icon={<ShieldAlert className="h-3.5 w-3.5" aria-hidden />} />

            <MetaStat
              label="Highest score"
              value={String(highestScore)}
              icon={<Flame className="h-3.5 w-3.5" aria-hidden />} />

            <MetaStat label="Mean time to mitigate" value="9 days" />
          </>
        }
        actions={
          <>
            <Button variant="ai" iconLeft={<Sparkles className="h-4 w-4" />}>
              Analyze register
            </Button>
            <Button variant="primary" iconLeft={<Plus className="h-4 w-4" />}>
              New risk
            </Button>
          </>
        } />


      <div className="grid gap-4 xl:grid-cols-3">
        <SectionCard
          title="Risk posture by status"
          description="Every registered risk, grouped by lifecycle state and severity"
          className="xl:col-span-2">

          {/* The register is a point-in-time snapshot — there is no opened/closed
              history in the data, so this shows the real current distribution
              instead of a fabricated velocity trend. */}
          <StackedBarsChart
            label="Risks by status and severity"
            data={riskByStatus}
            xKey="status"
            height={196}
            series={[
              { key: 'critical', name: 'Critical', color: 'var(--risk-critical)' },
              { key: 'high', name: 'High', color: 'var(--risk-high)' },
              { key: 'medium', name: 'Medium', color: 'var(--risk-medium)' },
              { key: 'low', name: 'Low', color: 'var(--success)' }]
            } />

        </SectionCard>
        <SectionCard
          title="Concentration"
          description="Where exposure clusters"
          delay={0.05}>

          <StackedBarsChart
            label="Risk by domain and severity"
            data={riskByDomain}
            xKey="domain"
            layout="vertical"
            height={196}
            series={[
              { key: 'critical', name: 'Critical', color: 'var(--risk-critical)' },
              { key: 'high', name: 'High', color: 'var(--risk-high)' },
              { key: 'medium', name: 'Medium', color: 'var(--risk-medium)' }]
            } />

        </SectionCard>
      </div>

      <DataTable<RiskItem>
        ariaLabel="Risk register"
        columns={columns}
        rows={items}
        getRowId={(r) => r.id}
        filters={filters}
        pageSize={9}
        exportName="sentinel-risk-register"
        searchPlaceholder="Search risks, assets, owners, controls..."
        onRowClick={setActive}
        bulkActions={(selected, clear) =>
          <>
            <Button
              variant="outline"
              size="sm"
              iconLeft={<UserPlus className="h-3.5 w-3.5" />}
              onClick={clear}>

              Assign owner
            </Button>
            <Button
              variant="ai"
              size="sm"
              iconLeft={<Sparkles className="h-3.5 w-3.5" />}
              onClick={clear}>

              Draft mitigations ({selected.length})
            </Button>
          </>
        }
        emptyTitle="No risks match these filters"
        emptyDescription="Nothing in the register matches this slice. Widen the filters to see more exposures." />


      <InvestigationDrawer risk={active} onClose={() => setActive(null)} />
    </div>);

}

/**
 * Group live risk rows into the {key, critical, high, medium, low} shape the
 * stacked bar chart expects. Counts only — no smoothing, no projection.
 */
function aggregateBy(
  rows: RiskItem[],
  keyOf: (risk: RiskItem) => string,
  keyName: string
): Array<Record<string, string | number>> {
  const buckets = new Map<string, Record<string, number>>();
  for (const row of rows) {
    const key = keyOf(row) || 'Unassigned';
    const bucket =
    buckets.get(key) ?? { critical: 0, high: 0, medium: 0, low: 0 };
    if (row.severity in bucket) bucket[row.severity] += 1;
    buckets.set(key, bucket);
  }
  return [...buckets.entries()].
  map(([key, counts]) => ({ [keyName]: key, ...counts })).
  sort(
    (a, b) =>
    Number(b.critical) + Number(b.high) - (Number(a.critical) + Number(a.high))
  ).
  slice(0, 8);
}
