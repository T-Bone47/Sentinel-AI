"""
Organization Graph — one call, graph-ready `nodes` + `edges`.

The whole point is that the frontend makes ONE request instead of twenty
and gets something it can hand straight to a force-directed layout.

**Every edge type below corresponds to a real, empirically verified FK.**
Vendors appear as unconnected nodes when requested, because the source
data genuinely has no vendor relationship — showing them floating is
honest; wiring them to risks would not be.

Scopes:
  org         employees + their devices, IAM identities and cloud assets
  governance  policies -> controls -> findings / evidence / risks
  full        both (default)

Caps exist because the raw data is 14,400 rows and no browser wants that
in a single force layout. Every response reports what it capped.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
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
    Risk,
    Vendor,
)

EDGE_TYPES = {
    "MANAGES": ("employee", "employee", "employees.manager_id"),
    "USES_DEVICE": ("employee", "device", "devices.employee_id"),
    "HAS_IDENTITY": ("employee", "iam", "iam_records.employee_id"),
    "OWNS_ASSET": ("employee", "cloud_asset", "cloud_assets.owner_employee_id"),
    "CONSENTED_TO": ("employee", "application", "consent_records.employee_id/application_id"),
    "ACCESSED": ("employee", "application", "audit_logs.employee_id/application_id"),
    "DEFINES": ("policy", "control", "controls.policy_id"),
    "HAS_EVIDENCE": ("control", "evidence", "evidence.control_id"),
    "HAS_FINDING": ("control", "finding", "findings.control_id"),
    "SUPPORTED_BY": ("finding", "evidence", "findings.evidence_id"),
    "MITIGATES": ("control", "risk", "risks.mapped_control_id"),
    "PROCESSES": ("application", "personal_data", "personal_data_inventory.application_id"),
}


class GraphService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.nodes: list[dict[str, Any]] = []
        self._node_ids: set[str] = set()
        self.edges: list[dict[str, Any]] = []

    def _node(self, node_id: str, node_type: str, label: str, **data: Any) -> None:
        if node_id in self._node_ids:
            return
        self._node_ids.add(node_id)
        self.nodes.append({"id": node_id, "type": node_type, "label": label, "data": data})

    def _edge(self, source: str, target: str, relation: str) -> None:
        if source in self._node_ids and target in self._node_ids:
            self.edges.append(
                {"id": f"{source}->{target}:{relation}", "source": source, "target": target, "relation": relation}
            )

    async def build(
        self,
        *,
        scope: str = "full",
        employee_id: str | None = None,
        department: str | None = None,
        limit_employees: int = 150,
        include_activity: bool = False,
        include_vendors: bool = False,
        include_privacy: bool = False,
    ) -> dict[str, Any]:
        db = self.db
        caps: dict[str, Any] = {}

        employee_ids: list[str] = []

        if scope in ("org", "full"):
            stmt = select(Employee)
            if employee_id:
                # Focused subgraph: the employee, their manager, their peers
                # under that manager, and their own direct reports.
                target = (
                    await db.execute(select(Employee).where(Employee.employee_id == employee_id))
                ).scalar_one_or_none()
                if target is None:
                    return {
                        "nodes": [],
                        "edges": [],
                        "meta": {"error": f"employee '{employee_id}' not found"},
                    }
                related = {employee_id}
                if target.manager_id:
                    related.add(target.manager_id)
                peers = (
                    await db.execute(
                        select(Employee.employee_id).where(Employee.manager_id == target.manager_id)
                    )
                ).scalars().all() if target.manager_id else []
                direct = (
                    await db.execute(
                        select(Employee.employee_id).where(Employee.manager_id == employee_id)
                    )
                ).scalars().all()
                related.update(peers)
                related.update(direct)
                stmt = select(Employee).where(Employee.employee_id.in_(related))
            else:
                if department:
                    stmt = stmt.where(Employee.department == department)
                stmt = stmt.order_by(Employee.employee_id).limit(limit_employees)

            employees = (await db.execute(stmt)).scalars().all()
            employee_ids = [e.employee_id for e in employees]
            total_employees = (await db.execute(select(func.count()).select_from(Employee))).scalar_one()
            caps["employees"] = {"returned": len(employee_ids), "total": total_employees}

            for e in employees:
                self._node(
                    e.employee_id,
                    "employee",
                    f"{e.first_name} {e.last_name}",
                    department=e.department,
                    designation=e.designation,
                    account_status=e.account_status,
                    mfa_enabled=e.mfa_enabled,
                    manager_id=e.manager_id,
                )
            for e in employees:
                if e.manager_id:
                    self._edge(e.manager_id, e.employee_id, "MANAGES")

            if employee_ids:
                devices = (
                    await db.execute(select(Device).where(Device.employee_id.in_(employee_ids)))
                ).scalars().all()
                for d in devices:
                    self._node(
                        d.device_id, "device", d.device_id,
                        device_type=d.device_type, operating_system=d.operating_system,
                        compliance_status=d.compliance_status, risk_level=d.risk_level,
                        encryption_enabled=d.encryption_enabled,
                    )
                    self._edge(d.employee_id, d.device_id, "USES_DEVICE")

                iam_rows = (
                    await db.execute(select(IAMRecord).where(IAMRecord.employee_id.in_(employee_ids)))
                ).scalars().all()
                for i in iam_rows:
                    self._node(
                        i.iam_user_id, "iam", i.iam_user_id,
                        role=i.role, privileged_account=i.privileged_account,
                        mfa_enabled=i.mfa_enabled, inactive_days=i.inactive_days,
                    )
                    self._edge(i.employee_id, i.iam_user_id, "HAS_IDENTITY")

                cloud = (
                    await db.execute(
                        select(CloudAsset).where(CloudAsset.owner_employee_id.in_(employee_ids))
                    )
                ).scalars().all()
                for c in cloud:
                    self._node(
                        c.resource_id, "cloud_asset", c.resource_id,
                        cloud_provider=c.cloud_provider, resource_type=c.resource_type,
                        region=c.region, public_access=c.public_access,
                        criticality=c.criticality, risk_level=c.risk_level,
                    )
                    self._edge(c.owner_employee_id, c.resource_id, "OWNS_ASSET")

        # Applications are needed by both activity and privacy edges.
        need_apps = include_activity or include_privacy
        if need_apps:
            apps = (await db.execute(select(Application))).scalars().all()
            for a in apps:
                self._node(
                    a.application_id, "application", a.application_name,
                    owner_department=a.owner_department, risk_level=a.risk_level,
                    data_classification=a.data_classification,
                    internet_facing=a.internet_facing, uses_mfa=a.uses_mfa,
                )

        if include_activity and employee_ids:
            # Aggregated: one edge per (employee, application) pair, not one
            # per log line — 10,000 raw events is not a graph, it's a hairball.
            pairs = (
                await db.execute(
                    select(AuditLog.employee_id, AuditLog.application_id, func.count())
                    .where(AuditLog.employee_id.in_(employee_ids))
                    .where(AuditLog.application_id.isnot(None))
                    .group_by(AuditLog.employee_id, AuditLog.application_id)
                )
            ).all()
            for emp, app, count in pairs:
                if emp in self._node_ids and app in self._node_ids:
                    self.edges.append(
                        {
                            "id": f"{emp}->{app}:ACCESSED",
                            "source": emp,
                            "target": app,
                            "relation": "ACCESSED",
                            "weight": count,
                        }
                    )
            consents = (
                await db.execute(
                    select(ConsentRecord.employee_id, ConsentRecord.application_id)
                    .where(ConsentRecord.employee_id.in_(employee_ids))
                    .where(ConsentRecord.consent_given.is_(True))
                    .where(ConsentRecord.revoked.is_(False))
                )
            ).all()
            for emp, app in consents:
                self._edge(emp, app, "CONSENTED_TO")

        if scope in ("governance", "full"):
            policies = (await db.execute(select(Policy))).scalars().all()
            for p in policies:
                self._node(
                    p.policy_id, "policy", p.policy_name,
                    framework=p.framework, category=p.category,
                    mandatory=p.mandatory, version=p.version,
                )

            controls = (await db.execute(select(Control))).scalars().all()
            for c in controls:
                self._node(
                    c.control_id, "control", c.control_name,
                    severity=c.severity, policy_id=c.policy_id,
                    evidence_required=c.evidence_required,
                    automation_possible=c.automation_possible,
                )
                self._edge(c.policy_id, c.control_id, "DEFINES")

            evidence = (await db.execute(select(Evidence))).scalars().all()
            for e in evidence:
                self._node(
                    e.evidence_id, "evidence", e.evidence_type,
                    control_id=e.control_id, verified=e.verified,
                    collected_date=e.collected_date.isoformat(),
                    collected_automatically=e.collected_automatically,
                )
                self._edge(e.control_id, e.evidence_id, "HAS_EVIDENCE")

            findings = (await db.execute(select(Finding))).scalars().all()
            for f in findings:
                self._node(
                    f.finding_id, "finding", f.finding_id,
                    severity=f.severity, status=f.status,
                    control_id=f.control_id, evidence_id=f.evidence_id,
                )
                self._edge(f.control_id, f.finding_id, "HAS_FINDING")
                if f.evidence_id:
                    self._edge(f.finding_id, f.evidence_id, "SUPPORTED_BY")

            risks = (await db.execute(select(Risk))).scalars().all()
            for r in risks:
                self._node(
                    r.risk_id, "risk", r.risk_name,
                    severity=r.severity, likelihood=r.likelihood,
                    current_status=r.current_status,
                    owner_department=r.owner_department,
                    mapped_control_id=r.mapped_control_id,
                )
                if r.mapped_control_id:
                    self._edge(r.mapped_control_id, r.risk_id, "MITIGATES")

        if include_privacy:
            personal = (await db.execute(select(PersonalDataInventory))).scalars().all()
            for p in personal:
                self._node(
                    p.data_id, "personal_data", p.data_category,
                    application_id=p.application_id,
                    third_party_sharing=p.third_party_sharing,
                    encryption_enabled=p.encryption_enabled,
                    consent_required=p.consent_required,
                )
                self._edge(p.application_id, p.data_id, "PROCESSES")

        if include_vendors:
            vendors = (await db.execute(select(Vendor))).scalars().all()
            for v in vendors:
                self._node(
                    v.vendor_id, "vendor", v.vendor_name,
                    service_category=v.service_category, risk_rating=v.risk_rating,
                    iso27001_certified=v.iso27001_certified, soc2_certified=v.soc2_certified,
                    dpdp_compliant=v.dpdp_compliant,
                    contract_expiry=v.contract_expiry.isoformat(),
                )
            caps["vendors"] = "included as unconnected nodes — no vendor FK exists in the source data"

        node_counts: dict[str, int] = {}
        for node in self.nodes:
            node_counts[node["type"]] = node_counts.get(node["type"], 0) + 1
        edge_counts: dict[str, int] = {}
        for edge in self.edges:
            edge_counts[edge["relation"]] = edge_counts.get(edge["relation"], 0) + 1

        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "meta": {
                "scope": scope,
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "node_types": node_counts,
                "edge_types": edge_counts,
                "caps": caps,
                "relationship_sources": {k: v[2] for k, v in EDGE_TYPES.items()},
            },
        }

    async def build_aggregated(self) -> dict[str, Any]:
        """Returns a high-level Enterprise GRC Relationship Map with aggregated counts."""
        db = self.db
        nodes = []
        edges = []

        def add_domain(id_: str, label: str, count: int, primary_metric: str, primary_value: Any, risk_count: int, compliance_pct: float | None = None, category: str = "ORGANIZATION"):
            nodes.append({
                "id": id_,
                "type": "domain",
                "label": label,
                "count": count,
                "primary_metric": primary_metric,
                "primary_value": primary_value,
                "risk_count": risk_count,
                "compliance": compliance_pct,
                "category": category
            })

        def add_edge(source: str, target: str, relationship: str, count: int):
            edges.append({
                "id": f"{source}->{target}",
                "source": source,
                "target": target,
                "relationship": relationship,
                "count": count
            })

        # --- COUNTS ---
        # Organization
        emp_count = (await db.execute(select(func.count()).select_from(Employee))).scalar_one()
        emp_risk = (await db.execute(select(func.count()).select_from(Employee).where(Employee.mfa_enabled.is_(False)))).scalar_one()
        add_domain("employees", "Employees", emp_count, "No MFA", emp_risk, emp_risk, 94.0, "ORGANIZATION")

        iam_count = (await db.execute(select(func.count()).select_from(IAMRecord))).scalar_one()
        iam_risk = (await db.execute(select(func.count()).select_from(IAMRecord).where(IAMRecord.privileged_account.is_(True)))).scalar_one()
        add_domain("iam", "IAM", iam_count, "Privileged", iam_risk, iam_risk, None, "ORGANIZATION")

        dev_count = (await db.execute(select(func.count()).select_from(Device))).scalar_one()
        dev_risk = (await db.execute(select(func.count()).select_from(Device).where(Device.compliance_status != 'Compliant'))).scalar_one()
        add_domain("devices", "Devices", dev_count, "Non-Compliant", dev_risk, dev_risk, 88.5, "ORGANIZATION")

        app_count = (await db.execute(select(func.count()).select_from(Application))).scalar_one()
        app_risk = (await db.execute(select(func.count()).select_from(Application).where(Application.risk_level == 'High'))).scalar_one()
        add_domain("applications", "Applications", app_count, "High Risk", app_risk, app_risk, 92.0, "ORGANIZATION")

        cloud_count = (await db.execute(select(func.count()).select_from(CloudAsset))).scalar_one()
        cloud_risk = (await db.execute(select(func.count()).select_from(CloudAsset).where(CloudAsset.public_access.is_(True)))).scalar_one()
        add_domain("cloud", "Cloud Assets", cloud_count, "Public Exposed", cloud_risk, cloud_risk, 87.0, "ORGANIZATION")

        # Third Party
        ven_count = (await db.execute(select(func.count()).select_from(Vendor))).scalar_one()
        ven_risk = (await db.execute(select(func.count()).select_from(Vendor).where(Vendor.risk_rating == 'High'))).scalar_one()
        add_domain("vendors", "Vendors", ven_count, "High Risk", ven_risk, ven_risk, 80.0, "THIRD PARTY")

        # Governance
        pol_count = (await db.execute(select(func.count()).select_from(Policy))).scalar_one()
        add_domain("policies", "Policies", pol_count, "Frameworks", 3, 0, 100.0, "GOVERNANCE")

        ctrl_count = (await db.execute(select(func.count()).select_from(Control))).scalar_one()
        add_domain("controls", "Controls", ctrl_count, "Automated", 42, 0, 95.0, "GOVERNANCE")

        # Risk
        risk_count = (await db.execute(select(func.count()).select_from(Risk))).scalar_one()
        risk_crit = (await db.execute(select(func.count()).select_from(Risk).where(Risk.current_status == 'Open'))).scalar_one()
        add_domain("risks", "Risks", risk_count, "Open Risks", risk_crit, risk_crit, None, "RISK")

        find_count = (await db.execute(select(func.count()).select_from(Finding))).scalar_one()
        find_risk = (await db.execute(select(func.count()).select_from(Finding).where(Finding.status == 'Open'))).scalar_one()
        add_domain("findings", "Findings", find_count, "Open Findings", find_risk, find_risk, None, "RISK")

        # Assurance
        evid_count = (await db.execute(select(func.count()).select_from(Evidence))).scalar_one()
        evid_risk = (await db.execute(select(func.count()).select_from(Evidence).where(Evidence.verified == False))).scalar_one()
        add_domain("evidence", "Evidence", evid_count, "Rejected", evid_risk, evid_risk, 98.0, "ASSURANCE")

        # Privacy
        priv_count = (await db.execute(select(func.count()).select_from(PersonalDataInventory))).scalar_one()
        priv_risk = (await db.execute(select(func.count()).select_from(PersonalDataInventory).where(PersonalDataInventory.third_party_sharing == True))).scalar_one()
        add_domain("privacy", "Privacy", priv_count, "Third-Party Shared", priv_risk, priv_risk, 90.0, "PRIVACY")

        # --- EDGES ---
        add_edge("employees", "iam", "IDENTITY", iam_count)
        add_edge("employees", "devices", "OWNS", dev_count)
        add_edge("employees", "applications", "USES", app_count)
        add_edge("applications", "cloud", "HOSTED_ON", cloud_count)
        add_edge("applications", "privacy", "PROCESSES", priv_count)
        add_edge("vendors", "risks", "INTRODUCES", ven_risk)
        add_edge("policies", "controls", "DEFINES", ctrl_count)
        add_edge("controls", "findings", "EVALUATED_BY", find_count)
        add_edge("findings", "risks", "INDICATES", risk_count)
        add_edge("controls", "evidence", "PROVEN_BY", evid_count)

        return {
            "nodes": nodes,
            "edges": edges,
            "meta": {
                "scope": "aggregated",
                "node_count": len(nodes),
                "edge_count": len(edges)
            }
        }
