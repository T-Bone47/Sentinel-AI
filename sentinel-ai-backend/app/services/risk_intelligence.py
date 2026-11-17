"""
Risk Intelligence — Phase 2, Priority 2.

Turns "show me risks" into "explain and prioritize risks", built entirely
on the same verified FK chain `detail_router.risk_detail` already walks
(risk -> control -> findings/evidence by control_id — see
docs/profiling/relationships.txt). This does not touch or duplicate that
endpoint; it adds the missing explanation layer on top: a numeric score
for ranking, a priority band, named risk drivers, a confidence label tied
to how much structured evidence actually exists for the risk, and a
template-based recommendation.

Honesty constraint the brief is explicit about: the real risk_register
data has NO structural FK to a specific employee/device/cloud_asset/
application/vendor row — only `owner_department`, a free-text field that
happens to share vocabulary with employees.department. "affected_assets"
below is reported as a department-level correlation and labelled as such,
never presented as a verified per-row relationship, because that
relationship does not exist in the data.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CloudAsset, Control, Device, Employee, Evidence, Finding, Risk

SEVERITY_SCORE = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
LIKELIHOOD_SCORE = {"High": 3, "Medium": 2, "Low": 1}
OPEN_FINDING_STATUSES = ("Open", "In Progress")


def _priority(score: int) -> str:
    if score >= 10:
        return "Critical"
    if score >= 6:
        return "High"
    if score >= 3:
        return "Medium"
    return "Low"


class RiskIntelligenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def top_risks(self, limit: int = 10) -> list[dict[str, Any]]:
        stmt = select(Risk).where(Risk.current_status.in_(("Open", "In Remediation")))
        risks = (await self.db.execute(stmt)).scalars().all()
        explained = [await self._explain(risk, include_affected_assets=False) for risk in risks]
        explained.sort(key=lambda r: r["risk_score"], reverse=True)
        return explained[:limit]

    async def explain(self, risk_id: str) -> dict[str, Any] | None:
        risk = (
            await self.db.execute(select(Risk).where(Risk.risk_id == risk_id))
        ).scalar_one_or_none()
        if risk is None:
            return None
        return await self._explain(risk, include_affected_assets=True)

    async def _explain(self, risk: Risk, *, include_affected_assets: bool) -> dict[str, Any]:
        db = self.db
        severity_pts = SEVERITY_SCORE.get(risk.severity, 1)
        likelihood_pts = LIKELIHOOD_SCORE.get(risk.likelihood, 1)
        risk_score = severity_pts * likelihood_pts

        control = None
        if risk.mapped_control_id:
            control = (
                await db.execute(select(Control).where(Control.control_id == risk.mapped_control_id))
            ).scalar_one_or_none()

        related_findings: list[Finding] = []
        related_evidence: list[Evidence] = []
        if control is not None:
            related_findings = list(
                (
                    await db.execute(select(Finding).where(Finding.control_id == control.control_id))
                ).scalars()
            )
            related_evidence = list(
                (
                    await db.execute(select(Evidence).where(Evidence.control_id == control.control_id))
                ).scalars()
            )

        open_findings = [f for f in related_findings if f.status in OPEN_FINDING_STATUSES]
        verified_evidence = [e for e in related_evidence if e.verified]

        drivers = self._risk_drivers(risk, control, open_findings, related_evidence)
        confidence = self._confidence(risk, control, related_findings, related_evidence)
        recommended_action = self._recommend(risk, control, open_findings)

        result: dict[str, Any] = {
            "risk_id": risk.risk_id,
            "risk_name": risk.risk_name,
            "risk_score": risk_score,
            "severity": risk.severity,
            "likelihood": risk.likelihood,
            "priority": _priority(risk_score),
            "current_status": risk.current_status,
            "business_impact": risk.business_impact,
            "owner_department": risk.owner_department,
            "affected_controls": [control.control_id] if control else [],
            "control_name": control.control_name if control else None,
            "related_findings": [
                {"finding_id": f.finding_id, "severity": f.severity, "status": f.status}
                for f in related_findings
            ],
            "related_evidence": [
                {"evidence_id": e.evidence_id, "evidence_type": e.evidence_type, "verified": e.verified}
                for e in related_evidence
            ],
            "open_finding_count": len(open_findings),
            "verified_evidence_count": len(verified_evidence),
            "risk_drivers": drivers,
            "recommended_action": recommended_action,
            "confidence": confidence,
        }

        if include_affected_assets:
            result["affected_assets"] = await self._department_footprint(risk.owner_department)

        return result

    async def _department_footprint(self, department: str) -> dict[str, Any]:
        """NOT a verified per-row relationship — see module docstring.
        Counts of assets that share the risk's owning department, offered
        as directional context only."""
        db = self.db
        employees = await db.scalar(
            select(func.count()).select_from(Employee).where(Employee.department == department)
        )
        devices = await db.scalar(
            select(func.count())
            .select_from(Device)
            .join(Employee, Device.employee_id == Employee.employee_id)
            .where(Employee.department == department)
        )
        cloud_assets = await db.scalar(
            select(func.count())
            .select_from(CloudAsset)
            .join(Employee, CloudAsset.owner_employee_id == Employee.employee_id)
            .where(Employee.department == department)
        )
        return {
            "basis": "department-level correlation via owner_department — "
            "not a verified per-row FK, no such relationship exists in the source data",
            "department": department,
            "employees_in_department": employees or 0,
            "devices_owned_in_department": devices or 0,
            "cloud_assets_owned_in_department": cloud_assets or 0,
        }

    @staticmethod
    def _risk_drivers(
        risk: Risk, control: Control | None, open_findings: list[Finding], evidence: list[Evidence]
    ) -> list[str]:
        drivers = [f"Risk recorded at {risk.severity} severity, {risk.likelihood} likelihood."]
        if control is None:
            drivers.append("No control is mapped to this risk — nothing structured explains it further.")
            return drivers
        drivers.append(f"Mapped to control '{control.control_name}' ({control.severity} severity).")
        if open_findings:
            drivers.append(f"{len(open_findings)} open finding(s) on that control keep it active.")
        else:
            drivers.append("No open findings on the mapped control right now.")
        if not evidence:
            drivers.append("The mapped control has zero evidence on file.")
        elif not any(e.verified for e in evidence):
            drivers.append(f"{len(evidence)} evidence item(s) exist but none are verified.")
        return drivers

    @staticmethod
    def _confidence(
        risk: Risk, control: Control | None, findings: list[Finding], evidence: list[Evidence]
    ) -> dict[str, Any]:
        """Deterministic proxy for confidence: how much structured data
        actually backs this explanation, not a model's self-reported
        certainty. Labelled accordingly."""
        if control is None:
            return {"level": "low", "basis": "risk has no mapped control — explanation relies on risk fields only"}
        if findings and evidence:
            return {"level": "high", "basis": "mapped control has both findings and evidence on record"}
        return {"level": "medium", "basis": "mapped control exists but findings or evidence are sparse"}

    @staticmethod
    def _recommend(risk: Risk, control: Control | None, open_findings: list[Finding]) -> dict[str, Any]:
        if control is None:
            action = f"Map '{risk.risk_name}' to a compliance control so it can be tracked and evidenced."
        elif open_findings:
            action = (
                f"Resolve {len(open_findings)} open finding(s) on control "
                f"'{control.control_name}' ({control.control_id}) to close out this risk."
            )
        else:
            action = f"Attach current evidence to control '{control.control_name}' to support this risk's status."
        return {"action": action, "generated_by": "deterministic_rules_v1"}
