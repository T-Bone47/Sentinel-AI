import type { AssetRecord } from '../types/domain';

export const assets: AssetRecord[] = [
{
  id: 'AST-1042',
  name: 'Atlas Support Agent',
  type: 'Agent',
  environment: 'Production',
  owner: 'Customer Experience',
  riskLevel: 'critical',
  dataClass: 'Confidential',
  drift: 4.2,
  lastScan: '2026-08-07T05:00:00Z',
  status: 'degraded'
},
{
  id: 'AST-1038',
  name: 'Underwriting Model v7',
  type: 'LLM Model',
  environment: 'Production',
  owner: 'Risk Analytics',
  riskLevel: 'high',
  dataClass: 'Restricted',
  drift: 6.8,
  lastScan: '2026-08-07T04:30:00Z',
  status: 'degraded'
},
{
  id: 'AST-1031',
  name: 'Claims Corpus v4',
  type: 'Dataset',
  environment: 'Production',
  owner: 'Data Platform',
  riskLevel: 'critical',
  dataClass: 'Restricted',
  drift: 0,
  lastScan: '2026-08-06T22:00:00Z',
  status: 'healthy'
},
{
  id: 'AST-1027',
  name: 'Decision Orchestrator',
  type: 'Pipeline',
  environment: 'Production',
  owner: 'Platform Engineering',
  riskLevel: 'high',
  dataClass: 'Confidential',
  drift: 1.1,
  lastScan: '2026-08-07T03:15:00Z',
  status: 'healthy'
},
{
  id: 'AST-1019',
  name: 'Pinecone / eu-central',
  type: 'Vector Store',
  environment: 'Production',
  owner: 'Data Platform',
  riskLevel: 'medium',
  dataClass: 'Confidential',
  drift: 0,
  lastScan: '2026-08-06T18:40:00Z',
  status: 'healthy'
},
{
  id: 'AST-1014',
  name: 'Vendor Gateway',
  type: 'Endpoint',
  environment: 'Production',
  owner: 'Security Engineering',
  riskLevel: 'high',
  dataClass: 'Internal',
  drift: 0,
  lastScan: '2026-08-05T09:00:00Z',
  status: 'offline'
},
{
  id: 'AST-1009',
  name: 'Marketing Copy Assistant',
  type: 'Agent',
  environment: 'Staging',
  owner: 'Growth Marketing',
  riskLevel: 'medium',
  dataClass: 'Internal',
  drift: 2.4,
  lastScan: '2026-08-04T15:20:00Z',
  status: 'healthy'
},
{
  id: 'AST-1004',
  name: 'Eval Datastore',
  type: 'Dataset',
  environment: 'Development',
  owner: 'AI Governance Office',
  riskLevel: 'low',
  dataClass: 'Internal',
  drift: 0,
  lastScan: '2026-08-03T11:10:00Z',
  status: 'healthy'
},
{
  id: 'AST-0998',
  name: 'Fraud Signals Pipeline',
  type: 'Pipeline',
  environment: 'Production',
  owner: 'Risk Analytics',
  riskLevel: 'medium',
  dataClass: 'Restricted',
  drift: 3.6,
  lastScan: '2026-08-07T02:45:00Z',
  status: 'healthy'
},
{
  id: 'AST-0991',
  name: 'Internal Knowledge Copilot',
  type: 'Agent',
  environment: 'Production',
  owner: 'IT Services',
  riskLevel: 'low',
  dataClass: 'Internal',
  drift: 1.8,
  lastScan: '2026-08-06T20:05:00Z',
  status: 'healthy'
},
{
  id: 'AST-0985',
  name: 'Sentiment Classifier v2',
  type: 'LLM Model',
  environment: 'Staging',
  owner: 'Customer Experience',
  riskLevel: 'info',
  dataClass: 'Public',
  drift: 0.4,
  lastScan: '2026-08-02T09:30:00Z',
  status: 'healthy'
},
{
  id: 'AST-0977',
  name: 'Telemetry Pipeline',
  type: 'Pipeline',
  environment: 'Production',
  owner: 'Platform Engineering',
  riskLevel: 'medium',
  dataClass: 'Confidential',
  drift: 0,
  lastScan: '2026-08-05T07:50:00Z',
  status: 'healthy'
}];


export const assetGrowth = [
{ month: 'Apr', production: 18, staging: 12, development: 22 },
{ month: 'May', production: 21, staging: 14, development: 26 },
{ month: 'Jun', production: 24, staging: 16, development: 31 },
{ month: 'Jul', production: 29, staging: 18, development: 34 },
{ month: 'Aug', production: 34, staging: 21, development: 39 }];