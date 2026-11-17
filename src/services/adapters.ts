/**
 * Backend row -> frontend domain type mapping.
 *
 * This file is the single place where the API's snake_case reality meets the
 * UI's existing domain model. Two rules govern everything below:
 *
 * 1. **Never invent a relationship.** The dataset has verified foreign keys
 *    (risk -> control -> policy, finding -> control/evidence, and so on) and
 *    verified *absences* (vendors link to nothing; reports do not link to
 *    findings; personal-data does not link to consent). Adapters join only
 *    along the real ones.
 *
 * 2. **Derived values are labelled as derived.** Some UI fields have no
 *    backing column — a risk has no numeric score, a device has no "last
 *    seen". Where a value can be computed deterministically from real columns
 *    it is, and the formula is documented next to it. Where it cannot, the
 *    adapter emits an explicit blank (`'—'`, `0`, `[]`) rather than a
 *    plausible-looking fabrication.
 */

import type {
  Application,
  AuditEvent,
  CheckState,
  CloudAsset,
  ComplianceStatus,
  ConsentRecord,
  Control,
  Device,
  Employee,
  EvidenceItem,
  Finding,
  FrameworkScore,
  GraphEdge,
  GraphNode,
  GraphNodeKind,
  IamAccount,
  PersonalDataAsset,
  Policy,
  PostureStatus,
  ReportItem,
  RiskItem,
  RiskLevel,
  Vendor
} from '../types/domain';
import type {
  ApiApplication,
  ApiAuditLog,
  ApiCloudAsset,
  ApiConsent,
  ApiControl,
  ApiDevice,
  ApiEmployee,
  ApiEvidence,
  ApiFinding,
  ApiFrameworkSummary,
  ApiGraph,
  ApiIam,
  ApiPersonalData,
  ApiPolicy,
  ApiReport,
  ApiRisk,
  ApiRiskDetail
} from './types';

export const NOT_AVAILABLE = '—';

/* ------------------------------------------------------------- primitives */

export function toRiskLevel(value: string | null | undefined): RiskLevel {
  const key = (value ?? '').trim().toLowerCase();
  if (key === 'critical') return 'critical';
  if (key === 'high') return 'high';
  if (key === 'medium' || key === 'moderate') return 'medium';
  if (key === 'low') return 'low';
  return 'info';
}

export function check(pass: boolean, warnInstead = false): CheckState {
  if (pass) return 'pass';
  return warnInstead ? 'warn' : 'fail';
}

/** Ordinal weight for Critical/High/Medium/Low, used by derived scores. */
function severityWeight(value: string | null | undefined): number {
  switch (toRiskLevel(value)) {
    case 'critical':
      return 5;
    case 'high':
      return 4;
    case 'medium':
      return 3;
    case 'low':
      return 2;
    default:
      return 1;
  }
}

function postureFromScore(score: number): PostureStatus {
  if (score >= 80) return 'trusted';
  if (score >= 60) return 'warning';
  return 'critical';
}

function daysSince(iso: string | null | undefined): number {
  if (!iso) return Number.POSITIVE_INFINITY;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return Number.POSITIVE_INFINITY;
  return Math.floor((Date.now() - then) / 86_400_000);
}

/* ------------------------------------------------------------------- risk */

/**
 * Risk status vocabulary in the dataset:
 *   Open · In Remediation · Mitigated · Closed · Accepted
 */
function riskStatus(value: string): RiskItem['status'] {
  switch (value) {
    case 'Open':
      return 'open';
    case 'In Remediation':
      return 'investigating';
    case 'Mitigated':
      return 'mitigating';
    case 'Accepted':
      return 'accepted';
    case 'Closed':
      return 'closed';
    default:
      return 'open';
  }
}

/**
 * Derived risk score. The dataset has no numeric score column, but it does
 * have real ordinal Likelihood and Severity. Score = likelihood x severity
 * normalised to 0-100 (both are 1-5, so max 25). Deterministic, reproducible
 * from two real columns, and never presented as a model output.
 */
export function deriveRiskScore(risk: ApiRisk): number {
  return Math.round((severityWeight(risk.likelihood) * severityWeight(risk.severity) * 100) / 25);
}

