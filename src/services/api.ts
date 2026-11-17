/**
 * Sentinel AI frontend API client.
 *
 * One function per screen's data need. Where a screen needs data the backend
 * does not pre-join (a control's framework lives on its policy; a device's
 * owner name lives on the employee row), the join happens here against the
 * small reference tables rather than in the component — the backend is not
 * modified to add endpoints it does not need.
 *
 * Nothing in this file falls back to seed data. If the backend is down, these
 * throw and the calling screen renders a connection state. See http.ts.
 */

import {
  getAll,
  getList,
  getOne,
  getRaw,
  post,
  tokenStore,
  type Paged,
  type QueryParams
} from './http';
import * as map from './adapters';
import type {
  ApiApplication,
  ApiApplicationDetail,
  ApiAuditLog,
  ApiCloudAsset,
  ApiConsent,
  ApiControl,
  ApiControlDetail,
  ApiDashboard,
  ApiDevice,
  ApiEmployee,
  ApiEmployeeDetail,
  ApiEvidence,
  ApiEvidenceDetail,
  ApiFinding,
  ApiFindingDetail,
  ApiFrameworkSummary,
  ApiGraph,
  ApiIam,
  ApiLoginResponse,
  ApiPersonalData,
  ApiPolicy,
  ApiPolicyDetail,
  ApiReport,
  ApiRisk,
  ApiRiskDetail,
  ApiUser,
  ApiVendor
} from './types';
import type {
  Application,
  AuditEvent,
  CloudAsset,
  ConsentRecord,
  Control,
  Device,
  Employee,
  EvidenceItem,
  Finding,
  FrameworkScore,
  GraphEdge,
  GraphNode,
  IamAccount,
  PersonalDataAsset,
  Policy,
  ReportItem,
  RiskItem,
  Vendor
} from '../types/domain';

/** Page size used when a screen filters client-side over a small table. */
const FULL = 200;

/* ------------------------------------------------------------ reference */

let employeeNameCache: Map<string, string> | null = null;
let applicationNameCache: Map<string, string> | null = null;

async function employeeNames(): Promise<Map<string, string>> {
  if (employeeNameCache) return employeeNameCache;
  const rows = await getAll<ApiEmployee>('/employees');
  employeeNameCache = new Map(
    rows.map((e) => [e.employee_id, `${e.first_name} ${e.last_name}`])
  );
  return employeeNameCache;
}

async function applicationNames(): Promise<Map<string, string>> {
  if (applicationNameCache) return applicationNameCache;
  const rows = await getAll<ApiApplication>('/applications');
  applicationNameCache = new Map(rows.map((a) => [a.application_id, a.application_name]));
  return applicationNameCache;
}

/** Clear memoised lookups — call on logout or after a data reload. */
export function resetReferenceCache() {
  employeeNameCache = null;
  applicationNameCache = null;
}

/* ------------------------------------------------------------ system */

export async function getHealthStatus() {
  return getRaw<{ status: string; service: string; version: string }>('/health');
}

/* ------------------------------------------------------------ dashboard */

export interface ScoreComponent {
  id: string;
  label: string;
  ratio: number;
  weight: number;
  points: number;
}

export interface DashboardView {
  raw: ApiDashboard;
  trustScore: {
    value: number | null;
    max: number;
    band: string;
    engine: string;
    formula: string;
    note: string;
    components: ScoreComponent[];
  };
  auditReadiness: {
    value: number | null;
    engine: string;
    components: ScoreComponent[];
  };
  frameworkScores: FrameworkScore[];
}

const COMPONENT_LABELS: Record<string, string> = {
  control_evidence_coverage: 'Control evidence coverage',
  finding_health: 'Finding health',
  risk_health: 'Risk health',
  asset_hygiene: 'Asset hygiene',
  identity_hygiene: 'Identity hygiene',
  evidence_coverage: 'Evidence coverage',
  evidence_verification: 'Evidence verification',
  mandatory_control_coverage: 'Mandatory control coverage',
  severe_finding_health: 'Critical/high finding health'
};

function scoreComponents(score: {
  components?: Record<string, number>;
  weights?: Record<string, number>;
}): ScoreComponent[] {
  const components = score.components ?? {};
  const weights = score.weights ?? {};
  return Object.entries(components)
    .map(([id, ratio]) => ({
      id,
      label: COMPONENT_LABELS[id] ?? id.replace(/_/g, ' '),
      ratio,
      weight: weights[id] ?? 0,
      points: Math.round(ratio * (weights[id] ?? 0) * 100 * 10) / 10
    }))
    .sort((a, b) => b.points - a.points);
}

