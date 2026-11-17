"""
The central permission matrix: which role may do what to which resource.

This is the single source of truth for authorization. Everything else
(route guards, row scoping, the AI query engine's table allow-list, the
`permissions` list returned by /auth/me) is derived from it.

Rules:
  * Default deny. A (role, resource, action) combination that is not written
    down here is refused — including resources and actions nobody has
    thought of yet.
  * The role is always read from the database row of the authenticated user,
    never from a token claim.
  * Sentinel is single-tenant. This matrix separates roles and, for the
    employee role, individual people. It does not provide tenant isolation.

Resource names are the URL segments of the dataset endpoints
(`app/api/v1/resources.py`) plus a few names for compound endpoints.

Who the roles are:
  admin               platform administrator — full read
  compliance_officer  runs the GRC and privacy programme — full read
  security_analyst    security operations — everything except individual
                      consent records, which are privacy-programme data
  auditor             external auditor — governance, risk and asset
                      inventory; no per-person records (employees, devices,
                      IAM, consents, audit logs)
  employee            self-service only — their own records, and policies
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import UserRole as R

READ = "read"
QUERY = "query"  # ask the AI engine a question (it reads on the caller's behalf)
INGEST = "ingest"  # add records to the security-event store
MEASURE = "measure"  # record a point in a score's history
RUN = "run"  # start a detection run

_ALL_STAFF = frozenset({R.ADMIN, R.COMPLIANCE_OFFICER, R.SECURITY_ANALYST, R.AUDITOR})
_INTERNAL_STAFF = frozenset({R.ADMIN, R.COMPLIANCE_OFFICER, R.SECURITY_ANALYST})
_PRIVACY_STAFF = frozenset({R.ADMIN, R.COMPLIANCE_OFFICER})
_SELF = frozenset({R.EMPLOYEE})  # always combined with a row scope below

MATRIX: dict[str, dict[str, frozenset[R]]] = {
    # --- per-person records -------------------------------------------
    "employees": {READ: _INTERNAL_STAFF | _SELF},
    "devices": {READ: _INTERNAL_STAFF | _SELF},
    "iam": {READ: _INTERNAL_STAFF | _SELF},
    "audit-logs": {READ: _INTERNAL_STAFF},
    "dpdp/consents": {READ: _PRIVACY_STAFF | _SELF},
    # Raw records of what individual accounts did. Only an admin may add to
    # them; nobody may change them (there is no such action to grant).
    "security-events": {READ: _INTERNAL_STAFF, INGEST: frozenset({R.ADMIN})},
    # Rules hold no personal data; alerts cite per-person events.
    "detection-rules": {READ: _ALL_STAFF},
    "detections": {READ: _INTERNAL_STAFF, RUN: frozenset({R.ADMIN, R.SECURITY_ANALYST})},
    # --- asset inventory ----------------------------------------------
    "cloud-assets": {READ: _ALL_STAFF},
    "applications": {READ: _ALL_STAFF},
    "vendors": {READ: _ALL_STAFF},
    "dpdp/personal-data": {READ: _ALL_STAFF},  # inventory of data categories, not personal records
    # --- governance and risk ------------------------------------------
    "policies": {READ: _ALL_STAFF | _SELF},  # every employee may read company policy
    "controls": {READ: _ALL_STAFF},
    "risks": {READ: _ALL_STAFF},
    "evidence": {READ: _ALL_STAFF},
    "findings": {READ: _ALL_STAFF},
    "reports": {READ: _ALL_STAFF},
    # --- compound endpoints -------------------------------------------
    # These only open the door. Each one additionally requires READ on every
    # dataset it actually returns rows from — see the routers.
    "dashboard": {READ: _ALL_STAFF},
    "frameworks": {READ: _ALL_STAFF},
    "organization-graph": {READ: _ALL_STAFF},
    # MEASURE: add a point to the trust score's history. Limited to the people
    # accountable for the programme the score describes.
    "intelligence": {READ: _ALL_STAFF, MEASURE: frozenset({R.ADMIN, R.COMPLIANCE_OFFICER})},
    "copilot": {READ: _ALL_STAFF, QUERY: _ALL_STAFF},
}

# Roles that hold READ on a resource only for rows that belong to them:
# role -> resource -> column that must equal the user's own employee_id.
OWN_ROWS_ONLY: dict[R, dict[str, str]] = {
    R.EMPLOYEE: {
        "employees": "employee_id",
        "devices": "employee_id",
        "iam": "employee_id",
        "dpdp/consents": "employee_id",
    },
}


def is_allowed(role: R, resource: str, action: str = READ) -> bool:
    return role in MATRIX.get(resource, {}).get(action, frozenset())


def readable_resources(role: R) -> list[str]:
    return sorted(resource for resource in MATRIX if is_allowed(role, resource, READ))


@dataclass(frozen=True)
class RowScope:
    """Every row returned must have `column == value`. A `value` of None means
    the account is not linked to any record, so it matches nothing — never
    "rows where the column is NULL"."""

    column: str
    value: str | None


def row_scope(role: R, employee_id: str | None, resource: str) -> RowScope | None:
    """The restriction that applies to this caller on this resource, or None
    when the role may read every row."""
    column = OWN_ROWS_ONLY.get(role, {}).get(resource)
    return RowScope(column, employee_id) if column else None


def is_unrestricted(role: R, resource: str) -> bool:
    """True only when the role may read every row of the resource."""
    return is_allowed(role, resource, READ) and resource not in OWN_ROWS_ONLY.get(role, {})
