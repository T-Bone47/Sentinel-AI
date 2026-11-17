"""
Trust Intelligence — Phase 2, Priority 1.

Upgrades (does NOT replace) the Phase 1 deterministic Trust Score in
DashboardService. That service still owns the actual formula and the five
weighted components (`control_evidence_coverage`, `finding_health`,
`risk_health`, `asset_hygiene`, `identity_hygiene`) — this service calls it,
then adds the explanation layer: banding, contributor ranking, a real score
history (see app/models/trust.py), concrete risk drivers, and recommended
actions. Every number below is either read straight out of
`DashboardService.build()` or computed from a live query against Risk/
Finding/Control/Evidence — nothing is invented.

Level 1 of the AI Strategy in the brief ("deterministic intelligence").
Structured so Level 2 (LLM enhancement) can later replace `_recommend()`
and the narrative in `top_risk_drivers` without touching the scoring path.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Control, Finding, Risk, TrustScoreSnapshot
from app.services.dashboard import DashboardService

LEVEL_BANDS = (
    (85, "Strong"),
    (70, "Adequate"),
    (50, "At Risk"),
    (0, "Critical"),
)

# A domain counts as a positive contributor above this, negative below this.
# Deliberately not 0.5/0.5 — a component sitting at exactly "half" isn't
# meaningfully helping or hurting, so it's reported as neutral instead of
# padding one list or the other with noise.
POSITIVE_THRESHOLD = 0.80
NEGATIVE_THRESHOLD = 0.60

DOMAIN_LABELS = {
    "control_evidence_coverage": "Evidence coverage",
    "finding_health": "Finding health",
    "risk_health": "Risk health",
    "asset_hygiene": "Asset hygiene",
    "identity_hygiene": "IAM hygiene",
}


MEASUREMENT_TRIGGERS = ("manual", "scheduled", "dataset_ingestion")


def _utc_iso(value: datetime) -> str:
    """SQLite returns naive timestamps for this table; they are UTC."""
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def _measurement_out(row: TrustScoreSnapshot) -> dict[str, Any]:
    return {
        "id": row.id,
        "trust_score": row.trust_score,
        "audit_readiness": row.audit_readiness,
        "components": row.components,
        "engine": row.engine,
        "trigger": row.trigger,
        "recorded_by": row.recorded_by,
        "computed_at": _utc_iso(row.computed_at),
    }


def _level(score: float) -> str:
    for floor, label in LEVEL_BANDS:
        if score >= floor:
            return label
    return "Critical"


class TrustIntelligenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build(self) -> dict[str, Any]:
        db = self.db
        dashboard = await DashboardService(db).build(include_scores=True)
        trust = dashboard["trust_score"]
        readiness = dashboard["audit_readiness"]

        if trust.get("value") is None:
            return {
                "trust_score": None,
                "status": trust.get("status", "pending Phase 2 scoring engine"),
                "note": "Deterministic score unavailable — call /dashboard without ?scores=off first.",
            }

        domains = [
            {
                "key": key,
                "label": DOMAIN_LABELS.get(key, key),
                "value": value,
                "value_pct": round(value * 100, 1),
                "weight": trust["weights"][key],
                "contribution_points": round(value * trust["weights"][key] * 100, 2),
            }
            for key, value in trust["components"].items()
        ]
        domains.sort(key=lambda d: d["contribution_points"], reverse=True)

        positive = [d for d in domains if d["value"] >= POSITIVE_THRESHOLD]
        negative = sorted(
            (d for d in domains if d["value"] < NEGATIVE_THRESHOLD),
            key=lambda d: d["value"],
        )

        top_risk_drivers = await self._top_risk_drivers()
        score_change = await self._diff_against_latest(trust["value"])
        recommended_actions = await self._recommend(negative, top_risk_drivers, dashboard)

        return {
            "trust_score": trust["value"],
            "trust_level": _level(trust["value"]),
            "engine": trust["engine"],
            "formula": trust["formula"],
            "trust_domains": domains,
            "positive_contributors": positive,
            "negative_contributors": negative,
            "score_change": score_change,
            "top_risk_drivers": top_risk_drivers,
            "evidence_coverage": dashboard["evidence_coverage"],
            "control_coverage": dashboard["compliance_coverage"],
            "audit_readiness": readiness,
            "recommended_actions": recommended_actions,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": trust["note"],
        }

    async def _top_risk_drivers(self, limit: int = 5) -> list[dict[str, Any]]:
        """Real open Critical/High risks, ranked. Not a model score — a
        direct read of the same rows a reviewer would click into on the
        Risk Center screen."""
        stmt = (
            select(Risk)
            .where(Risk.severity.in_(("Critical", "High")))
            .where(Risk.current_status.in_(("Open", "In Remediation")))
            .order_by(
                (Risk.severity == "Critical").desc(),
                desc(Risk.risk_id),
            )
            .limit(limit)
        )
        risks = (await self.db.execute(stmt)).scalars().all()

        drivers = []
        for risk in risks:
            open_findings = 0
            if risk.mapped_control_id:
                count_stmt = select(Finding).where(
                    Finding.control_id == risk.mapped_control_id,
                    Finding.status.in_(("Open", "In Progress")),
                )
                open_findings = len((await self.db.execute(count_stmt)).scalars().all())
            drivers.append(
                {
                    "risk_id": risk.risk_id,
                    "risk_name": risk.risk_name,
                    "severity": risk.severity,
                    "status": risk.current_status,
                    "owner_department": risk.owner_department,
                    "mapped_control_id": risk.mapped_control_id,
                    "open_findings_on_control": open_findings,
                }
            )
        return drivers

    async def _latest_snapshot(self) -> TrustScoreSnapshot | None:
        stmt = select(TrustScoreSnapshot).order_by(
            desc(TrustScoreSnapshot.computed_at), desc(TrustScoreSnapshot.id)
        ).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _diff_against_latest(self, trust_score: float) -> dict[str, Any]:
        """Compare the live score with the most recent recorded measurement.
        Read-only: looking at the score must never change its history."""
        prior = await self._latest_snapshot()
        if prior is None:
            return {
                "delta": None,
                "prior_score": None,
                "prior_computed_at": None,
                "status": "no measurement recorded yet — nothing to compare against",
            }
        return {
            "delta": round(trust_score - prior.trust_score, 1),
            "prior_score": prior.trust_score,
            "prior_computed_at": _utc_iso(prior.computed_at),
            "status": "compared against the most recent recorded measurement",
        }

    async def record_measurement(self, *, trigger: str, recorded_by: str | None) -> dict[str, Any]:
        """Add the current score to its history — the only code path that
        writes a snapshot. Called deliberately (API, scheduler script) or when
        the data the score is computed from has just been reloaded.

        Deduplicated: if nothing the score is built from has changed since the
        latest snapshot, no row is written. The history therefore records
        changes, and an unchanged score leaves no trace however often it is
        measured."""
        if trigger not in MEASUREMENT_TRIGGERS:
            raise ValueError(f"trigger must be one of: {', '.join(MEASUREMENT_TRIGGERS)}")
        dashboard = await DashboardService(self.db).build(include_scores=True)
        trust, readiness = dashboard["trust_score"], dashboard["audit_readiness"]
        if trust.get("value") is None:
            return {"recorded": False, "reason": "the deterministic score is unavailable", "measurement": None}

        latest = await self._latest_snapshot()
        current = (trust["value"], readiness["value"], trust["components"])
        if latest is not None and (latest.trust_score, latest.audit_readiness, latest.components) == current:
            return {
                "recorded": False,
                "reason": "unchanged since the last recorded measurement",
                "measurement": _measurement_out(latest),
            }

        snapshot = TrustScoreSnapshot(
            trust_score=trust["value"],
            audit_readiness=readiness["value"],
            components=trust["components"],
            trigger=trigger,
            recorded_by=recorded_by,
            computed_at=datetime.now(timezone.utc),
        )
        self.db.add(snapshot)
        await self.db.commit()
        return {
            "recorded": True,
            "reason": "first measurement" if latest is None else "score or components changed",
            "measurement": _measurement_out(snapshot),
        }

    async def measurements(self, limit: int = 50) -> list[dict[str, Any]]:
        stmt = select(TrustScoreSnapshot).order_by(
            desc(TrustScoreSnapshot.computed_at), desc(TrustScoreSnapshot.id)
        ).limit(limit)
        return [_measurement_out(row) for row in (await self.db.execute(stmt)).scalars().all()]

    async def _recommend(
        self,
        negative: list[dict[str, Any]],
        top_risk_drivers: list[dict[str, Any]],
        dashboard: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Deterministic, template-based — every number plugged in is a
        real count from this call. Labelled `generated_by` so nothing
        downstream mistakes this for an LLM. This is exactly the seam
        the brief asks for: swap the template for an LLM call later
        without touching what feeds it."""
        actions: list[dict[str, Any]] = []

        critical_open = dashboard["findings"]["critical_open"]
        if critical_open > 0:
            control_ids = sorted({d["mapped_control_id"] for d in top_risk_drivers if d["mapped_control_id"]})
            control_ref = f" (controls: {', '.join(control_ids[:3])})" if control_ids else ""
            actions.append(
                {
                    "priority": "Critical",
                    "action": f"Resolve {critical_open} open Critical-severity finding(s){control_ref}.",
                    "basis": "findings.severity = Critical AND findings.status IN (Open, In Progress)",
                }
            )

        gap = dashboard["evidence_coverage"]["controls_without_evidence"]
        if gap > 0:
            actions.append(
                {
                    "priority": "High",
                    "action": f"Attach evidence to {gap} control(s) with none on file.",
                    "basis": "controls with zero rows in evidence for that control_id",
                }
            )

        priv_no_mfa = dashboard["iam_statistics"]["privileged_without_mfa"]
        if priv_no_mfa > 0:
            actions.append(
                {
                    "priority": "High",
                    "action": f"Enforce MFA on {priv_no_mfa} privileged account(s) currently without it.",
                    "basis": "iam_records.privileged_account = true AND mfa_enabled = false",
                }
            )

        vendor_ratings = dashboard["vendor_risk"]["by_risk_rating"]
        high_risk_vendors = vendor_ratings.get("Critical", 0) + vendor_ratings.get("High", 0)
        if high_risk_vendors > 0:
            actions.append(
                {
                    "priority": "Medium",
                    "action": f"Review {high_risk_vendors} vendor(s) rated Critical/High risk.",
                    "basis": "vendors.risk_rating IN (Critical, High)",
                }
            )

        for item in actions:
            item["generated_by"] = "deterministic_rules_v1"
        return actions[:5]