function band(value: number | null): string {
  if (value === null) return 'PENDING';
  if (value >= 85) return 'STRONG';
  if (value >= 70) return 'GOOD';
  if (value >= 55) return 'FAIR';
  return 'AT RISK';
}

export async function getDashboard(): Promise<DashboardView> {
  const raw = await getRaw<ApiDashboard>('/dashboard');
  return {
    raw,
    trustScore: {
      value: raw.trust_score.value,
      max: 100,
      band: band(raw.trust_score.value),
      engine: raw.trust_score.engine ?? 'unknown',
      formula: raw.trust_score.formula ?? '',
      note: raw.trust_score.note ?? raw.trust_score.status ?? '',
      components: scoreComponents(raw.trust_score)
    },
    auditReadiness: {
      value: raw.audit_readiness.value,
      engine: raw.audit_readiness.engine ?? 'unknown',
      components: scoreComponents(raw.audit_readiness)
    },
    frameworkScores: (raw.framework_status ?? []).map(map.toFrameworkScore)
  };
}

/* ----------------------------------------------------------------- risk */

export async function getRisks(params?: QueryParams): Promise<Paged<RiskItem>> {
  const [page, controls, policies] = await Promise.all([
    getList<ApiRisk>('/risks', { page_size: FULL, ...params }),
    getAll<ApiControl>('/controls'),
    getAll<ApiPolicy>('/policies')
  ]);
  const controlById = new Map(controls.map((c) => [c.control_id, c]));
  const policyById = new Map(policies.map((p) => [p.policy_id, p]));

  return {
    meta: page.meta,
    data: page.data.map((risk) => {
      const control = risk.mapped_control_id ? controlById.get(risk.mapped_control_id) : undefined;
      const policy = control ? policyById.get(control.policy_id) : undefined;
      return map.toRiskItem(risk, control?.control_name, policy?.framework);
    })
  };
}

export async function getRisk(id: string): Promise<{ item: RiskItem; detail: ApiRiskDetail }> {
  const detail = await getOne<ApiRiskDetail>('/risks', id);
  return { item: map.toRiskDetail(detail), detail };
}

/* ------------------------------------------------------------- findings */

export async function getFindings(params?: QueryParams): Promise<Paged<Finding>> {
  const [page, controls] = await Promise.all([
    getList<ApiFinding>('/findings', { page_size: FULL, ...params }),
    getAll<ApiControl>('/controls')
  ]);
  const controlById = new Map(controls.map((c) => [c.control_id, c]));
  return {
    meta: page.meta,
    data: page.data.map((f) => map.toFinding(f, controlById.get(f.control_id)?.control_name))
  };
}

export async function getFinding(id: string) {
  return getOne<ApiFindingDetail>('/findings', id);
}

/* ----------------------------------------------------------- governance */

export async function getPolicies(params?: QueryParams): Promise<Paged<Policy>> {
  const [page, controls] = await Promise.all([
    getList<ApiPolicy>('/policies', { page_size: FULL, ...params }),
    getAll<ApiControl>('/controls')
  ]);
  const counts = new Map<string, number>();
  for (const control of controls) {
    counts.set(control.policy_id, (counts.get(control.policy_id) ?? 0) + 1);
  }
  return {
    meta: page.meta,
    data: page.data.map((p) => map.toPolicy(p, counts.get(p.policy_id) ?? 0))
  };
}

export async function getPolicy(id: string) {
  return getOne<ApiPolicyDetail>('/policies', id);
}

export async function getControls(params?: QueryParams): Promise<Paged<Control>> {
  const [page, policies, findings, evidence] = await Promise.all([
    getList<ApiControl>('/controls', { page_size: FULL, ...params }),
    getAll<ApiPolicy>('/policies'),
    getAll<ApiFinding>('/findings'),
    getAll<ApiEvidence>('/evidence')
  ]);
  const policyById = new Map(policies.map((p) => [p.policy_id, p]));

  const findingsByControl = new Map<string, ApiFinding[]>();
  for (const finding of findings) {
    const list = findingsByControl.get(finding.control_id) ?? [];
    list.push(finding);
    findingsByControl.set(finding.control_id, list);
  }
  const evidenceCount = new Map<string, number>();
  for (const item of evidence) {
    evidenceCount.set(item.control_id, (evidenceCount.get(item.control_id) ?? 0) + 1);
  }

  return {
    meta: page.meta,
    data: page.data.map((control) => {
      const policy = policyById.get(control.policy_id);
      return map.toControl(control, {
        framework: policy?.framework,
        policyName: policy?.policy_name,
        evidenceCount: evidenceCount.get(control.control_id) ?? 0,
        findings: findingsByControl.get(control.control_id) ?? []
      });
    })
  };
}

