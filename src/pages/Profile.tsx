import { useState } from 'react';
import { Bell, Mail, MapPin, Shield, Smartphone } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { SectionCard } from '../components/common/SectionCard';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { Field, Input, Textarea } from '../components/ui/Input';
import { Switch } from '../components/ui/Controls';
import { formatRelative, initialsOf } from '../utils/format';
import { getAuditLogs } from '../services/api';
import { useApiResource } from '../hooks/useApiResource';
import { cn } from '../utils/cn';

export function Profile() {
  // Real audit-log rows stand in for the activity feed; the seeded feed was
  // the last place this screen could have shown invented history.
  const activityState = useApiResource(() => getAuditLogs({ page_size: 8 }), []);
  const activityFeed = (activityState.data?.data ?? []).map((event) => ({
    id: event.id,
    label: event.action,
    detail: `${event.target} · ${event.source}`,
    time: event.timestamp,
    actor: event.actor,
    action: event.action,
    target: event.target,
    ai: event.source === 'Sentinel AI'
  }));
  const [bio, setBio] = useState(
    'Chief Information Security Officer at Northwind Financial. Accountable for AI governance, model risk and regulatory readiness across EMEA.'
  );
  const [prefs, setPrefs] = useState({
    criticalEmail: true,
    weeklyDigest: true,
    aiSuggestions: true,
    mobilePush: false
  });

  const set = (key: keyof typeof prefs) => (value: boolean) =>
  setPrefs((p) => ({ ...p, [key]: value }));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Profile"
        subtitle="Your identity, access and notification preferences across the Sentinel workspace."
        actions={
        <>
            <Button variant="ghost">Discard</Button>
            <Button variant="primary">Save profile</Button>
          </>
        } />
      

      <Card
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex flex-col gap-5 p-6 sm:flex-row sm:items-center">
        
        <span
          className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-primary/12 text-xl font-semibold text-primary"
          aria-hidden>
          
          {initialsOf('Dana Okafor')}
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold tracking-tight">Dana Okafor</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Chief Information Security Officer
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Mail className="h-3.5 w-3.5" aria-hidden />
              dana.okafor@northwind.io
            </span>
            <span className="flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5" aria-hidden />
              London, UK
            </span>
            <span className="flex items-center gap-1.5">
              <Shield className="h-3.5 w-3.5" aria-hidden />
              Owner
            </span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone="success" dot>
            MFA enabled
          </Badge>
          <Badge tone="primary">SSO · Okta</Badge>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Personal details" description="Visible to your workspace team.">
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="First name" required>
                {({ id }) => <Input id={id} defaultValue="Dana" />}
              </Field>
              <Field label="Last name" required>
                {({ id }) => <Input id={id} defaultValue="Okafor" />}
              </Field>
            </div>
            <Field label="Job title">
              {({ id }) =>
              <Input id={id} defaultValue="Chief Information Security Officer" />
              }
            </Field>
            <Field
              label="Bio"
              hint="Shown on approvals and attestation records.">
              
              {({ id }) =>
              <Textarea
                id={id}
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                maxLength={240}
                showCounter />

              }
            </Field>
          </div>
        </SectionCard>

        <div className="space-y-4">
          <SectionCard
            title="Notifications"
            description="Choose what reaches you and where."
            delay={0.05}>
            
            <div className="space-y-5">
              <Switch
                checked={prefs.criticalEmail}
                onChange={set('criticalEmail')}
                label="Critical risk alerts"
                description="Email the moment a risk is escalated to critical." />
              
              <Switch
                checked={prefs.weeklyDigest}
                onChange={set('weeklyDigest')}
                label="Weekly posture digest"
                description="Monday morning summary of posture, incidents and audits." />
              
              <Switch
                checked={prefs.aiSuggestions}
                onChange={set('aiSuggestions')}
                label="Sentinel recommendations"
                description="Notify me when Sentinel surfaces a high-impact recommendation." />
              
              <Switch
                checked={prefs.mobilePush}
                onChange={set('mobilePush')}
                label="Mobile push"
                description="Requires the Sentinel mobile app." />
              
            </div>
          </SectionCard>

          <SectionCard title="Sessions" description="Devices signed in to your account." delay={0.1}>
            <ul className="space-y-2.5">
              {[
              ['MacBook Pro · London', 'Current session', true],
              ['iPhone 16 Pro · London', '2 hours ago', false],
              ['Chrome · Frankfurt', '3 days ago', false]].
              map(([device, when, current]) =>
              <li
                key={String(device)}
                className="flex items-center gap-3 rounded-lg border border-border bg-surface-2/50 px-3.5 py-3">
                
                  <Smartphone className="h-4 w-4 text-muted-foreground" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[13px] font-medium">{device}</p>
                    <p className="text-2xs text-muted-foreground">{when}</p>
                  </div>
                  {current ?
                <Badge tone="success" dot>
                      Active
                    </Badge> :

                <Button variant="ghost" size="xs">
                      Revoke
                    </Button>
                }
                </li>
              )}
            </ul>
          </SectionCard>
        </div>
      </div>

      <SectionCard
        title="Your recent activity"
        description="Actions attributed to your account"
        delay={0.05}
        actions={
        <Badge tone="neutral">
            <Bell className="h-3 w-3" aria-hidden />
            Audit trail
          </Badge>
        }>
        
        <ol className="space-y-3">
          {activityFeed.map((event) =>
          <li
            key={event.id}
            className="flex items-start gap-3 rounded-lg border border-border bg-surface-2/50 px-3.5 py-3">
            
              <span
              className={cn(
                'mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full',
                event.ai ? 'bg-ai' : 'bg-primary'
              )}
              aria-hidden />
            
              <div className="min-w-0">
                <p className="text-[13px]">
                  <span className="font-medium">{event.actor}</span>{' '}
                  <span className="text-muted-foreground">{event.action}</span>{' '}
                  <span className="font-medium">{event.target}</span>
                </p>
                <p className="mt-0.5 text-2xs text-muted-foreground">
                  {formatRelative(event.time)}
                </p>
              </div>
            </li>
          )}
        </ol>
      </SectionCard>
    </div>);

}