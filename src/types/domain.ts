export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type TrendDirection = 'up' | 'down' | 'flat';

export type PostureStatus = 'trusted' | 'warning' | 'critical';

export type ComplianceStatus =
'compliant' |
'at-risk' |
'non-compliant' |
'not-assessed';

export type PolicyStatus = 'published' | 'in-review' | 'draft' | 'archived';

/* ------------------------------------------------------------------ trust */

export interface TrustDomain {
  id: string;
  label: string;
  score: number;
  delta: number;
  status: PostureStatus;
  detail: string;
}

export interface Kpi {
  id: string;
  label: string;
  value: number;
  suffix?: string;
  prefix?: string;
  delta: number;
  direction: TrendDirection;
  positiveIsGood: boolean;
  caption: string;
  status: PostureStatus;
  spark: number[];
}

export interface StreamEvent {
  id: string;
  time: string;
  severity: RiskLevel;
  title: string;
  source: string;
}

export interface FrameworkScore {
  id: string;
  name: string;
  coverage: number;
  passed: number;
  failed: number;
  evidence: number;
  findings: number;
  readiness: number;
  status: ComplianceStatus;
  authority: string;
  nextAudit: string;
  owner: string;
  controlDomains?: Array<{ domain: string; passing: number; failing: number }>;
}

export interface Framework {
  id: string;
  name: string;
  shortName: string;
  authority: string;
  coverage: number;
  controlsTotal: number;
  controlsPassing: number;
  controlsFailing: number;
  status: string;
  nextAudit: string;
  owner: string;
}

export interface Incident {
  id: string;
  title: string;
  level: string;
  system: string;
  openedAt: string;
  status: string;
  assignee: string;
}

/* ------------------------------------------------------------------- risk */

export interface RiskItem {
  id: string;
  title: string;
  severity: RiskLevel;
  score: number;
  asset: string;
  assetType: string;
  control: string;
  framework: string;
  owner: string;
  department: string;
  status: 'open' | 'investigating' | 'mitigating' | 'accepted' | 'closed';
  updatedAt: string;
  likelihood: number;
  impact: number;
  /** Optional: Phase 1 has no model, so real data leaves this undefined. */
  aiConfidence?: number;
  /** Investigation chain rendered in the investigation workspace. */
  chain: {
    policy: string;
    control: string;
    finding: string;
    asset: string;
    evidence: string;
    impact: string;
    recommendation: string;
  };
}

export interface Finding {
  id: string;
  title: string;
  severity: RiskLevel;
  control: string;
  asset: string;
  /** Widened from a fixed union: the real dataset has no detection-source column. */
  source: string;
  status: 'open' | 'in-progress' | 'resolved' | 'suppressed';
  owner: string;
  detectedAt: string;
  riskId?: string;
}

/* -------------------------------------------------------------- governance */

export interface Policy {
  id: string;
  name: string;
  framework: string;
  owner: string;
  controls?: number;
  status: PolicyStatus;
  lastReviewed: string;
  nextReview: string;
  aiGenerated: boolean;
}

export interface Control {
  id: string;
  name: string;
  framework: string;
  status: 'passing' | 'failing' | 'partial' | 'not-tested';
  evidence: number;
  findings: number;
  owner: string;
  policy: string;
  automated: boolean;
  lastTested: string;
}

export interface EvidenceItem {
  id: string;
  name: string;
  control: string;
  source: string;
  collectedAt: string;
  validUntil: string;
  owner: string;
  status: 'verified' | 'pending' | 'expiring' | 'expired';
  automated: boolean;
}

/* ------------------------------------------------------------ organization */

export type CheckState = 'pass' | 'warn' | 'fail';

export interface Employee {
  id: string;
  name: string;
  email: string;
  department: string;
  role: string;
  mfa: CheckState;
  device: string;
  accessRisk: RiskLevel;
  compliance: CheckState;
  joinedAt: string;
  apps: string[];
  privileged: boolean;
}

