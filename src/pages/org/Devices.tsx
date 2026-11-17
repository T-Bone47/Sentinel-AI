import React from 'react';
import { Laptop } from 'lucide-react';
import { EntityWorkspace } from '../../components/org/EntityWorkspace';
import { MetricTile } from '../../components/common/MetricCard';
import { SectionCard } from '../../components/common/SectionCard';
import { Badge, RiskBadge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { CheckPill } from '../../components/common/StatusPills';
import { RelationChain } from '../../components/cyber/InvestigationChain';
import { ProgressBar } from '../../components/ui/Progress';
import { MetaStat } from '../../components/layout/PageHeader';
import { type Column, type TableFilter } from '../../components/ui/DataTable';
import { getDevices } from '../../services/api';
import { useApiResource } from '../../hooks/useApiResource';
import { AsyncSection } from '../../components/common/AsyncSection';
import { formatRelative } from '../../utils/format';
import type { Device } from '../../types/domain';

const columns: Column<Device>[] = [
{
  id: 'id',
  header: 'Device',
  accessor: (d) => d.id,
  width: 190,
  sticky: true,
  hideable: false,
  cell: (d) =>
  <div className="min-w-0">
        <p className="truncate font-mono text-xs font-medium">{d.id}</p>
        <p className="truncate text-2xs text-muted-foreground">{d.name}</p>
      </div>

},
{ id: 'owner', header: 'Owner', accessor: (d) => d.owner, width: 160 },
{ id: 'os', header: 'OS', accessor: (d) => d.os, width: 150 },
{
  id: 'encryption',
  header: 'Encryption',
  accessor: (d) => d.encryption,
  width: 108,
  cell: (d) => <CheckPill state={d.encryption} />
},
{
  id: 'edr',
  header: 'EDR',
  accessor: (d) => d.edr,
  width: 80,
  cell: (d) => <CheckPill state={d.edr} />
},
{
  id: 'patch',
  header: 'Patch',
  accessor: (d) => d.patch,
  width: 88,
  cell: (d) => <CheckPill state={d.patch} />
},
{
  id: 'risk',
  header: 'Risk',
  accessor: (d) => d.riskLevel,
  width: 112,
  cell: (d) => <RiskBadge level={d.riskLevel} withDot={false} />
},
{
  id: 'compliance',
  header: 'Compliance',
  accessor: (d) => d.compliance,
  width: 110,
  cell: (d) => <CheckPill state={d.compliance} />
},
{
  id: 'lastSeen',
  header: 'Last seen',
  accessor: (d) => d.lastSeen,
  width: 124,
  cell: (d) =>
  <span className="font-mono text-2xs text-muted-foreground">
        {formatRelative(d.lastSeen)}
      </span>

}];


const buildFilters = (rows: Device[]): TableFilter<Device>[] => [
{
  id: 'os',
  label: 'Platform',
  options: Array.from(new Set(rows.map((d) => d.os.split(' ')[0]))).map((o) => ({
    value: o,
    label: o
  })),
  predicate: (row, value) => row.os.startsWith(value)
},
{
  id: 'risk',
  label: 'Risk',
  options: [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' }],

  predicate: (row, value) => row.riskLevel === value
},
{
  id: 'edr',
  label: 'EDR',
  options: [
  { value: 'pass', label: 'Healthy' },
  { value: 'warn', label: 'Degraded' },
  { value: 'fail', label: 'Unhealthy' }],

  predicate: (row, value) => row.edr === value
}];


export function Devices() {
  const state = useApiResource(() => getDevices(), []);
  const devices = state.data?.data ?? [];
  const filters = React.useMemo(() => buildFilters(devices), [devices]);
  const unhealthy = devices.filter((d) => d.edr !== 'pass').length;
  const totalDevices = devices.length;
  const encryptedCount = devices.filter((d) => d.encryption === 'pass').length;
  const edrCount = devices.filter((d) => d.edr === 'pass').length;
  const patchCount = devices.filter((d) => d.patch === 'pass').length;
  const encryptedPct = totalDevices ? Math.round((encryptedCount / totalDevices) * 100) : 0;
  const edrPct = totalDevices ? Math.round((edrCount / totalDevices) * 100) : 0;
  const patchPct = totalDevices ? Math.round((patchCount / totalDevices) * 100) : 0;

  const deviceHealth = [
    { id: 'encryption', label: 'Disk encryption', value: encryptedPct },
    { id: 'edr', label: 'EDR agent healthy', value: edrPct },
    { id: 'patch', label: 'Patch level current', value: patchPct }
  ];


  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <EntityWorkspace<Device>
      title="Devices"
      subtitle="Endpoint fleet health — encryption, EDR telemetry, patch currency and the risk each device contributes to its owner's identity."
      eyebrow={
      <Badge tone="warning" dot>
          {unhealthy} endpoints with degraded telemetry
        </Badge>
      }
      meta={
      <>
          <MetaStat
          label="Managed"
          value={String(totalDevices)}
          icon={<Laptop className="h-3.5 w-3.5" aria-hidden />} />
        
          <MetaStat label="Encryption" value={`${encryptedPct}%`} />
          <MetaStat label="Patch currency" value={`${patchPct}%`} />
        </>
      }
      metrics={
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricTile label="Managed endpoints" value={totalDevices} index={0} />
          <MetricTile
          label="EDR issues"
          value={unhealthy}
          tone="critical"
          caption="agent unhealthy or degraded"
          index={1} />
        
          <MetricTile
          label="Patch drift"
          value={9}
          tone="warning"
          caption=">14 days behind"
          index={2} />
        
          <MetricTile
          label="Encrypted"
          value={encryptedPct}
          suffix="%"
          tone="success"
          caption="full-disk encryption"
          index={3} />
        
        </section>
      }
      aside={
      <SectionCard title="Fleet health" description="Control coverage across the fleet">
          <div className="space-y-4">
            {deviceHealth.map((metric) =>
          <ProgressBar
            key={metric.id}
            label={metric.label}
            value={metric.value}
            tone={
            metric.value >= 95 ? 'success' : metric.value >= 85 ? 'primary' : 'warning'
            }
            showValue />

          )}
          </div>
        </SectionCard>
      }
      columns={columns}
      rows={devices}
      getRowId={(d) => d.id}
      filters={filters}
      pageSize={7}
      ariaLabel="Device inventory"
      exportName="sentinel-devices"
      searchPlaceholder="Search devices, owners, platforms..."
      bulkActions={(selected, clear) =>
      <Button variant="outline" size="sm" onClick={clear}>
          Force compliance check ({selected.length})
        </Button>
      }
      detail={{
        title: (d) => d.id,
        subtitle: (d) => `${d.name} · ${d.os} · ${d.owner}`,
        eyebrow: (d) =>
        <div className="flex flex-wrap items-center gap-2">
            <RiskBadge level={d.riskLevel} />
            <Badge tone="neutral">Last seen {formatRelative(d.lastSeen)}</Badge>
          </div>,

        actions: () => <Button variant="primary">Remediate device</Button>,
        render: (d) =>
        <div className="space-y-6">
            <div className="grid grid-cols-3 gap-3">
              {[
            { label: 'Encryption', state: d.encryption },
            { label: 'EDR agent', state: d.edr },
            { label: 'Patch level', state: d.patch }].
            map((item) =>
            <div
              key={item.label}
              className="rounded-lg border border-border bg-surface-2/50 p-3.5">
              
                  <p className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                    {item.label}
                  </p>
                  <div className="mt-2">
                    <CheckPill state={item.state} />
                  </div>
                </div>
            )}
            </div>
            <RelationChain
            items={[
            { label: 'Device', value: `${d.id} · ${d.os}` },
            { label: 'Owner', value: d.owner },
            {
              label: 'Telemetry',
              value: d.edr === 'pass' ? 'EDR reporting normally' : 'EDR agent degraded',
              tone: d.edr === 'pass' ? 'neutral' : 'critical'
            },
            {
              label: 'Control',
              value: 'CTL-INT-04 · Endpoint encryption and EDR coverage',
              tone: 'warning'
            },
            {
              label: 'Risk',
              value: `${d.riskLevel.toUpperCase()} device risk`,
              tone:
              d.riskLevel === 'critical' || d.riskLevel === 'high' ?
              'critical' :
              'neutral'
            }]
            } />
          
          </div>

      }} />);


}