export async function getControl(id: string) {
  return getOne<ApiControlDetail>('/controls', id);
}

export async function getFrameworks(): Promise<FrameworkScore[]> {
  const rows = await getRaw<ApiFrameworkSummary[]>('/frameworks');
  return rows.map(map.toFrameworkScore);
}

export async function getFrameworkSummaries(): Promise<ApiFrameworkSummary[]> {
  return getRaw<ApiFrameworkSummary[]>('/frameworks');
}

export async function getFramework(id: string) {
  return getOne<ApiFrameworkSummary>('/frameworks', id);
}

/* -------------------------------------------------------------- evidence */

export async function getEvidence(params?: QueryParams): Promise<Paged<EvidenceItem>> {
  const [page, controls] = await Promise.all([
    getList<ApiEvidence>('/evidence', { page_size: FULL, ...params }),
    getAll<ApiControl>('/controls')
  ]);
  const controlById = new Map(controls.map((c) => [c.control_id, c]));
  return {
    meta: page.meta,
    data: page.data.map((e) => map.toEvidenceItem(e, controlById.get(e.control_id)?.control_name))
  };
}

export async function getEvidenceItem(id: string) {
  return getOne<ApiEvidenceDetail>('/evidence', id);
}

/* ---------------------------------------------------------- organization */

export async function getEmployees(params?: QueryParams): Promise<Paged<Employee>> {
  const [page, iam] = await Promise.all([
    getList<ApiEmployee>('/employees', { page_size: FULL, ...params }),
    getAll<ApiIam>('/iam')
  ]);
  const iamByEmployee = new Map(iam.map((i) => [i.employee_id, i]));
  return {
    meta: page.meta,
    data: page.data.map((e) => map.toEmployee(e, iamByEmployee.get(e.employee_id)))
  };
}

export async function getEmployee(id: string) {
  return getOne<ApiEmployeeDetail>('/employees', id);
}

export async function getIdentities(params?: QueryParams): Promise<Paged<IamAccount>> {
  const [page, names] = await Promise.all([
    getList<ApiIam>('/iam', { page_size: FULL, ...params }),
    employeeNames()
  ]);
  return {
    meta: page.meta,
    data: page.data.map((i) => map.toIamAccount(i, names.get(i.employee_id)))
  };
}

export async function getIdentity(id: string) {
  return getOne<ApiIam>('/iam', id);
}

export async function getDevices(params?: QueryParams): Promise<Paged<Device>> {
  const [page, names] = await Promise.all([
    getList<ApiDevice>('/devices', { page_size: FULL, ...params }),
    employeeNames()
  ]);
  return {
    meta: page.meta,
    data: page.data.map((d) => map.toDevice(d, names.get(d.employee_id)))
  };
}

export async function getDevice(id: string) {
  return getOne<ApiDevice>('/devices', id);
}

export async function getApplications(params?: QueryParams): Promise<Paged<Application>> {
  const page = await getList<ApiApplication>('/applications', { page_size: FULL, ...params });
  return { meta: page.meta, data: page.data.map((a) => map.toApplication(a)) };
}

export async function getApplication(id: string) {
  return getOne<ApiApplicationDetail>('/applications', id);
}

export async function getCloudAssets(params?: QueryParams): Promise<Paged<CloudAsset>> {
  const [page, names] = await Promise.all([
    getList<ApiCloudAsset>('/cloud-assets', { page_size: FULL, ...params }),
    employeeNames()
  ]);
  return {
    meta: page.meta,
    data: page.data.map((a) =>
      map.toCloudAsset(a, a.owner_employee_id ? names.get(a.owner_employee_id) : undefined)
    )
  };
}

export async function getCloudAsset(id: string) {
  return getOne<ApiCloudAsset>('/cloud-assets', id);
}

export async function getVendors(params?: QueryParams): Promise<Paged<Vendor>> {
  const page = await getList<ApiVendor>('/vendors', { page_size: FULL, ...params });
  return { meta: page.meta, data: page.data.map(map.toVendor) };
}

