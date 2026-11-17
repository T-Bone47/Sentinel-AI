import type { RiskItem } from '../types/domain';

export const risks: RiskItem[] = [
{
  id: 'RSK-2291',
  title: 'Public storage exposure of claim archives',
  severity: 'critical',
  score: 94,
  asset: 's3://nw-claims-archive',
  assetType: 'Cloud Asset',
  control: 'CTL-A.8.12',
  framework: 'ISO 27001',
  owner: 'Kenji Tanaka',
  department: 'Data Platform',
  status: 'investigating',
  updatedAt: '2026-08-07T09:42:00Z',
  likelihood: 5,
  impact: 5,
  aiConfidence: 96,
  chain: {
    policy: 'Cloud Security Standard v2.1 — storage must deny public access by default',
    control: 'CTL-A.8.12 · Data leakage prevention on public cloud storage — FAILING',
    finding: 'FND-9012 · Bucket policy allows s3:ListBucket to principal "*"',
    asset: 's3://nw-claims-archive · AWS eu-central-1 · 128,402 claim records',
    evidence: 'EV-8829 · Bucket policy snapshot captured by AWS Config at 09:42:18',
    impact:
    'Sensitive personal and medical claim data is publicly enumerable. Reportable under DPDP §8 and blocks the ISO 27001 surveillance audit on Sep 29.',
    recommendation:
    'Apply the deny-public-access SCP to the account, enable Block Public Access at bucket level, then re-run the DLP control test. Sentinel can raise the change request with the evidence pre-attached.'
  }
},
{
  id: 'RSK-2288',
  title: 'MFA coverage gap on privileged identities',
  severity: 'high',
  score: 87,
  asset: 'Okta directory',
  assetType: 'Identity',
  control: 'CTL-A.5.17',
  framework: 'SOC 2',
  owner: 'Dana Okafor',
  department: 'Security',
  status: 'mitigating',
  updatedAt: '2026-08-07T09:38:00Z',
  likelihood: 4,
  impact: 5,
  aiConfidence: 93,
  chain: {
    policy: 'Access Control Policy v4.2 — MFA mandatory for all privileged access',
    control: 'CTL-A.5.17 · Multi-factor authentication on privileged accounts — FAILING',
    finding: 'FND-9008 · 6 privileged identities enrolled without a second factor',
    asset: 'Okta directory · 27 privileged identities · 6 non-compliant',
    evidence: 'EV-8836 · MFA enrollment report exported 2026-08-07 04:00 UTC',
    impact:
    'Credential compromise on any of the 6 identities grants AWS AdministratorAccess. Directly reduces Trust Score by 2 points and fails SOC 2 CC6.1 evidence review.',
    recommendation:
    'Enforce the privileged-access MFA policy in Okta and expire active sessions for the 6 identities. Estimated Trust Score recovery +2.0.'
  }
},
{
  id: 'RSK-2284',
  title: 'Unencrypted volume attached to payments-api',
  severity: 'high',
  score: 84,
  asset: 'vol-0f2c payments-api',
  assetType: 'Cloud Asset',
  control: 'CTL-A.8.12',
  framework: 'ISO 27001',
  owner: 'Rohan Bhatt',
  department: 'Engineering',
  status: 'open',
  updatedAt: '2026-08-07T09:33:00Z',
  likelihood: 3,
  impact: 5,
  aiConfidence: 91,
  chain: {
    policy: 'Cloud Security Standard v2.1 — encryption at rest for all production volumes',
    control: 'CTL-A.8.12 · Data leakage prevention — PARTIAL',
    finding: 'FND-9004 · EBS volume vol-0f2c created without KMS encryption',
    asset: 'vol-0f2c · attached to payments-api · AWS eu-west-1',
    evidence: 'EV-8748 · AWS Config resource export',
    impact:
    'Cardholder-adjacent data written to an unencrypted volume. Fails ISO 27001 A.8.12 and the internal change-management control.',
    recommendation:
    'Snapshot, re-create the volume with the production KMS key, and add the encryption guardrail to the Terraform module.'
  }
},
{
  id: 'RSK-2280',
  title: 'Vendor certification expired — Lumenpay',
  severity: 'high',
  score: 82,
  asset: 'Lumenpay',
  assetType: 'Vendor',
  control: 'CTL-CC9.2',
  framework: 'SOC 2',
  owner: 'Elena Petrova',
  department: 'Finance',
  status: 'mitigating',
  updatedAt: '2026-08-06T11:20:00Z',
  likelihood: 4,
  impact: 4,
  aiConfidence: 88,
  chain: {
    policy: 'Third-Party Risk Policy v3.1 — valid assurance report required for tier-1 vendors',
    control: 'CTL-CC9.2 · Third-party risk assessment before onboarding — PARTIAL',
    finding: 'FND-8996 · SOC 2 Type II report expired 2026-07-14',
    asset: 'Lumenpay · payments processor · cardholder data shared',
    evidence: 'EV-8812 · Vendor due diligence questionnaire (expiring)',
    impact:
    'A tier-1 payments vendor is operating without current assurance. Auditors will treat all dependent controls as unsupported.',
    recommendation:
    'Request the FY26 SOC 2 report, apply a compensating monitoring control for 30 days, and record the exception with an expiry date.'
  }
},
{
  id: 'RSK-2274',
  title: 'Personal data retained beyond DPDP limit',
  severity: 'medium',
  score: 68,
  asset: 'Claims Portal',
  assetType: 'Application',
  control: 'CTL-DPDP-8',
  framework: 'DPDP',
  owner: 'Maya Lindqvist',
  department: 'Legal & Privacy',
  status: 'open',
  updatedAt: '2026-08-07T09:28:00Z',
  likelihood: 4,
  impact: 3,
  aiConfidence: 90,
  chain: {
    policy: 'Data Retention Standard v1.6 — claim records purged after 7 years',
    control: 'CTL-DPDP-8 · Personal data retention limits enforced — FAILING',
    finding: 'FND-8990 · 1,204 records exceed the retention window',
    asset: 'Claims Portal · sensitive personal data · 128,402 records',
    evidence: 'EV-8790 · Retention job execution log (pending verification)',
    impact:
    'Retention breach under DPDP §8(7). Increases the blast radius of any future exposure on the same dataset.',
    recommendation:
    'Re-run the retention task with the corrected predicate and add a monitor that alerts when the purge job skips partitions.'
  }
},
{
  id: 'RSK-2269',
  title: 'EDR agent unhealthy on privileged endpoint',
  severity: 'high',
  score: 76,
  asset: 'NW-MBP-102',
  assetType: 'Device',
  control: 'CTL-INT-04',
  framework: 'Internal Controls',
  owner: 'Security Engineering',
  department: 'Security',
  status: 'investigating',
  updatedAt: '2026-08-07T08:12:00Z',
  likelihood: 4,
  impact: 4,
  aiConfidence: 86,
  chain: {
    policy: 'Endpoint Hardening Standard — EDR required on all managed endpoints',
    control: 'CTL-INT-04 · Endpoint encryption and EDR coverage — PARTIAL',
    finding: 'FND-8984 · EDR agent has not reported for 62 hours',
    asset: 'NW-MBP-102 · Jonas Meyer · privileged AWS access',
    evidence: 'EV-8798 · Endpoint encryption attestation',
    impact:
    'An endpoint with AdministratorAccess is unmonitored, compounding the open MFA gap on the same identity.',
    recommendation:
    'Force agent reinstall via MDM and temporarily suspend the privileged role until telemetry resumes.'
  }
},
{
  id: 'RSK-2261',
  title: 'Dormant contractor retains data warehouse access',
  severity: 'medium',
  score: 61,
  asset: 'contractor.jsmith@partner.io',
  assetType: 'Identity',
  control: 'CTL-CC6.1',
  framework: 'SOC 2',
  owner: 'Dana Okafor',
  department: 'Security',
  status: 'mitigating',
  updatedAt: '2026-08-05T06:40:00Z',
  likelihood: 3,
  impact: 3,
  aiConfidence: 82,
  chain: {
    policy: 'Access Control Policy v4.2 — access revoked within 24h of inactivity threshold',
    control: 'CTL-CC6.1 · Logical access provisioning and deprovisioning — PASSING with exception',
    finding: 'FND-8975 · Account inactive 71 days, entitlements intact',
    asset: 'contractor.jsmith@partner.io · Snowflake analyst role',
    evidence: 'EV-8841 · Privileged access review Q3 2026',
    impact: 'Unused standing access to analytics data containing sensitive personal records.',
    recommendation: 'Auto-disable the account and convert the entitlement to just-in-time access.'
  }
},
{
  id: 'RSK-2258',
  title: 'Biometric data shared with uncertified vendor',
  severity: 'critical',
  score: 91,
  asset: 'Vireo Screening',
  assetType: 'Vendor',
  control: 'CTL-CC9.2',
  framework: 'DPDP',
  owner: 'Aisha Bello',
  department: 'Operations',
  status: 'open',
  updatedAt: '2026-08-04T15:10:00Z',
  likelihood: 4,
  impact: 5,
  aiConfidence: 94,
  chain: {
    policy: 'Third-Party Risk Policy v3.1 — sensitive personal data requires certified processors',
    control: 'CTL-CC9.2 · Third-party risk assessment — PARTIAL',
    finding: 'FND-8968 · Government ID and biometric data shared without certification',
    asset: 'Vireo Screening · 1,842 data principals · hosted in IN',
    evidence: 'EV-8760 · Security questionnaire (expired)',
    impact:
    'Highest-severity DPDP exposure in the estate: biometric data processed by an uncertified vendor with 48% consent coverage.',
    recommendation:
    'Suspend new submissions, execute a data processing agreement with audit rights, and run a DPIA before resuming.'
  }
},
{
  id: 'RSK-2250',
  title: 'Consent basis missing for behavioral analytics',
  severity: 'medium',
  score: 58,
  asset: 'Helix Analytics',
  assetType: 'Vendor',
  control: 'CTL-DPDP-6',
  framework: 'DPDP',
  owner: 'Maya Lindqvist',
  department: 'Legal & Privacy',
  status: 'open',
  updatedAt: '2026-08-01T13:15:00Z',
  likelihood: 4,
  impact: 3,
  aiConfidence: 87,
  chain: {
    policy: 'DPDP Privacy Policy v2.0 — every purpose requires a recorded lawful basis',
    control: 'CTL-DPDP-6 · Valid consent captured for every processing purpose — PARTIAL',
    finding: 'FND-8944 · 39% of principals lack consent for product analytics',
    asset: 'Helix Analytics · 2.1M behavioral events · hosted in US',
    evidence: 'EV-8820 · Consent ledger extract',
    impact: 'Processing without lawful basis plus a cross-border transfer to an uncertified vendor.',
    recommendation: 'Suppress analytics ingestion for non-consented principals and re-collect consent in-product.'
  }
},
{
  id: 'RSK-2244',
  title: 'CloudTrail logging disabled on legacy ETL role',
  severity: 'medium',
  score: 54,
  asset: 'iam/role-legacy-etl',
  assetType: 'Cloud Asset',
  control: 'CTL-CC7.2',
  framework: 'SOC 2',
  owner: 'Kenji Tanaka',
  department: 'Data Platform',
  status: 'open',
  updatedAt: '2026-08-03T22:05:00Z',
  likelihood: 3,
  impact: 3,
  aiConfidence: 79,
  chain: {
    policy: 'Monitoring & Logging Policy — all data-plane access must be logged',
    control: 'CTL-CC7.2 · Continuous monitoring and anomaly detection — PASSING with gap',
    finding: 'FND-8960 · CloudTrail data events disabled for the role',
    asset: 'iam/role-legacy-etl · global · used by svc-legacy-etl',
    evidence: 'EV-8748 · CloudTrail configuration export',
    impact: 'Data access by a dormant service account cannot be reconstructed for auditors.',
    recommendation: 'Enable data events, or decommission the role — it has been unused for 127 days.'
  }
},
{
  id: 'RSK-2238',
  title: 'Patch level drift across 9 endpoints',
  severity: 'low',
  score: 38,
  asset: 'Device fleet',
  assetType: 'Device',
  control: 'CTL-INT-04',
  framework: 'Internal Controls',
  owner: 'Security Engineering',
  department: 'Security',
  status: 'mitigating',
  updatedAt: '2026-08-02T07:30:00Z',
  likelihood: 3,
  impact: 2,
  aiConfidence: 74,
  chain: {
    policy: 'Endpoint Hardening Standard — critical patches within 14 days',
    control: 'CTL-INT-04 · Endpoint encryption and EDR coverage — PARTIAL',
    finding: 'FND-8952 · 9 endpoints 41 days behind',
    asset: 'Device fleet · 312 managed endpoints',
    evidence: 'EV-8798 · Endpoint attestation export',
    impact: 'Known-exploited vulnerabilities remain open on a small subset of the fleet.',
    recommendation: 'Force the deferred update ring and report exceptions to the device owners.'
  }
},
{
  id: 'RSK-2230',
  title: 'Change approval missing on production deploys',
  severity: 'low',
  score: 32,
  asset: 'payments-api',
  assetType: 'Application',
  control: 'CTL-INT-14',
  framework: 'Internal Controls',
  owner: 'Rohan Bhatt',
  department: 'Engineering',
  status: 'closed',
  updatedAt: '2026-07-28T09:00:00Z',
  likelihood: 2,
  impact: 2,
  aiConfidence: 68,
  chain: {
    policy: 'Change Management Policy — production changes require documented approval',
    control: 'CTL-INT-14 · Change management approval — NOT TESTED',
    finding: 'FND-8930 · 3 deploys merged without linked approval',
    asset: 'payments-api · 42 users · critical',
    evidence: 'EV-8781 · Change approval records',
    impact: 'Audit trail gap for three production changes; remediated with retroactive approvals.',
    recommendation: 'Enforce the branch protection rule requiring a linked change ticket.'
  }
}];


export const riskByDomain = [
{ domain: 'Cloud', critical: 2, high: 3, medium: 4 },
{ domain: 'Identity', critical: 1, high: 4, medium: 3 },
{ domain: 'Vendors', critical: 1, high: 2, medium: 2 },
{ domain: 'Privacy', critical: 0, high: 2, medium: 4 },
{ domain: 'Devices', critical: 0, high: 2, medium: 3 }];


export const riskVelocity = [
{ week: 'W27', opened: 12, closed: 8 },
{ week: 'W28', opened: 14, closed: 11 },
{ week: 'W29', opened: 9, closed: 13 },
{ week: 'W30', opened: 11, closed: 12 },
{ week: 'W31', opened: 8, closed: 15 },
{ week: 'W32', opened: 10, closed: 14 },
{ week: 'W33', opened: 6, closed: 12 }];