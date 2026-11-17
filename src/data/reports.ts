import type { ReportItem } from '../types/domain';

export const reports: ReportItem[] = [
{
  id: 'REP-2091',
  name: 'Board AI Risk Brief — Q3 2026',
  type: 'Board',
  framework: 'Cross-framework',
  period: 'Q3 2026',
  status: 'ready',
  generatedAt: '2026-08-06T09:00:00Z',
  owner: 'Dana Okafor',
  aiGenerated: true
},
{
  id: 'REP-2088',
  name: 'EU AI Act Annex IV Technical Documentation',
  type: 'Regulatory',
  framework: 'EU AI Act',
  period: 'Aug 2026',
  status: 'generating',
  generatedAt: '2026-08-07T07:40:00Z',
  owner: 'Legal & Compliance',
  aiGenerated: true
},
{
  id: 'REP-2084',
  name: 'ISO 42001 Management Review Pack',
  type: 'Regulatory',
  framework: 'ISO 42001',
  period: 'H1 2026',
  status: 'ready',
  generatedAt: '2026-08-01T13:20:00Z',
  owner: 'AI Governance Office',
  aiGenerated: false
},
{
  id: 'REP-2080',
  name: 'Monthly Control Effectiveness',
  type: 'Operational',
  framework: 'SOC 2',
  period: 'Jul 2026',
  status: 'ready',
  generatedAt: '2026-08-01T06:00:00Z',
  owner: 'Security Engineering',
  aiGenerated: false
},
{
  id: 'REP-2076',
  name: 'Executive Posture Summary',
  type: 'Executive',
  framework: 'Cross-framework',
  period: 'Aug 2026',
  status: 'scheduled',
  generatedAt: '2026-08-15T06:00:00Z',
  owner: 'Dana Okafor',
  aiGenerated: true
},
{
  id: 'REP-2071',
  name: 'GDPR Records of Processing (AI systems)',
  type: 'Regulatory',
  framework: 'GDPR',
  period: 'Q2 2026',
  status: 'ready',
  generatedAt: '2026-07-12T10:30:00Z',
  owner: 'Privacy Office',
  aiGenerated: false
},
{
  id: 'REP-2067',
  name: 'HIPAA Gap Assessment',
  type: 'Regulatory',
  framework: 'HIPAA',
  period: 'Q2 2026',
  status: 'failed',
  generatedAt: '2026-07-09T16:45:00Z',
  owner: 'Privacy Office',
  aiGenerated: false
},
{
  id: 'REP-2060',
  name: 'Vendor Model Assurance Digest',
  type: 'Operational',
  framework: 'ISO 27001',
  period: 'Jul 2026',
  status: 'ready',
  generatedAt: '2026-07-31T08:15:00Z',
  owner: 'Kenji Tanaka',
  aiGenerated: true
}];