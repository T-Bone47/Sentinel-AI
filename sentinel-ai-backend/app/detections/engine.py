"""
Running the detection rules and storing what they find.

  * Deterministic: the same events and rule versions always give the same
    alerts. An alert's id is the SHA-256 of rule id, rule version and trigger
    event, so running again stores nothing new (ADR-011).
  * Immutable: a stored alert is never changed. If later events mean a rule
    would no longer raise it (an approval that arrived late, say), the alert
    stays and the run counts it in alerts_no_longer_raised. What that means is
    a triage decision for Gate 4 (ADR-012).
  * Bounded: a run refuses a source with more than MAX_EVENTS_PER_RUN events.
  * Accounted for: every run leaves a row saying what it did, including failure.

A run covers one source and all of its history, inline in the caller's
request or command (ADR-006).
"""
from __future__ import annotations

import base64
import hashlib
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.detections.rules import RULES, EventView, Finding, Rule, evaluate
from app.events.adapters import ADAPTERS
from app.events.contract import SOURCE_ID_PATTERN
from app.models import DetectionAlert, DetectionAlertEvent, DetectionRun, SecurityEvent

# ponytail: a run holds one source's events in memory; per-actor streaming
# state is the upgrade path if a source outgrows this.
MAX_EVENTS_PER_RUN = 50_000
MAX_ATTEMPTS = 3
CHUNK = 500
LIST_FILTERS = ("rule_id", "severity", "actor_id", "source_type", "source_id")


class RunTooLarge(ValueError):
    """The source holds more events than one run may load."""


