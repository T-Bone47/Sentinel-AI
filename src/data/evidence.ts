import type { EvidenceItem } from '../types/domain';

export const evidenceItems: EvidenceItem[] = [
{
  id: 'EV-8841',
  name: 'Privileged access review — Q3 2026',
  control: 'CTL-INT-09',
  source: 'Okta · automated export',
  collectedAt: '2026-08-07T04:00:00Z',
  validUntil: '2026-11-07',
  owner: 'Dana Okafor',
  status: 'verified',
  automated: true
},
{
  id: 'EV-8836',
  name: 'MFA enrollment report',
  control: 'CTL-A.5.17',
  source: 'Okta · automated export',
  collectedAt: '2026-08-07T04:00:00Z',
  validUntil: '2026-09-07',
  owner: 'Dana Okafor',
  status: 'verified',
  automated: true
},
{
  id: 'EV-8829',
  name: 'S3 bucket policy snapshot',
  control: 'CTL-A.8.12',
  source: 'AWS Config',
  collectedAt: '2026-08-07T09:42:00Z',
  validUntil: '2026-09-06',
  owner: 'Kenji Tanaka',
  status: 'verified',
  automated: true
},
{
  id: 'EV-8820',
  name: 'Consent ledger extract — DPDP purposes',
  control: 'CTL-DPDP-6',
  source: 'OneTrust',
  collectedAt: '2026-08-06T04:00:00Z',
  validUntil: '2026-09-05',
  owner: 'Maya Lindqvist',
  status: 'verified',
  automated: true
},
{
  id: 'EV-8812',
  name: 'Vendor due diligence questionnaire — Lumenpay',
  control: 'CTL-CC9.2',
  source: 'Manual upload',
  collectedAt: '2026-06-14T10:00:00Z',
  validUntil: '2026-08-14',
  owner: 'Elena Petrova',
  status: 'expiring',
  automated: false
},
{
  id: 'EV-8804',
  name: 'Incident response tabletop minutes',
  control: 'CTL-CC7.2',
  source: 'Manual upload',
  collectedAt: '2026-05-02T14:00:00Z',
  validUntil: '2026-08-02',
  owner: 'Dana Okafor',
  status: 'expired',
  automated: false
},
{
  id: 'EV-8798',
  name: 'Endpoint encryption attestation',
  control: 'CTL-INT-04',
  source: 'Device Agent',
  collectedAt: '2026-08-07T04:00:00Z',
  validUntil: '2026-09-07',
  owner: 'Security Engineering',
  status: 'verified',
  automated: true
},
{
  id: 'EV-8790',
  name: 'Retention job execution log',
  control: 'CTL-DPDP-8',
  source: 'Snowflake task history',
  collectedAt: '2026-08-05T02:00:00Z',
  validUntil: '2026-09-04',
  owner: 'Kenji Tanaka',
  status: 'pending',
  automated: true
},
{
  id: 'EV-8781',
  name: 'Change approval records — payments-api',
  control: 'CTL-INT-14',
  source: 'Jira export',
  collectedAt: '2026-07-28T09:00:00Z',
  validUntil: '2026-10-28',
  owner: 'Rohan Bhatt',
  status: 'verified',
  automated: false
},
{
  id: 'EV-8772',
  name: 'Data principal request register',
  control: 'CTL-DPDP-11',
  source: 'OneTrust',
  collectedAt: '2026-08-02T04:00:00Z',
  validUntil: '2026-11-02',
  owner: 'Maya Lindqvist',
  status: 'verified',
  automated: true
},
{
  id: 'EV-8760',
  name: 'Vireo Screening security questionnaire',
  control: 'CTL-CC9.2',
  source: 'Manual upload',
  collectedAt: '2026-04-11T10:00:00Z',
  validUntil: '2026-07-11',
  owner: 'Aisha Bello',
  status: 'expired',
  automated: false
},
{
  id: 'EV-8748',
  name: 'CloudTrail configuration export',
  control: 'CTL-CC7.2',
  source: 'AWS Config',
  collectedAt: '2026-08-06T04:00:00Z',
  validUntil: '2026-09-05',
  owner: 'Kenji Tanaka',
  status: 'verified',
  automated: true
}];


export const evidenceCoverage = [
{ id: 'automated', label: 'Automated collection', value: 74 },
{ id: 'manual', label: 'Manual upload', value: 18 },
{ id: 'ai', label: 'AI-assisted', value: 8 }];