export async function getVendor(id: string) {
  return getOne<ApiVendor>('/vendors', id);
}

/* --------------------------------------------------------------- privacy */

export async function getPersonalData(params?: QueryParams): Promise<Paged<PersonalDataAsset>> {
  const [page, names] = await Promise.all([
    getList<ApiPersonalData>('/dpdp/personal-data', { page_size: FULL, ...params }),
    applicationNames()
  ]);
  return {
    meta: page.meta,
    data: page.data.map((r) => map.toPersonalDataAsset(r, names.get(r.application_id)))
  };
}

export async function getPersonalDataRecord(id: string) {
  return getOne<ApiPersonalData>('/dpdp/personal-data', id);
}

export async function getConsents(params?: QueryParams): Promise<Paged<ConsentRecord>> {
  const [page, apps, employees] = await Promise.all([
    getList<ApiConsent>('/dpdp/consents', { page_size: FULL, ...params }),
    applicationNames(),
    employeeNames()
  ]);
  return {
    meta: page.meta,
    data: page.data.map((c) =>
      map.toConsentRecord(c, apps.get(c.application_id), employees.get(c.employee_id))
    )
  };
}

export async function getConsent(id: string) {
  return getOne<ApiConsent>('/dpdp/consents', id);
}

/* -------------------------------------------------------------- assurance */

/**
 * Audit logs are the one table that must stay server-paginated: 10,000 rows.
 * Filters map straight onto backend query params, including the date range
 * and min_risk_score the API exposes.
 */
export async function getAuditLogs(params?: QueryParams): Promise<Paged<AuditEvent>> {
  const [page, employees, apps] = await Promise.all([
    getList<ApiAuditLog>('/audit-logs', { page_size: 50, sort: '-timestamp', ...params }),
    employeeNames(),
    applicationNames()
  ]);
  return {
    meta: page.meta,
    data: page.data.map((log) =>
      map.toAuditEvent(
        log,
        log.employee_id ? employees.get(log.employee_id) : undefined,
        log.application_id ? apps.get(log.application_id) : undefined
      )
    )
  };
}

export async function getAuditLog(id: string) {
  return getOne<ApiAuditLog>('/audit-logs', id);
}

export async function getReports(params?: QueryParams): Promise<Paged<ReportItem>> {
  const page = await getList<ApiReport>('/reports', { page_size: FULL, ...params });
  return { meta: page.meta, data: page.data.map(map.toReportItem) };
}

export async function getReport(id: string) {
  return getOne<ApiReport>('/reports', id);
}

/** Raw report rows — the Reports screen shows the real score breakdown. */
export async function getReportRows(params?: QueryParams): Promise<Paged<ApiReport>> {
  return getList<ApiReport>('/reports', { page_size: FULL, ...params });
}

/* ------------------------------------------------------------------ graph */

export interface GraphView {
  nodes: GraphNode[];
  edges: GraphEdge[];
  meta: ApiGraph['meta'];
}

export async function getOrganizationGraph(
  params: QueryParams = { scope: 'full', limit_employees: 60 }
): Promise<any> {
  const graph = await getRaw<any>('/organization/graph', params);
  if (params.aggregated) {
    return { nodes: graph.nodes, edges: graph.edges, meta: graph.meta };
  }
  const { nodes, edges } = map.toGraph(graph);
  return { nodes, edges, meta: graph.meta };
}

/* ------------------------------------------------------------------- auth */

export async function login(email: string, password: string): Promise<ApiLoginResponse> {
  const result = await post<ApiLoginResponse>('/auth/login', { email, password });
  tokenStore.set(result.access_token, result.refresh_token);
  resetReferenceCache(); // never show one user data cached for another
  return result;
}

export async function getCurrentUser(): Promise<ApiUser> {
  return getRaw<ApiUser>('/auth/me');
}

/** Ends the session on the server, then forgets it locally. The local part
 * always happens, even if the server cannot be reached. */
export async function logout(): Promise<void> {
  try {
    await post('/auth/logout', {});
  } catch {
    // Nothing useful to do: the tokens are discarded below either way.
  }
  tokenStore.clear();
  resetReferenceCache();
}

export function hasSession(): boolean {
  return Boolean(tokenStore.access);
}

export { ApiError } from './http';

/* ------------------------------------------------------------- detections */

