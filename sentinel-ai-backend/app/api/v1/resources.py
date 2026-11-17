"""
The declarative registry of plain dataset resources.

Each entry becomes `GET /api/v1/<name>` + `GET /api/v1/<name>/{id}` via
the router factory. Filter/search/sort fields are chosen from columns that
actually exist and that the frontend screens actually filter on — adding a
filter here is a one-line change, which is the point.
"""
from __future__ import annotations

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
from app.core.permissions import is_unrestricted
from app.models.enums import UserRole
from app.schemas import resources as s
from app.services.resource import ResourceSpec

RESOURCES: tuple[ResourceSpec, ...] = (
    ResourceSpec(
        name="employees",
        model=Employee,
        pk="employee_id",
        schema=s.EmployeeOut,
        tag="employees",
        search_fields=("employee_id", "first_name", "last_name", "email", "designation"),
        filter_fields=("department", "account_status", "employment_type", "mfa_enabled", "office_location", "manager_id"),
        sort_fields=("employee_id", "last_name", "department", "joining_date", "last_login"),
        description="Enterprise employees (dataset1).",
        has_custom_detail=True,
    ),
    ResourceSpec(
        name="devices",
        model=Device,
        pk="device_id",
        schema=s.DeviceOut,
        tag="devices",
        search_fields=("device_id", "employee_id", "operating_system", "os_version"),
        filter_fields=("device_type", "operating_system", "compliance_status", "risk_level", "employee_id", "encryption_enabled", "edr_installed"),
        sort_fields=("device_id", "risk_level", "last_patch_date", "compliance_status"),
        description="Managed enterprise devices (dataset2).",
    ),
    ResourceSpec(
        name="cloud-assets",
        model=CloudAsset,
        pk="resource_id",
        schema=s.CloudAssetOut,
        tag="cloud-assets",
        search_fields=("resource_id", "resource_type", "region", "owner_employee_id"),
        filter_fields=("cloud_provider", "resource_type", "region", "criticality", "risk_level", "public_access", "encryption_enabled", "logging_enabled", "owner_employee_id"),
        sort_fields=("resource_id", "risk_level", "criticality", "cloud_provider"),
        description="Cloud resources across providers (dataset3).",
    ),
    ResourceSpec(
        name="applications",
        model=Application,
        pk="application_id",
        schema=s.ApplicationOut,
        tag="applications",
        search_fields=("application_id", "application_name", "owner_department"),
        filter_fields=("owner_department", "data_classification", "risk_level", "internet_facing", "uses_mfa", "encryption_enabled"),
        sort_fields=("application_id", "application_name", "risk_level"),
        description="Business applications (dataset4).",
        has_custom_detail=True,
    ),
    ResourceSpec(
        name="vendors",
        model=Vendor,
        pk="vendor_id",
        schema=s.VendorOut,
        tag="vendors",
        search_fields=("vendor_id", "vendor_name", "service_category"),
        filter_fields=("service_category", "risk_rating", "iso27001_certified", "soc2_certified", "dpdp_compliant"),
        sort_fields=("vendor_id", "vendor_name", "risk_rating", "contract_expiry"),
        description="Third-party vendors (dataset5). Island table — no FK to risks or controls in the source data.",
    ),
    ResourceSpec(
        name="policies",
        model=Policy,
        pk="policy_id",
        schema=s.PolicyOut,
        tag="policies",
        search_fields=("policy_id", "policy_name", "category"),
        filter_fields=("framework", "category", "mandatory", "owner_department"),
        sort_fields=("policy_id", "policy_name", "framework"),
        description="Security policies (dataset6).",
        has_custom_detail=True,
    ),
    ResourceSpec(
        name="controls",
        model=Control,
        pk="control_id",
        schema=s.ControlOut,
        tag="controls",
        search_fields=("control_id", "control_name", "description"),
        filter_fields=("policy_id", "severity", "automation_possible", "evidence_required"),
        sort_fields=("control_id", "control_name", "severity"),
        description="Compliance controls (dataset7). Each maps to exactly one policy.",
        has_custom_detail=True,
    ),
    ResourceSpec(
        name="risks",
        model=Risk,
        pk="risk_id",
        schema=s.RiskOut,
        tag="risks",
        search_fields=("risk_id", "risk_name", "description", "business_impact"),
        filter_fields=("severity", "likelihood", "current_status", "owner_department", "mapped_control_id"),
        sort_fields=("risk_id", "risk_name", "severity", "likelihood", "current_status"),
        description="Risk register (dataset8).",
        has_custom_detail=True,
    ),
    ResourceSpec(
        name="evidence",
        model=Evidence,
        pk="evidence_id",
        schema=s.EvidenceOut,
        tag="evidence",
        search_fields=("evidence_id", "control_id", "evidence_type", "evidence_location"),
        filter_fields=("control_id", "evidence_type", "verified", "collected_automatically"),
        sort_fields=("evidence_id", "collected_date", "evidence_type"),
        description="Evidence repository (dataset10).",
        has_custom_detail=True,
    ),
    ResourceSpec(
        name="findings",
        model=Finding,
        pk="finding_id",
        schema=s.FindingOut,
        tag="findings",
        search_fields=("finding_id", "description", "recommendation", "control_id"),
        filter_fields=("severity", "status", "control_id", "evidence_id"),
        sort_fields=("finding_id", "severity", "status"),
        description="Compliance findings (dataset11).",
        has_custom_detail=True,
    ),
    ResourceSpec(
        name="reports",
        model=Report,
        pk="report_id",
        schema=s.ReportOut,
        tag="reports",
        search_fields=("report_id", "framework", "compliance_status"),
        filter_fields=("framework", "compliance_status"),
        sort_fields=("report_id", "generated_date", "overall_score", "framework"),
        description="Compliance reports (dataset12). Framework-level rollups — no FK to individual findings.",
    ),
    ResourceSpec(
        name="dpdp/personal-data",
        model=PersonalDataInventory,
        pk="data_id",
        schema=s.PersonalDataOut,
        tag="dpdp",
        search_fields=("data_id", "data_category", "purpose_of_processing", "application_id"),
        filter_fields=("application_id", "data_category", "third_party_sharing", "encryption_enabled", "consent_required"),
        sort_fields=("data_id", "data_category"),
        description="DPDP personal data inventory (dataset13).",
    ),
    ResourceSpec(
        name="dpdp/consents",
        model=ConsentRecord,
        pk="consent_id",
        schema=s.ConsentOut,
        tag="dpdp",
        search_fields=("consent_id", "employee_id", "application_id"),
        filter_fields=("employee_id", "application_id", "consent_given", "revoked"),
        sort_fields=("consent_id", "consent_date", "expiry_date"),
        description="DPDP consent records (dataset14). Not FK-linked to personal-data; both join via applications.",
    ),
    ResourceSpec(
        name="iam",
        model=IAMRecord,
        pk="iam_user_id",
        schema=s.IAMOut,
        tag="iam",
        search_fields=("iam_user_id", "employee_id", "role", "privileges"),
        filter_fields=("employee_id", "role", "privileged_account", "mfa_enabled"),
        sort_fields=("iam_user_id", "inactive_days", "last_privilege_review", "role"),
        description="Identity & access records (dataset15).",
    ),
    ResourceSpec(
        name="audit-logs",
        model=AuditLog,
        pk="log_id",
        schema=s.AuditLogOut,
        tag="audit-logs",
        search_fields=("log_id", "employee_id", "application_id", "ip_address", "geo_location"),
        filter_fields=("employee_id", "application_id", "action", "result", "geo_location"),
        sort_fields=("log_id", "timestamp", "risk_score"),
        description=(
            "Audit logs (dataset9, 10,000 rows — always paginate). Extra query params: "
            "`date_from`/`date_to` (ISO date or datetime) and `min_risk_score`."
        ),
    ),
)

BY_NAME = {spec.name: spec for spec in RESOURCES}


def readable_tables(role: UserRole) -> frozenset[str]:
    """Database tables this role may read every row of — the allow-list handed
    to the AI query engine. Tables a role can only read its own rows of are
    excluded, because the engine does not apply row scopes."""
    return frozenset(spec.model.__tablename__ for spec in RESOURCES if is_unrestricted(role, spec.name))
