import React, { useState } from 'react';
import { Activity, Download, Lock, Sparkles } from 'lucide-react';
import { PageHeader, MetaStat } from '../components/layout/PageHeader';
import { DataTable, type Column, type TableFilter } from '../components/ui/DataTable';
import { Button } from '../components/ui/Button';
import { Badge, RiskBadge } from '../components/ui/Badge';
import { Drawer } from '../components/ui/Drawer';
import { SegmentedControl } from '../components/ui/Tabs';
import { getAuditLogs } from '../services/api';
import { useApiResource } from '../hooks/useApiResource';
import { AsyncSection } from '../components/common/AsyncSection';
import { formatDateTime, formatRelative } from '../utils/format';
import type { AuditEvent } from '../types/domain';

const columns: Column<AuditEvent>[] = [
{
  id: 'timestamp',
  header: 'Time',
  accessor: (e) => e.timestamp,
  width: 168,
  sticky: true,
  hideable: false,
  cell: (e) =>
  <div>
        <p className="font-mono text-xs">{formatDateTime(e.timestamp).split(' at ')[1]}</p>
        <p className="mt-0.5 text-2xs text-muted-foreground">{formatRelative(e.timestamp)}</p>
      </div>

},
{
  id: 'action',
  header: 'Action',
  accessor: (e) => e.action,
  width: 240,
  hideable: false,
  cell: (e) =>
  <span className="font-mono text-xs font-medium text-foreground">{e.action}</span>

},
{
  id: 'actor',
  header: 'Actor',
  accessor: (e) => e.actor,
  width: 240,
  cell: (e) =>
  <div className="min-w-0">
        <p
      className={
      e.source === 'Sentinel AI' ?
      'truncate text-[13px] font-medium text-ai' :
      'truncate text-[13px] font-medium'
      }>
      
          {e.actor}
        </p>
        <p className="mt-0.5 truncate text-2xs text-muted-foreground">{e.actorRole}</p>
      </div>

},
{ id: 'target', header: 'Target', accessor: (e) => e.target, width: 260 },
{
  id: 'severity',
  header: 'Severity',
  accessor: (e) => e.severity,
  width: 118,
  cell: (e) => <RiskBadge level={e.severity} />
},
{
  id: 'source',
  header: 'Source',
  accessor: (e) => e.source,
  width: 132,
  cell: (e) =>
  <Badge tone={e.source === 'Sentinel AI' ? 'ai' : 'neutral'}>{e.source}</Badge>

},
{
  id: 'ip',
  header: 'IP address',
  accessor: (e) => e.ip,
  width: 140,
  cell: (e) => <span className="font-mono text-xs text-muted-foreground">{e.ip}</span>
}];


const buildFilters = (rows: AuditEvent[]): TableFilter<AuditEvent>[] => [
{
  id: 'severity',
  label: 'Severity',
  options: [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
  { value: 'info', label: 'Info' }],

  predicate: (row, value) => row.severity === value
},
{
  id: 'source',
  label: 'Source',
  options: Array.from(new Set(rows.map((r) => r.source))).map((s) => ({
    value: s,
    label: s
  })),
  predicate: (row, value) => row.source === value
}];


const ranges = [
{ id: '24h', label: '24h' },
{ id: '7d', label: '7d' },
{ id: '30d', label: '30d' }];


export function AuditLog() {
  const [range, setRange] = useState('7d');
  const [active, setActive] = useState<AuditEvent | null>(null);

  // 10,000 rows live in Postgres, so this stays server-paginated and pushes
  // the date window down to the API rather than pulling everything.
  const days = range === '24h' ? 1 : range === '7d' ? 7 : range === '30d' ? 30 : 0;
  const dateFrom = days
    ? new Date(Date.now() - days * 86_400_000).toISOString().slice(0, 10)
    : undefined;
  const state = useApiResource(
    () => getAuditLogs({ page_size: 200, date_from: dateFrom }),
    [dateFrom]
  );
  const auditEvents = state.data?.data ?? [];
  const filters = React.useMemo(() => buildFilters(auditEvents), [auditEvents]);


  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={
        <Badge tone="success" dot>
            <Lock className="h-3 w-3" aria-hidden />
            Tamper-evident · WORM storage
          </Badge>
        }
        title="Audit Log"
        subtitle="An immutable record of every action taken by people, services and Sentinel across the workspace."
        meta={
        <>
            <MetaStat
            label="Events retained"
            value="7 years"
            icon={<Activity className="h-3.5 w-3.5" aria-hidden />} />
          
            <MetaStat label="Streamed to" value="Splunk · S3" />
            <MetaStat label="Integrity checks" value="Passing" />
          </>
        }
        actions={
        <>
            <SegmentedControl
            items={ranges}
            value={range}
            onChange={setRange}
            ariaLabel="Time range" />
          
            <Button variant="outline" iconLeft={<Download className="h-4 w-4" />}>
              Export log
            </Button>
          </>
        } />
      

      <DataTable<AuditEvent>
        ariaLabel="Audit log"
        columns={columns}
        rows={auditEvents}
        getRowId={(e) => e.id}
        filters={filters}
        pageSize={10}
        exportName="sentinel-audit-log"
        searchPlaceholder="Search actors, actions, targets..."
        onRowClick={setActive}
        toolbarExtra={
        <Button variant="ghost" size="sm" iconLeft={<Sparkles className="h-3.5 w-3.5" />}>
            Explain activity
          </Button>
        } />
      

      <Drawer
        open={Boolean(active)}
        onClose={() => setActive(null)}
        title={active?.action ?? ''}
        subtitle={active ? formatDateTime(active.timestamp) : undefined}
        eyebrow={active ? <RiskBadge level={active.severity} /> : undefined}
        footer={
        <Button variant="ghost" onClick={() => setActive(null)}>
            Close
          </Button>
        }>
        
        {active &&
        <div className="space-y-5">
            <dl className="grid grid-cols-2 gap-3">
              {[
            ['Event ID', active.id],
            ['Actor', active.actor],
            ['Role', active.actorRole],
            ['Source', active.source],
            ['Target', active.target],
            ['IP address', active.ip]].
            map(([label, value]) =>
            <div key={label} className="rounded-lg border border-border bg-surface-2/50 p-3">
                  <dt className="text-2xs uppercase tracking-wider text-muted-foreground">
                    {label}
                  </dt>
                  <dd className="mt-1 break-words font-mono text-xs">{value}</dd>
                </div>
            )}
            </dl>
            <div>
              <h3 className="mb-2 text-[13px] font-semibold">Raw event</h3>
              <pre className="overflow-x-auto rounded-lg border border-border bg-surface-2/60 p-3.5 font-mono text-2xs leading-relaxed text-muted-foreground">
                {JSON.stringify(active, null, 2)}
              </pre>
            </div>
          </div>
        }
      </Drawer>
    </div>);

}