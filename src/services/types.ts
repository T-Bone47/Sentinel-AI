/**
 * Backend row shapes, exactly as the FastAPI layer returns them (snake_case).
 *
 * These mirror app/schemas/resources.py. They are deliberately NOT the types
 * the UI components consume — see adapters.ts for the mapping into
 * types/domain.ts. Keeping the two separate means a backend field rename is a
 * one-line adapter change instead of a hunt through 20 page components.
 */

export interface ApiEmployee {
  employee_id: string;
  first_name: string;
  last_name: string;
  email: string;
  department: string;
  designation: string;
  manager_id: string | null;
  office_location: string;
  employment_type: string;
  joining_date: string;
  password_length: number;
  password_last_changed: string;
  mfa_enabled: boolean;
  account_status: string;
  device_id: string | null;
  last_login: string | null;
}

export interface ApiDevice {
  device_id: string;
  employee_id: string;
  device_type: string;
  operating_system: string;
  os_version: string;
  encryption_enabled: boolean;
  firewall_enabled: boolean;
  antivirus_installed: boolean;
  edr_installed: boolean;
  compliance_status: string;
  risk_level: string;
  last_patch_date: string;
}

export interface ApiCloudAsset {
  resource_id: string;
  cloud_provider: string;
  resource_type: string;
  region: string;
  owner_employee_id: string | null;
  public_access: boolean;
  encryption_enabled: boolean;
  logging_enabled: boolean;
  criticality: string;
  risk_level: string;
}

export interface ApiApplication {
  application_id: string;
  application_name: string;
  owner_department: string;
  authentication_method: string;
  uses_mfa: boolean;
  encryption_enabled: boolean;
  data_classification: string;
  internet_facing: boolean;
  risk_level: string;
}

export interface ApiVendor {
  vendor_id: string;
  vendor_name: string;
  service_category: string;
  iso27001_certified: boolean;
  soc2_certified: boolean;
  dpdp_compliant: boolean;
  risk_rating: string;
  contract_expiry: string;
}

export interface ApiPolicy {
  policy_id: string;
  policy_name: string;
  framework: string;
  category: string;
  version: string;
  owner_department: string;
  mandatory: boolean;
}

export interface ApiControl {
  control_id: string;
  policy_id: string;
  control_name: string;
  description: string;
  severity: string;
  automation_possible: boolean;
  evidence_required: boolean;
}

export interface ApiRisk {
  risk_id: string;
  risk_name: string;
  description: string;
  business_impact: string;
  likelihood: string;
  severity: string;
  owner_department: string;
  mapped_control_id: string | null;
  current_status: string;
}

export interface ApiEvidence {
  evidence_id: string;
  control_id: string;
  evidence_type: string;
  evidence_location: string;
  collected_date: string;
  verified: boolean;
  collected_automatically: boolean;
}

export interface ApiFinding {
  finding_id: string;
  control_id: string;
  severity: string;
  description: string;
  evidence_id: string | null;
  recommendation: string;
  status: string;
}

export interface ApiReport {
  report_id: string;
  framework: string;
  generated_date: string;
  overall_score: number;
  critical_findings: number;
  high_findings: number;
  medium_findings: number;
  low_findings: number;
  compliance_status: string;
}

export interface ApiPersonalData {
  data_id: string;
  application_id: string;
  data_category: string;
  purpose_of_processing: string;
  retention_period: string;
  third_party_sharing: boolean;
  encryption_enabled: boolean;
  consent_required: boolean;
}

export interface ApiConsent {
  consent_id: string;
  employee_id: string;
  application_id: string;
  consent_given: boolean;
  consent_date: string;
  expiry_date: string;
  revoked: boolean;
}

export interface ApiIam {
  iam_user_id: string;
  employee_id: string;
  role: string;
  privileges: string;
  privileged_account: boolean;
  mfa_enabled: boolean;
  inactive_days: number;
  last_privilege_review: string;
}

export interface ApiAuditLog {
  log_id: string;
  timestamp: string;
  employee_id: string | null;
  application_id: string | null;
  action: string;
  ip_address: string;
  geo_location: string;
  result: string;
  risk_score: number;
}

/* ------------------------------------------------------- enriched details */

export interface ApiRiskDetail extends ApiRisk {
  control: ApiControl | null;
  policy: ApiPolicy | null;
  findings: ApiFinding[];
  evidence: ApiEvidence[];
  open_finding_count: number;
  verified_evidence_count: number;
}

export interface ApiFindingDetail extends ApiFinding {
  control: ApiControl | null;
  policy: ApiPolicy | null;
  evidence: ApiEvidence | null;
  related_risks: ApiRisk[];
}