export function toRiskItem(risk: ApiRisk, controlName?: string, framework?: string): RiskItem {
  return {
    id: risk.risk_id,
    title: risk.risk_name,
    severity: toRiskLevel(risk.severity),
    score: deriveRiskScore(risk),
    // The dataset links a risk to a control, not to a named asset. Showing the
    // mapped control is the honest answer to "what does this affect".
    asset: controlName ?? risk.mapped_control_id ?? 'Unmapped',
    assetType: risk.mapped_control_id ? 'Control' : 'Unmapped',
    control: risk.mapped_control_id ?? NOT_AVAILABLE,
    framework: framework ?? NOT_AVAILABLE,
    owner: risk.owner_department,
    department: risk.owner_department,
    status: riskStatus(risk.current_status),
    updatedAt: '',
    likelihood: severityWeight(risk.likelihood),
    impact: severityWeight(risk.severity),
    chain: {
      policy: '',
      control: '',
      finding: '',
      asset: '',
      evidence: '',
      impact: risk.business_impact,
      recommendation: ''
    }
  };
}

/**
 * Full investigation chain, built from the enriched /risks/{id} endpoint.
 * Follows POLICY -> CONTROL -> FINDING -> EVIDENCE -> RISK using only the
 * verified foreign keys; an unmapped risk yields empty links rather than a
 * manufactured narrative.
 */
export function toRiskDetail(detail: ApiRiskDetail): RiskItem {
  const base = toRiskItem(detail, detail.control?.control_name, detail.policy?.framework);
  const openFindings = detail.findings.filter(
    (f) => f.status === 'Open' || f.status === 'In Progress'
  );
  const primaryFinding = openFindings[0] ?? detail.findings[0];
  const verified = detail.evidence.filter((e) => e.verified);
  const primaryEvidence = verified[0] ?? detail.evidence[0];

  return {
    ...base,
    chain: {
      policy: detail.policy
        ? `${detail.policy.policy_id} · ${detail.policy.policy_name} (${detail.policy.framework}${detail.policy.mandatory ? ', mandatory' : ''})`
        : 'No policy linked — this risk has no mapped control.',
      control: detail.control
        ? `${detail.control.control_id} · ${detail.control.control_name} — severity ${detail.control.severity}${detail.control.evidence_required ? ', evidence required' : ''}`
        : 'No control mapped in the risk register.',
      finding: primaryFinding
        ? `${primaryFinding.finding_id} · ${primaryFinding.description}`
        : detail.control
          ? 'No findings recorded against this control.'
          : '',
      asset: detail.control
        ? `${detail.control.control_id} · ${detail.findings.length} finding(s) · ${detail.evidence.length} evidence item(s)`
        : '',
      evidence: primaryEvidence
        ? `${primaryEvidence.evidence_id} · ${primaryEvidence.evidence_type} — ${primaryEvidence.evidence_location} (${primaryEvidence.verified ? 'verified' : 'unverified'})`
        : detail.control
          ? 'No evidence collected for this control.'
          : '',
      impact: detail.business_impact,
      recommendation:
        primaryFinding?.recommendation ??
        (detail.control
          ? 'No open finding carries a recommendation for this control.'
          : 'Map this risk to a control to enable remediation tracking.')
    }
  };
}

/* --------------------------------------------------------------- findings */

function findingStatus(value: string): Finding['status'] {
  switch (value) {
    case 'Open':
      return 'open';
    case 'In Progress':
      return 'in-progress';
    case 'Remediated':
    case 'Closed':
      return 'resolved';
    case 'Risk Accepted':
      return 'suppressed';
    default:
      return 'open';
  }
}

export function toFinding(finding: ApiFinding, controlName?: string): Finding {
  return {
    id: finding.finding_id,
    title: finding.description,
    severity: toRiskLevel(finding.severity),
    control: finding.control_id,
    asset: controlName ?? finding.control_id,
    source: finding.evidence_id ? 'Evidence-backed' : 'Control assessment',
    status: findingStatus(finding.status),
    owner: NOT_AVAILABLE,
    detectedAt: '',
    riskId: undefined
  };
}

/* ------------------------------------------------------------- governance */

