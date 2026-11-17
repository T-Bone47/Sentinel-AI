import { useState } from 'react';
import {
  Building2,
  KeyRound,
  Plug,
  ShieldCheck,
  Sparkles,
  Trash2,
  Users } from
'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { SectionCard } from '../components/common/SectionCard';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { Field, Input } from '../components/ui/Input';
import { Select, Switch } from '../components/ui/Controls';
import { Tabs } from '../components/ui/Tabs';
import { cn } from '../utils/cn';

const tabs = [
{ id: 'workspace', label: 'Workspace' },
{ id: 'security', label: 'Security' },
{ id: 'ai', label: 'AI governance' },
{ id: 'integrations', label: 'Integrations', count: 9 },
{ id: 'team', label: 'Team', count: 24 }];


const team = [
{ name: 'Dana Okafor', email: 'dana.okafor@northwind.io', role: 'Owner', mfa: true },
{ name: 'Maya Lindqvist', email: 'maya.l@northwind.io', role: 'Admin', mfa: true },
{ name: 'Sofia Alvarez', email: 'sofia.a@northwind.io', role: 'Risk Manager', mfa: true },
{ name: 'Rohan Bhatt', email: 'rohan.b@northwind.io', role: 'Policy Owner', mfa: false },
{ name: 'Kenji Tanaka', email: 'kenji.t@northwind.io', role: 'Analyst', mfa: true }];


const integrations = [
{ name: 'AWS Bedrock', category: 'Model provider', connected: true },
{ name: 'Azure OpenAI', category: 'Model provider', connected: true },
{ name: 'Snowflake', category: 'Data platform', connected: true },
{ name: 'Okta', category: 'Identity', connected: true },
{ name: 'Splunk', category: 'SIEM', connected: true },
{ name: 'Jira', category: 'Workflow', connected: false },
{ name: 'ServiceNow', category: 'Workflow', connected: false },
{ name: 'Slack', category: 'Notifications', connected: true },
{ name: 'Vanta', category: 'Compliance', connected: false }];


