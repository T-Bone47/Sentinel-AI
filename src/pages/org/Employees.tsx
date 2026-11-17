import React from 'react';
import { Users } from 'lucide-react';
import { EntityWorkspace } from '../../components/org/EntityWorkspace';
import { MetricTile } from '../../components/common/MetricCard';
import { Badge, RiskBadge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { CheckPill } from '../../components/common/StatusPills';
import { RelationChain } from '../../components/cyber/InvestigationChain';
import { MetaStat } from '../../components/layout/PageHeader';
import { type Column, type TableFilter } from '../../components/ui/DataTable';
import { getEmployees } from '../../services/api';
import { useApiResource } from '../../hooks/useApiResource';
import { AsyncSection } from '../../components/common/AsyncSection';
import { formatDate } from '../../utils/format';
import type { Employee } from '../../types/domain';

const columns: Column<Employee>[] = [
{
  id: 'name',
  header: 'Employee',
  accessor: (e) => e.name,
  width: 220,
  sticky: true,
  hideable: false,
  cell: (e) =>
  <div className="min-w-0">
        <p className="flex items-center gap-2 truncate font-medium">
          {e.name}
          {e.privileged && <Badge tone="primary">Privileged</Badge>}
        </p>
        <p className="truncate font-mono text-2xs text-muted-foreground">{e.email}</p>
      </div>

},
{ id: 'department', header: 'Department', accessor: (e) => e.department, width: 160 },
{ id: 'role', header: 'Role', accessor: (e) => e.role, width: 190 },
{
  id: 'mfa',
  header: 'MFA',
  accessor: (e) => e.mfa,
  width: 80,
  cell: (e) => <CheckPill state={e.mfa} />
},
{
  id: 'device',
  header: 'Device',
  accessor: (e) => e.device,
  width: 140,
  cell: (e) => <span className="font-mono text-2xs">{e.device}</span>
},
{
  id: 'accessRisk',
  header: 'Access risk',
  accessor: (e) => e.accessRisk,
  width: 120,
  cell: (e) => <RiskBadge level={e.accessRisk} withDot={false} />
},
{
  id: 'compliance',
  header: 'Compliance',
  accessor: (e) => e.compliance,
  width: 110,
  cell: (e) => <CheckPill state={e.compliance} />
},
{
  id: 'joined',
  header: 'Joined',
  accessor: (e) => e.joinedAt,
  width: 120,
  cell: (e) =>
  <span className="font-mono text-2xs text-muted-foreground">
        {formatDate(e.joinedAt, 'MMM yyyy')}
      </span>

}];


const buildFilters = (rows: Employee[]): TableFilter<Employee>[] => [
{
  id: 'department',
  label: 'Department',
  options: Array.from(new Set(rows.map((e) => e.department))).map((d) => ({
    value: d,
    label: d
  })),
  predicate: (row, value) => row.department === value
},
{
  id: 'mfa',
  label: 'MFA',
  options: [
  { value: 'pass', label: 'Enrolled' },
  { value: 'warn', label: 'Partial' },
  { value: 'fail', label: 'Missing' }],

  predicate: (row, value) => row.mfa === value
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
},
{
  id: 'privileged',
  label: 'Privilege',
  options: [
  { value: 'yes', label: 'Privileged' },
  { value: 'no', label: 'Standard' }],

  predicate: (row, value) => value === 'yes' ? row.privileged : !row.privileged
}];


export function Employees() {
  const state = useApiResource(() => getEmployees(), []);
  const employees = state.data?.data ?? [];
  const filters = React.useMemo(() => buildFilters(employees), [employees]);
  const privileged = employees.filter((e) => e.privileged).length;
  const mfaGaps = employees.filter((e) => e.mfa !== 'pass').length;


  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <EntityWorkspace<Employee>
      title="Employees"
      subtitle="Every person in the organization, resolved to their identity, device, application access and resulting risk."
      eyebrow={
      <Badge tone={mfaGaps ? 'warning' : 'success'} dot>
          {mfaGaps} employees with MFA gaps
        </Badge>
      }
      meta={
      <>
          <MetaStat
          label="Headcount"
          value={String(employees.length)}
          icon={<Users className="h-3.5 w-3.5" aria-hidden />} />
        
          <MetaStat label="Privileged" value={String(privileged)} />
          <MetaStat label="Security training" value="96%" />
        </>
      }
      metrics={
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricTile label="Employees" value={employees.length} index={0} />
          <MetricTile
          label="Privileged"
          value={privileged}
          tone="warning"
          caption="elevated entitlements"
          index={1} />
        
          <MetricTile
          label="MFA gaps"
          value={mfaGaps}
          tone="critical"
          caption="requires enrollment"
          index={2} />
        
          <MetricTile
          label="Compliant"
          value={employees.filter((e) => e.compliance === 'pass').length}
          tone="success"
          caption="policy attestations current"
          index={3} />
        
        </section>
      }
      columns={columns}
      rows={employees}
      getRowId={(e) => e.id}
      filters={filters}
      ariaLabel="Employee directory"
      exportName="sentinel-employees"
      searchPlaceholder="Search people, departments, roles..."
      bulkActions={(selected, clear) =>
      <Button variant="outline" size="sm" onClick={clear}>
          Request MFA enrollment ({selected.length})
        </Button>
      }
      detail={{
        title: (e) => e.name,
        subtitle: (e) => `${e.role} · ${e.department} · ${e.email}`,
        eyebrow: (e) =>
        <div className="flex flex-wrap items-center gap-2">
            <RiskBadge level={e.accessRisk} />
            {e.privileged && <Badge tone="primary">Privileged access</Badge>}
            <Badge tone="neutral">{e.id}</Badge>
          </div>,

        actions: () => <Button variant="primary">Review access</Button>,
        render: (e) =>
        <div className="space-y-6">
            <dl className="grid grid-cols-2 gap-4">
              <Detail label="MFA">
                <CheckPill state={e.mfa} label={e.mfa === 'pass' ? 'Enrolled' : 'Gap'} />
              </Detail>
              <Detail label="Compliance">
                <CheckPill
                state={e.compliance}
                label={e.compliance === 'pass' ? 'Compliant' : 'Attention'} />
              
              </Detail>
              <Detail label="Device">
                <span className="font-mono text-[13px]">{e.device}</span>
              </Detail>
              <Detail label="Joined">
                <span className="text-[13px]">{formatDate(e.joinedAt)}</span>
              </Detail>
            </dl>

            <div>
              <p className="mb-2 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                Application access
              </p>
              <div className="flex flex-wrap gap-1.5">
                {e.apps.map((app) =>
              <Badge key={app} tone="neutral">
                    {app}
                  </Badge>
              )}
              </div>
            </div>

            <div>
              <p className="mb-3 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                Access chain
              </p>
              <RelationChain
              items={[
              { label: 'Employee', value: `${e.name} · ${e.department}` },
              {
                label: 'Identity',
                value: e.email,
                tone: e.mfa === 'pass' ? 'neutral' : 'critical'
              },
              { label: 'Device', value: e.device },
              { label: 'Applications', value: e.apps.join(', ') },
              {
                label: 'Access',
                value: e.privileged ? 'Privileged entitlements' : 'Standard entitlements',
                tone: e.privileged ? 'warning' : 'neutral'
              },
              {
                label: 'Risk',
                value: `${e.accessRisk.toUpperCase()} access risk`,
                tone:
                e.accessRisk === 'critical' || e.accessRisk === 'high' ?
                'critical' :
                'neutral'
              }]
              } />
            
            </div>
          </div>

      }} />);


}

function Detail({ label, children }: {label: string;children: React.ReactNode;}) {
  return (
    <div>
      <dt className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1.5">{children}</dd>
    </div>);

}