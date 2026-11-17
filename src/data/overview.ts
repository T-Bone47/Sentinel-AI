import type { Kpi, Incident } from '../types/domain';

export const kpis: Kpi[] = [
{
  id: 'posture',
  label: 'Security posture',
  value: 92.4,
  suffix: '',
  delta: 3.1,
  direction: 'up',
  positiveIsGood: true,
  caption: 'vs. last 30 days',
  status: 'trusted',
  spark: [84, 85, 83, 86, 88, 87, 90, 91, 92.4]
},
{
  id: 'risk',
  label: 'Open risk exposure',
  value: 18.6,
  prefix: '$',
  suffix: 'M',
  delta: -8.4,
  direction: 'down',
  positiveIsGood: false,
  caption: 'residual, annualized',
  status: 'trusted',
  spark: [26, 25, 24, 23.5, 22, 21, 20.4, 19.2, 18.6]
},
{
  id: 'controls',
  label: 'Controls passing',
  value: 1284,
  delta: 42,
  direction: 'up',
  positiveIsGood: true,
  caption: 'of 1,392 monitored',
  status: 'trusted',
  spark: [1180, 1195, 1210, 1222, 1240, 1251, 1266, 1275, 1284]
},
{
  id: 'incidents',
  label: 'Active incidents',
  value: 7,
  delta: -3,
  direction: 'down',
  positiveIsGood: false,
  caption: '2 critical, 5 high',
  status: 'trusted',
  spark: [14, 13, 12, 12, 11, 10, 9, 8, 7]
}];


export const riskTrend = [
{ month: 'Jan', critical: 14, high: 32, medium: 58, residual: 74 },
{ month: 'Feb', critical: 12, high: 30, medium: 62, residual: 71 },
{ month: 'Mar', critical: 15, high: 28, medium: 55, residual: 69 },
{ month: 'Apr', critical: 11, high: 26, medium: 51, residual: 64 },
{ month: 'May', critical: 9, high: 24, medium: 49, residual: 59 },
{ month: 'Jun', critical: 10, high: 21, medium: 47, residual: 55 },
{ month: 'Jul', critical: 7, high: 19, medium: 44, residual: 49 },
{ month: 'Aug', critical: 6, high: 17, medium: 41, residual: 45 },
{ month: 'Sep', critical: 5, high: 15, medium: 38, residual: 41 }];


export const complianceTrend = [
{ month: 'Apr', score: 78, target: 90 },
{ month: 'May', score: 81, target: 90 },
{ month: 'Jun', score: 84, target: 90 },
{ month: 'Jul', score: 86, target: 90 },
{ month: 'Aug', score: 89, target: 90 },
{ month: 'Sep', score: 92, target: 90 }];


export const controlCoverage = [
{ pillar: 'Governance', coverage: 94 },
{ pillar: 'Data', coverage: 88 },
{ pillar: 'Model', coverage: 81 },
{ pillar: 'Access', coverage: 96 },
{ pillar: 'Monitoring', coverage: 73 },
{ pillar: 'Vendor', coverage: 68 }];


export const incidents: Incident[] = [
{
  id: 'INC-4821',
  title: 'Prompt injection attempt on Atlas support agent',
  level: 'critical',
  system: 'Atlas Support Agent',
  openedAt: '2026-08-07T06:12:00Z',
  status: 'investigating',
  assignee: 'D. Okafor'
},
{
  id: 'INC-4818',
  title: 'PII leakage detected in fine-tuning corpus',
  level: 'critical',
  system: 'Corpus / claims-v4',
  openedAt: '2026-08-06T21:40:00Z',
  status: 'contained',
  assignee: 'M. Lindqvist'
},
{
  id: 'INC-4815',
  title: 'Model drift beyond tolerance on credit scoring',
  level: 'high',
  system: 'Underwriting Model v7',
  openedAt: '2026-08-06T14:05:00Z',
  status: 'triage',
  assignee: 'S. Alvarez'
},
{
  id: 'INC-4809',
  title: 'Unapproved vendor endpoint called from staging',
  level: 'high',
  system: 'Vendor Gateway',
  openedAt: '2026-08-05T09:22:00Z',
  status: 'investigating',
  assignee: 'R. Bhatt'
},
{
  id: 'INC-4803',
  title: 'Retention policy exception on vector store',
  level: 'medium',
  system: 'Pinecone / eu-central',
  openedAt: '2026-08-04T17:48:00Z',
  status: 'resolved',
  assignee: 'K. Tanaka'
}];


export const upcomingAudits = [
{
  id: 'AUD-01',
  framework: 'EU AI Act — Annex IV',
  auditor: 'Deloitte',
  date: '2026-08-21',
  readiness: 86,
  owner: 'Legal & Compliance'
},
{
  id: 'AUD-02',
  framework: 'ISO/IEC 42001',
  auditor: 'BSI Group',
  date: '2026-09-04',
  readiness: 72,
  owner: 'AI Governance Office'
},
{
  id: 'AUD-03',
  framework: 'SOC 2 Type II',
  auditor: 'Prescient Assurance',
  date: '2026-09-29',
  readiness: 94,
  owner: 'Security Engineering'
}];


export const policyHealth = [
{ label: 'Published & attested', value: 68, tone: 'success' as const },
{ label: 'Awaiting attestation', value: 19, tone: 'warning' as const },
{ label: 'In review', value: 9, tone: 'primary' as const },
{ label: 'Expired', value: 4, tone: 'danger' as const }];


export const activityFeed = [
{
  id: 'a1',
  actor: 'Sentinel AI',
  action: 'drafted a mitigation plan for',
  target: 'RSK-2291',
  time: '2026-08-07T07:58:00Z',
  ai: true
},
{
  id: 'a2',
  actor: 'Dana Okafor',
  action: 'approved control evidence for',
  target: 'ISO 42001 · A.6.2.4',
  time: '2026-08-07T07:31:00Z',
  ai: false
},
{
  id: 'a3',
  actor: 'Maya Lindqvist',
  action: 'escalated incident',
  target: 'INC-4818',
  time: '2026-08-07T06:04:00Z',
  ai: false
},
{
  id: 'a4',
  actor: 'Sentinel AI',
  action: 'flagged anomalous inference volume on',
  target: 'Atlas Support Agent',
  time: '2026-08-07T05:12:00Z',
  ai: true
},
{
  id: 'a5',
  actor: 'Rohan Bhatt',
  action: 'published policy',
  target: 'Third-Party Model Usage v3.1',
  time: '2026-08-06T18:45:00Z',
  ai: false
}];