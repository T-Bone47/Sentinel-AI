import type { AuditEvent } from '../types/domain';

export const auditEvents: AuditEvent[] = [
{
  id: 'EVT-90412',
  actor: 'Sentinel AI',
  actorRole: 'Automation',
  action: 'policy.draft.generated',
  target: 'POL-036 Training Data Provenance',
  severity: 'info',
  source: 'Sentinel AI',
  ip: '10.24.8.19',
  timestamp: '2026-08-07T07:58:12Z'
},
{
  id: 'EVT-90409',
  actor: 'dana.okafor@northwind.io',
  actorRole: 'CISO',
  action: 'control.evidence.approved',
  target: 'ISO 42001 · A.6.2.4',
  severity: 'low',
  source: 'Console',
  ip: '92.14.221.4',
  timestamp: '2026-08-07T07:31:02Z'
},
{
  id: 'EVT-90404',
  actor: 'svc-pipeline-prod',
  actorRole: 'Service Account',
  action: 'asset.scan.completed',
  target: 'AST-1042 Atlas Support Agent',
  severity: 'medium',
  source: 'Automation',
  ip: '10.12.4.88',
  timestamp: '2026-08-07T05:00:44Z'
},
{
  id: 'EVT-90398',
  actor: 'maya.lindqvist@northwind.io',
  actorRole: 'Privacy Lead',
  action: 'incident.escalated',
  target: 'INC-4818',
  severity: 'critical',
  source: 'Console',
  ip: '81.44.130.9',
  timestamp: '2026-08-07T06:04:31Z'
},
{
  id: 'EVT-90391',
  actor: 'rohan.bhatt@northwind.io',
  actorRole: 'Policy Owner',
  action: 'policy.published',
  target: 'POL-039 v3.1',
  severity: 'low',
  source: 'Console',
  ip: '103.88.9.140',
  timestamp: '2026-08-06T18:45:19Z'
},
{
  id: 'EVT-90387',
  actor: 'api-key-7f2c',
  actorRole: 'Integration',
  action: 'export.generated',
  target: 'Risk register (CSV)',
  severity: 'medium',
  source: 'API',
  ip: '34.201.88.12',
  timestamp: '2026-08-06T16:12:07Z'
},
{
  id: 'EVT-90380',
  actor: 'kenji.tanaka@northwind.io',
  actorRole: 'Data Governance',
  action: 'retention.exception.granted',
  target: 'AST-1019 Pinecone / eu-central',
  severity: 'high',
  source: 'Console',
  ip: '126.14.9.201',
  timestamp: '2026-08-06T11:38:55Z'
},
{
  id: 'EVT-90374',
  actor: 'Sentinel AI',
  actorRole: 'Automation',
  action: 'anomaly.detected',
  target: 'Inference volume · Atlas Support Agent',
  severity: 'high',
  source: 'Sentinel AI',
  ip: '10.24.8.19',
  timestamp: '2026-08-06T05:12:40Z'
},
{
  id: 'EVT-90366',
  actor: 'sofia.alvarez@northwind.io',
  actorRole: 'Model Risk',
  action: 'model.approval.revoked',
  target: 'AST-1038 Underwriting Model v7',
  severity: 'critical',
  source: 'Console',
  ip: '77.90.14.63',
  timestamp: '2026-08-05T19:22:10Z'
},
{
  id: 'EVT-90359',
  actor: 'unknown',
  actorRole: 'Unauthenticated',
  action: 'auth.failed',
  target: 'SSO / SAML assertion',
  severity: 'high',
  source: 'API',
  ip: '45.146.9.77',
  timestamp: '2026-08-05T03:47:29Z'
},
{
  id: 'EVT-90350',
  actor: 'dana.okafor@northwind.io',
  actorRole: 'CISO',
  action: 'report.exported',
  target: 'Board risk brief · Q3',
  severity: 'low',
  source: 'Console',
  ip: '92.14.221.4',
  timestamp: '2026-08-04T14:02:11Z'
},
{
  id: 'EVT-90341',
  actor: 'svc-vendor-sync',
  actorRole: 'Service Account',
  action: 'vendor.endpoint.blocked',
  target: 'api.unknown-llm.dev',
  severity: 'medium',
  source: 'Automation',
  ip: '10.12.4.31',
  timestamp: '2026-08-04T09:19:48Z'
}];