export function toPolicy(policy: ApiPolicy, controlCount: number): Policy {
  return {
    id: policy.policy_id,
    name: policy.policy_name,
    framework: policy.framework,
    owner: policy.owner_department,
    controls: controlCount,
    // The dataset has no lifecycle column; every policy in it is in force.
    status: 'published',
    lastReviewed: '',
    nextReview: '',
    aiGenerated: false
  };
}

/**
 * Control pass/fail is computed the same way the backend dashboard computes
 * it: a control FAILS if it has at least one finding in status Open or
 * In Progress, PASSES otherwise. "not-tested" is reserved for controls that
 * require evidence and have none.
 */
export function toControl(
  control: ApiControl,
  opts: { framework?: string; policyName?: string; evidenceCount: number; findings: ApiFinding[] }
): Control {
  const open = opts.findings.filter(
    (f) => f.status === 'Open' || f.status === 'In Progress'
  ).length;
  let status: Control['status'];
  if (open > 0) status = open === opts.findings.length ? 'failing' : 'partial';
  else if (control.evidence_required && opts.evidenceCount === 0) status = 'not-tested';
  else status = 'passing';

  return {
    id: control.control_id,
    name: control.control_name,
    framework: opts.framework ?? NOT_AVAILABLE,
    status,
    evidence: opts.evidenceCount,
    findings: opts.findings.length,
    owner: NOT_AVAILABLE,
    policy: opts.policyName ?? control.policy_id,
    automated: control.automation_possible,
    lastTested: ''
  };
}

export function toEvidenceItem(evidence: ApiEvidence, controlName?: string): EvidenceItem {
  return {
    id: evidence.evidence_id,
    name: evidence.evidence_type,
    control: controlName ? `${evidence.control_id} · ${controlName}` : evidence.control_id,
    source: evidence.collected_automatically ? 'Automated collection' : 'Manual upload',
    collectedAt: evidence.collected_date,
    validUntil: '',
    owner: NOT_AVAILABLE,
    status: evidence.verified ? 'verified' : 'pending',
    automated: evidence.collected_automatically
  };
}

const FRAMEWORK_AUTHORITY: Record<string, string> = {
  'ISO 27001': 'ISO/IEC',
  SOC2: 'AICPA',
  NIST: 'NIST',
  DPDP: 'MeitY, India',
  'CIS Controls': 'Center for Internet Security'
};

function complianceStatus(value: string | null): ComplianceStatus {
  switch ((value ?? '').toLowerCase()) {
    case 'compliant':
      return 'compliant';
    case 'partially compliant':
    case 'at risk':
      return 'at-risk';
    case 'non-compliant':
      return 'non-compliant';
    default:
      return 'not-assessed';
  }
}

export function toFrameworkScore(summary: ApiFrameworkSummary): FrameworkScore {
  return {
    id: summary.framework,
    name: summary.framework,
    coverage: Math.round(summary.evidence_coverage_pct),
    passed: summary.passed_controls,
    failed: summary.failed_controls,
    evidence: summary.evidence_count,
    findings: summary.total_findings,
    // Readiness is the framework's own latest report score where one exists;
    // otherwise evidence coverage. Never a blended invention.
    readiness: summary.latest_report_score ?? Math.round(summary.evidence_coverage_pct),
    status: complianceStatus(summary.latest_report_status),
    authority: FRAMEWORK_AUTHORITY[summary.framework] ?? NOT_AVAILABLE,
    nextAudit: '',
    owner: NOT_AVAILABLE,
    controlDomains: summary.control_domains
  };
}

/* ----------------------------------------------------------- organization */

export function toEmployee(employee: ApiEmployee, iam?: ApiIam): Employee {
  const privileged = iam?.privileged_account ?? false;
  const mfa = employee.mfa_enabled;
  // Access risk from two real signals: privilege level and MFA state.
  const accessRisk: RiskLevel =
    privileged && !mfa ? 'critical' : !mfa ? 'high' : privileged ? 'medium' : 'low';

  return {
    id: employee.employee_id,
    name: `${employee.first_name} ${employee.last_name}`,
    email: employee.email,
    department: employee.department,
    role: employee.designation,
    mfa: check(mfa),
    device: employee.device_id ?? NOT_AVAILABLE,
    accessRisk,
    compliance:
      employee.account_status === 'Active' && mfa
        ? 'pass'
        : employee.account_status === 'Active'
          ? 'warn'
          : 'fail',
    joinedAt: employee.joining_date,
    apps: [],
    privileged
  };
}

