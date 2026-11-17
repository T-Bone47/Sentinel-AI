import { useState } from 'react';
import {
  CalendarClock,
  Download,
  FileBarChart,
  Loader2,
  Plus,
  Sparkles } from
'lucide-react';
import { PageHeader, MetaStat } from '../components/layout/PageHeader';
import { SectionCard } from '../components/common/SectionCard';
import { Button } from '../components/ui/Button';
import { Badge, type BadgeTone } from '../components/ui/Badge';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { Field, Input } from '../components/ui/Input';
import { Select, Switch } from '../components/ui/Controls';
import { Tabs } from '../components/ui/Tabs';
import { EmptyState } from '../components/ui/States';
import { getReports } from '../services/api';
import { useApiResource } from '../hooks/useApiResource';
import { AsyncSection } from '../components/common/AsyncSection';
import { formatDate } from '../utils/format';
import type { ReportItem } from '../types/domain';

const statusCopy: Record<ReportItem['status'], {label: string;tone: BadgeTone;}> = {
  ready: { label: 'Ready', tone: 'success' },
  generating: { label: 'Generating', tone: 'ai' },
  scheduled: { label: 'Scheduled', tone: 'primary' },
  failed: { label: 'Failed', tone: 'danger' }
};

const tabs = [
{ id: 'all', label: 'All reports' },
{ id: 'Board', label: 'Board' },
{ id: 'Executive', label: 'Executive' },
{ id: 'Regulatory', label: 'Regulatory' },
{ id: 'Operational', label: 'Operational' }];


