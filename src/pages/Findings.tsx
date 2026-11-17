import React, { useState } from 'react';
import { Gauge, Sparkles, Zap } from 'lucide-react';
import { PageHeader, MetaStat } from '../components/layout/PageHeader';
import { DataTable, type Column, type TableFilter } from '../components/ui/DataTable';
import { Button } from '../components/ui/Button';
import { Badge, RiskBadge } from '../components/ui/Badge';
import { RemediationDrawer } from '../components/risk/RemediationDrawer';
import { FindingStatusBadge } from '../components/common/StatusPills';
import { getFindings, getTopRemediations } from '../services/api';
import { useApiResource } from '../hooks/useApiResource';
import { AsyncSection } from '../components/common/AsyncSection';
import { getRisk } from '../services/api';
import { formatRelative } from '../utils/format';
import type { Finding } from '../types/domain';

const columns: Column<Finding>[] = [
{
  id: 'id',
  header: 'ID',
  accessor: (f) => f.id,
  width: 104,
  sticky: true,
  hideable: false,
  cell: (f) => <span className="font-mono text-xs text-muted-foreground">{f.id}</span>
},
{
  id: 'title',
  header: 'Finding',
  accessor: (f) => f.title,
  width: 340,
  hideable: false,
  cell: (f) =>
  <div className="min-w-0">
        <p className="truncate font-medium">{f.title}</p>
        <p className="mt-0.5 truncate font-mono text-2xs text-muted-foreground">{f.asset}</p>
      </div>

},
{
  id: 'severity',
  header: 'Severity',
  accessor: (f) => f.severity,
  width: 112,
  cell: (f) => <RiskBadge level={f.severity} withDot={false} />
},
{
  id: 'control',
  header: 'Control',
  accessor: (f) => f.control,
  width: 140,
  cell: (f) => <span className="font-mono text-2xs text-primary">{f.control}</span>
},
{
  id: 'source',
  header: 'Source',
  accessor: (f) => f.source,
  width: 140,
  cell: (f) =>
  <Badge tone={f.source === 'Sentinel AI' ? 'ai' : 'neutral'}>{f.source}</Badge>

},
{ id: 'owner', header: 'Owner', accessor: (f) => f.owner, width: 168 },
{
  id: 'status',
  header: 'Status',
  accessor: (f) => f.status,
  width: 128,
  cell: (f) => <FindingStatusBadge status={f.status} />
},
{
  id: 'detected',
  header: 'Detected',
  accessor: (f) => f.detectedAt,
  width: 128,
  cell: (f) =>
  <span className="font-mono text-2xs text-muted-foreground">
        {formatRelative(f.detectedAt)}
      </span>

}];


const buildFilters = (rows: Finding[]): TableFilter<Finding>[] => [
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
  { value: 'in-progress', label: 'In progress' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'suppressed', label: 'Suppressed' }],

  predicate: (row, value) => row.status === value
},
{
  id: 'source',
  label: 'Source',
  options: Array.from(new Set(rows.map((f) => f.source))).map((s) => ({
    value: s,
    label: s
  })),
  predicate: (row, value) => row.source === value
}];


export function Findings() {
  const state = useApiResource(
    () => Promise.all([getFindings(), getTopRemediations(4)]).then(([findingsRes, topRemediationsRes]) => ({
      findings: findingsRes.data ?? [],
      topRemediations: topRemediationsRes
    })),
    []
  );

  const findings = state.data?.findings ?? [];
  const topRemediations = state.data?.topRemediations ?? [];
  const filters = React.useMemo(() => buildFilters(findings), [findings]);
  const [activeFinding, setActiveFinding] = useState<Finding | null>(null);
  const open = findings.filter((f) => f.status === 'open').length;

  const openRemediation = (finding: Finding) => {
    setActiveFinding(finding);
  };

  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow={
        <Badge tone="warning" dot>
            {open} findings awaiting triage
          </Badge>
        }
        title="Findings"
        subtitle="Raw detections from cloud scans, identity sync, device agents, vendor reviews and Sentinel — each mapped to the control it breaks."
        meta={
        <>
            <MetaStat
            label="Total"
            value={String(findings.length)}
            icon={<Gauge className="h-3.5 w-3.5" aria-hidden />} />
          
            <MetaStat
            label="Auto-remediable"
            value="11"
            icon={<Zap className="h-3.5 w-3.5" aria-hidden />} />
          
            <MetaStat label="Mean time to detect" value="4 minutes" />
          </>
        }
        actions={
        <Button variant="ai" iconLeft={<Sparkles className="h-4 w-4" />}>
            Auto-remediate eligible
          </Button>
        } />
      
      {topRemediations.length > 0 && (
         <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="col-span-full">
               <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  Top Findings Requiring Remediation
               </h3>
               <p className="text-xs text-muted-foreground">Prioritized by AI based on risk severity and impact.</p>
            </div>
            {topRemediations.map((rem: any, idx: number) => (
               <div key={rem.finding_id} className="rounded-xl border border-border bg-card p-4 hover:border-primary/50 transition-colors cursor-pointer" onClick={() => setActiveFinding(findings.find(f => f.id === rem.finding_id) || null)}>
                  <div className="flex items-start justify-between gap-2 mb-2">
                     <RiskBadge level={rem.severity} />
                     <Badge tone="neutral">{rem.finding_id}</Badge>
                  </div>
                  <p className="text-sm font-medium line-clamp-2 mb-1">{rem.description}</p>
                  <p className="text-xs text-muted-foreground line-clamp-1">{rem.control_context?.control_name}</p>
               </div>
            ))}
         </div>
      )}

      <DataTable<Finding>
        ariaLabel="Findings"
        columns={columns}
        rows={findings}
        getRowId={(f) => f.id}
        filters={filters}
        pageSize={10}
        exportName="sentinel-findings"
        searchPlaceholder="Search findings, assets, controls..."
        onRowClick={openRemediation}
        bulkActions={(selected, clear) =>
        <>
            <Button variant="outline" size="sm" onClick={clear}>
              Assign ({selected.length})
            </Button>
            <Button
            variant="ai"
            size="sm"
            iconLeft={<Sparkles className="h-3.5 w-3.5" />}
            onClick={clear}>
            
              Remediate
            </Button>
          </>
        } />
      

      <RemediationDrawer finding={activeFinding} onClose={() => setActiveFinding(null)} />
    </div>);


}
