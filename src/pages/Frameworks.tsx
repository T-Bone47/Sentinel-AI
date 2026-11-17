import { useState } from 'react';
import { CheckCircle2, Plus, ScrollText, Sparkles, XCircle } from 'lucide-react';
import { PageHeader, MetaStat } from '../components/layout/PageHeader';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '../components/ui/Card';
import { ProgressBar } from '../components/ui/Progress';
import { SegmentedControl } from '../components/ui/Tabs';
import { SearchInput } from '../components/ui/Input';
import { Drawer } from '../components/ui/Drawer';
import { EmptyState } from '../components/ui/States';
import { ComplianceStatusBadge } from '../components/common/StatusPills';
import { StackedBarsChart } from '../components/charts/ChartPrimitives';
import { getFrameworks } from '../services/api';
import { useApiResource } from '../hooks/useApiResource';
import { AsyncSection } from '../components/common/AsyncSection';
import { formatDate } from '../utils/format';
import type { FrameworkScore } from '../types/domain';

const statusFilters = [
{ id: 'all', label: 'All' },
{ id: 'compliant', label: 'Compliant' },
{ id: 'at-risk', label: 'At risk' },
{ id: 'non-compliant', label: 'Gaps' }];


export function Frameworks() {
  const state = useApiResource(() => getFrameworks(), []);
  const frameworks = state.data ?? [];
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const [active, setActive] = useState<FrameworkScore | null>(null);

  const visible = frameworks.filter((f) => {
    const matchesQuery =
    !query ||
    `${f.name} ${f.authority}`.toLowerCase().includes(query.toLowerCase());
    const matchesStatus = status === 'all' || f.status === status;
    return matchesQuery && matchesStatus;
  });


  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Frameworks"
        subtitle="Adopt regulations once, then let Sentinel map controls, reuse evidence and monitor drift across every framework."
        meta={
        <>
            <MetaStat
            label="Adopted"
            value={String(frameworks.length)}
            icon={<ScrollText className="h-3.5 w-3.5" aria-hidden />} />
          
            <MetaStat label="Shared controls" value="612 reusable" />
            <MetaStat label="Average coverage" value="79%" />
          </>
        }
        actions={
        <>
            <Button variant="ai" iconLeft={<Sparkles className="h-4 w-4" />}>
              Map controls
            </Button>
            <Button variant="primary" iconLeft={<Plus className="h-4 w-4" />}>
              Adopt framework
            </Button>
          </>
        } />
      

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SearchInput
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search frameworks or authorities..."
          aria-label="Search frameworks"
          wrapperClassName="w-full sm:w-80" />
        
        <SegmentedControl
          items={statusFilters}
          value={status}
          onChange={setStatus}
          ariaLabel="Filter by status" />
        
      </div>

      {visible.length === 0 ?
      <Card className="p-0">
          <EmptyState
          icon={<ScrollText className="h-6 w-6" />}
          title="No frameworks match"
          description="Nothing in your adopted set matches this search. Adopt a new framework or clear the filters."
          action={
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setQuery('');
              setStatus('all');
            }}>
            
                Clear filters
              </Button>
          } />
        
        </Card> :

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((framework, i) =>
        <Card
          key={framework.id}
          interactive
          tabIndex={0}
          role="button"
          onClick={() => setActive(framework)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') setActive(framework);
          }}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, delay: i * 0.04, ease: [0.22, 1, 0.36, 1] }}
          className="flex flex-col">
          
              <CardHeader>
                <div className="min-w-0">
                  <CardTitle as="h3">{framework.name}</CardTitle>
                </div>
                <ComplianceStatusBadge status={framework.status} />
              </CardHeader>
              <CardContent className="flex-1">
                <ProgressBar
              value={framework.coverage}
              tone={
              framework.coverage >= 90 ?
              'success' :
              framework.coverage >= 70 ?
              'warning' :
              'danger'
              }
              label="Control coverage"
              showValue />
            
                <div className="mt-4 grid grid-cols-2 gap-2">
                  <div className="rounded-lg border border-border bg-surface-2/50 px-3 py-2">
                    <p className="flex items-center gap-1.5 text-2xs text-muted-foreground">
                      <CheckCircle2 className="h-3 w-3 text-success" aria-hidden />
                      Passing
                    </p>
                    <p className="mt-0.5 font-mono text-sm font-semibold">
                      {framework.passed}
                    </p>
                  </div>
                  <div className="rounded-lg border border-border bg-surface-2/50 px-3 py-2">
                    <p className="flex items-center gap-1.5 text-2xs text-muted-foreground">
                      <XCircle className="h-3 w-3 text-destructive" aria-hidden />
                      Failing
                    </p>
                    <p className="mt-0.5 font-mono text-sm font-semibold">
                      {framework.failed}
                    </p>
                  </div>
                </div>
              </CardContent>
              <CardFooter>
                <span className="text-2xs text-muted-foreground">
                  {framework.authority}
                </span>
                <Badge tone="neutral">Audit {formatDate(framework.nextAudit, 'MMM d')}</Badge>
              </CardFooter>
            </Card>
        )}
        </div>
      }

      <Drawer
        open={Boolean(active)}
        onClose={() => setActive(null)}
        width="xl"
        title={active?.name ?? ''}
        subtitle={active ? `${active.authority} · owned by ${active.owner}` : undefined}
        eyebrow={active ? <ComplianceStatusBadge status={active.status} /> : undefined}
        footer={
        <>
            <Button variant="ghost" onClick={() => setActive(null)}>
              Close
            </Button>
            <Button variant="outline">Export evidence</Button>
            <Button variant="ai" iconLeft={<Sparkles className="h-4 w-4" />}>
              Close gaps with Sentinel
            </Button>
          </>
        }>
        
        {active &&
        <div className="space-y-6">
            <ProgressBar
            value={active.coverage}
            tone={active.coverage >= 90 ? 'success' : 'warning'}
            label="Control coverage"
            showValue />
          
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
            ['Controls', String(active.passed + active.failed)],
            ['Passing', String(active.passed)],
            ['Failing', String(active.failed)],
            ['Next audit', formatDate(active.nextAudit, 'MMM d, yyyy')]].
            map(([label, value]) =>
            <div key={label} className="rounded-lg border border-border bg-surface-2/50 p-3">
                  <dt className="text-2xs uppercase tracking-wider text-muted-foreground">
                    {label}
                  </dt>
                  <dd className="mt-1 font-mono text-[13px] font-medium">{value}</dd>
                </div>
            )}
            </dl>
            <div>
              <h3 className="mb-3 text-[13px] font-semibold">Control domains</h3>
            {active.controlDomains && active.controlDomains.length > 0 ? (
              <StackedBarsChart
                label="Passing and failing controls by domain"
                data={active.controlDomains}
                xKey="domain"
                layout="vertical"
                height={260}
                series={[
                  { key: 'passing', name: 'Passing', color: 'var(--success)' },
                  { key: 'failing', name: 'Failing', color: 'var(--risk-critical)' }
                ]}
              />
            ) : (
              <p className="text-sm text-muted-foreground mt-4">
                No domain data available for this framework.
              </p>
            )}
            </div>
          </div>
        }
      </Drawer>
    </div>);

}