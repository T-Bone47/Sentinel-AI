import React from 'react';
import { Handshake } from 'lucide-react';
import { EntityWorkspace } from '../../components/org/EntityWorkspace';
import { MetricTile } from '../../components/common/MetricCard';
import { Badge, RiskBadge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  CheckPill,
  RiskScore,
  VendorStatusBadge } from
'../../components/common/StatusPills';
import { RelationChain } from '../../components/cyber/InvestigationChain';
import { MetaStat } from '../../components/layout/PageHeader';
import { type Column, type TableFilter } from '../../components/ui/DataTable';
import { getVendors } from '../../services/api';
import { useApiResource } from '../../hooks/useApiResource';
import { AsyncSection } from '../../components/common/AsyncSection';
import { formatDate } from '../../utils/format';
import type { Vendor } from '../../types/domain';

const columns: Column<Vendor>[] = [
{
  id: 'name',
  header: 'Vendor',
  accessor: (v) => v.name,
  width: 200,
  sticky: true,
  hideable: false,
  cell: (v) =>
  <div className="min-w-0">
        <p className="truncate font-medium">{v.name}</p>
        <p className="truncate text-2xs text-muted-foreground">{v.category}</p>
      </div>

},
{
  id: 'risk',
  header: 'Risk',
  accessor: (v) => v.riskScore,
  width: 120,
  cell: (v) =>
  <span className="flex items-center gap-2">
        <RiskScore score={v.riskScore} />
        <RiskBadge level={v.riskLevel} withDot={false} />
      </span>

},
{
  id: 'compliance',
  header: 'Compliance',
  accessor: (v) => v.compliance,
  width: 110,
  cell: (v) => <CheckPill state={v.compliance} />
},
{
  id: 'certification',
  header: 'Certification',
  accessor: (v) => v.certification,
  width: 150,
  cell: (v) =>
  <Badge tone={v.certification === 'None' ? 'danger' : 'neutral'}>
        {v.certification}
      </Badge>

},
{
  id: 'status',
  header: 'Status',
  accessor: (v) => v.certificationStatus,
  width: 128,
  cell: (v) => <VendorStatusBadge status={v.certificationStatus} />
},
{
  id: 'dataShared',
  header: 'Data shared',
  accessor: (v) => v.dataShared.join(', '),
  width: 250,
  cell: (v) =>
  <span className="flex flex-wrap gap-1">
        {v.dataShared.slice(0, 2).map((item) =>
    <Badge key={item} tone="neutral">
            {item}
          </Badge>
    )}
        {v.dataShared.length > 2 &&
    <Badge tone="neutral">+{v.dataShared.length - 2}</Badge>
    }
      </span>

},
{ id: 'owner', header: 'Owner', accessor: (v) => v.owner, width: 156 },
{
  id: 'expiry',
  header: 'Expiry',
  accessor: (v) => v.expiry,
  width: 124,
  cell: (v) =>
  <span className="font-mono text-2xs text-muted-foreground">
        {formatDate(v.expiry, 'MMM d, yyyy')}
      </span>

}];


const buildFilters = (rows: Vendor[]): TableFilter<Vendor>[] => [
{
  id: 'status',
  label: 'Certification',
  options: [
  { value: 'compliant', label: 'Compliant' },
  { value: 'expiring', label: 'Expiring' },
  { value: 'expired', label: 'Expired' },
  { value: 'high-risk', label: 'High risk' }],

  predicate: (row, value) => row.certificationStatus === value
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
  id: 'category',
  label: 'Category',
  options: Array.from(new Set(rows.map((v) => v.category))).map((c) => ({
    value: c,
    label: c
  })),
  predicate: (row, value) => row.category === value
}];


