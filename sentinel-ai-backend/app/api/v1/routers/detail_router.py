"""
Enriched detail endpoints.

These are registered BEFORE the generic resource routers so they win the
path match for `/{id}`. Everything they return is walked through a
verified FK — a risk with no mapped control gets nulls and empty lists,
not an invented chain.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.auth_router import require_permission
from app.core.permissions import is_allowed, is_unrestricted, row_scope
from app.database.session import get_db
from app.models import (
    User,
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
    Risk,
)
from app.schemas import resources as s

router = APIRouter()

RECENT_ACTIVITY_LIMIT = 20

# Each detail view joins across datasets, so its guard lists every dataset it
# returns rows from. The four governance views all walk the same chain.
_GOVERNANCE_CHAIN = require_permission("risks", "controls", "policies", "findings", "evidence")


async def _one(db: AsyncSession, model: Any, column: Any, value: Any) -> Any:
    if value is None:
        return None
    return (await db.execute(select(model).where(column == value))).scalar_one_or_none()


async def _many(db: AsyncSession, stmt) -> list[Any]:
    return list((await db.execute(stmt)).scalars().all())


def _missing(kind: str, identifier: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{kind} '{identifier}' not found")


# --------------------------------------------------------------------------
# Risk investigation — POLICY -> CONTROL -> FINDING -> EVIDENCE -> RISK
# --------------------------------------------------------------------------

@router.get("/risks/{risk_id}", tags=["risks"], summary="Risk investigation detail", response_model=None, dependencies=[Depends(_GOVERNANCE_CHAIN)])
async def risk_detail(risk_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    risk = await _one(db, Risk, Risk.risk_id, risk_id)
    if risk is None:
        raise _missing("Risk", risk_id)

    control = await _one(db, Control, Control.control_id, risk.mapped_control_id)
    policy = await _one(db, Policy, Policy.policy_id, control.policy_id) if control else None

    findings: list[Any] = []
    evidence: list[Any] = []
    if control is not None:
        findings = await _many(db, select(Finding).where(Finding.control_id == control.control_id))
        evidence = await _many(db, select(Evidence).where(Evidence.control_id == control.control_id))

    payload = s.RiskDetailOut.model_validate(risk).model_dump(mode="json")
    payload.update(
        control=s.ControlOut.model_validate(control).model_dump(mode="json") if control else None,
        policy=s.PolicyOut.model_validate(policy).model_dump(mode="json") if policy else None,
        findings=[s.FindingOut.model_validate(f).model_dump(mode="json") for f in findings],
        evidence=[s.EvidenceOut.model_validate(e).model_dump(mode="json") for e in evidence],
        open_finding_count=sum(1 for f in findings if f.status == "Open"),
        verified_evidence_count=sum(1 for e in evidence if e.verified),
    )
    return {"data": payload, "error": None}


# --------------------------------------------------------------------------
# Findings
# --------------------------------------------------------------------------

@router.get("/findings/{finding_id}", tags=["findings"], summary="Finding detail with control, policy, evidence and risk context", response_model=None, dependencies=[Depends(_GOVERNANCE_CHAIN)])
async def finding_detail(finding_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    finding = await _one(db, Finding, Finding.finding_id, finding_id)
    if finding is None:
        raise _missing("Finding", finding_id)

    control = await _one(db, Control, Control.control_id, finding.control_id)
    policy = await _one(db, Policy, Policy.policy_id, control.policy_id) if control else None
    evidence = await _one(db, Evidence, Evidence.evidence_id, finding.evidence_id)
    # Legitimate link: both a finding and a risk can point at the same control.
    related_risks = await _many(db, select(Risk).where(Risk.mapped_control_id == finding.control_id))

    payload = s.FindingDetailOut.model_validate(finding).model_dump(mode="json")
    payload.update(
        control=s.ControlOut.model_validate(control).model_dump(mode="json") if control else None,
        policy=s.PolicyOut.model_validate(policy).model_dump(mode="json") if policy else None,
        evidence=s.EvidenceOut.model_validate(evidence).model_dump(mode="json") if evidence else None,
        related_risks=[s.RiskOut.model_validate(r).model_dump(mode="json") for r in related_risks],
    )
    return {"data": payload, "error": None}


# --------------------------------------------------------------------------
# Evidence
# --------------------------------------------------------------------------

@router.get("/evidence/{evidence_id}", tags=["evidence"], summary="Evidence detail with control and finding linkage", response_model=None, dependencies=[Depends(_GOVERNANCE_CHAIN)])
async def evidence_detail(evidence_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    evidence = await _one(db, Evidence, Evidence.evidence_id, evidence_id)
    if evidence is None:
        raise _missing("Evidence", evidence_id)

    control = await _one(db, Control, Control.control_id, evidence.control_id)
    policy = await _one(db, Policy, Policy.policy_id, control.policy_id) if control else None
    findings = await _many(db, select(Finding).where(Finding.evidence_id == evidence_id))
    related_risks = await _many(db, select(Risk).where(Risk.mapped_control_id == evidence.control_id))

    payload = s.EvidenceDetailOut.model_validate(evidence).model_dump(mode="json")
    payload.update(
        control=s.ControlOut.model_validate(control).model_dump(mode="json") if control else None,
        policy=s.PolicyOut.model_validate(policy).model_dump(mode="json") if policy else None,
        findings=[s.FindingOut.model_validate(f).model_dump(mode="json") for f in findings],
        related_risks=[s.RiskOut.model_validate(r).model_dump(mode="json") for r in related_risks],
    )
    return {"data": payload, "error": None}


# --------------------------------------------------------------------------
# Controls / policies
# --------------------------------------------------------------------------

@router.get("/controls/{control_id}", tags=["controls"], summary="Control detail with policy, evidence, findings and risks", response_model=None, dependencies=[Depends(_GOVERNANCE_CHAIN)])
async def control_detail(control_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    control = await _one(db, Control, Control.control_id, control_id)
    if control is None:
        raise _missing("Control", control_id)

    policy = await _one(db, Policy, Policy.policy_id, control.policy_id)
    evidence = await _many(db, select(Evidence).where(Evidence.control_id == control_id))
    findings = await _many(db, select(Finding).where(Finding.control_id == control_id))
    risks = await _many(db, select(Risk).where(Risk.mapped_control_id == control_id))

    payload = s.ControlDetailOut.model_validate(control).model_dump(mode="json")
    payload.update(
        policy=s.PolicyOut.model_validate(policy).model_dump(mode="json") if policy else None,
        evidence=[s.EvidenceOut.model_validate(e).model_dump(mode="json") for e in evidence],
        findings=[s.FindingOut.model_validate(f).model_dump(mode="json") for f in findings],
        risks=[s.RiskOut.model_validate(r).model_dump(mode="json") for r in risks],
    )
    return {"data": payload, "error": None}


@router.get("/policies/{policy_id}", tags=["policies"], summary="Policy detail with its controls", response_model=None, dependencies=[Depends(require_permission("policies", "controls"))])
async def policy_detail(policy_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    policy = await _one(db, Policy, Policy.policy_id, policy_id)
    if policy is None:
        raise _missing("Policy", policy_id)

    controls = await _many(db, select(Control).where(Control.policy_id == policy_id))
    payload = s.PolicyDetailOut.model_validate(policy).model_dump(mode="json")
    payload.update(
        controls=[s.ControlOut.model_validate(c).model_dump(mode="json") for c in controls],
        control_count=len(controls),
    )
    return {"data": payload, "error": None}


# --------------------------------------------------------------------------
# Employee / application 360 views
# --------------------------------------------------------------------------

class _Sections:
    """Per-section authorization for a compound response. A section the caller
    may not read is left empty and its name recorded in `withheld`, so a
    client can say "not available to your role" instead of implying that no
    records exist."""

    def __init__(self, user: User) -> None:
        self.user = user
        self.withheld: list[str] = []

    def allows(self, section: str, resource: str, *, belongs_to_subject: bool = False) -> bool:
        """`belongs_to_subject`: the section holds the viewed record's own
        data, so a row-scoped role looking at its own record may see it.
        Otherwise the section lists other records and needs unrestricted read."""
        check = is_allowed if belongs_to_subject else is_unrestricted
        allowed = check(self.user.role, resource)
        if not allowed:
            self.withheld.append(section)
        return allowed


@router.get("/employees/{employee_id}", tags=["employees"], summary="Employee 360 view", response_model=None)
async def employee_detail(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("employees")),
) -> dict[str, Any]:
    scope = row_scope(user.role, user.employee_id, "employees")
    employee = await _one(db, Employee, Employee.employee_id, employee_id)
    # Out of scope is reported exactly like missing: do not confirm it exists.
    if employee is None or (scope is not None and employee.employee_id != scope.value):
        raise _missing("Employee", employee_id)

    # From here a row-scoped caller is, by the check above, viewing their own record.
    sections = _Sections(user)
    manager = (
        await _one(db, Employee, Employee.employee_id, employee.manager_id)
        if sections.allows("manager", "employees") else None
    )
    device = (
        await _one(db, Device, Device.employee_id, employee_id)
        if sections.allows("device", "devices", belongs_to_subject=True) else None
    )
    iam = (
        await _one(db, IAMRecord, IAMRecord.employee_id, employee_id)
        if sections.allows("iam_record", "iam", belongs_to_subject=True) else None
    )
    cloud = (
        await _many(db, select(CloudAsset).where(CloudAsset.owner_employee_id == employee_id))
        if sections.allows("cloud_assets", "cloud-assets") else []
    )
    reports = (
        await _many(db, select(Employee).where(Employee.manager_id == employee_id))
        if sections.allows("direct_reports", "employees") else []
    )
    activity = (
        await _many(
            db,
            select(AuditLog)
            .where(AuditLog.employee_id == employee_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(RECENT_ACTIVITY_LIMIT),
        )
        if sections.allows("recent_activity", "audit-logs") else []
    )

    payload = s.EmployeeDetailOut.model_validate(employee).model_dump(mode="json")
    payload.update(
        manager=s.EmployeeOut.model_validate(manager).model_dump(mode="json") if manager else None,
        device=s.DeviceOut.model_validate(device).model_dump(mode="json") if device else None,
        iam_record=s.IAMOut.model_validate(iam).model_dump(mode="json") if iam else None,
        cloud_assets=[s.CloudAssetOut.model_validate(c).model_dump(mode="json") for c in cloud],
        direct_reports=[s.EmployeeOut.model_validate(e).model_dump(mode="json") for e in reports],
        recent_activity=[s.AuditLogOut.model_validate(a).model_dump(mode="json") for a in activity],
        withheld=sections.withheld,
    )
    return {"data": payload, "error": None}


@router.get("/applications/{application_id}", tags=["applications"], summary="Application detail with privacy and activity context", response_model=None)
async def application_detail(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("applications")),
) -> dict[str, Any]:
    application = await _one(db, Application, Application.application_id, application_id)
    if application is None:
        raise _missing("Application", application_id)

    sections = _Sections(user)
    personal = (
        await _many(
            db, select(PersonalDataInventory).where(PersonalDataInventory.application_id == application_id)
        )
        if sections.allows("personal_data_records", "dpdp/personal-data") else []
    )
    consents = (
        await _many(
            db, select(ConsentRecord).where(ConsentRecord.application_id == application_id).limit(100)
        )
        if sections.allows("consent_records", "dpdp/consents") else []
    )
    activity = (
        await _many(
            db,
            select(AuditLog)
            .where(AuditLog.application_id == application_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(RECENT_ACTIVITY_LIMIT),
        )
        if sections.allows("recent_activity", "audit-logs") else []
    )

    payload = s.ApplicationDetailOut.model_validate(application).model_dump(mode="json")
    payload.update(
        personal_data_records=[s.PersonalDataOut.model_validate(p).model_dump(mode="json") for p in personal],
        consent_records=[s.ConsentOut.model_validate(c).model_dump(mode="json") for c in consents],
        recent_activity=[s.AuditLogOut.model_validate(a).model_dump(mode="json") for a in activity],
        withheld=sections.withheld,
    )
    return {"data": payload, "error": None}
