import { useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useAuth } from '../contexts/AuthContext';
import { useApiResource } from '../hooks/useApiResource';
import {
  ApiError,
  getDetectionAlert,
  getDetectionAlerts,
  getDetectionRules,
  getEventSources,
  startDetectionRun,
  type DetectionAlert,
  type DetectionRunReport
} from '../services/api';

const RETROSPECTIVE =
'Retrospective batch analysis: alerts are raised when a detection run is started over stored events, not as events arrive.';

const cell = 'border-b border-border px-2 py-1.5 text-left align-top';

function Section({ title, children }: {title: string;children: React.ReactNode;}) {
  return (
    <section aria-label={title} className="rounded-xl border border-border bg-surface-1 p-4">
      <h2 className="mb-3 text-sm font-semibold">{title}</h2>
      {children}
    </section>);

}

function Loading<T>({ state, children }: {state: {status: string;error: Error | null;data: T | null;};children: (data: T) => React.ReactNode;}) {
  if (state.status === 'loading') return <p className="text-sm text-muted-foreground" role="status">Loading…</p>;
  if (state.status === 'error' || state.data === null) {
    return <p className="text-sm text-destructive" role="alert">{state.error?.message ?? 'Could not load this data.'}</p>;
  }
  return <>{children(state.data)}</>;
}

const short = (id: string) => `${id.slice(0, 12)}…`;

