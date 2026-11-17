"""
Response DTOs, one per dataset table.

Field names/types mirror the verified models exactly — no invented fields
are added to make a UI look fuller (explicit Phase 1 instruction). Where
the frontend needs joined context (a finding's control, a risk's evidence
chain), that lives in the composite schemas at the bottom of this file,
built only from relationships that actually exist in the data.
"""
from __future__ import annotations

from datetime import date, datetime

from app.schemas.common import ORMModel


class EmployeeOut(ORMModel):
    employee_id: str
    first_name: str
    last_name: str
    email: str
    department: str
    designation: str
    manager_id: str | None = None
    office_location: str
    employment_type: str
    joining_date: date
    password_length: int
    password_last_changed: date
    mfa_enabled: bool
    account_status: str
    device_id: str | None = None
    last_login: datetime | None = None


class DeviceOut(ORMModel):
    device_id: str
    employee_id: str
    device_type: str
    operating_system: str
    os_version: str
    encryption_enabled: bool
    firewall_enabled: bool
    antivirus_installed: bool
    edr_installed: bool
    compliance_status: str
    risk_level: str
    last_patch_date: date


class CloudAssetOut(ORMModel):
    resource_id: str
    cloud_provider: str
    resource_type: str
    region: str
    owner_employee_id: str | None = None
    public_access: bool
    encryption_enabled: bool
    logging_enabled: bool
    criticality: str
    risk_level: str


class ApplicationOut(ORMModel):
    application_id: str
    application_name: str
    owner_department: str
    authentication_method: str
    uses_mfa: bool
    encryption_enabled: bool
    data_classification: str
    internet_facing: bool
    risk_level: str


class VendorOut(ORMModel):
    vendor_id: str
    vendor_name: str
    service_category: str
    iso27001_certified: bool
    soc2_certified: bool
    dpdp_compliant: bool
    risk_rating: str
    contract_expiry: date


class PolicyOut(ORMModel):
    policy_id: str
    policy_name: str
    framework: str
    category: str
    version: str
    owner_department: str
    mandatory: bool


class ControlOut(ORMModel):
    control_id: str
    policy_id: str
    control_name: str
    description: str
    severity: str
    automation_possible: bool
    evidence_required: bool


class RiskOut(ORMModel):
    risk_id: str
    risk_name: str
    description: str
    business_impact: str
    likelihood: str
    severity: str
    owner_department: str
    mapped_control_id: str | None = None
    current_status: str


class EvidenceOut(ORMModel):
    evidence_id: str
    control_id: str
    evidence_type: str
    evidence_location: str
    collected_date: date
    verified: bool
    collected_automatically: bool


class FindingOut(ORMModel):
    finding_id: str
    control_id: str
    severity: str
    description: str
    evidence_id: str | None = None
    recommendation: str
    status: str


class ReportOut(ORMModel):
    report_id: str
    framework: str
    generated_date: date
    overall_score: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    compliance_status: str


class PersonalDataOut(ORMModel):
    data_id: str
    application_id: str
    data_category: str
    purpose_of_processing: str
    retention_period: str
    third_party_sharing: bool
    encryption_enabled: bool
    consent_required: bool


class ConsentOut(ORMModel):
    consent_id: str
    employee_id: str
    application_id: str
    consent_given: bool
    consent_date: date
    expiry_date: date
    revoked: bool


class IAMOut(ORMModel):
    iam_user_id: str
    employee_id: str
    role: str
    privileges: str
    privileged_account: bool
    mfa_enabled: bool
    inactive_days: int
    last_privilege_review: date


class AuditLogOut(ORMModel):
    log_id: str
    timestamp: datetime
    employee_id: str | None = None
    application_id: str | None = None
    action: str
    ip_address: str
    geo_location: str
    result: str
    risk_score: int


# ---------------------------------------------------------------------------
# Composite / detail schemas — joined views the frontend screens need.
# Every relationship below is one of the empirically verified FKs. Nothing
# here is synthesised: absent links (vendor->risk, report->finding,
# personal_data->consent) stay absent.
# ---------------------------------------------------------------------------


class EmployeeDetailOut(EmployeeOut):
    manager: EmployeeOut | None = None
    device: DeviceOut | None = None
    iam_record: IAMOut | None = None
    cloud_assets: list[CloudAssetOut] = []
    direct_reports: list[EmployeeOut] = []
    recent_activity: list[AuditLogOut] = []


class ControlDetailOut(ControlOut):
    policy: PolicyOut | None = None
    evidence: list[EvidenceOut] = []
    findings: list[FindingOut] = []
    risks: list[RiskOut] = []


class PolicyDetailOut(PolicyOut):
    controls: list[ControlOut] = []
    control_count: int = 0


class FindingDetailOut(FindingOut):
    control: ControlOut | None = None
    policy: PolicyOut | None = None
    evidence: EvidenceOut | None = None
    related_risks: list[RiskOut] = []


class EvidenceDetailOut(EvidenceOut):
    control: ControlOut | None = None
    policy: PolicyOut | None = None
    findings: list[FindingOut] = []
    related_risks: list[RiskOut] = []


class RiskDetailOut(RiskOut):
    """
    Powers the Investigations screen. The chain
    POLICY -> CONTROL -> FINDING -> EVIDENCE -> RISK is walked through real
    FKs only: risk.mapped_control_id is the hinge, and everything else hangs
    off that control. A risk with no mapped control returns nulls/empties
    rather than a fabricated chain.
    """

    control: ControlOut | None = None
    policy: PolicyOut | None = None
    findings: list[FindingOut] = []
    evidence: list[EvidenceOut] = []
    open_finding_count: int = 0
    verified_evidence_count: int = 0


class ApplicationDetailOut(ApplicationOut):
    personal_data_records: list[PersonalDataOut] = []
    consent_records: list[ConsentOut] = []
    recent_activity: list[AuditLogOut] = []


class FrameworkSummaryOut(ORMModel):
    """
    Framework-level rollup. There is no frameworks table in the source data
    — Framework is a shared vocabulary on policies and reports. This is
    aggregated live from policies -> controls -> findings/evidence, plus the
    latest real report row for that framework where one exists.
    """

    framework: str
    total_policies: int
    mandatory_policies: int
    total_controls: int
    controls_with_evidence: int
    controls_with_open_findings: int
    passed_controls: int
    failed_controls: int
    evidence_count: int
    verified_evidence_count: int
    evidence_coverage_pct: float
    total_findings: int
    open_findings: int
    critical_findings: int
    high_findings: int
    latest_report_id: str | None = None
    latest_report_score: int | None = None
    latest_report_status: str | None = None
    latest_report_date: date | None = None