export function Vendors() {
  const state = useApiResource(() => getVendors(), []);
  const vendors = state.data?.data ?? [];
  const filters = React.useMemo(() => buildFilters(vendors), [vendors]);
  const atRisk = vendors.filter((v) => v.certificationStatus !== 'compliant').length;


  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <EntityWorkspace<Vendor>
      title="Third-Party Vendors"
      subtitle="Third-party risk across the supply chain — what data each vendor receives, whether their assurance is current, and the exposure that creates."
      eyebrow={
      <Badge tone="danger" dot>
          {atRisk} vendors require assurance action
        </Badge>
      }
      meta={
      <>
          <MetaStat
          label="Vendors"
          value="38"
          icon={<Handshake className="h-3.5 w-3.5" aria-hidden />} />
        
          <MetaStat label="Tier 1" value="9" />
          <MetaStat label="Highest risk" value="91 · Vireo Screening" />
        </>
      }
      metrics={
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricTile label="Active vendors" value={38} index={0} />
          <MetricTile
          label="Expired assurance"
          value={vendors.filter((v) => v.certificationStatus === 'expired').length}
          tone="critical"
          caption="reports out of date"
          index={1} />
        
          <MetricTile
          label="High risk"
          value={vendors.filter((v) => v.certificationStatus === 'high-risk').length}
          tone="critical"
          caption="uncertified processors"
          index={2} />
        
          <MetricTile
          label="Compliant"
          value={vendors.filter((v) => v.certificationStatus === 'compliant').length}
          tone="success"
          caption="current certification"
          index={3} />
        
        </section>
      }
      columns={columns}
      rows={vendors}
      getRowId={(v) => v.id}
      filters={filters}
      ariaLabel="Vendor register"
      exportName="sentinel-vendors"
      searchPlaceholder="Search vendors, categories, owners..."
      bulkActions={(selected, clear) =>
      <Button variant="outline" size="sm" onClick={clear}>
          Request assurance ({selected.length})
        </Button>
      }
      detail={{
        title: (v) => v.name,
        subtitle: (v) => `${v.category} · ${v.id} · owner ${v.owner}`,
        eyebrow: (v) =>
        <div className="flex flex-wrap items-center gap-2">
            <RiskBadge level={v.riskLevel} />
            <VendorStatusBadge status={v.certificationStatus} />
            <Badge tone="neutral">Risk {v.riskScore}</Badge>
          </div>,

        actions: () => <Button variant="primary">Start review</Button>,
        render: (v) =>
        <div className="space-y-6">
            <div className="rounded-xl border border-border bg-surface-2/50 p-4">
              <div className="flex items-end justify-between gap-4">
                <div>
                  <p className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                    Vendor risk score
                  </p>
                  <p className="mt-1 font-mono text-4xl font-semibold leading-none">
                    {v.riskScore}
                    <span className="text-base font-normal text-muted-foreground"> / 100</span>
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xs uppercase tracking-label text-muted-foreground">
                    Assurance expires
                  </p>
                  <p className="mt-1 font-mono text-[13px]">{formatDate(v.expiry)}</p>
                </div>
              </div>
            </div>

            <div>
              <p className="mb-2 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                Data shared
              </p>
              <div className="flex flex-wrap gap-1.5">
                {v.dataShared.map((item) =>
              <Badge key={item} tone="warning">
                    {item}
                  </Badge>
              )}
              </div>
            </div>

            <RelationChain
            items={[
            { label: 'Vendor', value: `${v.name} · ${v.category}` },
            { label: 'Data shared', value: v.dataShared.join(', '), tone: 'warning' },
            {
              label: 'Control',
              value: 'CTL-CC9.2 · Third-party risk assessment before onboarding',
              tone: 'warning'
            },
            {
              label: 'Findings',
              value:
              v.certificationStatus === 'compliant' ?
              'No open vendor findings' :
              'Assurance report missing or expired',
              tone: v.certificationStatus === 'compliant' ? 'success' : 'critical'
            },
            {
              label: 'Evidence',
              value: `Due diligence questionnaire · ${v.certification}`,
              tone: v.certification === 'None' ? 'critical' : 'success'
            },
            {
              label: 'Risk',
              value: `${v.riskLevel.toUpperCase()} third-party risk · score ${v.riskScore}`,
              tone:
              v.riskLevel === 'critical' || v.riskLevel === 'high' ?
              'critical' :
              'neutral'
            }]
            } />
          
          </div>

      }} />);


}