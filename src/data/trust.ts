import type {
  FrameworkScore,
  Kpi,
  StreamEvent,
  TrustDomain } from
'../types/domain';

export const trustScore = {
  value: 87,
  max: 100,
  band: 'GOOD',
  delta: 4.2,
  previous: 83,
  updatedAt: '2026-08-07T09:42:00Z',
  signalsEvaluated: 14_208,
  history: [79, 80, 82, 81, 83, 84, 86, 87]
};

/** Domains rendered around the trust ring AND in the posture panel. */
export const trustDomains: TrustDomain[] = [
{
  id: 'identity',
  label: 'Identity',
  score: 82,
  delta: -2.1,
  status: 'warning',
  detail: 'MFA coverage 94% · 6 privileged gaps'
},
{
  id: 'people',
  label: 'People',
  score: 91,
  delta: 1.4,
  status: 'trusted',
  detail: '248 employees · 96% trained'
},
{
  id: 'devices',
  label: 'Devices',
  score: 88,
  delta: 2.6,
  status: 'trusted',
  detail: '312 managed · 9 unpatched'
},
{
  id: 'applications',
  label: 'Applications',
  score: 85,
  delta: 0.8,
  status: 'trusted',
  detail: '64 apps · 4 high access risk'
},
{
  id: 'cloud',
  label: 'Cloud',
  score: 74,
  delta: -5.2,
  status: 'critical',
  detail: '1 public bucket · 3 logging gaps'
},
{
  id: 'vendors',
  label: 'Vendors',
  score: 79,
  delta: -1.2,
  status: 'warning',
  detail: '38 vendors · 2 certs expired'
},
{
  id: 'policies',
  label: 'Policies',
  score: 93,
  delta: 3.1,
  status: 'trusted',
  detail: '41 policies · 2 in review'
},
{
  id: 'privacy',
  label: 'Privacy',
  score: 90,
  delta: 2.2,
  status: 'trusted',
  detail: 'DPDP 91% · consent 94%'
},
{
  id: 'evidence',
  label: 'Evidence',
  score: 86,
  delta: 1.9,
  status: 'trusted',
  detail: '418 artifacts · 96% fresh'
}];


export const executiveKpis: Kpi[] = [
{
  id: 'audit-readiness',
  label: 'Audit readiness',
  value: 91,
  suffix: '%',
  delta: 3.4,
  direction: 'up',
  positiveIsGood: true,
  caption: 'ISO 27001 · SOC 2 · DPDP',
  status: 'trusted',
  spark: [82, 84, 85, 87, 88, 90, 91]
},
{
  id: 'critical-risks',
  label: 'Critical risks',
  value: 4,
  delta: 1,
  direction: 'up',
  positiveIsGood: false,
  caption: '2 opened in last 24h',
  status: 'critical',
  spark: [2, 2, 3, 3, 2, 3, 4]
},
{
  id: 'open-findings',
  label: 'Open findings',
  value: 23,
  delta: -6,
  direction: 'down',
  positiveIsGood: false,
  caption: '11 auto-remediable',
  status: 'warning',
  spark: [38, 35, 33, 30, 28, 26, 23]
},
{
  id: 'evidence-coverage',
  label: 'Evidence coverage',
  value: 86,
  suffix: '%',
  delta: 2.1,
  direction: 'up',
  positiveIsGood: true,
  caption: '418 of 486 controls',
  status: 'trusted',
  spark: [76, 78, 80, 81, 83, 85, 86]
}];