@dataclass
class RunReport:
    run_id: str
    source_type: str
    source_id: str
    status: str = "running"
    events_considered: int = 0
    alerts_created: int = 0
    alerts_existing: int = 0
    alerts_no_longer_raised: int = 0
    rule_versions: dict[str, int] = field(default_factory=dict)
    not_evaluable: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def alert_id_for(rule_id: str, version: int, trigger_event_id: str) -> str:
    return hashlib.sha256("\x1f".join((rule_id, str(version), trigger_event_id)).encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


async def _present(db: AsyncSession, alert_ids: list[str]) -> set[str]:
    found: set[str] = set()
    for start in range(0, len(alert_ids), CHUNK):
        chunk = alert_ids[start:start + CHUNK]
        found.update((await db.execute(select(DetectionAlert.alert_id).where(DetectionAlert.alert_id.in_(chunk)))).scalars())
    return found


async def _store(db: AsyncSession, run_id: str, source_type: str, source_id: str,
                 candidates: dict[str, tuple[Rule, Finding]], events: dict[str, EventView]) -> tuple[int, int]:
    """Insert the alerts not already stored, with their links, in one
    transaction. If another run stores some first, the primary key refuses the
    transaction; look again and retry."""
    for _ in range(MAX_ATTEMPTS):
        present = await _present(db, list(candidates))
        new = [(alert_id, rule, finding) for alert_id, (rule, finding) in candidates.items() if alert_id not in present]
        created_at = _now()
        db.add_all(DetectionAlert(
            alert_id=alert_id, rule_id=rule.id, rule_version=rule.version, severity=rule.severity,
            confidence=rule.confidence, source_type=source_type, source_id=source_id,
            actor_id=events[finding.trigger_id].actor_id, trigger_at=events[finding.trigger_id].occurred_at,
            summary=finding.summary, run_id=run_id, created_at=created_at) for alert_id, rule, finding in new)
        try:
            await db.flush()                           # alerts before the links that reference them
            for alert_id, _, finding in new:
                context = sorted(finding.context_ids, key=lambda i: (events[i].occurred_at, i))
                db.add(DetectionAlertEvent(alert_id=alert_id, event_id=finding.trigger_id, role="trigger", ordinal=0))
                db.add_all(DetectionAlertEvent(alert_id=alert_id, event_id=event_id, role="context", ordinal=n)
                           for n, event_id in enumerate(context, 1))
            await db.commit()
        except IntegrityError:
            await db.rollback()
            continue
        return len(new), len(candidates) - len(new)
    raise RuntimeError(f"could not store alerts after {MAX_ATTEMPTS} attempts")


async def _stored_for(db: AsyncSession, source_type: str, source_id: str, versions: dict[str, int]) -> set[str]:
    if not versions:
        return set()
    same_version = or_(*(and_(DetectionAlert.rule_id == rule_id, DetectionAlert.rule_version == version)
                         for rule_id, version in versions.items()))
    stmt = select(DetectionAlert.alert_id).where(
        DetectionAlert.source_type == source_type, DetectionAlert.source_id == source_id, same_version)
    return set((await db.execute(stmt)).scalars())


async def run_detections(db: AsyncSession, *, source_type: str, source_id: str, origin: str,
                         triggered_by: str | None = None, rules: dict[str, Rule] | None = None) -> RunReport:
    """Run the rules over every stored event of one source. Raises ValueError
    (RunTooLarge for size) before writing anything if the run is not acceptable."""
    active = RULES if rules is None else rules
    if source_type not in ADAPTERS:
        raise ValueError(f"unknown source_type; known types: {', '.join(sorted(ADAPTERS))}")
    if not re.fullmatch(SOURCE_ID_PATTERN, source_id):
        raise ValueError("source_id must be 1 to 120 characters: letters, digits, '.', '_', ':' or '-'")
    in_source = and_(SecurityEvent.source_type == source_type, SecurityEvent.source_id == source_id)
    count = (await db.execute(select(func.count()).select_from(SecurityEvent).where(in_source))).scalar_one()
    if count > MAX_EVENTS_PER_RUN:
        raise RunTooLarge(f"this source has {count} events; a run is limited to {MAX_EVENTS_PER_RUN}")

    versions = {rule.id: rule.version for rule in active.values()}
    report = RunReport(run_id=str(uuid.uuid4()), source_type=source_type, source_id=source_id, rule_versions=versions)
    db.add(DetectionRun(id=report.run_id, source_type=source_type, source_id=source_id, origin=origin,
                        triggered_by=triggered_by, status="running", started_at=_now(), rule_versions=versions,
                        events_considered=0, alerts_created=0, alerts_existing=0, alerts_no_longer_raised=0,
                        not_evaluable={}))
    await db.commit()
    try:
        columns = (SecurityEvent.event_id, SecurityEvent.occurred_at, SecurityEvent.action, SecurityEvent.outcome,
                   SecurityEvent.actor_id, SecurityEvent.target_id, SecurityEvent.attributes)
        views = [EventView(event_id=r.event_id, occurred_at=r.occurred_at, action=r.action, outcome=r.outcome,
                           actor_id=r.actor_id, target_id=r.target_id, attributes=r.attributes or {})
                 for r in (await db.execute(select(*columns).where(in_source))).all()]
        results = evaluate(views, active)
        candidates = {alert_id_for(rule_id, active[rule_id].version, finding.trigger_id): (active[rule_id], finding)
                      for rule_id, result in results.items() for finding in result.findings}
        report.events_considered = len(views)
        report.not_evaluable = {rule_id: result.not_evaluable for rule_id, result in results.items()}
        report.alerts_created, report.alerts_existing = await _store(
            db, report.run_id, source_type, source_id, candidates, {v.event_id: v for v in views})
        report.alerts_no_longer_raised = len(await _stored_for(db, source_type, source_id, versions) - set(candidates))
        report.status = "completed"
        await db.execute(update(DetectionRun).where(DetectionRun.id == report.run_id).values(
            status="completed", finished_at=_now(), events_considered=report.events_considered,
            alerts_created=report.alerts_created, alerts_existing=report.alerts_existing,
            alerts_no_longer_raised=report.alerts_no_longer_raised, not_evaluable=report.not_evaluable))
        await db.commit()
    except Exception:
        await db.rollback()
        await db.execute(update(DetectionRun).where(DetectionRun.id == report.run_id)
                         .values(status="failed", finished_at=_now()))
        await db.commit()
        raise
    return report


# --- reading ---------------------------------------------------------------------

def _alert_out(a: DetectionAlert) -> dict[str, Any]:
    return {"alert_id": a.alert_id, "rule_id": a.rule_id, "rule_version": a.rule_version, "severity": a.severity,
            "confidence": a.confidence, "source_type": a.source_type, "source_id": a.source_id,
            "actor_id": a.actor_id, "trigger_at": _iso(a.trigger_at), "summary": a.summary, "run_id": a.run_id,
            "created_at": _iso(a.created_at)}


async def _cited_events(db: AsyncSession, alert_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for start in range(0, len(alert_ids), CHUNK):
        rows = await db.execute(
            select(DetectionAlertEvent.alert_id, DetectionAlertEvent.role, SecurityEvent.event_id,
                   SecurityEvent.source_event_id, SecurityEvent.occurred_at, SecurityEvent.action,
                   SecurityEvent.outcome, SecurityEvent.actor_id, SecurityEvent.target_id, SecurityEvent.raw_sha256)
            .join(SecurityEvent, SecurityEvent.event_id == DetectionAlertEvent.event_id)
            .where(DetectionAlertEvent.alert_id.in_(alert_ids[start:start + CHUNK]))
            .order_by(DetectionAlertEvent.alert_id, DetectionAlertEvent.ordinal))
        for r in rows.all():
            out.setdefault(r.alert_id, []).append({
                "role": r.role, "event_id": r.event_id, "source_event_id": r.source_event_id,
                "occurred_at": _iso(r.occurred_at), "action": r.action, "outcome": r.outcome,
                "actor_id": r.actor_id, "target_id": r.target_id, "raw_sha256": r.raw_sha256,
                "path": f"/api/v1/security-events/{r.event_id}"})
    return out


async def export_alerts(db: AsyncSession, *, source_type: str | None = None,
                        source_id: str | None = None) -> list[dict[str, Any]]:
    """Every stored alert (for one source, if given) with the events it cites,
    in trigger-time order — the evaluator's input."""
    stmt = select(DetectionAlert).order_by(DetectionAlert.trigger_at, DetectionAlert.alert_id)
    if source_type is not None:
        stmt = stmt.where(DetectionAlert.source_type == source_type)
    if source_id is not None:
        stmt = stmt.where(DetectionAlert.source_id == source_id)
    alerts = list((await db.execute(stmt)).scalars().all())
    cited = await _cited_events(db, [a.alert_id for a in alerts])
    return [{**_alert_out(a), "events": cited.get(a.alert_id, [])} for a in alerts]


def _encode_cursor(trigger_at: datetime, alert_id: str) -> str:
    return base64.urlsafe_b64encode(f"{trigger_at.isoformat()}|{alert_id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        stamp, alert_id = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8").split("|")
        at = datetime.fromisoformat(stamp)
        if at.tzinfo is None or not re.fullmatch(r"[0-9a-f]{64}", alert_id):
            raise ValueError
    except ValueError:
        raise ValueError("invalid cursor") from None
    return at, alert_id


async def list_alerts(db: AsyncSession, *, filters: dict[str, str | None] | None = None, order: str = "desc",
                      limit: int = 50, cursor: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
    at, aid = DetectionAlert.trigger_at, DetectionAlert.alert_id
    stmt = select(DetectionAlert)
    for name, value in (filters or {}).items():
        if name not in LIST_FILTERS:
            raise KeyError(name)
        if value is not None:
            stmt = stmt.where(getattr(DetectionAlert, name) == value)
    if cursor:
        last_at, last_id = _decode_cursor(cursor)
        stmt = stmt.where(or_(at > last_at, and_(at == last_at, aid > last_id)) if order == "asc"
                          else or_(at < last_at, and_(at == last_at, aid < last_id)))
    stmt = stmt.order_by(at.asc(), aid.asc()) if order == "asc" else stmt.order_by(at.desc(), aid.desc())
    rows = list((await db.execute(stmt.limit(limit + 1))).scalars().all())
    more, rows = len(rows) > limit, rows[:limit]
    return [_alert_out(r) for r in rows], (_encode_cursor(rows[-1].trigger_at, rows[-1].alert_id) if more else None)


async def get_alert(db: AsyncSession, alert_id: str) -> dict[str, Any] | None:
    row = (await db.execute(select(DetectionAlert).where(DetectionAlert.alert_id == alert_id))).scalar_one_or_none()
    if row is None:
        return None
    return {**_alert_out(row), "events": (await _cited_events(db, [alert_id])).get(alert_id, [])}


async def get_run(db: AsyncSession, run_id: str) -> dict[str, Any] | None:
    r = (await db.execute(select(DetectionRun).where(DetectionRun.id == run_id))).scalar_one_or_none()
    if r is None:
        return None
    return {"run_id": r.id, "source_type": r.source_type, "source_id": r.source_id, "origin": r.origin,
            "triggered_by": r.triggered_by, "status": r.status, "started_at": _iso(r.started_at),
            "finished_at": _iso(r.finished_at), "rule_versions": r.rule_versions,
            "events_considered": r.events_considered, "alerts_created": r.alerts_created,
            "alerts_existing": r.alerts_existing, "alerts_no_longer_raised": r.alerts_no_longer_raised,
            "not_evaluable": r.not_evaluable}