export interface IamAccount {
  id: string;
  principal: string;
  type: 'Human' | 'Service' | 'Contractor';
  provider: string;
  privileged: boolean;
  mfa: CheckState;
  lastActive: string;
  dormant: boolean;
  violations: number;
  riskLevel: RiskLevel;
  entitlements: string[];
}

export interface Device {
  id: string;
  name: string;
  owner: string;
  os: string;
  encryption: CheckState;
  edr: CheckState;
  patch: CheckState;
  riskLevel: RiskLevel;
  compliance: CheckState;
  lastSeen: string;
}

export interface Application {
  id: string;
  name: string;
  owner: string;
  criticality: string;
  /** Widened: data_classification is free-text in the source dataset. */
  dataClass: string;
  accessRisk: RiskLevel;
  compliance: CheckState;
  users: number;
  cloudAssets: string[];
  hostedIn: string;
}

export interface CloudAsset {
  id: string;
  provider: string;
  resource: string;
  service: string;
  region: string;
  criticality: string;
  encryption: CheckState;
  publicAccess: CheckState;
  logging: CheckState;
  riskLevel: RiskLevel;
  owner: string;
}

export interface Vendor {
  id: string;
  name: string;
  category: string;
  riskLevel: RiskLevel;
  riskScore: number;
  compliance: CheckState;
  certification: string;
  certificationStatus: 'compliant' | 'expiring' | 'expired' | 'high-risk';
  dataShared: string[];
  owner: string;
  expiry: string;
}

/* ---------------------------------------------------------------- privacy */

export interface PersonalDataAsset {
  id: string;
  dataElement: string;
  category: string;
  application: string;
  purpose: string;
  consent: CheckState;
  retention: string;
  retentionRisk: CheckState;
  riskLevel: RiskLevel;
  records: number;
  location: string;
}

export interface ConsentRecord {
  id: string;
  purpose: string;
  application: string;
  principals: number;
  coverage: number;
  basis: string;
  status: 'valid' | 'partial' | 'violation';
  lastUpdated: string;
  withdrawalRate: number;
}

/* ----------------------------------------------------------------- shared */

export interface AuditEvent {
  id: string;
  actor: string;
  actorRole: string;
  action: string;
  target: string;
  severity: RiskLevel;
  /** Widened: real logs carry a result/outcome, not a fixed channel enum. */
  source: string;
  ip: string;
  timestamp: string;
}

export interface ReportItem {
  id: string;
  name: string;
  type: string;
  framework: string;
  period: string;
  status: 'ready' | 'generating' | 'scheduled' | 'failed';
  generatedAt: string;
  owner: string;
  aiGenerated: boolean;
}

export interface AiInsight {
  id: string;
  title: string;
  summary: string;
  confidence: number;
  impact: RiskLevel;
  category: 'Prediction' | 'Recommendation' | 'Anomaly' | 'Policy Draft';
  createdAt: string;
}

export interface NotificationItem {
  id: string;
  title: string;
  body: string;
  kind: 'risk' | 'compliance' | 'ai' | 'system';
  read: boolean;
  createdAt: string;
}

export type GraphNodeKind =
'employee' |
'iam' |
'device' |
'application' |
'cloud' |
'vendor' |
'policy' |
'control' |
'finding' |
'evidence';

export interface GraphNode {
  id: string;
  label: string;
  kind: GraphNodeKind;
  x: number;
  y: number;
  severity?: RiskLevel;
  meta: string;
}

export interface GraphEdge {
  from: string;
  to: string;
  kind?: 'risk' | 'default';
}

export interface AssetRecord {
  id: string;
  name: string;
  type: string;
  environment: string;
  owner: string;
  riskLevel: RiskLevel;
  dataClass?: string;
  drift?: number;
  lastScan?: string;
  status?: string;
  controls?: number;
}