import React from 'react';
import { Fingerprint, ShieldAlert } from 'lucide-react';
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
import { getIdentities } from '../../services/api';
import { useApiResource } from '../../hooks/useApiResource';
import { AsyncSection } from '../../components/common/AsyncSection';
import { formatRelative } from '../../utils/format';
import type { IamAccount } from '../../types/domain';

const columns: Column<IamAccount>[] = [
{
  id: 'principal',
  header: 'Principal',
  accessor: (a) => a.principal,
  width: 250,
  sticky: true,
  hideable: false,
  cell: (a) =>
  <div className="min-w-0">
        <p className="flex items-center gap-2 truncate font-mono text-xs">
          {a.principal}
          {a.privileged && <Badge tone="primary">PRIV</Badge>}
        </p>
        <p className="mt-0.5 truncate text-2xs text-muted-foreground">
          {a.entitlements.slice(0, 2).join(' · ')}
        </p>
      </div>

},
{
  id: 'type',
  header: 'Type',
  accessor: (a) => a.type,
  width: 118,
  cell: (a) => <Badge tone={a.type === 'Service' ? 'info' : 'neutral'}>{a.type}</Badge>
},
{ id: 'provider', header: 'Provider', accessor: (a) => a.provider, width: 128 },
{
  id: 'mfa',
  header: 'MFA',
  accessor: (a) => a.mfa,
  width: 80,
  cell: (a) => <CheckPill state={a.mfa} />
},
{
  id: 'dormant',
  header: 'Activity',
  accessor: (a) => a.lastActive,
  width: 140,
  cell: (a) =>
  <span
    className={
    a.dormant ?
    'font-mono text-2xs text-warning' :
    'font-mono text-2xs text-muted-foreground'
    }>
    
        {formatRelative(a.lastActive)}
        {a.dormant && ' · dormant'}
      </span>

},
{
  id: 'violations',
  header: 'Violations',
  accessor: (a) => a.violations,
  width: 104,
  align: 'right',
  cell: (a) =>
  <span
    className={
    a.violations > 0 ?
    'font-mono text-sm font-semibold text-risk-critical' :
    'font-mono text-sm text-muted-foreground'
    }>
    
        {a.violations}
      </span>

},
{
  id: 'risk',
  header: 'Risk',
  accessor: (a) => a.riskLevel,
  width: 112,
  cell: (a) => <RiskBadge level={a.riskLevel} withDot={false} />
}];


const buildFilters = (rows: IamAccount[]): TableFilter<IamAccount>[] => [
{
  id: 'type',
  label: 'Type',
  options: [
  { value: 'Human', label: 'Human' },
  { value: 'Service', label: 'Service' },
  { value: 'Contractor', label: 'Contractor' }],

  predicate: (row, value) => row.type === value
},
{
  id: 'privileged',
  label: 'Privilege',
  options: [
  { value: 'yes', label: 'Privileged' },
  { value: 'no', label: 'Standard' }],

  predicate: (row, value) => value === 'yes' ? row.privileged : !row.privileged
},
{
  id: 'mfa',
  label: 'MFA',
  options: [
  { value: 'pass', label: 'Enrolled' },
  { value: 'fail', label: 'Missing' }],

  predicate: (row, value) => row.mfa === value
},
{
  id: 'dormant',
  label: 'Dormancy',
  options: [
  { value: 'yes', label: 'Dormant' },
  { value: 'no', label: 'Active' }],

  predicate: (row, value) => value === 'yes' ? row.dormant : !row.dormant
}];