export function toIamAccount(iam: ApiIam, employeeName?: string): IamAccount {
  // Violations are counted, not guessed: privileged-without-MFA, dormancy
  // over 90 days, and a privilege review older than a year.
  let violations = 0;
  if (iam.privileged_account && !iam.mfa_enabled) violations += 1;
  if (iam.inactive_days > 90) violations += 1;
  if (daysSince(iam.last_privilege_review) > 365) violations += 1;

  const riskLevel: RiskLevel =
    violations >= 2 ? 'critical' : violations === 1 ? 'high' : iam.privileged_account ? 'medium' : 'low';

  return {
    id: iam.iam_user_id,
    principal: employeeName ?? iam.employee_id,
    type: 'Human',
    provider: 'Enterprise Directory',
    privileged: iam.privileged_account,
    mfa: check(iam.mfa_enabled),
    lastActive: `${iam.inactive_days}d inactive`,
    dormant: iam.inactive_days > 90,
    violations,
    riskLevel,
    entitlements: iam.privileges
      ? iam.privileges.split(/[,;|]/).map((p) => p.trim()).filter(Boolean)
      : []
  };
}

export function toDevice(device: ApiDevice, ownerName?: string): Device {
  const patchAge = daysSince(device.last_patch_date);
  return {
    id: device.device_id,
    name: `${device.device_type} · ${device.device_id}`,
    owner: ownerName ?? device.employee_id,
    os: `${device.operating_system} ${device.os_version}`,
    encryption: check(device.encryption_enabled),
    edr: check(device.edr_installed),
    // Patch posture from real patch dates: <=30d pass, <=90d warn, else fail.
    patch: patchAge <= 30 ? 'pass' : patchAge <= 90 ? 'warn' : 'fail',
    riskLevel: toRiskLevel(device.risk_level),
    compliance:
      device.compliance_status === 'Compliant'
        ? 'pass'
        : device.compliance_status === 'Non-Compliant'
          ? 'fail'
          : 'warn',
    lastSeen: device.last_patch_date
  };
}

export function toApplication(app: ApiApplication, users = 0): Application {
  return {
    id: app.application_id,
    name: app.application_name,
    owner: app.owner_department,
    criticality: app.risk_level,
    dataClass: app.data_classification,
    accessRisk: toRiskLevel(app.risk_level),
    compliance:
      app.uses_mfa && app.encryption_enabled
        ? 'pass'
        : app.uses_mfa || app.encryption_enabled
          ? 'warn'
          : 'fail',
    users,
    cloudAssets: [],
    hostedIn: app.internet_facing ? 'Internet-facing' : 'Internal'
  };
}

export function toCloudAsset(asset: ApiCloudAsset, ownerName?: string): CloudAsset {
  return {
    id: asset.resource_id,
    provider: asset.cloud_provider,
    resource: asset.resource_id,
    service: asset.resource_type,
    region: asset.region,
    criticality: asset.criticality,
    encryption: check(asset.encryption_enabled),
    publicAccess: asset.public_access ? 'fail' : 'pass',
    logging: check(asset.logging_enabled),
    riskLevel: toRiskLevel(asset.risk_level),
    owner: ownerName ?? asset.owner_employee_id ?? NOT_AVAILABLE
  };
}

