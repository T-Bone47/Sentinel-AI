import type { ConsentRecord, PersonalDataAsset } from '../types/domain';

export const privacyMetrics = [
{
  id: 'assets',
  label: 'Personal data assets',
  value: 42,
  caption: 'across 18 applications'
},
{ id: 'consent', label: 'Consent coverage', value: 94, suffix: '%', caption: 'target 100%' },
{ id: 'high-risk', label: 'High-risk data', value: 7, caption: 'sensitive + biometric' },
{ id: 'retention', label: 'Retention risks', value: 3, caption: '1,204 records overdue' },
{ id: 'violations', label: 'Consent violations', value: 2, caption: 'requires legal review' }];


export const personalDataAssets: PersonalDataAsset[] = [
{
  id: 'PD-7101',
  dataElement: 'Government ID (Aadhaar / PAN)',
  category: 'Biometric',
  application: 'Vireo Screening',
  purpose: 'Background verification',
  consent: 'fail',
  retention: '5 years',
  retentionRisk: 'fail',
  riskLevel: 'critical',
  records: 1_842,
  location: 'Vendor · IN'
},
{
  id: 'PD-7094',
  dataElement: 'Claim history & medical notes',
  category: 'Sensitive Personal',
  application: 'Claims Portal',
  purpose: 'Claims adjudication',
  consent: 'pass',
  retention: '7 years',
  retentionRisk: 'warn',
  riskLevel: 'high',
  records: 128_402,
  location: 'AWS eu-central-1'
},
{
  id: 'PD-7088',
  dataElement: 'Cardholder data (tokenized)',
  category: 'Financial',
  application: 'Lumenpay Gateway',
  purpose: 'Payment processing',
  consent: 'pass',
  retention: '3 years',
  retentionRisk: 'pass',
  riskLevel: 'high',
  records: 84_210,
  location: 'Vendor · EU'
},
{
  id: 'PD-7076',
  dataElement: 'Support conversation transcripts',
  category: 'Personal',
  application: 'Atlas Support Agent',
  purpose: 'Customer support',
  consent: 'warn',
  retention: '18 months',
  retentionRisk: 'warn',
  riskLevel: 'medium',
  records: 412_908,
  location: 'AWS eu-central-1'
},
{
  id: 'PD-7065',
  dataElement: 'Behavioral analytics events',
  category: 'Personal',
  application: 'Helix Analytics',
  purpose: 'Product analytics',
  consent: 'fail',
  retention: '24 months',
  retentionRisk: 'fail',
  riskLevel: 'high',
  records: 2_104_882,
  location: 'Vendor · US'
},
{
  id: 'PD-7052',
  dataElement: 'Employee directory attributes',
  category: 'Personal',
  application: 'Okta Identity Cloud',
  purpose: 'Identity management',
  consent: 'pass',
  retention: 'Employment + 1 year',
  retentionRisk: 'pass',
  riskLevel: 'low',
  records: 312,
  location: 'SaaS · EU'
},
{
  id: 'PD-7041',
  dataElement: 'Email address & contact preferences',
  category: 'Personal',
  application: 'Copy Assistant',
  purpose: 'Marketing communication',
  consent: 'warn',
  retention: '12 months',
  retentionRisk: 'pass',
  riskLevel: 'medium',
  records: 96_441,
  location: 'GCP europe-west4'
},
{
  id: 'PD-7030',
  dataElement: 'Analytics warehouse copies',
  category: 'Sensitive Personal',
  application: 'Snowflake Analytics',
  purpose: 'Risk modelling',
  consent: 'pass',
  retention: '2 years',
  retentionRisk: 'warn',
  riskLevel: 'medium',
  records: 640_112,
  location: 'Azure westeurope'
}];


export const consentRecords: ConsentRecord[] = [
{
  id: 'CNS-6201',
  purpose: 'Claims adjudication',
  application: 'Claims Portal',
  principals: 128_402,
  coverage: 99,
  basis: 'Contract',
  status: 'valid',
  lastUpdated: '2026-08-06T04:00:00Z',
  withdrawalRate: 0.4
},
{
  id: 'CNS-6188',
  purpose: 'Payment processing',
  application: 'Lumenpay Gateway',
  principals: 84_210,
  coverage: 100,
  basis: 'Contract',
  status: 'valid',
  lastUpdated: '2026-08-06T04:00:00Z',
  withdrawalRate: 0.1
},
{
  id: 'CNS-6174',
  purpose: 'Product analytics',
  application: 'Helix Analytics',
  principals: 2_104_882,
  coverage: 61,
  basis: 'Consent',
  status: 'violation',
  lastUpdated: '2026-08-01T13:15:00Z',
  withdrawalRate: 7.2
},
{
  id: 'CNS-6160',
  purpose: 'Background verification',
  application: 'Vireo Screening',
  principals: 1_842,
  coverage: 48,
  basis: 'Consent',
  status: 'violation',
  lastUpdated: '2026-07-22T10:00:00Z',
  withdrawalRate: 2.1
},
{
  id: 'CNS-6142',
  purpose: 'Customer support',
  application: 'Atlas Support Agent',
  principals: 412_908,
  coverage: 88,
  basis: 'Legal Obligation',
  status: 'partial',
  lastUpdated: '2026-08-04T04:00:00Z',
  withdrawalRate: 1.4
},
{
  id: 'CNS-6130',
  purpose: 'Marketing communication',
  application: 'Copy Assistant',
  principals: 96_441,
  coverage: 92,
  basis: 'Consent',
  status: 'partial',
  lastUpdated: '2026-08-03T04:00:00Z',
  withdrawalRate: 4.8
},
{
  id: 'CNS-6118',
  purpose: 'Identity management',
  application: 'Okta Identity Cloud',
  principals: 312,
  coverage: 100,
  basis: 'Legal Obligation',
  status: 'valid',
  lastUpdated: '2026-08-07T04:00:00Z',
  withdrawalRate: 0
}];


/** PERSONAL DATA → APPLICATION → PURPOSE → CONSENT → RETENTION → RISK */
export const privacyFlow = [
{ id: 'data', label: 'Personal data', value: '42 assets', status: 'warning' as const },
{ id: 'app', label: 'Application', value: '18 apps', status: 'trusted' as const },
{ id: 'purpose', label: 'Purpose', value: '11 purposes', status: 'trusted' as const },
{ id: 'consent', label: 'Consent', value: '94% covered', status: 'warning' as const },
{ id: 'retention', label: 'Retention', value: '3 overdue', status: 'critical' as const },
{ id: 'risk', label: 'Risk', value: '2 violations', status: 'critical' as const }];