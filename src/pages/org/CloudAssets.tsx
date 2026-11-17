import React from 'react';
import { Cloud, ShieldAlert } from 'lucide-react';
import { EntityWorkspace } from '../../components/org/EntityWorkspace';
import { MetricTile } from '../../components/common/MetricCard';
import { SectionCard } from '../../components/common/SectionCard';
import { Badge, RiskBadge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { CheckPill } from '../../components/common/StatusPills';
import { RelationChain } from '../../components/cyber/InvestigationChain';
import { DonutChart } from '../../components/charts/ChartPrimitives';
import { MetaStat } from '../../components/layout/PageHeader';
import { type Column, type TableFilter } from '../../components/ui/DataTable';
import { getCloudAssets } from '../../services/api';
import { useApiResource } from '../../hooks/useApiResource';
import { AsyncSection } from '../../components/common/AsyncSection';
import type { CloudAsset } from '../../types/domain';

const providerTone: Record<string, 'warning' | 'info' | 'primary'> = { AWS: 'warning', Azure: 'info', GCP: 'primary' };

const columns: Column<CloudAsset>[] = [
{
  id: 'resource',
  header: 'Resource',
  accessor: (c) => c.resource,
  width: 244,
  sticky: true,
  hideable: false,
  cell: (c) =>
  <div className="min-w-0">
        <p className="truncate font-mono text-xs font-medium">{c.resource}</p>
        <p className="truncate text-2xs text-muted-foreground">
          {c.service} · {c.region}
        </p>
      </div>

},
{
  id: 'provider',
  header: 'Provider',
  accessor: (c) => c.provider,
  width: 108,
  cell: (c) => <Badge tone={providerTone[c.provider]}>{c.provider}</Badge>
},
{
  id: 'criticality',
  header: 'Criticality',
  accessor: (c) => c.criticality,
  width: 112,
  cell: (c) =>
  <Badge tone={c.criticality === 'Critical' ? 'danger' : 'neutral'}>
        {c.criticality}
      </Badge>

},
{
  id: 'encryption',
  header: 'Encryption',
  accessor: (c) => c.encryption,
  width: 108,
  cell: (c) => <CheckPill state={c.encryption} />
},
{
  id: 'publicAccess',
  header: 'Public access',
  accessor: (c) => c.publicAccess,
  width: 124,
  cell: (c) => <CheckPill state={c.publicAccess} />
},
{
  id: 'logging',
  header: 'Logging',
  accessor: (c) => c.logging,
  width: 100,
  cell: (c) => <CheckPill state={c.logging} />
},
{
  id: 'risk',
  header: 'Risk',
  accessor: (c) => c.riskLevel,
  width: 112,
  cell: (c) => <RiskBadge level={c.riskLevel} withDot={false} />
},
{ id: 'owner', header: 'Owner', accessor: (c) => c.owner, width: 168 }];


const buildFilters = (rows: CloudAsset[]): TableFilter<CloudAsset>[] => [
{
  id: 'provider',
  label: 'Provider',
  options: [
  { value: 'AWS', label: 'AWS' },
  { value: 'Azure', label: 'Azure' },
  { value: 'GCP', label: 'GCP' }],

  predicate: (row, value) => row.provider === value
},
{
  id: 'exposure',
  label: 'Exposure',
  options: [
  { value: 'public', label: 'Publicly reachable' },
  { value: 'private', label: 'Private only' }],

  predicate: (row, value) =>
  value === 'public' ? row.publicAccess !== 'pass' : row.publicAccess === 'pass'
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
}];


export function CloudAssets() {
  const state = useApiResource(() => getCloudAssets(), []);
  const cloudAssets = state.data?.data ?? [];
  const filters = React.useMemo(() => buildFilters(cloudAssets), [cloudAssets]);
  const exposed = cloudAssets.filter((c) => c.publicAccess !== 'pass').length;
  const byProvider = ['AWS', 'Azure', 'GCP'].map((provider, i) => ({
    name: provider,
    value: cloudAssets.filter((c) => c.provider === provider).length,
    color: `var(--chart-${i + 1})`
  }));


  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <EntityWorkspace<CloudAsset>
      title="Cloud Assets"
      subtitle="Multi-cloud posture across AWS, Azure and GCP — encryption, public exposure and logging evaluated on every resource."
      eyebrow={
      <Badge tone="danger" dot>
          {exposed} resources with public exposure
        </Badge>
      }
      meta={
      <>
          <MetaStat
          label="Resources"
          value="186"
          icon={<Cloud className="h-3.5 w-3.5" aria-hidden />} />
        
          <MetaStat
          label="Misconfigurations"
          value="7"
          icon={<ShieldAlert className="h-3.5 w-3.5" aria-hidden />} />
        
          <MetaStat label="Regions" value="6" />
        </>
      }
      metrics={
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricTile label="Cloud resources" value={186} index={0} />
          <MetricTile
          label="Public exposure"
          value={exposed}
          tone="critical"
          caption="immediate action required"
          index={1} />
        
          <MetricTile
          label="Unencrypted"
          value={cloudAssets.filter((c) => c.encryption !== 'pass').length}
          tone="warning"
          caption="encryption at rest missing"
          index={2} />
        
          <MetricTile
          label="Logging gaps"
          value={cloudAssets.filter((c) => c.logging !== 'pass').length}
          tone="warning"
          caption="audit trail incomplete"
          index={3} />
        
        </section>
      }
      aside={
      <SectionCard title="Distribution" description="Inventory by cloud provider">
          <DonutChart
          label="Cloud assets by provider"
          data={byProvider}
          height={188}
          centerValue="186"
          centerLabel="resources" />
        
          <ul className="mt-3 space-y-1.5">
            {byProvider.map((provider) =>
          <li key={provider.name} className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{provider.name}</span>
                <span className="font-mono font-medium">{provider.value}</span>
              </li>
          )}
          </ul>
        </SectionCard>
      }
      columns={columns}
      rows={cloudAssets}
      getRowId={(c) => c.id}
      filters={filters}
      pageSize={7}
      ariaLabel="Cloud asset inventory"
      exportName="sentinel-cloud-assets"
      searchPlaceholder="Search resources, services, regions..."
      bulkActions={(selected, clear) =>
      <Button variant="danger" size="sm" onClick={clear}>
          Block public access ({selected.length})
        </Button>
      }
      detail={{
        title: (c) => c.resource,
        subtitle: (c) => `${c.provider} · ${c.service} · ${c.region} · ${c.owner}`,
        eyebrow: (c) =>
        <div className="flex flex-wrap items-center gap-2">
            <RiskBadge level={c.riskLevel} />
            <Badge tone={providerTone[c.provider]}>{c.provider}</Badge>
            <Badge tone={c.criticality === 'Critical' ? 'danger' : 'neutral'}>
              {c.criticality}
            </Badge>
          </div>,

        actions: () => <Button variant="primary">Remediate</Button>,
        render: (c) =>
        <div className="space-y-6">
            <div className="grid grid-cols-3 gap-3">
              {[
            { label: 'Encryption', state: c.encryption },
            { label: 'Public access', state: c.publicAccess },
            { label: 'Logging', state: c.logging }].
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
            { label: 'Resource', value: `${c.resource} · ${c.region}` },
            {
              label: 'Exposure',
              value:
              c.publicAccess === 'pass' ?
              'No public access path' :
              'Publicly reachable',
              tone: c.publicAccess === 'pass' ? 'success' : 'critical'
            },
            {
              label: 'Control',
              value: 'CTL-A.8.12 · Data leakage prevention on public cloud storage',
              tone: 'warning'
            },
            {
              label: 'Evidence',
              value: 'EV-8829 · Configuration snapshot from AWS Config',
              tone: 'success'
            },
            {
              label: 'Risk',
              value: `${c.riskLevel.toUpperCase()} cloud risk · owner ${c.owner}`,
              tone: c.riskLevel === 'critical' ? 'critical' : 'neutral'
            }]
            } />
          
          </div>

      }} />);


}