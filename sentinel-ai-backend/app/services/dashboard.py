"""
Dashboard aggregation — every number here is a live COUNT/GROUP BY against
the ingested tables. Nothing is cached, seeded, or hardcoded.

## Trust Score and Audit Readiness

Phase 1 does NOT ship an AI/ML scoring engine — that is Phase 2. What it
does ship is a **transparent deterministic score**: a fixed weighted mean
of ratios that are themselves plain row counts. The response carries its
own `formula` and `components`, so a reviewer can recompute it by hand
from the same API. It is explicitly labelled `engine: "deterministic_phase1"`.

That is the option §10 of the brief allows ("a simple deterministic
demonstration score calculated transparently from actual database fields
without inventing business logic"). If you would rather show nothing,
call the endpoint with `?scores=off` and both come back `null` with
`"pending Phase 2 scoring engine"`.

Status vocabularies below are the real distinct values in the data, not
assumptions:
  findings.status  = Open | In Progress | Remediated | Closed | Risk Accepted
  risks.current_status = Open | In Remediation | Mitigated | Closed | Accepted
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

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

OPEN_FINDING_STATUSES = ("Open", "In Progress")
OPEN_RISK_STATUSES = ("Open", "In Remediation")
SEVERITY_ORDER = ("Critical", "High", "Medium", "Low")

TRUST_WEIGHTS = {
    "control_evidence_coverage": 0.25,
    "finding_health": 0.20,
    "risk_health": 0.20,
    "asset_hygiene": 0.20,
    "identity_hygiene": 0.15,
}
READINESS_WEIGHTS = {
    "evidence_coverage": 0.40,
    "evidence_verification": 0.25,
    "mandatory_control_coverage": 0.20,
    "severe_finding_health": 0.15,
}


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _pct(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 2) if denominator else 0.0


async def _scalar(db: AsyncSession, stmt) -> int:
    return (await db.execute(stmt)).scalar_one() or 0


async def _count(db: AsyncSession, model: Any, *conditions) -> int:
    stmt = select(func.count()).select_from(model)
    for condition in conditions:
        stmt = stmt.where(condition)
    return await _scalar(db, stmt)


async def _group(db: AsyncSession, column) -> dict[str, int]:
    rows = await db.execute(select(column, func.count()).group_by(column))
    return {str(k): v for k, v in rows.all()}


def _ordered_severity(counts: dict[str, int]) -> dict[str, int]:
    ordered = {s: counts.get(s, 0) for s in SEVERITY_ORDER}
    ordered.update({k: v for k, v in counts.items() if k not in ordered})
    return ordered


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build(self, include_scores: bool = True) -> dict[str, Any]:
        db = self.db

        # ---- raw counts -------------------------------------------------
        totals = {
            "employees": await _count(db, Employee),
            "devices": await _count(db, Device),
            "cloud_assets": await _count(db, CloudAsset),
            "applications": await _count(db, Application),
            "vendors": await _count(db, Vendor),
            "policies": await _count(db, Policy),
            "controls": await _count(db, Control),
            "risks": await _count(db, Risk),
            "evidence": await _count(db, Evidence),
            "findings": await _count(db, Finding),
            "reports": await _count(db, Report),
            "personal_data_records": await _count(db, PersonalDataInventory),
            "consent_records": await _count(db, ConsentRecord),
            "iam_records": await _count(db, IAMRecord),
            "audit_logs": await _count(db, AuditLog),
        }

        # ---- risks ------------------------------------------------------
        risk_severity = _ordered_severity(await _group(db, Risk.severity))
        risk_status = await _group(db, Risk.current_status)
        open_risks = sum(risk_status.get(s, 0) for s in OPEN_RISK_STATUSES)
        risks_block = {
            "total": totals["risks"],
            "critical": risk_severity.get("Critical", 0),
            "high": risk_severity.get("High", 0),
            "medium": risk_severity.get("Medium", 0),
            "low": risk_severity.get("Low", 0),
            "open": open_risks,
            "by_severity": risk_severity,
            "by_status": risk_status,
            "by_likelihood": await _group(db, Risk.likelihood),
            "by_department": await _group(db, Risk.owner_department),
            "mapped_to_control": await _count(db, Risk, Risk.mapped_control_id.isnot(None)),
        }

        # ---- findings ---------------------------------------------------
        finding_severity = _ordered_severity(await _group(db, Finding.severity))
        finding_status = await _group(db, Finding.status)
        open_findings = sum(finding_status.get(s, 0) for s in OPEN_FINDING_STATUSES)
        severe_open = await _count(
            db,
            Finding,
            Finding.status.in_(OPEN_FINDING_STATUSES),
            Finding.severity.in_(("Critical", "High")),
        )
        findings_block = {
            "total": totals["findings"],
            "open": open_findings,
            "critical_open": await _count(
                db, Finding, Finding.status.in_(OPEN_FINDING_STATUSES), Finding.severity == "Critical"
            ),
            "high_open": await _count(
                db, Finding, Finding.status.in_(OPEN_FINDING_STATUSES), Finding.severity == "High"
            ),
            "severe_open": severe_open,
            "with_evidence": await _count(db, Finding, Finding.evidence_id.isnot(None)),
            "by_severity": finding_severity,
            "by_status": finding_status,
            "open_statuses": list(OPEN_FINDING_STATUSES),
        }

        # ---- evidence coverage -----------------------------------------
        controls_with_evidence = await _scalar(
            db, select(func.count(func.distinct(Evidence.control_id)))
        )
        controls_with_open_findings = await _scalar(
            db,
            select(func.count(func.distinct(Finding.control_id))).where(
                Finding.status.in_(OPEN_FINDING_STATUSES)
            ),
        )
        verified_evidence = await _count(db, Evidence, Evidence.verified.is_(True))
        evidence_block = {
            "total_controls": totals["controls"],
            "controls_with_evidence": controls_with_evidence,
            "controls_without_evidence": totals["controls"] - controls_with_evidence,
            "coverage_pct": _pct(controls_with_evidence, totals["controls"]),
            "total_evidence": totals["evidence"],
            "verified_evidence": verified_evidence,
            "verified_pct": _pct(verified_evidence, totals["evidence"]),
            "auto_collected": await _count(db, Evidence, Evidence.collected_automatically.is_(True)),
            "by_type": await _group(db, Evidence.evidence_type),
        }

        # ---- compliance coverage ---------------------------------------
        mandatory_policies = await _count(db, Policy, Policy.mandatory.is_(True))
        mandatory_controls = await _scalar(
            db,
            select(func.count())
            .select_from(Control)
            .join(Policy, Control.policy_id == Policy.policy_id)
            .where(Policy.mandatory.is_(True)),
        )
        mandatory_controls_with_evidence = await _scalar(
            db,
            select(func.count(func.distinct(Control.control_id)))
            .select_from(Control)
            .join(Policy, Control.policy_id == Policy.policy_id)
            .join(Evidence, Evidence.control_id == Control.control_id)
            .where(Policy.mandatory.is_(True)),
        )
        compliance_block = {
            "total_policies": totals["policies"],
            "mandatory_policies": mandatory_policies,
            "total_controls": totals["controls"],
            "controls_with_evidence": controls_with_evidence,
            "controls_with_open_findings": controls_with_open_findings,
            "passed_controls": totals["controls"] - controls_with_open_findings,
            "failed_controls": controls_with_open_findings,
            "pass_rate_pct": _pct(totals["controls"] - controls_with_open_findings, totals["controls"]),
            "mandatory_controls": mandatory_controls,
            "mandatory_controls_with_evidence": mandatory_controls_with_evidence,
            "policies_by_framework": await _group(db, Policy.framework),
            "controls_by_severity": _ordered_severity(await _group(db, Control.severity)),
            "definitions": {
                "passed_control": "a control with zero findings in status Open or In Progress",
                "failed_control": "a control with at least one finding in status Open or In Progress",
            },
        }

        # ---- framework status ------------------------------------------
        framework_status = await self._framework_status()

        # ---- audit activity --------------------------------------------
        latest_log = (await db.execute(select(func.max(AuditLog.timestamp)))).scalar_one_or_none()
        window_start = latest_log - timedelta(days=7) if latest_log else None
        recent_rows = (
            await db.execute(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10))
        ).scalars().all()
        activity_block = {
            "total_events": totals["audit_logs"],
            "latest_event_at": latest_log.isoformat() if latest_log else None,
            "window": "7 days back from the most recent log timestamp in the dataset",
            "events_in_window": (
                await _count(db, AuditLog, AuditLog.timestamp >= window_start) if window_start else 0
            ),
            "failures_in_window": (
                await _count(
                    db, AuditLog, AuditLog.timestamp >= window_start, AuditLog.result == "Failure"
                )
                if window_start
                else 0
            ),
            "total_failures": await _count(db, AuditLog, AuditLog.result == "Failure"),
            "high_risk_events": await _count(db, AuditLog, AuditLog.risk_score >= 70),
            "by_result": await _group(db, AuditLog.result),
            "top_actions": dict(
                sorted((await _group(db, AuditLog.action)).items(), key=lambda kv: kv[1], reverse=True)[:8]
            ),
            "recent": [
                {
                    "log_id": r.log_id,
                    "timestamp": r.timestamp.isoformat(),
                    "employee_id": r.employee_id,
                    "application_id": r.application_id,
                    "action": r.action,
                    "result": r.result,
                    "risk_score": r.risk_score,
                    "geo_location": r.geo_location,
                }
                for r in recent_rows
            ],
        }

        # ---- assets -----------------------------------------------------
        compliant_devices = await _count(db, Device, Device.compliance_status == "Compliant")
        public_assets = await _count(db, CloudAsset, CloudAsset.public_access.is_(True))
        assets_block = {
            "employees": {
                "total": totals["employees"],
                "active": await _count(db, Employee, Employee.account_status == "Active"),
                "by_status": await _group(db, Employee.account_status),
                "by_department": await _group(db, Employee.department),
                "mfa_enabled": await _count(db, Employee, Employee.mfa_enabled.is_(True)),
            },
            "devices": {
                "total": totals["devices"],
                "compliant": compliant_devices,
                "compliance_pct": _pct(compliant_devices, totals["devices"]),
                "by_compliance_status": await _group(db, Device.compliance_status),
                "by_risk_level": _ordered_severity(await _group(db, Device.risk_level)),
                "by_type": await _group(db, Device.device_type),
                "encrypted": await _count(db, Device, Device.encryption_enabled.is_(True)),
                "edr_installed": await _count(db, Device, Device.edr_installed.is_(True)),
            },
            "cloud_assets": {
                "total": totals["cloud_assets"],
                "public_access": public_assets,
                "public_access_pct": _pct(public_assets, totals["cloud_assets"]),
                "encrypted": await _count(db, CloudAsset, CloudAsset.encryption_enabled.is_(True)),
                "logging_enabled": await _count(db, CloudAsset, CloudAsset.logging_enabled.is_(True)),
                "by_provider": await _group(db, CloudAsset.cloud_provider),
                "by_risk_level": _ordered_severity(await _group(db, CloudAsset.risk_level)),
                "by_criticality": _ordered_severity(await _group(db, CloudAsset.criticality)),
            },
            "applications": {
                "total": totals["applications"],
                "internet_facing": await _count(db, Application, Application.internet_facing.is_(True)),
                "uses_mfa": await _count(db, Application, Application.uses_mfa.is_(True)),
                "encrypted": await _count(db, Application, Application.encryption_enabled.is_(True)),
                "by_risk_level": _ordered_severity(await _group(db, Application.risk_level)),
                "by_data_classification": await _group(db, Application.data_classification),
            },
        }

        # ---- vendors ----------------------------------------------------
        horizon = date.today() + timedelta(days=90)
        vendor_block = {
            "total": totals["vendors"],
            "by_risk_rating": _ordered_severity(await _group(db, Vendor.risk_rating)),
            "iso27001_certified": await _count(db, Vendor, Vendor.iso27001_certified.is_(True)),
            "soc2_certified": await _count(db, Vendor, Vendor.soc2_certified.is_(True)),
            "dpdp_compliant": await _count(db, Vendor, Vendor.dpdp_compliant.is_(True)),
            "no_certifications": await _count(
                db,
                Vendor,
                Vendor.iso27001_certified.is_(False),
                Vendor.soc2_certified.is_(False),
            ),
            "contracts_expiring_90d": await _count(
                db, Vendor, Vendor.contract_expiry <= horizon, Vendor.contract_expiry >= date.today()
            ),
            "by_service_category": await _group(db, Vendor.service_category),
            "note": "Vendors are an island dataset — no verified FK to risks or controls.",
        }

        # ---- privacy ----------------------------------------------------
        today = date.today()
        privacy_block = {
            "personal_data_records": totals["personal_data_records"],
            "third_party_sharing": await _count(
                db, PersonalDataInventory, PersonalDataInventory.third_party_sharing.is_(True)
            ),
            "encrypted": await _count(
                db, PersonalDataInventory, PersonalDataInventory.encryption_enabled.is_(True)
            ),
            "consent_required": await _count(
                db, PersonalDataInventory, PersonalDataInventory.consent_required.is_(True)
            ),
            "by_data_category": await _group(db, PersonalDataInventory.data_category),
            "consent_records": totals["consent_records"],
            "consent_given": await _count(db, ConsentRecord, ConsentRecord.consent_given.is_(True)),
            "consent_revoked": await _count(db, ConsentRecord, ConsentRecord.revoked.is_(True)),
            "consent_expired": await _count(db, ConsentRecord, ConsentRecord.expiry_date < today),
            "applications_with_personal_data": await _scalar(
                db, select(func.count(func.distinct(PersonalDataInventory.application_id)))
            ),
        }

        # ---- IAM --------------------------------------------------------
        privileged = await _count(db, IAMRecord, IAMRecord.privileged_account.is_(True))
        iam_block = {
            "total": totals["iam_records"],
            "privileged_accounts": privileged,
            "mfa_enabled": await _count(db, IAMRecord, IAMRecord.mfa_enabled.is_(True)),
            "privileged_without_mfa": await _count(
                db, IAMRecord, IAMRecord.privileged_account.is_(True), IAMRecord.mfa_enabled.is_(False)
            ),
            "inactive_over_90_days": await _count(db, IAMRecord, IAMRecord.inactive_days > 90),
            "by_role": dict(
                sorted((await _group(db, IAMRecord.role)).items(), key=lambda kv: kv[1], reverse=True)[:10]
            ),
        }

        payload: dict[str, Any] = {
            "generated_at": None,  # filled by the router with request time
            "totals": totals,
            "risks": risks_block,
            "findings": findings_block,
            "evidence_coverage": evidence_block,
            "compliance_coverage": compliance_block,
            "framework_status": framework_status,
            "recent_audit_activity": activity_block,
            "asset_statistics": assets_block,
            "vendor_risk": vendor_block,
            "privacy_statistics": privacy_block,
            "iam_statistics": iam_block,
        }

        if include_scores:
            payload["trust_score"], payload["audit_readiness"] = self._scores(
                totals=totals,
                controls_with_evidence=controls_with_evidence,
                open_findings=open_findings,
                severe_open=severe_open,
                open_risks=open_risks,
                verified_evidence=verified_evidence,
                mandatory_controls=mandatory_controls,
                mandatory_controls_with_evidence=mandatory_controls_with_evidence,
                assets=assets_block,
                iam=iam_block,
            )
        else:
            placeholder = {"value": None, "status": "pending Phase 2 scoring engine"}
            payload["trust_score"] = dict(placeholder)
            payload["audit_readiness"] = dict(placeholder)

        return payload

    # ------------------------------------------------------------------
    # Scores
    # ------------------------------------------------------------------

    @staticmethod
    def _scores(
        *,
        totals: dict[str, int],
        controls_with_evidence: int,
        open_findings: int,
        severe_open: int,
        open_risks: int,
        verified_evidence: int,
        mandatory_controls: int,
        mandatory_controls_with_evidence: int,
        assets: dict[str, Any],
        iam: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        devices, cloud, apps, employees = (
            assets["devices"],
            assets["cloud_assets"],
            assets["applications"],
            assets["employees"],
        )

        asset_hygiene = round(
            (
                _ratio(devices["compliant"], devices["total"])
                + _ratio(cloud["total"] - cloud["public_access"], cloud["total"])
                + _ratio(cloud["encrypted"], cloud["total"])
                + _ratio(apps["encrypted"], apps["total"])
            )
            / 4,
            4,
        )
        identity_hygiene = round(
            (
                _ratio(employees["mfa_enabled"], employees["total"])
                + _ratio(iam["mfa_enabled"], iam["total"])
                + _ratio(
                    iam["privileged_accounts"] - iam["privileged_without_mfa"],
                    iam["privileged_accounts"],
                )
            )
            / 3,
            4,
        )

        trust_components = {
            "control_evidence_coverage": _ratio(controls_with_evidence, totals["controls"]),
            "finding_health": round(1 - _ratio(open_findings, totals["findings"]), 4),
            "risk_health": round(1 - _ratio(open_risks, totals["risks"]), 4),
            "asset_hygiene": asset_hygiene,
            "identity_hygiene": identity_hygiene,
        }
        trust_value = round(
            100 * sum(trust_components[k] * w for k, w in TRUST_WEIGHTS.items()), 1
        )

        readiness_components = {
            "evidence_coverage": _ratio(controls_with_evidence, totals["controls"]),
            "evidence_verification": _ratio(verified_evidence, totals["evidence"]),
            "mandatory_control_coverage": _ratio(mandatory_controls_with_evidence, mandatory_controls),
            "severe_finding_health": round(1 - _ratio(severe_open, totals["findings"]), 4),
        }
        readiness_value = round(
            100 * sum(readiness_components[k] * w for k, w in READINESS_WEIGHTS.items()), 1
        )

        note = (
            "Deterministic Phase 1 score. Every component is a live row-count ratio "
            "from this database; the weights are fixed constants. This is NOT the "
            "Phase 2 AI scoring engine and involves no model, no inference, and no "
            "invented business logic."
        )
        return (
            {
                "value": trust_value,
                "engine": "deterministic_phase1",
                "weights": TRUST_WEIGHTS,
                "components": trust_components,
                "formula": "100 * SUM(component * weight)",
                "note": note,
            },
            {
                "value": readiness_value,
                "engine": "deterministic_phase1",
                "weights": READINESS_WEIGHTS,
                "components": readiness_components,
                "formula": "100 * SUM(component * weight)",
                "note": note,
            },
        )

    # ------------------------------------------------------------------
    # Framework rollup (shared with /frameworks)
    # ------------------------------------------------------------------

    async def _framework_status(self) -> list[dict[str, Any]]:
        return await framework_summaries(self.db)


async def framework_summaries(db: AsyncSession) -> list[dict[str, Any]]:
    """
    Framework-level rollup, aggregated live.

    There is no frameworks table in the source data — `Framework` is a
    shared vocabulary across policies and reports (same 5 values, verified).
    So the rollup is computed policies -> controls -> evidence/findings, and
    the latest real report row for that framework is attached where one
    exists. No report<->finding join is invented: the report figures are
    reported as the report's own numbers.
    """
    open_case = case((Finding.status.in_(OPEN_FINDING_STATUSES), 1), else_=0)

    rows = (
        await db.execute(
            select(
                Policy.framework,
                func.count(func.distinct(Policy.policy_id)),
                func.count(func.distinct(case((Policy.mandatory.is_(True), Policy.policy_id)))),
                func.count(func.distinct(Control.control_id)),
            )
            .select_from(Policy)
            .outerjoin(Control, Control.policy_id == Policy.policy_id)
            .group_by(Policy.framework)
            .order_by(Policy.framework)
        )
    ).all()

    evidence_rows = dict(
        (
            await db.execute(
                select(Policy.framework, func.count(func.distinct(Evidence.control_id)))
                .select_from(Policy)
                .join(Control, Control.policy_id == Policy.policy_id)
                .join(Evidence, Evidence.control_id == Control.control_id)
                .group_by(Policy.framework)
            )
        ).all()
    )
    evidence_totals = dict(
        (
            await db.execute(
                select(Policy.framework, func.count(Evidence.evidence_id))
                .select_from(Policy)
                .join(Control, Control.policy_id == Policy.policy_id)
                .join(Evidence, Evidence.control_id == Control.control_id)
                .group_by(Policy.framework)
            )
        ).all()
    )
    verified_totals = dict(
        (
            await db.execute(
                select(Policy.framework, func.count(Evidence.evidence_id))
                .select_from(Policy)
                .join(Control, Control.policy_id == Policy.policy_id)
                .join(Evidence, Evidence.control_id == Control.control_id)
                .where(Evidence.verified.is_(True))
                .group_by(Policy.framework)
            )
        ).all()
    )
    finding_rows = {
        framework: (total, open_count, critical, high, failed_controls)
        for framework, total, open_count, critical, high, failed_controls in (
            await db.execute(
                select(
                    Policy.framework,
                    func.count(Finding.finding_id),
                    func.sum(open_case),
                    func.count(case((Finding.severity == "Critical", 1))),
                    func.count(case((Finding.severity == "High", 1))),
                    func.count(func.distinct(case((open_case == 1, Finding.control_id)))),
                )
                .select_from(Policy)
                .join(Control, Control.policy_id == Policy.policy_id)
                .join(Finding, Finding.control_id == Control.control_id)
                .group_by(Policy.framework)
            )
        ).all()
    }
    latest_reports = {
        r.framework: r
        for r in (
            await db.execute(select(Report).order_by(Report.generated_date.asc()))
        ).scalars().all()
    }  # ascending, so the last write per framework is the newest

    domains_data: dict[str, dict[str, dict[str, int]]] = {}
    controls_q = (
        select(
            Policy.framework,
            Policy.category,
            Control.control_id,
            case(
                (Control.control_id.in_(
                    select(Finding.control_id).where(Finding.status.in_(OPEN_FINDING_STATUSES))
                ), 1),
                else_=0
            ).label("is_failing")
        )
        .select_from(Policy)
        .join(Control, Control.policy_id == Policy.policy_id)
    )
    for framework, category, control_id, is_failing in (await db.execute(controls_q)).all():
        if framework not in domains_data:
            domains_data[framework] = {}
        if category not in domains_data[framework]:
            domains_data[framework][category] = {"passing": 0, "failing": 0}
        
        if is_failing:
            domains_data[framework][category]["failing"] += 1
        else:
            domains_data[framework][category]["passing"] += 1

    summaries: list[dict[str, Any]] = []
    for framework, policy_count, mandatory_count, control_count in rows:
        with_evidence = evidence_rows.get(framework, 0)
        total_findings, open_findings, critical, high, failed = finding_rows.get(
            framework, (0, 0, 0, 0, 0)
        )
        report = latest_reports.get(framework)
        
        control_domains = [
            {"domain": cat, "passing": counts["passing"], "failing": counts["failing"]}
            for cat, counts in domains_data.get(framework, {}).items()
        ]
        
        summaries.append(
            {
                "framework": framework,
                "total_policies": policy_count,
                "mandatory_policies": mandatory_count,
                "total_controls": control_count,
                "controls_with_evidence": with_evidence,
                "controls_with_open_findings": failed or 0,
                "passed_controls": control_count - (failed or 0),
                "failed_controls": failed or 0,
                "evidence_count": evidence_totals.get(framework, 0),
                "verified_evidence_count": verified_totals.get(framework, 0),
                "evidence_coverage_pct": _pct(with_evidence, control_count),
                "total_findings": total_findings or 0,
                "open_findings": int(open_findings or 0),
                "critical_findings": critical or 0,
                "high_findings": high or 0,
                "latest_report_id": report.report_id if report else None,
                "latest_report_score": report.overall_score if report else None,
                "latest_report_status": report.compliance_status if report else None,
                "latest_report_date": report.generated_date.isoformat() if report else None,
                "control_domains": control_domains,
            }
        )
    return summaries