export interface DetectionRule {
  id: string;
  version: number;
  title: string;
  severity: string;
  confidence: string;
  attack: string[];
  parameters: Record<string, unknown>;
  logic: string;
  /** The rule's written contract; null when research/rules/ is not deployed. */
  contract: {limitations?: string[];[key: string]: unknown;} | null;
}

export interface DetectionCitedEvent {
  role: 'trigger' | 'context';
  event_id: string;
  source_event_id: string;
  occurred_at: string;
  action: string;
  outcome: string;
  actor_id: string | null;
  target_id: string | null;
  raw_sha256: string;
}

export interface DetectionAlert {
  alert_id: string;
  rule_id: string;
  rule_version: number;
  severity: string;
  confidence: string;
  source_id: string;
  actor_id: string | null;
  trigger_at: string;
  summary: string;
  events?: DetectionCitedEvent[];
}

export interface DetectionRunReport {
  run_id: string;
  status: string;
  events_considered: number;
  alerts_created: number;
  alerts_existing: number;
  alerts_no_longer_raised: number;
  not_evaluable: Record<string, number>;
}

export async function getDetectionRules(): Promise<DetectionRule[]> {
  return getRaw<DetectionRule[]>('/detections/rules');
}

/** The 200 most recent alerts. */
export async function getDetectionAlerts(): Promise<DetectionAlert[]> {
  return getRaw<DetectionAlert[]>('/detections/alerts', { limit: 200 });
}

export async function getDetectionAlert(alertId: string): Promise<DetectionAlert> {
  return getRaw<DetectionAlert>(`/detections/alerts/${encodeURIComponent(alertId)}`);
}

export async function startDetectionRun(sourceId: string): Promise<DetectionRunReport> {
  return post<DetectionRunReport>('/detections/runs', { source_type: 'sentinel.native', source_id: sourceId });
}

/** Sources that have had events ingested, from the ingestion batch log. */
export async function getEventSources(): Promise<string[]> {
  const batches = await getRaw<{source_id: string;source_type: string;}[]>('/security-events/batches', { limit: 100 });
  return [...new Set(batches.filter((b) => b.source_type === 'sentinel.native').map((b) => b.source_id))].sort();
}
export type { Paged, QueryParams } from './http';

/* --------------------------------------------------- Phase 2B intelligence */

export interface EvidenceGap {
  control_id: string;
  control_name: string;
  control_severity: string;
  evidence_required: boolean;
  policy_id: string;
  policy_name: string | null;
  framework: string | null;
  mandatory_policy: boolean | null;
  evidence_items: number;
  verified_evidence_items: number;
  gap_type: 'no_evidence' | 'unverified_only';
  gap_severity: 'Critical' | 'High' | 'Medium' | 'Low';
  open_findings: number;
  open_finding_ids: string[];
  related_risk_ids: string[];
  why: string;
}

export interface EvidenceCoverage {
  coverage_percentage: number;
  total_controls: number;
  covered_controls: number;
  uncovered_controls: number;
  controls_with_no_evidence: number;
  controls_with_unverified_evidence_only: number;
  total_evidence_items: number;
  verified_evidence_items: number;
  unverified_evidence_items: number;
  auto_collected_evidence_items: number;
  critical_gaps: number;
  high_gaps: number;
  by_framework: Array<{
    framework: string;
    total_controls: number;
    covered_controls: number;
    uncovered_controls: number;
    coverage_percentage: number;
  }>;
  formula: string;
  adequacy_rule: string;
  freshness_policy_available: boolean;
  freshness_note: string;
  top_gaps?: EvidenceGap[];
  total_gaps?: number;
  evidence_gaps?: EvidenceGap[];
}

/** Evidence posture header: coverage, gap counts and the worst gaps. */
export async function getEvidenceIntelligence(gapLimit = 10): Promise<EvidenceCoverage> {
  return getRaw<EvidenceCoverage>('/intelligence/evidence', { gap_limit: gapLimit });
}

/** Full coverage including every gap — used by the Evidence Gap drawer. */
export async function getEvidenceCoverage(): Promise<EvidenceCoverage> {
  return getRaw<EvidenceCoverage>('/intelligence/evidence/coverage');
}

export async function getEvidenceExplanation(evidenceId: string) {
  return getRaw<Record<string, any>>(`/intelligence/evidence/${encodeURIComponent(evidenceId)}`);
}

/** "Can we prove this control works?" — evidence, findings and risks for one control. */
export async function getControlEvidence(controlId: string) {
  return getRaw<Record<string, any>>(
    `/intelligence/controls/${encodeURIComponent(controlId)}/evidence`
  );
}