export function Reports() {
  const state = useApiResource(() => getReports(), []);
  const reports = state.data?.data ?? [];
  const [tab, setTab] = useState('all');
  const [composerOpen, setComposerOpen] = useState(false);
  const [scheduled, setScheduled] = useState(true);
  const [busy, setBusy] = useState(false);

  const visible = reports.filter((r) => tab === 'all' || r.type === tab);

  const create = () => {
    setBusy(true);
    window.setTimeout(() => {
      setBusy(false);
      setComposerOpen(false);
    }, 1300);
  };


  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        subtitle="Board, regulator and operational reporting assembled from live control evidence — no manual collation."
        meta={
        <>
            <MetaStat
            label="Available"
            value={String(reports.length)}
            icon={<FileBarChart className="h-3.5 w-3.5" aria-hidden />} />
          
            <MetaStat
            label="Scheduled"
            value="4 recurring"
            icon={<CalendarClock className="h-3.5 w-3.5" aria-hidden />} />
          
            <MetaStat label="Average build time" value="2m 40s" />
          </>
        }
        actions={
        <>
            <Button variant="outline" iconLeft={<Download className="h-4 w-4" />}>
              Download all
            </Button>
            <Button
            variant="primary"
            iconLeft={<Plus className="h-4 w-4" />}
            onClick={() => setComposerOpen(true)}>
            
              New report
            </Button>
          </>
        } />
      

      <SectionCard
        tone="ai"
        title="Sentinel narrative reporting"
        description="Let Sentinel write the executive narrative, then review each claim against its cited evidence before publishing."
        actions={
        <Button variant="ai" size="sm" iconLeft={<Sparkles className="h-3.5 w-3.5" />}>
            Generate narrative
          </Button>
        }>
        
        <div className="grid gap-3 sm:grid-cols-3">
          {[
          ['Evidence cited', '418 artifacts'],
          ['Frameworks covered', '8 regulations'],
          ['Human review required', '4 claims']].
          map(([label, value]) =>
          <div key={label} className="rounded-lg border border-ai-border/50 bg-surface-1/60 p-3.5">
              <p className="text-2xs uppercase tracking-wider text-muted-foreground">
                {label}
              </p>
              <p className="mt-1 text-sm font-semibold">{value}</p>
            </div>
          )}
        </div>
      </SectionCard>

      <Tabs items={tabs} value={tab} onChange={setTab} ariaLabel="Report categories" />

      {visible.length === 0 ?
      <Card className="p-0">
          <EmptyState
          icon={<FileBarChart className="h-6 w-6" />}
          title="No reports in this category"
          description="Create a report or switch category to see what has already been generated."
          action={
          <Button variant="primary" size="sm" onClick={() => setComposerOpen(true)}>
                New report
              </Button>
          } />
        
        </Card> :

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((report, i) => {
          const status = statusCopy[report.status];
          return (
            <Card
              key={report.id}
              interactive
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.28, delay: i * 0.04, ease: [0.22, 1, 0.36, 1] }}
              className="flex flex-col">
              
                <CardHeader>
                  <div className="min-w-0">
                    <CardTitle as="h3" className="line-clamp-2">
                      {report.name}
                    </CardTitle>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {report.framework} · {report.period}
                    </p>
                  </div>
                  <Badge tone={status.tone} dot={report.status !== 'generating'}>
                    {report.status === 'generating' &&
                  <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
                  }
                    {status.label}
                  </Badge>
                </CardHeader>
                <CardContent className="flex-1">
                  <dl className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <dt className="text-2xs uppercase tracking-wider text-muted-foreground">
                        Type
                      </dt>
                      <dd className="mt-0.5 font-medium">{report.type}</dd>
                    </div>
                    <div>
                      <dt className="text-2xs uppercase tracking-wider text-muted-foreground">
                        Owner
                      </dt>
                      <dd className="mt-0.5 truncate font-medium">{report.owner}</dd>
                    </div>
                  </dl>
                  {report.aiGenerated &&
                <Badge tone="ai" className="mt-3">
                      <Sparkles className="h-3 w-3" aria-hidden />
                      Sentinel drafted
                    </Badge>
                }
                </CardContent>
                <CardFooter>
                  <span className="text-2xs text-muted-foreground">
                    {report.status === 'scheduled' ? 'Runs' : 'Generated'}{' '}
                    {formatDate(report.generatedAt, 'MMM d, yyyy')}
                  </span>
                  <Button
                  variant="ghost"
                  size="xs"
                  disabled={report.status !== 'ready'}
                  iconLeft={<Download className="h-3.5 w-3.5" />}>
                  
                    Download
                  </Button>
                </CardFooter>
              </Card>);

        })}
        </div>
      }

      <Modal
        open={composerOpen}
        onClose={() => setComposerOpen(false)}
        title="Create a report"
        description="Choose the audience and scope. Evidence is pulled live at build time."
        footer={
        <>
            <Button variant="ghost" onClick={() => setComposerOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" loading={busy} onClick={create}>
              {busy ? 'Building...' : 'Create report'}
            </Button>
          </>
        }>
        
        <div className="space-y-5">
          <Field label="Report name" required>
            {({ id }) => <Input id={id} placeholder="Q3 2026 Board AI Risk Brief" />}
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Audience">
              {({ id }) =>
              <Select
                id={id}
                options={[
                { value: 'Board', label: 'Board' },
                { value: 'Executive', label: 'Executive' },
                { value: 'Regulatory', label: 'Regulator' },
                { value: 'Operational', label: 'Operational' }]
                } />

              }
            </Field>
            <Field label="Framework scope">
              {({ id }) =>
              <Select
                id={id}
                options={[
                { value: 'all', label: 'Cross-framework' },
                { value: 'eu-ai-act', label: 'EU AI Act' },
                { value: 'iso-42001', label: 'ISO 42001' },
                { value: 'soc2', label: 'SOC 2 Type II' }]
                } />

              }
            </Field>
          </div>
          <div className="rounded-lg border border-border bg-surface-2/50 p-3.5">
            <Switch
              checked={scheduled}
              onChange={setScheduled}
              label="Run on a schedule"
              description="Rebuild monthly on the first business day and notify subscribers." />
            
          </div>
        </div>
      </Modal>
    </div>);

}