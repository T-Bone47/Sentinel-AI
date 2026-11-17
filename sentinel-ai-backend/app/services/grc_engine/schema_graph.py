"""
Ground-truth schema graph for the general-purpose GRC reasoning engine.

WHY THIS FILE EXISTS AND WHY IT IS HAND-WRITTEN, NOT LLM-DERIVED:

The brief for this engine is explicit: "Do not assume relationships that do
not exist. Inspect the database schema before implementing query logic."
This file *is* that inspection, made durable. Every table, column, and edge
below was read directly from PostgreSQL's own catalog
(`information_schema.columns` / `information_schema.table_constraints`)
against the real, fully-ingested database — not copied from a docstring,
not inferred from column-name conventions, and not left to the LLM to guess
at request time. The LLM never sees the raw database; it only ever sees
`describe_for_llm()`'s output, which is this file's contents rendered as
text. If a relationship isn't declared here, no code path in this engine
can join across it, no matter what the model asks for.

This is also where every known "the data doesn't actually connect the way
you'd expect" gap is recorded, because that turned out to matter as much as
what *does* connect:

  - `vendors` and `reports` have ZERO foreign keys to anything else (besides
    ingestion lineage). Every "which vendors handle personal data" or
    "which vendors have unresolved risks" style question is UNANSWERABLE
    from real relationships — vendors carry only their own attributes
    (certifications, risk_rating). The existing DashboardService already
    encodes this as `"note": "Vendors are an island dataset — no verified
    FK to risks or controls."`; ROUTING must inherit that honesty rather
    than silently join on a shared name/category string.
  - `iam_records` has no `application_id`. "Which employees have access to
    critical applications without MFA" — a literal example from the brief
    — cannot be answered via a real join; `iam_records.role`/`.privileges`
    are free text, not foreign keys to `applications`.
  - `personal_data_inventory` and `consent_records` do not reference each
    other directly. Both reference `applications`, so a join *through*
    `applications` is legitimate (same application, so a real correlation),
    but it is an indirect, application-level correlation, not a per-record
    link, and callers should say so.
  - `evidence.collected_date` gives a real, computable AGE ("collected N
    days ago"). It gives no defined FRESHNESS/STALENESS threshold — there
    is no policy-defined "evidence expires after N days" anywhere in this
    dataset (unlike `consent_records.expiry_date` or
    `vendors.contract_expiry`, which are real expiry dates). Age is a fact;
    "stale" is a judgment this engine must not invent a threshold for.

Row-level access here is intentionally read-only in spirit: this graph is
consumed only to build SELECT-shaped `QueryPlan`s (see query_dsl.py); there
is no representation of INSERT/UPDATE/DELETE anywhere in this module, so
there is nothing for a downstream compiler to accidentally support.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    type: str  # coarse type: "string" | "boolean" | "integer" | "date" | "timestamp" | "text"
    description: str = ""
    # For low-cardinality string columns, the real distinct values seen in
    # the data, so the LLM can be told the exact vocabulary instead of
    # guessing capitalization/spelling (e.g. "Critical" vs "critical").
    enum_values: tuple[str, ...] | None = None


@dataclass(frozen=True)
class TableInfo:
    name: str
    primary_key: str
    description: str
    columns: dict[str, ColumnInfo]
    # Real, FK-verified outbound edges only: local_column -> (target_table, target_column)
    foreign_keys: dict[str, tuple[str, str]] = field(default_factory=dict)
    notes: tuple[str, ...] = ()


def _cols(*infos: ColumnInfo) -> dict[str, ColumnInfo]:
    return {c.name: c for c in infos}


SEVERITY = ("Critical", "High", "Medium", "Low")

# ---------------------------------------------------------------------------
# The 15 business tables (ingestion_jobs/ingestion_logs/users/
# trust_score_snapshots/alembic_version are infrastructure, not GRC data,
# and are deliberately absent — nothing in this engine can ever select from
# them, because they are simply not part of the graph).
# ---------------------------------------------------------------------------
TABLES: dict[str, TableInfo] = {
    "employees": TableInfo(
        name="employees",
        primary_key="employee_id",
        description="Workforce roster.",
        columns=_cols(
            ColumnInfo("employee_id", "string"),
            ColumnInfo("first_name", "string"),
            ColumnInfo("last_name", "string"),
            ColumnInfo("email", "string"),
            ColumnInfo("department", "string"),
            ColumnInfo("designation", "string"),
            ColumnInfo("manager_id", "string", "self-referential: another employees.employee_id"),
            ColumnInfo("office_location", "string"),
            ColumnInfo("employment_type", "string"),
            ColumnInfo("joining_date", "date"),
            ColumnInfo("password_length", "integer"),
            ColumnInfo("password_last_changed", "date"),
            ColumnInfo("mfa_enabled", "boolean", "account-level MFA, distinct from iam_records.mfa_enabled (per-access-role MFA)"),
            ColumnInfo("account_status", "string", enum_values=("Active", "Inactive", "Suspended")),
            ColumnInfo("last_login", "timestamp"),
        ),
        foreign_keys={"manager_id": ("employees", "employee_id")},
    ),
    "devices": TableInfo(
        name="devices",
        primary_key="device_id",
        description="Endpoint devices, one row per device, each owned by exactly one employee.",
        columns=_cols(
            ColumnInfo("device_id", "string"),
            ColumnInfo("employee_id", "string"),
            ColumnInfo("device_type", "string"),
            ColumnInfo("operating_system", "string"),
            ColumnInfo("os_version", "string"),
            ColumnInfo("encryption_enabled", "boolean"),
            ColumnInfo("firewall_enabled", "boolean"),
            ColumnInfo("antivirus_installed", "boolean"),
            ColumnInfo("edr_installed", "boolean"),
            ColumnInfo("compliance_status", "string"),
            ColumnInfo("risk_level", "string", enum_values=SEVERITY),
            ColumnInfo("last_patch_date", "date"),
        ),
        foreign_keys={"employee_id": ("employees", "employee_id")},
        notes=(
            "employees.device_id exists as a plain column but is NOT a "
            "database foreign key (unenforced) — do not rely on it as a "
            "join path; use devices.employee_id -> employees instead.",
        ),
    ),
    "cloud_assets": TableInfo(
        name="cloud_assets",
        primary_key="resource_id",
        description="Cloud infrastructure resources.",
        columns=_cols(
            ColumnInfo("resource_id", "string"),
            ColumnInfo("cloud_provider", "string"),
            ColumnInfo("resource_type", "string"),
            ColumnInfo("region", "string"),
            ColumnInfo("owner_employee_id", "string"),
            ColumnInfo("public_access", "boolean"),
            ColumnInfo("encryption_enabled", "boolean"),
            ColumnInfo("logging_enabled", "boolean"),
            ColumnInfo("criticality", "string", enum_values=SEVERITY),
            ColumnInfo("risk_level", "string", enum_values=SEVERITY),
        ),
        foreign_keys={"owner_employee_id": ("employees", "employee_id")},
    ),
    "applications": TableInfo(
        name="applications",
        primary_key="application_id",
        description="Software applications the org runs.",
        columns=_cols(
            ColumnInfo("application_id", "string"),
            ColumnInfo("application_name", "string"),
            ColumnInfo("owner_department", "string"),
            ColumnInfo("authentication_method", "string"),
            ColumnInfo("uses_mfa", "boolean"),
            ColumnInfo("encryption_enabled", "boolean"),
            ColumnInfo("data_classification", "string", "e.g. Public/Internal/Confidential — the 'sensitive data' signal for applications"),
            ColumnInfo("internet_facing", "boolean"),
            ColumnInfo("risk_level", "string", enum_values=SEVERITY),
        ),
        foreign_keys={},
        notes=(
            "No FK from iam_records to applications exists. 'Which "
            "employees have IAM access to this application' is NOT "
            "answerable from real relationships in this schema.",
        ),
    ),
    "vendors": TableInfo(
        name="vendors",
        primary_key="vendor_id",
        description="Third-party vendors.",
        columns=_cols(
            ColumnInfo("vendor_id", "string"),
            ColumnInfo("vendor_name", "string"),
            ColumnInfo("service_category", "string"),
            ColumnInfo("iso27001_certified", "boolean"),
            ColumnInfo("soc2_certified", "boolean"),
            ColumnInfo("dpdp_compliant", "boolean"),
            ColumnInfo("risk_rating", "string", enum_values=SEVERITY),
            ColumnInfo("contract_expiry", "date"),
        ),
        foreign_keys={},
        notes=(
            "ISLAND TABLE: zero foreign keys to any other table. Vendor "
            "risk can ONLY be assessed from vendors' own columns "
            "(risk_rating, certifications, contract_expiry). Any question "
            "implying vendor -> risk / vendor -> personal-data / vendor -> "
            "control linkage has NO real join path — say so explicitly, "
            "do not join on vendor_name/service_category text similarity.",
        ),
    ),
    "policies": TableInfo(
        name="policies",
        primary_key="policy_id",
        description="Governance policies.",
        columns=_cols(
            ColumnInfo("policy_id", "string"),
            ColumnInfo("policy_name", "string"),
            ColumnInfo("framework", "string"),
            ColumnInfo("category", "string"),
            ColumnInfo("version", "string"),
            ColumnInfo("owner_department", "string"),
            ColumnInfo("mandatory", "boolean"),
        ),
        foreign_keys={},
    ),
    "controls": TableInfo(
        name="controls",
        primary_key="control_id",
        description="Compliance controls, each implementing exactly one policy.",
        columns=_cols(
            ColumnInfo("control_id", "string"),
            ColumnInfo("policy_id", "string"),
            ColumnInfo("control_name", "string"),
            ColumnInfo("description", "text"),
            ColumnInfo("severity", "string", enum_values=SEVERITY),
            ColumnInfo("automation_possible", "boolean"),
            ColumnInfo("evidence_required", "boolean"),
        ),
        foreign_keys={"policy_id": ("policies", "policy_id")},
    ),
    "risks": TableInfo(
        name="risks",
        primary_key="risk_id",
        description="Risk register.",
        columns=_cols(
            ColumnInfo("risk_id", "string"),
            ColumnInfo("risk_name", "string"),
            ColumnInfo("description", "text"),
            ColumnInfo("business_impact", "string"),
            ColumnInfo("likelihood", "string", enum_values=SEVERITY),
            ColumnInfo("severity", "string", enum_values=SEVERITY),
            ColumnInfo("owner_department", "string"),
            ColumnInfo("mapped_control_id", "string", "nullable — not every risk maps to a control"),
            ColumnInfo("current_status", "string", enum_values=("Open", "In Progress", "Mitigated", "Accepted", "Resolved", "Closed")),
            ColumnInfo("created_at", "timestamp", "usable as a proxy for 'how long has this been open' via now() - created_at"),
        ),
        foreign_keys={"mapped_control_id": ("controls", "control_id")},
        notes=("mapped_control_id is nullable; not every risk has a mapped control.",),
    ),
    "evidence": TableInfo(
        name="evidence",
        primary_key="evidence_id",
        description="Evidence artifacts supporting controls.",
        columns=_cols(
            ColumnInfo("evidence_id", "string"),
            ColumnInfo("control_id", "string"),
            ColumnInfo("evidence_type", "string"),
            ColumnInfo("evidence_location", "string"),
            ColumnInfo("collected_date", "date", "gives AGE (now() - collected_date); NOT a freshness/expiry verdict — no staleness threshold is defined anywhere in this dataset"),
            ColumnInfo("verified", "boolean"),
            ColumnInfo("collected_automatically", "boolean"),
        ),
        foreign_keys={"control_id": ("controls", "control_id")},
    ),
    "findings": TableInfo(
        name="findings",
        primary_key="finding_id",
        description="Compliance findings against controls.",
        columns=_cols(
            ColumnInfo("finding_id", "string"),
            ColumnInfo("control_id", "string"),
            ColumnInfo("severity", "string", enum_values=SEVERITY),
            ColumnInfo("description", "text"),
            ColumnInfo("evidence_id", "string", "nullable"),
            ColumnInfo("recommendation", "text", "the actual recommended fix, already authored — not something to invent"),
            ColumnInfo("status", "string", enum_values=("Open", "In Progress", "Resolved", "Closed", "Accepted Risk")),
        ),
        foreign_keys={
            "control_id": ("controls", "control_id"),
            "evidence_id": ("evidence", "evidence_id"),
        },
    ),
    "reports": TableInfo(
        name="reports",
        primary_key="report_id",
        description="Point-in-time compliance report snapshots. Self-contained summary counts.",
        columns=_cols(
            ColumnInfo("report_id", "string"),
            ColumnInfo("framework", "string"),
            ColumnInfo("generated_date", "date"),
            ColumnInfo("overall_score", "integer"),
            ColumnInfo("critical_findings", "integer"),
            ColumnInfo("high_findings", "integer"),
            ColumnInfo("medium_findings", "integer"),
            ColumnInfo("low_findings", "integer"),
            ColumnInfo("compliance_status", "string"),
        ),
        foreign_keys={},
        notes=(
            "ISLAND TABLE: zero foreign keys in or out. The *_findings "
            "columns are pre-aggregated counts from when the report was "
            "generated, NOT joinable to individual rows in `findings`.",
        ),
    ),
    "personal_data_inventory": TableInfo(
        name="personal_data_inventory",
        primary_key="data_id",
        description="DPDP personal-data inventory.",
        columns=_cols(
            ColumnInfo("data_id", "string"),
            ColumnInfo("application_id", "string"),
            ColumnInfo("data_category", "string"),
            ColumnInfo("purpose_of_processing", "string"),
            ColumnInfo("retention_period", "string"),
            ColumnInfo("third_party_sharing", "boolean"),
            ColumnInfo("encryption_enabled", "boolean"),
            ColumnInfo("consent_required", "boolean"),
        ),
        foreign_keys={"application_id": ("applications", "application_id")},
    ),
    "consent_records": TableInfo(
        name="consent_records",
        primary_key="consent_id",
        description="DPDP consent records.",
        columns=_cols(
            ColumnInfo("consent_id", "string"),
            ColumnInfo("employee_id", "string"),
            ColumnInfo("application_id", "string"),
            ColumnInfo("consent_given", "boolean"),
            ColumnInfo("consent_date", "date"),
            ColumnInfo("expiry_date", "date"),
            ColumnInfo("revoked", "boolean"),
        ),
        foreign_keys={
            "employee_id": ("employees", "employee_id"),
            "application_id": ("applications", "application_id"),
        },
        notes=(
            "No direct FK to personal_data_inventory. Both tables "
            "reference applications, so a same-application correlation is "
            "legitimate via a two-hop join through applications — but it "
            "is application-level, not a verified per-record link.",
        ),
    ),
    "iam_records": TableInfo(
        name="iam_records",
        primary_key="iam_user_id",
        description="Identity & access management grants.",
        columns=_cols(
            ColumnInfo("iam_user_id", "string"),
            ColumnInfo("employee_id", "string"),
            ColumnInfo("role", "string"),
            ColumnInfo("privileges", "text", "free text, NOT a foreign key to any table"),
            ColumnInfo("privileged_account", "boolean"),
            ColumnInfo("mfa_enabled", "boolean", "access-level MFA, distinct from employees.mfa_enabled (account-level MFA)"),
            ColumnInfo("inactive_days", "integer"),
            ColumnInfo("last_privilege_review", "date"),
        ),
        foreign_keys={"employee_id": ("employees", "employee_id")},
        notes=(
            "No application_id column exists on this table at all. "
            "'Access to application X' cannot be determined via a real "
            "join — role/privileges are free text.",
        ),
    ),
    "audit_logs": TableInfo(
        name="audit_logs",
        primary_key="log_id",
        description="System audit/activity log events.",
        columns=_cols(
            ColumnInfo("log_id", "string"),
            ColumnInfo("timestamp", "timestamp"),
            ColumnInfo("employee_id", "string", "nullable"),
            ColumnInfo("application_id", "string", "nullable"),
            ColumnInfo("action", "string"),
            ColumnInfo("ip_address", "string"),
            ColumnInfo("geo_location", "string"),
            ColumnInfo("result", "string", enum_values=("Success", "Failure")),
            ColumnInfo("risk_score", "integer", "0-100"),
        ),
        foreign_keys={
            "employee_id": ("employees", "employee_id"),
            "application_id": ("applications", "application_id"),
        },
    ),
}

# Pre-aggregated metric namespaces already computed correctly elsewhere in
# the codebase (DashboardService, TrustIntelligenceService,
# RiskIntelligenceService, EvidenceIntelligenceService). The reasoning layer
# prefers these over building an equivalent row-level query whenever a
# question is really asking for a count/rate/breakdown that one of these
# already answers — see metrics_catalog.py for the descriptions given to
# the LLM and the actual wiring.
METRIC_NAMESPACES = (
    "trust_score",
    "risks",
    "findings",
    "evidence_coverage",
    "compliance_coverage",
    "framework_status",
    "recent_audit_activity",
    "asset_statistics",
    "vendor_risk",
    "privacy_statistics",
    "iam_statistics",
)


def table_names() -> frozenset[str]:
    return frozenset(TABLES)


def is_valid_join(from_table: str, from_column: str, to_table: str, to_column: str) -> bool:
    """True only if this exact edge is a real, FK-verified relationship
    (in either direction) — the sole authority query_compiler consults."""
    t = TABLES.get(from_table)
    if t and t.foreign_keys.get(from_column) == (to_table, to_column):
        return True
    t2 = TABLES.get(to_table)
    if t2 and t2.foreign_keys.get(to_column) == (from_table, from_column):
        return True
    return False


def describe_for_llm() -> str:
    """Render the graph as compact text for the LLM prompt. Never sends raw
    rows — only table/column/type/enum/relationship metadata, which is not
    sensitive and is small enough to stay well within a reasonable prompt
    budget (~1.5KB) regardless of how large the underlying tables are."""
    lines: list[str] = []
    for t in TABLES.values():
        cols = ", ".join(
            f"{c.name}:{c.type}" + (f"[{'/'.join(c.enum_values)}]" if c.enum_values else "")
            for c in t.columns.values()
        )
        lines.append(f"TABLE {t.name} (pk={t.primary_key}): {cols}")
        if t.foreign_keys:
            edges = ", ".join(f"{col}->{tbl}.{tcol}" for col, (tbl, tcol) in t.foreign_keys.items())
            lines.append(f"  joins: {edges}")
        for note in t.notes:
            lines.append(f"  NOTE: {note}")
    lines.append(f"PRECOMPUTED METRICS AVAILABLE (prefer these over row queries for counts/rates): {', '.join(METRIC_NAMESPACES)}")
    return "\n".join(lines)
