import React from 'react';
import { Boxes } from 'lucide-react';
import { EntityWorkspace } from '../../components/org/EntityWorkspace';
import { MetricTile } from '../../components/common/MetricCard';
import { Badge, RiskBadge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { CheckPill } from '../../components/common/StatusPills';
import { RelationChain } from '../../components/cyber/InvestigationChain';
import { MetaStat } from '../../components/layout/PageHeader';
import { type Column, type TableFilter } from '../../components/ui/DataTable';
import { getApplications, getPersonalData } from '../../services/api';
import { useApiResource } from '../../hooks/useApiResource';
import { AsyncSection } from '../../components/common/AsyncSection';
import type { Application } from '../../types/domain';

import type { BadgeTone } from '../../components/ui/Badge';

const criticalityTone: Record<string, BadgeTone> = {
  Critical: 'danger',
  High: 'warning',
  Moderate: 'info',
  Low: 'neutral'
};

const columns: Column<Application>[] = [
{
  id: 'name',
  header: 'Application',
  accessor: (a) => a.name,
  width: 210,
  sticky: true,
  hideable: false,
  cell: (a) =>
  <div className="min-w-0">
        <p className="truncate font-medium">{a.name}</p>
        <p className="truncate font-mono text-2xs text-muted-foreground">{a.hostedIn}</p>
      </div>

},
{ id: 'owner', header: 'Owner', accessor: (a) => a.owner, width: 170 },
{
  id: 'criticality',
  header: 'Criticality',
  accessor: (a) => a.criticality,
  width: 118,
  cell: (a) => <Badge tone={criticalityTone[a.criticality]}>{a.criticality}</Badge>
},
{
  id: 'dataClass',
  header: 'Data classification',
  accessor: (a) => a.dataClass,
  width: 168,
  cell: (a) =>
  <Badge
    tone={
    a.dataClass === 'Sensitive Personal' || a.dataClass === 'Financial' ?
    'warning' :
    'neutral'
    }>
    
        {a.dataClass}
      </Badge>

},
{
  id: 'accessRisk',
  header: 'Access risk',
  accessor: (a) => a.accessRisk,
  width: 118,
  cell: (a) => <RiskBadge level={a.accessRisk} withDot={false} />
},
{
  id: 'compliance',
  header: 'Compliance',
  accessor: (a) => a.compliance,
  width: 110,
  cell: (a) => <CheckPill state={a.compliance} />
},
{
  id: 'users',
  header: 'Users',
  accessor: (a) => a.users,
  width: 88,
  align: 'right',
  cell: (a) => <span className="font-mono text-[13px]">{a.users}</span>
}];


const buildFilters = (rows: Application[]): TableFilter<Application>[] => [
{
  id: 'criticality',
  label: 'Criticality',
  options: ['Critical', 'High', 'Moderate', 'Low'].map((c) => ({ value: c, label: c })),
  predicate: (row, value) => row.criticality === value
},
{
  id: 'dataClass',
  label: 'Data class',
  options: Array.from(new Set(rows.map((a) => a.dataClass))).map((d) => ({
    value: d,
    label: d
  })),
  predicate: (row, value) => row.dataClass === value
},
{
  id: 'risk',
  label: 'Access risk',
  options: [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' }],

  predicate: (row, value) => row.accessRisk === value
}];


export function Applications() {
  const state = useApiResource(
    () =>
      Promise.all([getApplications(), getPersonalData()]).then(([apps, personal]) => ({
        applications: apps.data,
        personalDataAssets: personal.data
      })),
    []
  );
  const applications = state.data?.applications ?? [];
  const personalDataAssets = state.data?.personalDataAssets ?? [];
  const filters = React.useMemo(() => buildFilters(applications), [applications]);
  const critical = applications.filter((a) => a.criticality === 'Critical').length;
  const handlingPersonalData = new Set(personalDataAssets.map((p) => p.application)).size;
  const highAccessRisk = applications.filter((a) => a.accessRisk === 'critical' || a.accessRisk === 'high').length;


  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <EntityWorkspace<Application>
      title="Applications"
      subtitle="Business applications resolved to their owner, data classification, cloud footprint and the personal data they process."
      eyebrow={
      <Badge tone="primary" dot>
          {critical} business-critical applications
        </Badge>
      }
      meta={
      <>
          <MetaStat
          label="Applications"
          value={String(applications.length)}
          icon={<Boxes className="h-3.5 w-3.5" aria-hidden />} />
        
          <MetaStat label="Handling personal data" value={String(handlingPersonalData)} />
          <MetaStat label="High access risk" value={String(highAccessRisk)} />
        </>
      }
      metrics={
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricTile label="Applications" value={applications.length} index={0} />
          <MetricTile
          label="Business critical"
          value={critical}
          tone="warning"
          caption="tier-1 dependency"
          index={1} />
        
          <MetricTile
          label="Sensitive data"
          value={
          applications.filter(
            (a) => a.dataClass === 'Sensitive Personal' || a.dataClass === 'Financial'
          ).length
          }
          tone="critical"
          caption="regulated classifications"
          index={2} />
        
          <MetricTile
          label="Compliant"
          value={applications.filter((a) => a.compliance === 'pass').length}
          tone="success"
          caption="controls satisfied"
          index={3} />
        
        </section>
      }
      columns={columns}
      rows={applications}
      getRowId={(a) => a.id}
      filters={filters}
      ariaLabel="Application inventory"
      exportName="sentinel-applications"
      searchPlaceholder="Search applications, owners, data classes..."
      bulkActions={(selected, clear) =>
      <Button variant="outline" size="sm" onClick={clear}>
          Request review ({selected.length})
        </Button>
      }
      detail={{
        title: (a) => a.name,
        subtitle: (a) => `${a.id} · ${a.owner} · ${a.users} users · ${a.hostedIn}`,
        eyebrow: (a) =>
        <div className="flex flex-wrap items-center gap-2">
            <Badge tone={criticalityTone[a.criticality]}>{a.criticality}</Badge>
            <RiskBadge level={a.accessRisk} />
            <Badge tone="neutral">{a.dataClass}</Badge>
          </div>,

        actions: () => <Button variant="primary">Open in graph</Button>,
        render: (a) => {
          const data = personalDataAssets.filter((p) => p.application === a.name);
          return (
            <div className="space-y-6">
              <div>
                <p className="mb-2 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                  Cloud assets
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {a.cloudAssets.map((asset) =>
                  <Badge key={asset} tone="info" className="font-mono">
                      {asset}
                    </Badge>
                  )}
                </div>
              </div>

              <div>
                <p className="mb-2 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                  Personal data processed
                </p>
                {data.length ?
                <ul className="space-y-2">
                    {data.map((item) =>
                  <li
                    key={item.id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface-2/50 px-3.5 py-2.5">
                    
                        <span className="min-w-0">
                          <span className="block truncate text-[13px]">
                            {item.dataElement}
                          </span>
                          <span className="block font-mono text-2xs text-muted-foreground">
                            {item.records.toLocaleString()} records · {item.purpose}
                          </span>
                        </span>
                        <CheckPill state={item.consent} />
                      </li>
                  )}
                  </ul> :

                <p className="text-xs text-muted-foreground">
                    No personal data recorded for this application.
                  </p>
                }
              </div>

              <RelationChain
                items={[
                { label: 'Application', value: `${a.name} · ${a.criticality}` },
                { label: 'Data classification', value: a.dataClass, tone: 'warning' },
                { label: 'Cloud footprint', value: a.cloudAssets.join(', ') },
                {
                  label: 'Access risk',
                  value: `${a.accessRisk.toUpperCase()} · ${a.users} users`,
                  tone: a.accessRisk === 'critical' ? 'critical' : 'neutral'
                },
                {
                  label: 'Compliance',
                  value: a.compliance === 'pass' ? 'Controls satisfied' : 'Control gaps open',
                  tone: a.compliance === 'pass' ? 'success' : 'critical'
                }]
                } />
              
            </div>);

        }
      }} />);


}