export interface ApiEvidenceDetail extends ApiEvidence {
  control: ApiControl | null;
  policy: ApiPolicy | null;
  findings: ApiFinding[];
  related_risks: ApiRisk[];
}

export interface ApiControlDetail extends ApiControl {
  policy: ApiPolicy | null;
  evidence: ApiEvidence[];
  findings: ApiFinding[];
  risks: ApiRisk[];
}

export interface ApiPolicyDetail extends ApiPolicy {
  controls: ApiControl[];
  control_count: number;
}

export interface ApiEmployeeDetail extends ApiEmployee {
  manager: ApiEmployee | null;
  device: ApiDevice | null;
  iam_record: ApiIam | null;
  cloud_assets: ApiCloudAsset[];
  direct_reports: ApiEmployee[];
  recent_activity: ApiAuditLog[];
}

export interface ApiApplicationDetail extends ApiApplication {
  personal_data_records: ApiPersonalData[];
  consent_records: ApiConsent[];
  recent_activity: ApiAuditLog[];
}

/* ---------------------------------------------------------- aggregates */

export interface ApiScore {
  value: number | null;
  engine?: string;
  status?: string;
  weights?: Record<string, number>;
  components?: Record<string, number>;
  formula?: string;
  note?: string;
}

export interface ApiFrameworkSummary {
  framework: string;
  total_policies: number;
  mandatory_policies: number;
  total_controls: number;
  controls_with_evidence: number;
  controls_with_open_findings: number;
  passed_controls: number;
  failed_controls: number;
  evidence_count: number;
  verified_evidence_count: number;
  evidence_coverage_pct: number;
  total_findings: number;
  open_findings: number;
  critical_findings: number;
  high_findings: number;
  latest_report_id: string | null;
  latest_report_score: number | null;
  latest_report_status: string | null;
  latest_report_date: string | null;
  control_domains?: Array<{ domain: string; passing: number; failing: number }>;
}

export interface ApiDashboard {
  generated_at: string;
  totals: Record<string, number>;
  trust_score: ApiScore;
  audit_readiness: ApiScore;
  risks: {
    total: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    open: number;
    by_severity: Record<string, number>;
    by_status: Record<string, number>;
    by_likelihood: Record<string, number>;
    by_department: Record<string, number>;
    mapped_to_control: number;
  };
  findings: {
    total: number;
    open: number;
    critical_open: number;
    high_open: number;
    severe_open: number;
    with_evidence: number;
    by_severity: Record<string, number>;
    by_status: Record<string, number>;
  };
  evidence_coverage: {
    total_controls: number;
    controls_with_evidence: number;
    controls_without_evidence: number;
    coverage_pct: number;
    total_evidence: number;
    verified_evidence: number;
    verified_pct: number;
    auto_collected: number;
    by_type: Record<string, number>;
  };
  compliance_coverage: {
    total_policies: number;
    mandatory_policies: number;
    total_controls: number;
    controls_with_evidence: number;
    controls_with_open_findings: number;
    passed_controls: number;
    failed_controls: number;
    pass_rate_pct: number;
    mandatory_controls: number;
    mandatory_controls_with_evidence: number;
    policies_by_framework: Record<string, number>;
    controls_by_severity: Record<string, number>;
  };
  framework_status: ApiFrameworkSummary[];
  recent_audit_activity: {
    total_events: number;
    latest_event_at: string | null;
    window: string;
    events_in_window: number;
    failures_in_window: number;
    total_failures: number;
    high_risk_events: number;
    by_result: Record<string, number>;
    top_actions: Record<string, number>;
    recent: Array<{
      log_id: string;
      timestamp: string;
      employee_id: string | null;
      application_id: string | null;
      action: string;
      result: string;
      risk_score: number;
      geo_location: string;
    }>;
  };
  asset_statistics: {
    employees: Record<string, any>;
    devices: Record<string, any>;
    cloud_assets: Record<string, any>;
    applications: Record<string, any>;
  };
  vendor_risk: Record<string, any>;
  privacy_statistics: Record<string, any>;
  iam_statistics: Record<string, any>;
}

export interface ApiGraphNode {
  id: string;
  type: string;
  label: string;
  data: Record<string, any>;
}

export interface ApiGraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  weight?: number;
}

export interface ApiGraph {
  nodes: ApiGraphNode[];
  edges: ApiGraphEdge[];
  meta: {
    scope: string;
    node_count: number;
    edge_count: number;
    node_types: Record<string, number>;
    edge_types: Record<string, number>;
    caps: Record<string, any>;
    relationship_sources: Record<string, string>;
  };
}

export interface ApiUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  employee_id: string | null;
  /** Resources this role may read. For hiding UI only — the server enforces access. */
  permissions: string[];
}

export interface ApiLoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  role: string;
  email: string;
  full_name: string;
}