export function Settings() {
  const [tab, setTab] = useState('workspace');
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [toggles, setToggles] = useState({
    autoRemediate: true,
    aiDrafting: true,
    humanReview: true,
    anomalyAlerts: true,
    ssoOnly: true,
    ipAllowlist: false
  });

  const set = (key: keyof typeof toggles) => (value: boolean) =>
  setToggles((t) => ({ ...t, [key]: value }));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        subtitle="Configure the workspace, security posture and how Sentinel is allowed to act on your behalf."
        actions={
        <>
            <Button variant="ghost">Discard</Button>
            <Button variant="primary">Save changes</Button>
          </>
        } />
      

      <Tabs items={tabs} value={tab} onChange={setTab} ariaLabel="Settings sections" />

      {tab === 'workspace' &&
      <div className="grid gap-4 lg:grid-cols-2">
          <SectionCard
          title="Organization"
          description="Shown across reports, exports and the audit trail.">
          
            <div className="space-y-4">
              <Field label="Legal entity name" required>
                {({ id }) => <Input id={id} defaultValue="Northwind Financial Group plc" />}
              </Field>
              <Field label="Primary jurisdiction" hint="Drives default regulatory scope.">
                {({ id }) =>
              <Select
                id={id}
                defaultValue="eu"
                options={[
                { value: 'eu', label: 'European Union' },
                { value: 'uk', label: 'United Kingdom' },
                { value: 'us', label: 'United States' },
                { value: 'apac', label: 'APAC' }]
                } />

              }
              </Field>
              <Field label="Risk appetite" hint="Used to auto-classify residual risk.">
                {({ id }) =>
              <Select
                id={id}
                defaultValue="low"
                options={[
                { value: 'minimal', label: 'Minimal' },
                { value: 'low', label: 'Low' },
                { value: 'moderate', label: 'Moderate' }]
                } />

              }
              </Field>
            </div>
          </SectionCard>

          <SectionCard
          title="Danger zone"
          description="Irreversible actions affecting the whole workspace."
          delay={0.05}>
          
            <div className="rounded-lg border border-destructive/30 bg-destructive/[0.04] p-4">
              <p className="text-[13px] font-medium">Delete workspace</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                Permanently removes all risks, evidence and audit history for Northwind
                Financial. Retention obligations may prevent this action.
              </p>
              <Button
              variant="danger"
              size="sm"
              className="mt-4"
              onClick={() => setConfirmOpen(true)}
              iconLeft={<Trash2 className="h-3.5 w-3.5" />}>
              
                Delete workspace
              </Button>
            </div>
          </SectionCard>
        </div>
      }

      {tab === 'security' &&
      <div className="grid gap-4 lg:grid-cols-2">
          <SectionCard
          title="Authentication"
          description="How people access this workspace.">
          
            <div className="space-y-5">
              <Switch
              checked={toggles.ssoOnly}
              onChange={set('ssoOnly')}
              label="Require SSO"
              description="Disable password sign-in. Enforced through Okta SAML." />
            
              <Switch
              checked={toggles.ipAllowlist}
              onChange={set('ipAllowlist')}
              label="IP allowlist"
              description="Restrict console access to corporate egress ranges." />
            
              <div className="rounded-lg border border-border bg-surface-2/50 p-3.5">
                <div className="flex items-center gap-2.5">
                  <KeyRound className="h-4 w-4 text-primary" aria-hidden />
                  <div className="flex-1">
                    <p className="text-[13px] font-medium">Session lifetime</p>
                    <p className="text-2xs text-muted-foreground">
                      Sessions expire after 8 hours of inactivity
                    </p>
                  </div>
                  <Badge tone="success" dot>
                    Compliant
                  </Badge>
                </div>
              </div>
            </div>
          </SectionCard>

          <SectionCard
          title="Data protection"
          description="Where workspace data is stored and processed."
          delay={0.05}>
          
            <ul className="space-y-2.5">
              {[
            ['Data residency', 'EU (Frankfurt)'],
            ['Encryption at rest', 'AES-256, customer-managed keys'],
            ['Encryption in transit', 'TLS 1.3'],
            ['Audit retention', '7 years, WORM']].
            map(([label, value]) =>
            <li
              key={label}
              className="flex items-center justify-between gap-4 rounded-lg border border-border bg-surface-2/50 px-3.5 py-3">
              
                  <span className="text-[13px] text-muted-foreground">{label}</span>
                  <span className="text-[13px] font-medium">{value}</span>
                </li>
            )}
            </ul>
          </SectionCard>
        </div>
      }

      {tab === 'ai' &&
      <div className="grid gap-4 lg:grid-cols-2">
          <SectionCard
          tone="ai"
          title="Sentinel autonomy"
          description="Define exactly what Sentinel may do without a human in the loop.">
          
            <div className="space-y-5">
              <Switch
              checked={toggles.aiDrafting}
              onChange={set('aiDrafting')}
              label="Allow policy and report drafting"
              description="Sentinel may produce drafts. Publication always requires approval." />
            
              <Switch
              checked={toggles.autoRemediate}
              onChange={set('autoRemediate')}
              label="Auto-remediate low-severity findings"
              description="Applies pre-approved playbooks to low risks and logs every action." />
            
              <Switch
              checked={toggles.humanReview}
              onChange={set('humanReview')}
              label="Mandatory human review for high-risk systems"
              description="Required by EU AI Act Article 14. Cannot be disabled while the EU AI Act is adopted."
              disabled />
            
              <Switch
              checked={toggles.anomalyAlerts}
              onChange={set('anomalyAlerts')}
              label="Real-time anomaly alerting"
              description="Notify the on-call responder when behavior deviates from baseline." />
            
            </div>
          </SectionCard>

          <SectionCard
          title="Model configuration"
          description="Models powering Sentinel in this workspace."
          delay={0.05}>
          
            <div className="space-y-4">
              <Field label="Reasoning model" hint="Used for risk analysis and predictions.">
                {({ id }) =>
              <Select
                id={id}
                defaultValue="reasoner"
                options={[
                { value: 'reasoner', label: 'Sentinel Reasoner v4 (recommended)' },
                { value: 'reasoner-lite', label: 'Sentinel Reasoner Lite' },
                { value: 'byo', label: 'Bring your own (Azure OpenAI)' }]
                } />

              }
              </Field>
              <Field
              label="Minimum confidence to surface an insight"
              hint="Insights below this threshold are logged but not shown.">
              
                {({ id }) =>
              <Select
                id={id}
                defaultValue="70"
                options={[
                { value: '50', label: '50%' },
                { value: '70', label: '70%' },
                { value: '85', label: '85%' }]
                } />

              }
              </Field>
              <div className="flex items-start gap-2.5 rounded-lg border border-ai-border/60 bg-ai-surface/40 p-3.5">
                <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-ai" aria-hidden />
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Workspace data is never used to train foundation models. All inference runs
                  in your EU tenancy with zero retention.
                </p>
              </div>
            </div>
          </SectionCard>
        </div>
      }

      {tab === 'integrations' &&
      <SectionCard
        title="Connected systems"
        description="Evidence and telemetry sources feeding continuous assurance."
        actions={
        <Button variant="outline" size="sm" iconLeft={<Plug className="h-3.5 w-3.5" />}>
              Browse catalog
            </Button>
        }>
        
          <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {integrations.map((integration) =>
          <li
            key={integration.name}
            className={cn(
              'flex items-center gap-3 rounded-lg border p-3.5 transition-colors duration-180',
              integration.connected ?
              'border-border bg-surface-2/50' :
              'border-dashed border-border bg-transparent'
            )}>
            
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Building2 className="h-4 w-4" aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[13px] font-medium">{integration.name}</p>
                  <p className="text-2xs text-muted-foreground">{integration.category}</p>
                </div>
                {integration.connected ?
            <Badge tone="success" dot>
                    Connected
                  </Badge> :

            <Button variant="ghost" size="xs">
                    Connect
                  </Button>
            }
              </li>
          )}
          </ul>
        </SectionCard>
      }

      {tab === 'team' &&
      <SectionCard
        title="Team members"
        description="Roles determine what each person can see and approve."
        actions={
        <Button variant="primary" size="sm" iconLeft={<Users className="h-3.5 w-3.5" />}>
              Invite member
            </Button>
        }
        bodyClassName="px-0 pb-0">
        
          <ul className="divide-y divide-border border-t border-border">
            {team.map((member) =>
          <li
            key={member.email}
            className="flex items-center gap-4 px-5 py-3.5 transition-colors hover:bg-accent/50">
            
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/12 text-2xs font-semibold text-primary">
                  {member.name.
              split(' ').
              map((n) => n[0]).
              join('')}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[13px] font-medium">{member.name}</p>
                  <p className="truncate text-2xs text-muted-foreground">{member.email}</p>
                </div>
                <Badge tone="neutral">{member.role}</Badge>
                {member.mfa ?
            <Badge tone="success" dot>
                    MFA
                  </Badge> :

            <Badge tone="warning" dot>
                    No MFA
                  </Badge>
            }
                <Button variant="ghost" size="xs">
                  Manage
                </Button>
              </li>
          )}
          </ul>
        </SectionCard>
      }

      <Modal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        size="sm"
        title="Delete this workspace?"
        description="This removes 94 assets, 38 risks and 7 years of audit history. This cannot be undone."
        footer={
        <>
            <Button variant="ghost" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={() => setConfirmOpen(false)}>
              Delete permanently
            </Button>
          </>
        }>
        
        <div className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/[0.05] p-3.5">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-destructive" aria-hidden />
          <p className="text-xs leading-relaxed text-muted-foreground">
            Regulatory retention may legally require this data. Your compliance officer will
            be notified and must counter-approve within 24 hours.
          </p>
        </div>
      </Modal>
    </div>);

}