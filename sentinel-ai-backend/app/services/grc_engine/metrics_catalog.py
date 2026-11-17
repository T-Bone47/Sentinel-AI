"""
Named, pre-computed metric namespaces for the reasoning layer.

Every number in this module comes from a service that already exists,
already has its own tests, and was explicitly NOT to be duplicated (the
first brief on this codebase was direct: "Do not replace working GRC
calculations"). This module adds no new arithmetic of its own — it is
purely a name -> awaitable-producer registry so the Question Understanding
step can ask for `"vendor_risk"` instead of the LLM having to know that
means calling `DashboardService.build()` and reading `.vendor_risk`.

Reusing DashboardService.build() for every namespace below, rather than
calling five separate services, is deliberate: it already computes risks/
findings/evidence_coverage/compliance_coverage/framework_status/
asset_statistics/vendor_risk/privacy_statistics/iam_statistics together in
one pass, so requesting three namespaces for one question costs one query
pass, not three.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dashboard import DashboardService
from app.services.evidence_intelligence import EvidenceIntelligenceService
from app.services.risk_intelligence import RiskIntelligenceService
from app.services.trust_intelligence import TrustIntelligenceService

# name -> (human description shown to the LLM, dashboard key or None if it
# needs its own service call)
_DASHBOARD_KEYS = {
    "risks": "risks",
    "findings": "findings",
    "evidence_coverage": "evidence_coverage",
    "compliance_coverage": "compliance_coverage",
    "framework_status": "framework_status",
    "recent_audit_activity": "recent_audit_activity",
    "asset_statistics": "asset_statistics",
    "vendor_risk": "vendor_risk",
    "privacy_statistics": "privacy_statistics",
    "iam_statistics": "iam_statistics",
}

NAMESPACE_DESCRIPTIONS = {
    "trust_score": "Overall Trust Score (0-100), band, and the 5 weighted contributors that produced it",
    "risks": "Risk register counts by severity/status/likelihood/department, open count, how many map to a control",
    "findings": "Finding counts by severity/status, open/critical/high-open counts, how many have evidence attached",
    "evidence_coverage": "Control-evidence coverage %, verified-evidence %, evidence by type",
    "compliance_coverage": "Pass/fail control counts and rate, mandatory-control coverage, policies by framework",
    "framework_status": "Per-framework (ISO 27001, SOC2, NIST, DPDP, CIS) compliance status",
    "recent_audit_activity": "Audit log activity in the most recent 7-day window, failures, high-risk events",
    "asset_statistics": "Employee/device/cloud-asset/application counts: MFA, encryption, compliance, public exposure",
    "vendor_risk": "Vendor counts by risk rating, certification coverage, DPDP compliance (vendors are an island table — attributes only, no verified link to risks/controls/personal data)",
    "privacy_statistics": "DPDP personal-data records, consent given/revoked/expired, third-party sharing, encryption",
    "iam_statistics": "IAM record counts, privileged accounts, MFA coverage, privileged-without-MFA count",
}


async def fetch(db: AsyncSession, namespaces: list[str]) -> dict[str, Any]:
    """Fetch exactly the requested namespaces (deduplicated), never more —
    the brief is explicit: 'Do not send the entire database to the LLM' /
    'aggregate large datasets before passing results to the LLM'. Unknown
    namespace names are silently dropped rather than raising, because a
    slightly-off namespace guess from the LLM should degrade to 'that one
    metric is missing', not fail the whole request."""
    wanted = [n for n in dict.fromkeys(namespaces) if n in NAMESPACE_DESCRIPTIONS]
    if not wanted:
        return {}

    out: dict[str, Any] = {}

    if "trust_score" in wanted:
        out["trust_score"] = await TrustIntelligenceService(db).build()

    dashboard_needed = [n for n in wanted if n in _DASHBOARD_KEYS]
    if dashboard_needed:
        dashboard = await DashboardService(db).build(include_scores=False)
        for name in dashboard_needed:
            out[name] = dashboard[_DASHBOARD_KEYS[name]]

    return out


def describe_for_llm() -> str:
    return "\n".join(f"- {name}: {desc}" for name, desc in NAMESPACE_DESCRIPTIONS.items())