export const threatStream: StreamEvent[] = [
{
  id: 'ev-1',
  time: '09:42:18',
  severity: 'critical',
  title: 'Public cloud asset detected — s3://nw-claims-archive',
  source: 'Cloud Scan · AWS eu-central-1'
},
{
  id: 'ev-2',
  time: '09:38:41',
  severity: 'high',
  title: 'MFA coverage dropped to 94% across privileged accounts',
  source: 'IAM Sync · Okta'
},
{
  id: 'ev-3',
  time: '09:35:12',
  severity: 'medium',
  title: 'Vendor certification approaching expiry — Lumenpay',
  source: 'Vendor Review'
},
{
  id: 'ev-4',
  time: '09:33:57',
  severity: 'high',
  title: 'Unencrypted volume attached to payments-api',
  source: 'Cloud Scan · AWS eu-west-1'
},
{
  id: 'ev-5',
  time: '09:31:04',
  severity: 'info',
  title: 'Audit evidence collected — access review Q3',
  source: 'Automation · Okta'
},
{
  id: 'ev-6',
  time: '09:28:22',
  severity: 'medium',
  title: 'Retention window exceeded on 1,204 personal data records',
  source: 'Sentinel AI · DPDP monitor'
},
{
  id: 'ev-7',
  time: '09:24:10',
  severity: 'info',
  title: 'Device agent reported 312 endpoints healthy',
  source: 'Device Agent'
},
{
  id: 'ev-8',
  time: '09:21:48',
  severity: 'low',
  title: 'Dormant account flagged — contractor.jsmith',
  source: 'IAM Sync · Okta'
}];


export const frameworkScores: FrameworkScore[] = [
{
  id: 'iso-27001',
  name: 'ISO 27001',
  coverage: 94,
  passed: 176,
  failed: 11,
  evidence: 148,
  findings: 6,
  readiness: 95,
  status: 'compliant',
  authority: 'ISO',
  nextAudit: '2026-09-29',
  owner: 'Security Engineering'
},
{
  id: 'soc-2',
  name: 'SOC 2',
  coverage: 88,
  passed: 148,
  failed: 20,
  evidence: 132,
  findings: 9,
  readiness: 89,
  status: 'at-risk',
  authority: 'AICPA',
  nextAudit: '2026-10-14',
  owner: 'Security Engineering'
},
{
  id: 'dpdp',
  name: 'DPDP',
  coverage: 91,
  passed: 82,
  failed: 8,
  evidence: 74,
  findings: 4,
  readiness: 92,
  status: 'compliant',
  authority: 'Data Protection Board of India',
  nextAudit: '2026-11-05',
  owner: 'Privacy Office'
},
{
  id: 'internal',
  name: 'Internal Controls',
  coverage: 86,
  passed: 96,
  failed: 16,
  evidence: 64,
  findings: 4,
  readiness: 84,
  status: 'at-risk',
  authority: 'Northwind GRC',
  nextAudit: '2026-09-12',
  owner: 'AI Governance Office'
}];


/** Chain rendered by the Command Center topology preview. */
export const topologyChain = [
{ id: 'employees', label: 'Employees', count: 248, status: 'trusted' as const },
{ id: 'iam', label: 'IAM', count: 312, status: 'warning' as const },
{ id: 'devices', label: 'Devices', count: 312, status: 'trusted' as const },
{ id: 'applications', label: 'Applications', count: 64, status: 'trusted' as const },
{ id: 'cloud', label: 'Cloud', count: 186, status: 'critical' as const },
{ id: 'data', label: 'Data', count: 42, status: 'warning' as const },
{ id: 'vendors', label: 'Vendors', count: 38, status: 'warning' as const },
{ id: 'policies', label: 'Policies', count: 41, status: 'trusted' as const },
{ id: 'controls', label: 'Controls', count: 486, status: 'trusted' as const },
{ id: 'evidence', label: 'Evidence', count: 418, status: 'trusted' as const }];


export const trustTrend = [
{ day: 'Aug 1', score: 79, target: 90 },
{ day: 'Aug 2', score: 80, target: 90 },
{ day: 'Aug 3', score: 82, target: 90 },
{ day: 'Aug 4', score: 81, target: 90 },
{ day: 'Aug 5', score: 83, target: 90 },
{ day: 'Aug 6', score: 86, target: 90 },
{ day: 'Aug 7', score: 87, target: 90 }];