export function Detections() {
  const { can } = useAuth();
  const canSeeAlerts = can('detections');
  const canSeeSources = can('security-events');
  const [refresh, setRefresh] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [source, setSource] = useState('');
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<DetectionRunReport | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const rules = useApiResource(() => getDetectionRules(), []);
  const alerts = useApiResource(() => canSeeAlerts ? getDetectionAlerts() : Promise.resolve([]), [canSeeAlerts, refresh]);
  const sources = useApiResource(() => canSeeSources ? getEventSources() : Promise.resolve([]), [canSeeSources, refresh]);
  const detail = useApiResource(
    () => selected ? getDetectionAlert(selected) : Promise.resolve(null as DetectionAlert | null),
    [selected]
  );

  const run = async () => {
    setRunning(true);
    setRunError(null);
    setRunResult(null);
    try {
      setRunResult(await startDetectionRun(source));
      setRefresh((n) => n + 1);
    } catch (error) {
      setRunError(error instanceof ApiError && error.status === 403 ?
      'Your role cannot start detection runs. Ask an administrator or security analyst.' :
      error instanceof Error ? error.message : 'The run failed.');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader title="Detections" subtitle={RETROSPECTIVE} meta={<Badge tone="neutral">Retrospective · synthetic fixtures only</Badge>} />

      <Section title="Rules">
        <Loading state={rules}>
          {(list) =>
          <table className="w-full text-sm">
              <caption className="sr-only">Detection rules</caption>
              <thead className="text-xs text-muted-foreground">
                <tr>
                  <th className={cell} scope="col">Rule</th>
                  <th className={cell} scope="col">Fires on</th>
                  <th className={cell} scope="col">Severity</th>
                  <th className={cell} scope="col">Confidence</th>
                  <th className={cell} scope="col">ATT&amp;CK</th>
                  <th className={cell} scope="col">Known limits</th>
                </tr>
              </thead>
              <tbody>
                {list.map((rule) =>
              <tr key={rule.id}>
                    <td className={cell}><span className="font-mono text-xs">{rule.id} v{rule.version}</span><br />{rule.title}</td>
                    <td className={cell}>{rule.logic}</td>
                    <td className={cell}><Badge tone="primary">{rule.severity}</Badge></td>
                    <td className={cell}>{rule.confidence}</td>
                    <td className={`${cell} font-mono text-xs`}>{rule.attack.join(', ') || 'unmapped'}</td>
                    <td className={`${cell} text-xs text-muted-foreground`}>
                      {rule.contract?.limitations?.length ?
                  <ul className="list-disc pl-4">{rule.contract.limitations.map((l) => <li key={l}>{l}</li>)}</ul> :
                  'Contract not available in this deployment.'}
                    </td>
                  </tr>
              )}
              </tbody>
            </table>
          }
        </Loading>
      </Section>

      {!canSeeAlerts ?
      <Section title="Alerts">
          <p className="text-sm text-muted-foreground">
            Your role can see the rule catalogue but not alerts: alerts cite individual people&apos;s activity.
          </p>
        </Section> :

      <>
          <Section title="Run detections">
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex flex-col gap-1 text-xs font-medium">
                Source
                <select
                className="h-9 rounded-lg border border-input bg-surface-1 px-2 text-sm"
                value={source}
                onChange={(event) => setSource(event.target.value)}>
                  <option value="">Choose a source…</option>
                  {(sources.data ?? []).map((id) => <option key={id} value={id}>{id}</option>)}
                </select>
              </label>
              <Button onClick={run} disabled={!source || running} loading={running}>Run all rules</Button>
            </div>
            {runError && <p role="alert" className="mt-3 text-sm text-destructive">{runError}</p>}
            {runResult &&
          <p role="status" className="mt-3 text-sm">
                Considered {runResult.events_considered} events: {runResult.alerts_created} new alerts,{' '}
                {runResult.alerts_existing} already stored, {runResult.alerts_no_longer_raised} no longer raised by these rules.
              </p>
          }
          </Section>

          <Section title="Alerts">
            <Loading state={alerts}>
              {(list) => list.length === 0 ?
            <p className="text-sm text-muted-foreground">No alerts stored. Ingest events and start a run.</p> :

            <table className="w-full text-sm">
                  <caption className="sr-only">Stored alerts, newest first</caption>
                  <thead className="text-xs text-muted-foreground">
                    <tr>
                      <th className={cell} scope="col">Trigger time (UTC)</th>
                      <th className={cell} scope="col">Rule</th>
                      <th className={cell} scope="col">Severity / confidence</th>
                      <th className={cell} scope="col">Summary</th>
                    </tr>
                  </thead>
                  <tbody>
                    {list.map((alert) =>
                <tr key={alert.alert_id} className={selected === alert.alert_id ? 'bg-primary/10' : undefined}>
                        <td className={`${cell} font-mono text-xs`}>{alert.trigger_at}</td>
                        <td className={cell}>{alert.rule_id}</td>
                        <td className={cell}>{alert.severity} / {alert.confidence}</td>
                        <td className={cell}>
                          <button type="button" className="text-left underline-offset-2 hover:underline"
                    aria-pressed={selected === alert.alert_id} onClick={() => setSelected(alert.alert_id)}>
                            {alert.summary}
                          </button>
                        </td>
                      </tr>
                )}
                  </tbody>
                </table>
            }
            </Loading>
          </Section>

          {selected &&
        <Section title="Evidence for the selected alert">
              <Loading state={detail}>
                {(alert) => alert &&
            <>
                    <p className="mb-2 text-xs text-muted-foreground">
                      Alert <span className="font-mono">{short(alert.alert_id)}</span> · rule {alert.rule_id} v{alert.rule_version} ·
                      every event below is a stored source record; its SHA-256 lets you check it has not changed.
                    </p>
                    <table className="w-full text-sm">
                      <caption className="sr-only">Events this alert cites</caption>
                      <thead className="text-xs text-muted-foreground">
                        <tr>
                          <th className={cell} scope="col">Role</th>
                          <th className={cell} scope="col">Occurred (UTC)</th>
                          <th className={cell} scope="col">Action</th>
                          <th className={cell} scope="col">Outcome</th>
                          <th className={cell} scope="col">Actor → target</th>
                          <th className={cell} scope="col">Event / record hash</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(alert.events ?? []).map((event) =>
                  <tr key={event.event_id}>
                            <td className={cell}><Badge tone={event.role === 'trigger' ? 'primary' : 'neutral'}>{event.role}</Badge></td>
                            <td className={`${cell} font-mono text-xs`}>{event.occurred_at}</td>
                            <td className={cell}>{event.action}</td>
                            <td className={cell}>{event.outcome}</td>
                            <td className={cell}>{event.actor_id ?? '—'} → {event.target_id ?? '—'}</td>
                            <td className={`${cell} font-mono text-xs`}>{short(event.event_id)}<br />{short(event.raw_sha256)}</td>
                          </tr>
                  )}
                      </tbody>
                    </table>
                  </>
            }
              </Loading>
            </Section>
        }
        </>
      }
    </div>);

}