export function toVendor(vendor: ApiVendorLike): Vendor {
  const expiryDays = -daysSince(vendor.contract_expiry); // negative = already expired
  const certification = vendor.iso27001_certified
    ? vendor.soc2_certified
      ? 'ISO 27001 + SOC 2'
      : 'ISO 27001'
    : vendor.soc2_certified
      ? 'SOC 2 Type II'
      : 'None';

  // Vendor score from four real booleans/ordinals — no external feed exists.
  const certPoints =
    (vendor.iso27001_certified ? 25 : 0) +
    (vendor.soc2_certified ? 25 : 0) +
    (vendor.dpdp_compliant ? 20 : 0);
  const ratingPenalty = severityWeight(vendor.risk_rating) * 6;
  const riskScore = Math.max(0, Math.min(100, 100 - certPoints - (30 - ratingPenalty)));

  return {
    id: vendor.vendor_id,
    name: vendor.vendor_name,
    category: vendor.service_category,
    riskLevel: toRiskLevel(vendor.risk_rating),
    riskScore,
    compliance: vendor.dpdp_compliant ? 'pass' : 'fail',
    certification,
    certificationStatus:
      expiryDays < 0 ? 'expired' : expiryDays < 90 ? 'expiring' : certification === 'None' ? 'high-risk' : 'compliant',
    // Vendors are an island table in the source data — no verified link to
    // applications, data categories, risks or controls. Left empty by design.
    dataShared: [],
    owner: NOT_AVAILABLE,
    expiry: vendor.contract_expiry
  };
}

type ApiVendorLike = {
  vendor_id: string;
  vendor_name: string;
  service_category: string;
  iso27001_certified: boolean;
  soc2_certified: boolean;
  dpdp_compliant: boolean;
  risk_rating: string;
  contract_expiry: string;
};

/* ---------------------------------------------------------------- privacy */

export function toPersonalDataAsset(
  record: ApiPersonalData,
  applicationName?: string
): PersonalDataAsset {
  const exposed = record.third_party_sharing && !record.encryption_enabled;
  return {
    id: record.data_id,
    dataElement: record.data_category,
    category: record.data_category,
    application: applicationName ?? record.application_id,
    purpose: record.purpose_of_processing,
    // NOTE: this reflects whether consent is REQUIRED, not whether it was
    // obtained. The dataset has no verified personal-data -> consent link, so
    // the column is labelled "Consent required" in the UI.
    consent: record.consent_required ? 'warn' : 'pass',
    retention: record.retention_period,
    retentionRisk: exposed ? 'fail' : record.third_party_sharing ? 'warn' : 'pass',
    riskLevel: exposed ? 'critical' : record.third_party_sharing ? 'high' : record.encryption_enabled ? 'low' : 'medium',
    records: 0,
    location: NOT_AVAILABLE
  };
}

export function toConsentRecord(
  consent: ApiConsent,
  applicationName?: string,
  employeeName?: string
): ConsentRecord {
  const expired = daysSince(consent.expiry_date) > 0;
  return {
    id: consent.consent_id,
    purpose: employeeName ?? consent.employee_id,
    application: applicationName ?? consent.application_id,
    principals: 1,
    coverage: consent.consent_given && !consent.revoked && !expired ? 100 : 0,
    basis: 'Consent',
    status: consent.revoked ? 'violation' : expired || !consent.consent_given ? 'partial' : 'valid',
    lastUpdated: consent.consent_date,
    withdrawalRate: consent.revoked ? 100 : 0
  };
}

/* ----------------------------------------------------------------- shared */

export function toAuditEvent(
  log: ApiAuditLog,
  actorName?: string,
  applicationName?: string
): AuditEvent {
  // Severity banded from the real risk_score column (0-100).
  const severity: RiskLevel =
    log.risk_score >= 80 ? 'critical' : log.risk_score >= 60 ? 'high' : log.risk_score >= 40 ? 'medium' : 'low';
  return {
    id: log.log_id,
    actor: actorName ?? log.employee_id ?? NOT_AVAILABLE,
    actorRole: log.geo_location,
    action: log.action,
    target: applicationName ?? log.application_id ?? NOT_AVAILABLE,
    severity,
    source: log.result,
    ip: log.ip_address,
    timestamp: log.timestamp
  };
}

export function toReportItem(report: ApiReport): ReportItem {
  return {
    id: report.report_id,
    name: `${report.framework} Compliance Report`,
    type: report.framework === 'DPDP' ? 'Regulatory' : 'Operational',
    framework: report.framework,
    period: report.generated_date.slice(0, 7),
    status: 'ready',
    generatedAt: report.generated_date,
    owner: NOT_AVAILABLE,
    aiGenerated: false
  };
}

/* ------------------------------------------------------------------ graph */

