"""
Shared enum reference values.

Design note (Phase 1 report item D2): categorical dataset columns
(Severity, RiskLevel, Department, ...) are stored as plain `String`
columns in Postgres, NOT native Postgres ENUM types. A hard DB enum
would reject an entire ingestion row the moment a source system
introduces one new category value — which is exactly the kind of
"architecture must not require modification when datasets change"
brittleness the approved architecture explicitly warns against
(original doc, Section 13). Validity is instead checked at the
ingestion/Pydantic layer, where an unexpected value can be logged and
the row still processed, rather than the whole import failing.

Only genuinely platform-internal enums (things we invented, not values
that came from a source file) use real Postgres ENUM types — see
UserRole and the ingestion-status enums in app/models/ingestion.py and
app/models/auth.py.
"""
from enum import Enum


class UserRole(str, Enum):
    """The 5 roles required by Phase 1 Step 7. Deliberately flat — no
    separate roles/permissions join tables, per 'do not over-engineer
    authentication' / 'functional RBAC foundation for the demo'."""
    ADMIN = "admin"
    COMPLIANCE_OFFICER = "compliance_officer"
    SECURITY_ANALYST = "security_analyst"
    AUDITOR = "auditor"
    EMPLOYEE = "employee"


class SeverityLevel(str, Enum):
    """Reference values observed across Findings/Controls/Risks severity
    and Devices/CloudAssets/Applications/Vendors risk columns — same 4
    values everywhere per the empirical relationship-discovery pass."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class IngestionStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionLogLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DatasetType(str, Enum):
    """The 15 repository datasets, in their verified FK-safe load order
    (see app/ingestion/configs/registry.py for the rationale)."""
    EMPLOYEES = "employees"
    DEVICES = "devices"
    CLOUD_ASSETS = "cloud_assets"
    APPLICATIONS = "applications"
    VENDORS = "vendors"
    POLICIES = "policies"
    CONTROLS = "controls"
    RISKS = "risks"
    EVIDENCE = "evidence"
    FINDINGS = "findings"
    REPORTS = "reports"
    PERSONAL_DATA_INVENTORY = "personal_data_inventory"
    CONSENT_RECORDS = "consent_records"
    IAM_RECORDS = "iam_records"
    AUDIT_LOGS = "audit_logs"
