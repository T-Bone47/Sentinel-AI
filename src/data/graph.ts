import type { GraphEdge, GraphNode } from '../types/domain';

/** Coordinates are authored in a 1000 x 640 viewBox space. */
export const graphNodes: GraphNode[] = [
// People / identity column
{ id: 'emp-meyer', label: 'J. Meyer', kind: 'employee', x: 96, y: 132, meta: 'Engineering · privileged' },
{ id: 'emp-bhatt', label: 'R. Bhatt', kind: 'employee', x: 96, y: 260, meta: 'Platform Lead · privileged' },
{ id: 'emp-tanaka', label: 'K. Tanaka', kind: 'employee', x: 96, y: 388, meta: 'Data Governance Lead' },
{ id: 'emp-raman', label: 'P. Raman', kind: 'employee', x: 96, y: 512, meta: 'Support Manager' },

{ id: 'iam-meyer', label: 'AWS Admin', kind: 'iam', x: 258, y: 108, severity: 'critical', meta: 'No MFA · AdministratorAccess' },
{ id: 'iam-deploy', label: 'svc-payments-deploy', kind: 'iam', x: 258, y: 236, severity: 'high', meta: 'Service · s3:*' },
{ id: 'iam-snow', label: 'Snowflake admin', kind: 'iam', x: 258, y: 364, meta: 'Human · MFA enforced' },
{ id: 'iam-support', label: 'Zendesk agent', kind: 'iam', x: 258, y: 500, meta: 'Human · MFA enforced' },

{ id: 'dev-102', label: 'NW-MBP-102', kind: 'device', x: 176, y: 44, severity: 'critical', meta: 'EDR unhealthy' },
{ id: 'dev-007', label: 'NW-LNX-007', kind: 'device', x: 176, y: 324, severity: 'high', meta: 'Patch 41d behind' },

// Applications
{ id: 'app-payments', label: 'payments-api', kind: 'application', x: 430, y: 168, severity: 'critical', meta: 'Critical · financial data' },
{ id: 'app-claims', label: 'Claims Portal', kind: 'application', x: 430, y: 300, meta: 'Critical · sensitive personal' },
{ id: 'app-atlas', label: 'Atlas Support Agent', kind: 'application', x: 430, y: 432, severity: 'medium', meta: 'High · personal data' },
{ id: 'app-snowflake', label: 'Snowflake', kind: 'application', x: 430, y: 552, meta: 'High · confidential' },

// Cloud
{ id: 'cld-bucket', label: 's3://nw-claims-archive', kind: 'cloud', x: 620, y: 96, severity: 'critical', meta: 'Public access enabled' },
{ id: 'cld-vol', label: 'vol-0f2c', kind: 'cloud', x: 620, y: 226, severity: 'high', meta: 'Unencrypted volume' },
{ id: 'cld-rds', label: 'rds/nw-core-prod', kind: 'cloud', x: 620, y: 356, meta: 'Encrypted · logged' },
{ id: 'cld-run', label: 'run/copy-assistant', kind: 'cloud', x: 620, y: 486, severity: 'medium', meta: 'Ingress warning' },

// Vendors
{ id: 'ven-lumenpay', label: 'Lumenpay', kind: 'vendor', x: 792, y: 152, severity: 'high', meta: 'SOC 2 expired' },
{ id: 'ven-vireo', label: 'Vireo Screening', kind: 'vendor', x: 792, y: 286, severity: 'critical', meta: 'Uncertified · biometric data' },
{ id: 'ven-helix', label: 'Helix Analytics', kind: 'vendor', x: 792, y: 420, severity: 'high', meta: 'Consent gap' },

// Governance spine
{ id: 'pol-access', label: 'Access Control Policy', kind: 'policy', x: 366, y: 44, meta: 'v4.2 · published' },
{ id: 'pol-cloud', label: 'Cloud Security Standard', kind: 'policy', x: 700, y: 42, meta: 'v2.1 · published' },
{ id: 'ctl-mfa', label: 'CTL-A.5.17', kind: 'control', x: 500, y: 44, severity: 'high', meta: 'MFA on privileged · failing' },
{ id: 'ctl-dlp', label: 'CTL-A.8.12', kind: 'control', x: 860, y: 60, severity: 'critical', meta: 'Public storage DLP · failing' },
{ id: 'fnd-9012', label: 'FND-9012', kind: 'finding', x: 900, y: 196, severity: 'critical', meta: 'Public bucket exposure' },
{ id: 'fnd-9008', label: 'FND-9008', kind: 'finding', x: 366, y: 596, severity: 'high', meta: '6 identities without MFA' },
{ id: 'ev-8829', label: 'EV-8829', kind: 'evidence', x: 906, y: 330, meta: 'Bucket policy snapshot' },
{ id: 'ev-8836', label: 'EV-8836', kind: 'evidence', x: 528, y: 596, meta: 'MFA enrollment report' }];


export const graphEdges: GraphEdge[] = [
{ from: 'emp-meyer', to: 'iam-meyer', kind: 'risk' },
{ from: 'emp-meyer', to: 'dev-102', kind: 'risk' },
{ from: 'emp-bhatt', to: 'iam-deploy' },
{ from: 'emp-bhatt', to: 'dev-007', kind: 'risk' },
{ from: 'emp-tanaka', to: 'iam-snow' },
{ from: 'emp-raman', to: 'iam-support' },

{ from: 'iam-meyer', to: 'app-payments', kind: 'risk' },
{ from: 'iam-deploy', to: 'app-payments' },
{ from: 'iam-snow', to: 'app-snowflake' },
{ from: 'iam-snow', to: 'app-claims' },
{ from: 'iam-support', to: 'app-atlas' },

{ from: 'app-payments', to: 'cld-vol', kind: 'risk' },
{ from: 'app-payments', to: 'cld-rds' },
{ from: 'app-claims', to: 'cld-bucket', kind: 'risk' },
{ from: 'app-atlas', to: 'cld-run' },
{ from: 'app-snowflake', to: 'cld-rds' },

{ from: 'app-payments', to: 'ven-lumenpay' },
{ from: 'app-claims', to: 'ven-vireo', kind: 'risk' },
{ from: 'app-atlas', to: 'ven-helix', kind: 'risk' },

{ from: 'pol-access', to: 'ctl-mfa' },
{ from: 'pol-cloud', to: 'ctl-dlp' },
{ from: 'ctl-mfa', to: 'iam-meyer', kind: 'risk' },
{ from: 'ctl-mfa', to: 'fnd-9008', kind: 'risk' },
{ from: 'ctl-dlp', to: 'cld-bucket', kind: 'risk' },
{ from: 'ctl-dlp', to: 'fnd-9012', kind: 'risk' },
{ from: 'fnd-9012', to: 'ev-8829' },
{ from: 'fnd-9008', to: 'ev-8836' }];


export const graphLegend: {kind: GraphNode['kind'];label: string;}[] = [
{ kind: 'employee', label: 'Employee' },
{ kind: 'iam', label: 'Identity' },
{ kind: 'device', label: 'Device' },
{ kind: 'application', label: 'Application' },
{ kind: 'cloud', label: 'Cloud asset' },
{ kind: 'vendor', label: 'Vendor' },
{ kind: 'policy', label: 'Policy' },
{ kind: 'control', label: 'Control' },
{ kind: 'finding', label: 'Finding' },
{ kind: 'evidence', label: 'Evidence' }];