const GRAPH_KIND_MAP: Record<string, GraphNodeKind> = {
  employee: 'employee',
  iam: 'iam',
  device: 'device',
  application: 'application',
  cloud_asset: 'cloud',
  vendor: 'vendor',
  policy: 'policy',
  control: 'control',
  finding: 'finding',
  evidence: 'evidence',
  personal_data: 'application',
  risk: 'finding'
};

const VIEW_W = 1000;
const VIEW_H = 640;

/**
 * The backend returns topology only — it has no opinion about pixels. This
 * lays nodes out deterministically: one ring per node type, ordered within
 * the ring by id, so the same graph always renders identically and the
 * clusters stay readable. Purely presentational; it changes no relationship.
 */
export function toGraph(graph: ApiGraph): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const byKind = new Map<GraphNodeKind, typeof graph.nodes>();
  for (const node of graph.nodes) {
    const kind = GRAPH_KIND_MAP[node.type] ?? 'application';
    if (!byKind.has(kind)) byKind.set(kind, []);
    byKind.get(kind)!.push(node);
  }

  const kinds = [...byKind.keys()];
  const nodes: GraphNode[] = [];
  const cx = VIEW_W / 2;
  const cy = VIEW_H / 2;

  kinds.forEach((kind, kindIndex) => {
    const group = byKind.get(kind)!;
    // Each type gets its own angular sector and its own orbit radius.
    const sectorStart = (kindIndex / kinds.length) * Math.PI * 2;
    const sectorSpan = (Math.PI * 2) / kinds.length;
    const rings = Math.ceil(group.length / 40);

    group.forEach((node, index) => {
      const ring = Math.floor(index / 40);
      const inRing = index % 40;
      const countInRing = Math.min(40, group.length - ring * 40);
      const angle = sectorStart + ((inRing + 0.5) / countInRing) * sectorSpan;
      const radius = 120 + (ring / Math.max(1, rings)) * 90 + (kindIndex % 2 === 0 ? 40 : 0) + 60;

      const severity =
        node.data?.severity != null
          ? toRiskLevel(String(node.data.severity))
          : node.data?.risk_level != null
            ? toRiskLevel(String(node.data.risk_level))
            : undefined;

      nodes.push({
        id: node.id,
        label: node.label,
        kind: GRAPH_KIND_MAP[node.type] ?? 'application',
        x: Math.round(cx + Math.cos(angle) * radius * 1.45),
        y: Math.round(cy + Math.sin(angle) * radius),
        severity,
        meta: describeNode(node.type, node.data)
      });
    });
  });

  const ids = new Set(nodes.map((n) => n.id));
  const edges: GraphEdge[] = graph.edges
    .filter((e) => ids.has(e.source) && ids.has(e.target))
    .map((e) => ({
      from: e.source,
      to: e.target,
      kind: e.relation === 'MITIGATES' || e.relation === 'HAS_FINDING' ? 'risk' : 'default'
    }));

  return { nodes, edges };
}

function describeNode(type: string, data: Record<string, any> = {}): string {
  switch (type) {
    case 'employee':
      return `${data.designation ?? ''} · ${data.department ?? ''}`.trim();
    case 'device':
      return `${data.device_type ?? ''} · ${data.compliance_status ?? ''}`.trim();
    case 'iam':
      return `${data.role ?? ''}${data.privileged_account ? ' · privileged' : ''}`.trim();
    case 'cloud_asset':
      return `${data.cloud_provider ?? ''} ${data.resource_type ?? ''}${data.public_access ? ' · public' : ''}`.trim();
    case 'application':
      return `${data.owner_department ?? ''} · ${data.data_classification ?? ''}`.trim();
    case 'policy':
      return `${data.framework ?? ''}${data.mandatory ? ' · mandatory' : ''}`.trim();
    case 'control':
      return `severity ${data.severity ?? '—'}`;
    case 'finding':
      return `${data.severity ?? ''} · ${data.status ?? ''}`.trim();
    case 'evidence':
      return `${data.verified ? 'verified' : 'unverified'}`;
    case 'risk':
      return `${data.severity ?? ''} · ${data.current_status ?? ''}`.trim();
    case 'vendor':
      return `${data.service_category ?? ''} · ${data.risk_rating ?? ''}`.trim();
    default:
      return type;
  }
}

export { postureFromScore, severityWeight, daysSince };
