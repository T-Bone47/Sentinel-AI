"""
Evidence Intelligence — Phase 2B, Priority 1.

Answers the question the Evidence Repository screen exists to answer:
**"can we actually prove this control is working?"**

Built on the same verified FK chain the rest of the app uses
(evidence.control_id -> controls.control_id -> policies.policy_id, and
findings.control_id / findings.evidence_id), so nothing here needs a new
relationship. See docs/profiling/relationships.txt.

## Coverage formula — stated once, used everywhere

A control is **covered** when it has at least one *adequate* evidence item.
Adequacy has exactly two conditions, both from real columns:

    adequate = verified IS TRUE

    coverage_percentage = covered_controls / total_controls * 100

`verified` is a real boolean on every evidence row. Unverified evidence is
counted separately as `controls_with_unverified_evidence_only` — a control
with a stack of unverified artefacts is not the same as a control with
none, and collapsing those two into "uncovered" would misstate the gap.

There is no weighting by control severity in the percentage itself. Weights
would be arbitrary, and the brief forbids arbitrary weights. Severity is
used only to *rank* gaps, never to inflate or deflate the coverage number.

## Freshness — deliberately limited

`evidence.collected_date` is a real date, so "days since collection" is
real and is reported. What is **not** reported is any judgement about
whether that makes a piece of evidence stale: the dataset has no validity
period, no review cadence, and no control-level refresh requirement, so
"expired" or "stale" would be an invention. The service exposes the age and
the collection date and stops there. `freshness_policy_available` is False
in every response to make that explicit rather than silent.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Control, Evidence, Finding, Policy, Risk

OPEN_FINDING_STATUSES = ("Open", "In Progress")
SEVERITY_RANK = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}


def _gap_severity(control: Control, open_findings: int, has_unverified: bool) -> str:
    """
    Rank an evidence gap. Deterministic and explainable:

    * Critical — the control demands evidence, has none at all, and already
      has open findings against it. Nothing to show an auditor, and known
      failures.
    * High — evidence required and genuinely absent, or open findings with
      only unverified artefacts behind them.
    * Medium — evidence required, something was collected but nothing is
      verified.
    * Low — evidence not formally required by the control.
    """
    if not control.evidence_required:
        return "Low"
    if not has_unverified and open_findings > 0:
        return "Critical"
    if not has_unverified:
        return "High"
    if open_findings > 0:
        return "High"
    return "Medium"


class EvidenceIntelligenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # shared loaders
    # ------------------------------------------------------------------

    async def _load(self) -> tuple[
        list[Control],
        dict[str, list[Evidence]],
        dict[str, list[Finding]],
        dict[str, Policy],
        dict[str, list[Risk]],
    ]:
        db = self.db
        controls = list((await db.execute(select(Control))).scalars().all())
        evidence = list((await db.execute(select(Evidence))).scalars().all())
        findings = list((await db.execute(select(Finding))).scalars().all())
        policies = list((await db.execute(select(Policy))).scalars().all())
        risks = list((await db.execute(select(Risk))).scalars().all())

        evidence_by_control: dict[str, list[Evidence]] = {}
        for item in evidence:
            evidence_by_control.setdefault(item.control_id, []).append(item)

        findings_by_control: dict[str, list[Finding]] = {}
        for finding in findings:
            findings_by_control.setdefault(finding.control_id, []).append(finding)

        risks_by_control: dict[str, list[Risk]] = {}
        for risk in risks:
            if risk.mapped_control_id:
                risks_by_control.setdefault(risk.mapped_control_id, []).append(risk)

        policy_by_id = {policy.policy_id: policy for policy in policies}
        return controls, evidence_by_control, findings_by_control, policy_by_id, risks_by_control

    # ------------------------------------------------------------------
    # coverage
    # ------------------------------------------------------------------

    async def coverage(self) -> dict[str, Any]:
        (
            controls,
            evidence_by_control,
            findings_by_control,
            policy_by_id,
            risks_by_control,
        ) = await self._load()

        covered: list[str] = []
        unverified_only: list[str] = []
        uncovered: list[str] = []
        gaps: list[dict[str, Any]] = []

        for control in controls:
            items = evidence_by_control.get(control.control_id, [])
            verified = [e for e in items if e.verified]
            open_findings = [
                f for f in findings_by_control.get(control.control_id, [])
                if f.status in OPEN_FINDING_STATUSES
            ]

            if verified:
                covered.append(control.control_id)
                continue

            if items:
                unverified_only.append(control.control_id)
            else:
                uncovered.append(control.control_id)

            policy = policy_by_id.get(control.policy_id)
            severity = _gap_severity(control, len(open_findings), bool(items))
            gaps.append(
                {
                    "control_id": control.control_id,
                    "control_name": control.control_name,
                    "control_severity": control.severity,
                    "evidence_required": control.evidence_required,
                    "policy_id": control.policy_id,
                    "policy_name": policy.policy_name if policy else None,
                    "framework": policy.framework if policy else None,
                    "mandatory_policy": policy.mandatory if policy else None,
                    "evidence_items": len(items),
                    "verified_evidence_items": 0,
                    "gap_type": "no_evidence" if not items else "unverified_only",
                    "gap_severity": severity,
                    "open_findings": len(open_findings),
                    "open_finding_ids": [f.finding_id for f in open_findings][:10],
                    "related_risk_ids": [
                        r.risk_id for r in risks_by_control.get(control.control_id, [])
                    ][:10],
                    "why": self._explain_gap(control, items, open_findings),
                }
            )

        gaps.sort(
            key=lambda g: (
                SEVERITY_RANK.get(g["gap_severity"], 0),
                SEVERITY_RANK.get(g["control_severity"], 0),
                g["open_findings"],
            ),
            reverse=True,
        )

        total = len(controls)
        total_evidence = sum(len(v) for v in evidence_by_control.values())
        verified_evidence = sum(
            1 for items in evidence_by_control.values() for e in items if e.verified
        )

        return {
            "coverage_percentage": round(100 * len(covered) / total, 2) if total else 0.0,
            "total_controls": total,
            "covered_controls": len(covered),
            "uncovered_controls": len(uncovered) + len(unverified_only),
            "controls_with_no_evidence": len(uncovered),
            "controls_with_unverified_evidence_only": len(unverified_only),
            "total_evidence_items": total_evidence,
            "verified_evidence_items": verified_evidence,
            "unverified_evidence_items": total_evidence - verified_evidence,
            "auto_collected_evidence_items": sum(
                1 for items in evidence_by_control.values() for e in items if e.collected_automatically
            ),
            "critical_gaps": sum(1 for g in gaps if g["gap_severity"] == "Critical"),
            "high_gaps": sum(1 for g in gaps if g["gap_severity"] == "High"),
            "evidence_gaps": gaps,
            "by_framework": await self._coverage_by_framework(),
            "formula": (
                "coverage_percentage = controls with >= 1 VERIFIED evidence item / "
                "total controls * 100. No severity weighting is applied to the "
                "percentage; severity is used only to rank gaps."
            ),
            "adequacy_rule": "An evidence item counts toward coverage only when evidence.verified is true.",
            "freshness_policy_available": False,
            "freshness_note": (
                "Collection dates and ages are real and reported per item. The dataset "
                "defines no validity period or review cadence, so no evidence is "
                "labelled stale or expired — that judgement is not derivable."
            ),
        }

    @staticmethod
    def _explain_gap(
        control: Control, items: list[Evidence], open_findings: list[Finding]
    ) -> str:
        parts: list[str] = []
        if not items:
            parts.append("No evidence has been collected for this control")
        else:
            parts.append(
                f"{len(items)} evidence item(s) exist but none are verified"
            )
        if control.evidence_required:
            parts.append("the control is flagged as requiring evidence")
        else:
            parts.append("the control does not formally require evidence")
        if open_findings:
            severities = sorted(
                {f.severity for f in open_findings},
                key=lambda s: SEVERITY_RANK.get(s, 0),
                reverse=True,
            )
            parts.append(
                f"{len(open_findings)} open finding(s) already exist against it "
                f"({', '.join(severities)})"
            )
        return "; ".join(parts) + "."

    async def _coverage_by_framework(self) -> list[dict[str, Any]]:
        """Coverage grouped by framework, using the real policy->framework field."""
        rows = (
            await self.db.execute(
                select(
                    Policy.framework,
                    func.count(func.distinct(Control.control_id)),
                )
                .select_from(Policy)
                .join(Control, Control.policy_id == Policy.policy_id)
                .group_by(Policy.framework)
            )
        ).all()
        totals = {framework: count for framework, count in rows}

        covered_rows = (
            await self.db.execute(
                select(
                    Policy.framework,
                    func.count(func.distinct(Control.control_id)),
                )
                .select_from(Policy)
                .join(Control, Control.policy_id == Policy.policy_id)
                .join(Evidence, Evidence.control_id == Control.control_id)
                .where(Evidence.verified.is_(True))
                .group_by(Policy.framework)
            )
        ).all()
        covered = {framework: count for framework, count in covered_rows}

        return [
            {
                "framework": framework,
                "total_controls": total,
                "covered_controls": covered.get(framework, 0),
                "uncovered_controls": total - covered.get(framework, 0),
                "coverage_percentage": round(100 * covered.get(framework, 0) / total, 2)
                if total
                else 0.0,
            }
            for framework, total in sorted(totals.items())
        ]

    # ------------------------------------------------------------------
    # per-item and per-control views
    # ------------------------------------------------------------------

    async def explain_evidence(self, evidence_id: str) -> dict[str, Any] | None:
        db = self.db
        evidence = (
            await db.execute(select(Evidence).where(Evidence.evidence_id == evidence_id))
        ).scalar_one_or_none()
        if evidence is None:
            return None

        control = (
            await db.execute(select(Control).where(Control.control_id == evidence.control_id))
        ).scalar_one_or_none()
        policy = (
            await db.execute(select(Policy).where(Policy.policy_id == control.policy_id))
        ).scalar_one_or_none() if control else None

        # findings.evidence_id is a real FK — these findings cite this exact item.
        supported_findings = list(
            (
                await db.execute(select(Finding).where(Finding.evidence_id == evidence_id))
            ).scalars().all()
        )
        # Findings on the same control, which this evidence is contextually
        # relevant to but does not directly cite.
        control_findings = list(
            (
                await db.execute(
                    select(Finding).where(
                        Finding.control_id == evidence.control_id,
                        Finding.evidence_id != evidence_id,
                    )
                )
            ).scalars().all()
        )
        related_risks = list(
            (
                await db.execute(select(Risk).where(Risk.mapped_control_id == evidence.control_id))
            ).scalars().all()
        )

        age_days = (date.today() - evidence.collected_date).days

        return {
            "evidence_id": evidence.evidence_id,
            "evidence_type": evidence.evidence_type,
            "evidence_location": evidence.evidence_location,
            "collected_date": evidence.collected_date.isoformat(),
            "age_days": age_days,
            "verified": evidence.verified,
            "collected_automatically": evidence.collected_automatically,
            "counts_toward_coverage": evidence.verified,
            "adequacy_reason": (
                "Verified — this item counts toward its control's coverage."
                if evidence.verified
                else "Not verified — this item does not count toward coverage until it is."
            ),
            "control": {
                "control_id": control.control_id,
                "control_name": control.control_name,
                "severity": control.severity,
                "evidence_required": control.evidence_required,
            }
            if control
            else None,
            "policy": {
                "policy_id": policy.policy_id,
                "policy_name": policy.policy_name,
                "framework": policy.framework,
                "mandatory": policy.mandatory,
            }
            if policy
            else None,
            "directly_supports_findings": [
                {
                    "finding_id": f.finding_id,
                    "severity": f.severity,
                    "status": f.status,
                    "description": f.description,
                }
                for f in supported_findings
            ],
            "other_findings_on_control": [
                {"finding_id": f.finding_id, "severity": f.severity, "status": f.status}
                for f in control_findings[:10]
            ],
            "related_risks": [
                {
                    "risk_id": r.risk_id,
                    "risk_name": r.risk_name,
                    "severity": r.severity,
                    "current_status": r.current_status,
                }
                for r in related_risks
            ],
            "freshness_policy_available": False,
        }

    async def control_evidence(self, control_id: str) -> dict[str, Any] | None:
        db = self.db
        control = (
            await db.execute(select(Control).where(Control.control_id == control_id))
        ).scalar_one_or_none()
        if control is None:
            return None

        policy = (
            await db.execute(select(Policy).where(Policy.policy_id == control.policy_id))
        ).scalar_one_or_none()
        items = list(
            (
                await db.execute(select(Evidence).where(Evidence.control_id == control_id))
            ).scalars().all()
        )
        findings = list(
            (
                await db.execute(select(Finding).where(Finding.control_id == control_id))
            ).scalars().all()
        )
        risks = list(
            (
                await db.execute(select(Risk).where(Risk.mapped_control_id == control_id))
            ).scalars().all()
        )
        open_findings = [f for f in findings if f.status in OPEN_FINDING_STATUSES]
        verified = [e for e in items if e.verified]

        return {
            "control_id": control.control_id,
            "control_name": control.control_name,
            "description": control.description,
            "severity": control.severity,
            "evidence_required": control.evidence_required,
            "automation_possible": control.automation_possible,
            "policy": {
                "policy_id": policy.policy_id,
                "policy_name": policy.policy_name,
                "framework": policy.framework,
                "mandatory": policy.mandatory,
            }
            if policy
            else None,
            "covered": bool(verified),
            "can_we_prove_it_works": (
                f"Yes — {len(verified)} verified evidence item(s) support this control."
                if verified
                else (
                    f"No — {len(items)} evidence item(s) exist but none are verified."
                    if items
                    else "No — no evidence has been collected for this control."
                )
            ),
            "evidence_count": len(items),
            "verified_evidence_count": len(verified),
            "evidence": [
                {
                    "evidence_id": e.evidence_id,
                    "evidence_type": e.evidence_type,
                    "evidence_location": e.evidence_location,
                    "collected_date": e.collected_date.isoformat(),
                    "age_days": (date.today() - e.collected_date).days,
                    "verified": e.verified,
                    "collected_automatically": e.collected_automatically,
                }
                for e in sorted(items, key=lambda e: e.collected_date, reverse=True)
            ],
            "open_findings": [
                {
                    "finding_id": f.finding_id,
                    "severity": f.severity,
                    "status": f.status,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "cites_evidence_id": f.evidence_id,
                }
                for f in open_findings
            ],
            "total_findings": len(findings),
            "related_risks": [
                {
                    "risk_id": r.risk_id,
                    "risk_name": r.risk_name,
                    "severity": r.severity,
                    "current_status": r.current_status,
                }
                for r in risks
            ],
            "gap_severity": _gap_severity(control, len(open_findings), bool(items))
            if not verified
            else None,
        }

    # ------------------------------------------------------------------
    # summary for the Copilot and the Evidence page header
    # ------------------------------------------------------------------

    async def summary(self, gap_limit: int = 10) -> dict[str, Any]:
        coverage = await self.coverage()
        gaps = coverage["evidence_gaps"]
        return {
            **{k: v for k, v in coverage.items() if k != "evidence_gaps"},
            "top_gaps": gaps[:gap_limit],
            "total_gaps": len(gaps),
        }
