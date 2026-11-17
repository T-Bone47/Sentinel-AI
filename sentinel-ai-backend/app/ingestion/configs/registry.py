"""
Declarative CSV -> model mapping, one config per repository dataset.

Nothing here is inferred at runtime: every column mapping, type, and FK
comes from the empirically verified profiling output in docs/profiling/
and HANDOFF.md §6-§8. If a source file changes, this is the ONLY file
that should need editing — the ingestor itself is dataset-agnostic.

LOAD_ORDER is the FK-safe order from HANDOFF.md §13. Do not reorder it
without re-checking the dependency graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models import (
    Application,
    AuditLog,
    CloudAsset,
    ConsentRecord,
    Control,
    Device,
    Employee,
    Evidence,
    Finding,
    IAMRecord,
    PersonalDataInventory,
    Policy,
    Report,
    Risk,
    Vendor,
)
from app.models.enums import DatasetType


@dataclass(frozen=True)
class FieldSpec:
    """One CSV column -> one model attribute."""

    source: str
    target: str
    kind: str = "str"  # str | int | bool | date | datetime
    nullable: bool = False


@dataclass(frozen=True)
class FKSpec:
    """
    A foreign key the ingestor must respect.

    hard=True   -> the DB enforces it; a row pointing at a missing parent is
                   SKIPPED (non-nullable) or NULLED (nullable), never inserted
                   blind, because that would abort the whole transaction.
    hard=False  -> no DB constraint (e.g. employees.device_id); mismatches are
                   logged as warnings and the row is still loaded, per the
                   "warn-not-fail" rule in HANDOFF.md §11.
    """

    local: str  # model attribute on this table
    ref_table: str  # referenced table name
    ref_column: str  # referenced column name
    nullable: bool = False
    hard: bool = True


@dataclass(frozen=True)
class DatasetConfig:
    dataset_type: DatasetType
    filename: str
    model: Any
    pk: str
    fields: tuple[FieldSpec, ...]
    fks: tuple[FKSpec, ...] = field(default_factory=tuple)
    # Load the whole file in one INSERT statement. Needed for employees,
    # whose manager_id is self-referential: Postgres fires RI checks at end
    # of statement, so parent+child arriving together is fine, but only if
    # they are genuinely in the SAME statement.
    single_statement: bool = False


EMPLOYEES = DatasetConfig(
    dataset_type=DatasetType.EMPLOYEES,
    filename="dataset1_enterprise_employees.csv",
    model=Employee,
    pk="employee_id",
    single_statement=True,
    fields=(
        FieldSpec("EmployeeID", "employee_id"),
        FieldSpec("FirstName", "first_name"),
        FieldSpec("LastName", "last_name"),
        FieldSpec("Email", "email"),
        FieldSpec("Department", "department"),
        FieldSpec("Designation", "designation"),
        FieldSpec("ManagerID", "manager_id", nullable=True),
        FieldSpec("OfficeLocation", "office_location"),
        FieldSpec("EmploymentType", "employment_type"),
        FieldSpec("JoiningDate", "joining_date", "date"),
        FieldSpec("PasswordLength", "password_length", "int"),
        FieldSpec("PasswordLastChanged", "password_last_changed", "date"),
        FieldSpec("MFAEnabled", "mfa_enabled", "bool"),
        FieldSpec("AccountStatus", "account_status"),
        FieldSpec("DeviceID", "device_id", nullable=True),
        FieldSpec("LastLogin", "last_login", "datetime", nullable=True),
    ),
    fks=(
        FKSpec("manager_id", "employees", "employee_id", nullable=True),
        # devices isn't loaded yet on a cold start, and this is not a DB
        # constraint by design (HANDOFF.md §11) -> warn only, never block.
        FKSpec("device_id", "devices", "device_id", nullable=True, hard=False),
    ),
)

DEVICES = DatasetConfig(
    dataset_type=DatasetType.DEVICES,
    filename="dataset2_enterprise_devices.csv",
    model=Device,
    pk="device_id",
    fields=(
        FieldSpec("DeviceID", "device_id"),
        FieldSpec("EmployeeID", "employee_id"),
        FieldSpec("DeviceType", "device_type"),
        FieldSpec("OperatingSystem", "operating_system"),
        FieldSpec("OSVersion", "os_version"),
        FieldSpec("EncryptionEnabled", "encryption_enabled", "bool"),
        FieldSpec("FirewallEnabled", "firewall_enabled", "bool"),
        FieldSpec("AntivirusInstalled", "antivirus_installed", "bool"),
        FieldSpec("EDRInstalled", "edr_installed", "bool"),
        FieldSpec("ComplianceStatus", "compliance_status"),
        FieldSpec("RiskLevel", "risk_level"),
        FieldSpec("LastPatchDate", "last_patch_date", "date"),
    ),
    fks=(FKSpec("employee_id", "employees", "employee_id"),),
)

CLOUD_ASSETS = DatasetConfig(
    dataset_type=DatasetType.CLOUD_ASSETS,
    filename="dataset3_cloud_assets.csv",
    model=CloudAsset,
    pk="resource_id",
    fields=(
        FieldSpec("ResourceID", "resource_id"),
        FieldSpec("CloudProvider", "cloud_provider"),
        FieldSpec("ResourceType", "resource_type"),
        FieldSpec("Region", "region"),
        FieldSpec("OwnerEmployeeID", "owner_employee_id", nullable=True),
        FieldSpec("PublicAccess", "public_access", "bool"),
        FieldSpec("EncryptionEnabled", "encryption_enabled", "bool"),
        FieldSpec("LoggingEnabled", "logging_enabled", "bool"),
        FieldSpec("Criticality", "criticality"),
        FieldSpec("RiskLevel", "risk_level"),
    ),
    fks=(FKSpec("owner_employee_id", "employees", "employee_id", nullable=True),),
)

APPLICATIONS = DatasetConfig(
    dataset_type=DatasetType.APPLICATIONS,
    filename="dataset4_applications.csv",
    model=Application,
    pk="application_id",
    fields=(
        FieldSpec("ApplicationID", "application_id"),
        FieldSpec("ApplicationName", "application_name"),
        FieldSpec("OwnerDepartment", "owner_department"),
        FieldSpec("AuthenticationMethod", "authentication_method"),
        FieldSpec("UsesMFA", "uses_mfa", "bool"),
        FieldSpec("EncryptionEnabled", "encryption_enabled", "bool"),
        FieldSpec("DataClassification", "data_classification"),
        FieldSpec("InternetFacing", "internet_facing", "bool"),
        FieldSpec("RiskLevel", "risk_level"),
    ),
)

VENDORS = DatasetConfig(
    dataset_type=DatasetType.VENDORS,
    filename="dataset5_third_party_vendors.csv",
    model=Vendor,
    pk="vendor_id",
    # Island table — verified to have no FK to anything. Do not add one.
    fields=(
        FieldSpec("VendorID", "vendor_id"),
        FieldSpec("VendorName", "vendor_name"),
        FieldSpec("ServiceCategory", "service_category"),
        FieldSpec("ISO27001Certified", "iso27001_certified", "bool"),
        FieldSpec("SOC2Certified", "soc2_certified", "bool"),
        FieldSpec("DPDPCompliant", "dpdp_compliant", "bool"),
        FieldSpec("RiskRating", "risk_rating"),
        FieldSpec("ContractExpiry", "contract_expiry", "date"),
    ),
)

POLICIES = DatasetConfig(
    dataset_type=DatasetType.POLICIES,
    filename="dataset6_security_policies.csv",
    model=Policy,
    pk="policy_id",
    fields=(
        FieldSpec("PolicyID", "policy_id"),
        FieldSpec("PolicyName", "policy_name"),
        FieldSpec("Framework", "framework"),
        FieldSpec("Category", "category"),
        FieldSpec("Version", "version"),
        FieldSpec("OwnerDepartment", "owner_department"),
        FieldSpec("Mandatory", "mandatory", "bool"),
    ),
)

CONTROLS = DatasetConfig(
    dataset_type=DatasetType.CONTROLS,
    filename="dataset7_compliance_controls.csv",
    model=Control,
    pk="control_id",
    fields=(
        FieldSpec("ControlID", "control_id"),
        FieldSpec("PolicyID", "policy_id"),
        FieldSpec("ControlName", "control_name"),
        FieldSpec("Description", "description"),
        FieldSpec("Severity", "severity"),
        FieldSpec("AutomationPossible", "automation_possible", "bool"),
        FieldSpec("EvidenceRequired", "evidence_required", "bool"),
    ),
    fks=(FKSpec("policy_id", "policies", "policy_id"),),
)

RISKS = DatasetConfig(
    dataset_type=DatasetType.RISKS,
    filename="dataset8_risk_register.csv",
    model=Risk,
    pk="risk_id",
    fields=(
        FieldSpec("RiskID", "risk_id"),
        FieldSpec("RiskName", "risk_name"),
        FieldSpec("Description", "description"),
        FieldSpec("BusinessImpact", "business_impact"),
        FieldSpec("Likelihood", "likelihood"),
        FieldSpec("Severity", "severity"),
        FieldSpec("OwnerDepartment", "owner_department"),
        FieldSpec("MappedControlID", "mapped_control_id", nullable=True),
        FieldSpec("CurrentStatus", "current_status"),
    ),
    fks=(FKSpec("mapped_control_id", "controls", "control_id", nullable=True),),
)

EVIDENCE = DatasetConfig(
    dataset_type=DatasetType.EVIDENCE,
    filename="dataset10_evidence_repository.csv",
    model=Evidence,
    pk="evidence_id",
    fields=(
        FieldSpec("EvidenceID", "evidence_id"),
        FieldSpec("ControlID", "control_id"),
        FieldSpec("EvidenceType", "evidence_type"),
        FieldSpec("EvidenceLocation", "evidence_location"),
        FieldSpec("CollectedDate", "collected_date", "date"),
        FieldSpec("Verified", "verified", "bool"),
        FieldSpec("CollectedAutomatically", "collected_automatically", "bool"),
    ),
    fks=(FKSpec("control_id", "controls", "control_id"),),
)

FINDINGS = DatasetConfig(
    dataset_type=DatasetType.FINDINGS,
    filename="dataset11_compliance_findings.csv",
    model=Finding,
    pk="finding_id",
    fields=(
        FieldSpec("FindingID", "finding_id"),
        FieldSpec("ControlID", "control_id"),
        FieldSpec("Severity", "severity"),
        FieldSpec("Description", "description"),
        FieldSpec("EvidenceID", "evidence_id", nullable=True),
        FieldSpec("Recommendation", "recommendation"),
        FieldSpec("Status", "status"),
    ),
    fks=(
        FKSpec("control_id", "controls", "control_id"),
        FKSpec("evidence_id", "evidence", "evidence_id", nullable=True),
    ),
)

REPORTS = DatasetConfig(
    dataset_type=DatasetType.REPORTS,
    filename="dataset12_compliance_reports.csv",
    model=Report,
    pk="report_id",
    # Framework-level rollup. Verified to have NO FK to findings/controls.
    fields=(
        FieldSpec("ReportID", "report_id"),
        FieldSpec("Framework", "framework"),
        FieldSpec("GeneratedDate", "generated_date", "date"),
        FieldSpec("OverallScore", "overall_score", "int"),
        FieldSpec("CriticalFindings", "critical_findings", "int"),
        FieldSpec("HighFindings", "high_findings", "int"),
        FieldSpec("MediumFindings", "medium_findings", "int"),
        FieldSpec("LowFindings", "low_findings", "int"),
        FieldSpec("ComplianceStatus", "compliance_status"),
    ),
)

PERSONAL_DATA = DatasetConfig(
    dataset_type=DatasetType.PERSONAL_DATA_INVENTORY,
    filename="dataset13_dpdp_personal_data_inventory.csv",
    model=PersonalDataInventory,
    pk="data_id",
    fields=(
        FieldSpec("DataID", "data_id"),
        FieldSpec("ApplicationID", "application_id"),
        FieldSpec("DataCategory", "data_category"),
        FieldSpec("PurposeOfProcessing", "purpose_of_processing"),
        FieldSpec("RetentionPeriod", "retention_period"),
        FieldSpec("ThirdPartySharing", "third_party_sharing", "bool"),
        FieldSpec("EncryptionEnabled", "encryption_enabled", "bool"),
        FieldSpec("ConsentRequired", "consent_required", "bool"),
    ),
    fks=(FKSpec("application_id", "applications", "application_id"),),
)

CONSENTS = DatasetConfig(
    dataset_type=DatasetType.CONSENT_RECORDS,
    filename="dataset14_consent_records.csv",
    model=ConsentRecord,
    pk="consent_id",
    fields=(
        FieldSpec("ConsentID", "consent_id"),
        FieldSpec("EmployeeID", "employee_id"),
        FieldSpec("ApplicationID", "application_id"),
        FieldSpec("ConsentGiven", "consent_given", "bool"),
        FieldSpec("ConsentDate", "consent_date", "date"),
        FieldSpec("ExpiryDate", "expiry_date", "date"),
        FieldSpec("Revoked", "revoked", "bool"),
    ),
    fks=(
        FKSpec("employee_id", "employees", "employee_id"),
        FKSpec("application_id", "applications", "application_id"),
    ),
)

IAM = DatasetConfig(
    dataset_type=DatasetType.IAM_RECORDS,
    filename="dataset15_identity_access_management.csv",
    model=IAMRecord,
    pk="iam_user_id",
    fields=(
        FieldSpec("UserID", "iam_user_id"),
        FieldSpec("EmployeeID", "employee_id"),
        FieldSpec("Role", "role"),
        FieldSpec("Privileges", "privileges"),
        FieldSpec("PrivilegedAccount", "privileged_account", "bool"),
        FieldSpec("MFAEnabled", "mfa_enabled", "bool"),
        FieldSpec("InactiveDays", "inactive_days", "int"),
        FieldSpec("LastPrivilegeReview", "last_privilege_review", "date"),
    ),
    fks=(FKSpec("employee_id", "employees", "employee_id"),),
)

AUDIT_LOGS = DatasetConfig(
    dataset_type=DatasetType.AUDIT_LOGS,
    filename="dataset9_audit_logs.csv",
    model=AuditLog,
    pk="log_id",
    fields=(
        FieldSpec("LogID", "log_id"),
        FieldSpec("Timestamp", "timestamp", "datetime"),
        FieldSpec("EmployeeID", "employee_id", nullable=True),
        FieldSpec("ApplicationID", "application_id", nullable=True),
        FieldSpec("Action", "action"),
        FieldSpec("IPAddress", "ip_address"),
        FieldSpec("GeoLocation", "geo_location"),
        FieldSpec("Result", "result"),
        FieldSpec("RiskScore", "risk_score", "int"),
    ),
    fks=(
        FKSpec("employee_id", "employees", "employee_id", nullable=True),
        FKSpec("application_id", "applications", "application_id", nullable=True),
    ),
)


# FK-safe load order (HANDOFF.md §13). Order matters — do not shuffle.
LOAD_ORDER: tuple[DatasetConfig, ...] = (
    EMPLOYEES,
    DEVICES,
    CLOUD_ASSETS,
    APPLICATIONS,
    VENDORS,
    POLICIES,
    CONTROLS,
    RISKS,
    EVIDENCE,
    FINDINGS,
    REPORTS,
    PERSONAL_DATA,
    CONSENTS,
    IAM,
    AUDIT_LOGS,
)

BY_NAME: dict[str, DatasetConfig] = {c.dataset_type.value: c for c in LOAD_ORDER}
