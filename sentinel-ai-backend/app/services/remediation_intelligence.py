"""
Remediation Intelligence — Phase 2, Priority 4.

Scans open findings, prioritizes them by severity, and returns deterministic
recommendations. Explains a specific finding to provide a step-by-step remediation plan
using the deterministic recommendation field, augmented by risk and control context.
"""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Control, Finding, Risk

SEVERITY_SCORE = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
OPEN_FINDING_STATUSES = ("Open", "In Progress")

class RemediationIntelligenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def top_remediations(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Returns the top open findings that require remediation, prioritized by severity.
        """
        stmt = select(Finding).where(Finding.status.in_(OPEN_FINDING_STATUSES))
        findings = (await self.db.execute(stmt)).scalars().all()
        
        explained_findings = []
        for finding in findings:
            explained = await self._explain_finding(finding)
            explained_findings.append(explained)
            
        explained_findings.sort(key=lambda f: SEVERITY_SCORE.get(f["severity"], 1), reverse=True)
        return explained_findings[:limit]

    async def explain_remediation(self, finding_id: str) -> dict[str, Any] | None:
        """
        Dives deep into a specific finding and its context.
        """
        finding = (
            await self.db.execute(select(Finding).where(Finding.finding_id == finding_id))
        ).scalar_one_or_none()
        
        if finding is None:
            return None
            
        return await self._explain_finding(finding)
        
    async def _explain_finding(self, finding: Finding) -> dict[str, Any]:
        """
        Gathers related control and risks to contextualize the remediation.
        """
        control = (
            await self.db.execute(select(Control).where(Control.control_id == finding.control_id))
        ).scalar_one_or_none()
        
        related_risks: list[Risk] = []
        if control:
            related_risks = list(
                (
                    await self.db.execute(select(Risk).where(Risk.mapped_control_id == control.control_id))
                ).scalars()
            )
            
        # Format the deterministic step-by-step plan
        steps = [
            f"Review the finding description: {finding.description}",
            f"Review the deterministic recommendation: {finding.recommendation}"
        ]
        
        if control:
            steps.append(f"Ensure the fix satisfies control '{control.control_name}' requirements.")
        
        if related_risks:
            steps.append(f"Validate that the remediation mitigates the following risks: {', '.join(r.risk_id for r in related_risks)}.")
            
        return {
            "finding_id": finding.finding_id,
            "severity": finding.severity,
            "status": finding.status,
            "description": finding.description,
            "recommendation": finding.recommendation,
            "control_context": {
                "control_id": control.control_id if control else None,
                "control_name": control.control_name if control else None
            },
            "related_risks": [
                {
                    "risk_id": r.risk_id,
                    "risk_name": r.risk_name,
                    "severity": r.severity
                }
                for r in related_risks
            ],
            "remediation_plan": {
                "generated_by": "deterministic_rules_v1",
                "steps": steps
            }
        }