const computeIamMetrics = (accounts: IamAccount[]) => {
  const total = accounts.length;

  const mfaEnrolled = accounts.filter(
    (account) => account.mfa === 'pass'
  ).length;

  const privileged = accounts.filter(
    (account) => account.privileged
  ).length;

  const dormant = accounts.filter(
    (account) => account.dormant
  ).length;

  const violations = accounts.reduce(
    (total, account) => total + account.violations,
    0
  );

  const mfaCoverage = total
    ? Math.round((mfaEnrolled / total) * 100)
    : 0;

  return [
    {
      id: 'identities',
      label: 'Identities',
      value: total,
      caption: 'managed identities',
    },
    {
      id: 'privileged',
      label: 'Privileged',
      value: privileged,
      caption: 'identities with elevated access',
    },
    {
      id: 'mfa',
      label: 'MFA coverage',
      value: mfaCoverage,
      suffix: '%',
      caption: 'identities with MFA enrolled',
    },
    {
      id: 'dormant',
      label: 'Dormant',
      value: dormant,
      caption: 'inactive identities',
    },
    {
      id: 'violations',
      label: 'Violations',
      value: violations,
      caption: 'entitlement violations',
    },
  ];
};
export function Identity() {
  const state = useApiResource(() => getIdentities(), []);
  const iamAccounts = state.data?.data ?? [];

const filters = React.useMemo(
  () => buildFilters(iamAccounts),
  [iamAccounts]
);

const iamMetrics = computeIamMetrics(iamAccounts);

const mfaCoverage =
  iamMetrics.find((metric) => metric.id === 'mfa')?.value ?? 0;


  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <EntityWorkspace<IamAccount>
      title="Identity & Access"
      subtitle="Every human, service and contractor identity — with privilege, second factor, dormancy and entitlement violations resolved continuously."
      eyebrow={
      <Badge tone="danger" dot>
          6 access violations across privileged identities
        </Badge>
      }
      meta={
      <>
          <MetaStat
          label="Identities"
          value={String(iamAccounts.length)}
          icon={<Fingerprint className="h-3.5 w-3.5" aria-hidden />} />
        
          <MetaStat
          label="Privileged"
          value={String(
            iamAccounts.filter((account) => account.privileged).length
          )}
          icon={<ShieldAlert className="h-3.5 w-3.5" aria-hidden />} />
        
          <MetaStat label="MFA coverage" value={`${mfaCoverage}%`} />
        </>
      }
      metrics={
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {iamMetrics.map((metric, i) =>
        <MetricTile
          key={metric.id}
          label={metric.label}
          value={metric.value}
          suffix={metric.suffix}
          caption={metric.caption}
          tone={
          metric.id === 'violations' ?
          'critical' :
          metric.id === 'dormant' ?
          'warning' :
          'default'
          }
          index={i} />

        )}
        </section>
      }
      aside={
      <SectionCard
        title="Access hygiene"
        description="Least-privilege and authentication posture">
        
          <div className="space-y-4">
            <ProgressBar label="MFA coverage" value={mfaCoverage} tone="warning" showValue />
            <ProgressBar label="Least privilege" value={81} tone="warning" showValue />
            <ProgressBar label="JIT access adoption" value={62} tone="primary" showValue />
            <ProgressBar label="Quarterly review complete" value={100} tone="success" showValue />
          </div>
          <div className="mt-5 rounded-lg border border-border bg-surface-2/50 p-3.5">
            <p className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
              Highest-risk identity
            </p>
            <p className="mt-1.5 font-mono text-[13px]">jonas.meyer@northwind.io</p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              AdministratorAccess without a second factor, on an endpoint whose EDR agent has
              been silent for 62 hours.
            </p>
          </div>
        </SectionCard>
      }
      columns={columns}
      rows={iamAccounts}
      getRowId={(a) => a.id}
      filters={filters}
      pageSize={7}
      ariaLabel="Identity and access inventory"
      exportName="sentinel-identities"
      searchPlaceholder="Search identities, providers, entitlements..."
      bulkActions={(selected, clear) =>
      <Button variant="danger" size="sm" onClick={clear}>
          Revoke standing access ({selected.length})
        </Button>
      }
      detail={{
        title: (a) => a.principal,
        subtitle: (a) => `${a.type} identity · ${a.provider} · ${a.id}`,
        eyebrow: (a) =>
        <div className="flex flex-wrap items-center gap-2">
            <RiskBadge level={a.riskLevel} />
            {a.privileged && <Badge tone="primary">Privileged</Badge>}
            {a.dormant && <Badge tone="warning">Dormant</Badge>}
          </div>,

        actions: () => <Button variant="primary">Enforce policy</Button>,
        render: (a) =>
        <div className="space-y-6">
            <div>
              <p className="mb-2 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                Entitlements
              </p>
              <div className="flex flex-wrap gap-1.5">
                {a.entitlements.map((entitlement) =>
              <Badge key={entitlement} tone="neutral">
                    {entitlement}
                  </Badge>
              )}
              </div>
            </div>
            <RelationChain
            items={[
            { label: 'Identity', value: a.principal },
            {
              label: 'Authentication',
              value: a.mfa === 'pass' ? 'MFA enrolled' : 'No second factor',
              tone: a.mfa === 'pass' ? 'neutral' : 'critical'
            },
            { label: 'Provider', value: a.provider },
            {
              label: 'Activity',
              value: `Last active ${formatRelative(a.lastActive)}`,
              tone: a.dormant ? 'warning' : 'neutral'
            },
            {
              label: 'Violations',
              value: a.violations ?
              `${a.violations} entitlement violations` :
              'No violations recorded',
              tone: a.violations ? 'critical' : 'success'
            }]
            } />
          
          </div>

      }} />);


}