export interface PolicyRequirement {
  requirement_id: string;
  requirement: string;
  obligation: 'mandatory' | 'advisory';
  category: string | null;
  mapped_frameworks: string[];
  mapped_controls: Array<{
    control_id: string;
    control_name: string;
    control_severity: string;
    framework: string | null;
    match_score: number;
    matched_terms: string[];
  }>;
  mapping_source?: string;
  mapping_note: string | null;
  evidence_requirements: string[];
  current_state: string;
  gap: 'none' | 'partial' | 'unverified' | 'no_evidence' | 'unmapped';
  gap_severity: string;
  supporting_evidence: Array<Record<string, any>>;
  open_findings: Array<Record<string, any>>;
  related_risks: Array<Record<string, any>>;
  confidence: 'high' | 'medium' | 'low' | 'none' | 'verified';
  recommended_action: string;
}

export interface PolicyAnalysis {
  title: string;
  engine: string;
  matcher: string;
  llm_used: boolean;
  engine_note: string;
  characters_analyzed: number;
  requirements_found: number;
  requirements_mapped: number;
  requirements_unmapped: number;
  requirements_satisfied: number;
  requirements_with_gaps: number;
  compliance_percentage: number;
  compliance_formula: string;
  requirements: PolicyRequirement[];
  match_threshold: number | null;
  policy?: Record<string, any>;
  source?: string;
  source_note?: string;
  actual_controls?: Array<Record<string, any>>;
  actual_control_count?: number;
  actual_controls_covered?: number;
  actual_coverage_percentage?: number;
}

/** Analyse pasted or uploaded policy text. Rule-based — no LLM is configured. */
export async function analyzePolicyText(text: string, title?: string): Promise<PolicyAnalysis> {
  return post<PolicyAnalysis>('/intelligence/policy/analyze', { text, title });
}

/** Analyse a policy already in the database, using its real control FKs. */
export async function analyzeStoredPolicy(policyId: string): Promise<PolicyAnalysis> {
  return getRaw<PolicyAnalysis>(`/intelligence/policies/${encodeURIComponent(policyId)}`);
}

export interface CopilotAnswer {
  question: string;
  intent: string;
  intent_label: string;
  answer: string;
  supporting_data: Array<{ label: string; value: string | number | null; unit?: string }>;
  related_entities: Array<{ type: string; id: string; label: string; detail?: string }>;
  recommendations: string[];
  sources: Array<{ endpoint: string; field: string }>;
  confidence: 'high' | 'medium' | 'low' | 'none';
  engine: string;
  llm_used: boolean;
  suggested_questions: string[];
}

/** Ask the Compliance Copilot. Answers are composed from live data, not generated. */
export async function askCopilot(question: string): Promise<CopilotAnswer> {
  return post<CopilotAnswer>('/copilot/query', { question });
}

export async function getCopilotSuggestions() {
  return getRaw<{
    suggested_questions: string[];
    intents: Array<{ intent: string; label: string; example: string }>;
    engine: string;
    llm_used: boolean;
  }>('/copilot/suggestions');
}

// -----------------------------------------------------------------------------
// Phase 2: AI Intelligence Endpoints
// -----------------------------------------------------------------------------

export interface IntelligenceOrchestratorSummary {
  executive_summary: string;
  llm_used: boolean;
  posture: {
    trust_posture: { score: number; level: string; change: number };
    top_risks: any[];
    active_threats: any;
    immediate_remediations: any[];
    evidence_gaps: any[];
  };
}

export async function getOrchestratorSummary(): Promise<IntelligenceOrchestratorSummary> {
  return getRaw<IntelligenceOrchestratorSummary>('/intelligence/orchestrator/summary');
}

export async function getTrustIntelligence(): Promise<any> {
  return getRaw<any>('/intelligence/trust');
}

export async function getRiskIntelligence(id: string): Promise<any> {
  return getRaw<any>(`/intelligence/risks/${encodeURIComponent(id)}`);
}

export async function getTopRemediations(limit?: number): Promise<any> {
  const url = limit ? `/intelligence/remediation?limit=${limit}` : '/intelligence/remediation';
  return getRaw<any>(url);
}

export async function getRemediationIntelligence(findingId: string): Promise<any> {
  return getRaw<any>(`/intelligence/remediation/${encodeURIComponent(findingId)}`);
}

