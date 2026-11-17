"""
Detections over HTTP: the rule catalogue, detection runs, and the alerts they raise.

  GET  /detections/rules         all staff (rules hold no personal data)
  POST /detections/runs          admin, security analyst
  GET  /detections/runs/{id}     internal staff
  GET  /detections/alerts        internal staff (alerts cite per-person events)
  GET  /detections/alerts/{id}   internal staff

Nothing here changes or deletes an alert: alerts are immutable. Triage
(status, assignee, notes) belongs to Gate 4 and will be stored separately.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.auth_router import require_permission
from app.core.permissions import RUN
from app.database.session import get_db
from app.detections import engine
from app.detections.catalog import catalogue
from app.events.adapters import ADAPTERS
from app.events.contract import SOURCE_ID_PATTERN
from app.models import User

router = APIRouter()
_READ = require_permission("detections")
RETROSPECTIVE = ("Retrospective batch analysis: alerts are raised when a detection run is started over "
                 "stored events, not as events arrive.")


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str = Field(max_length=40, description="Adapter the source was read with, e.g. `sentinel.native`.")
    source_id: str = Field(pattern=SOURCE_ID_PATTERN, description="The source to run over.")


@router.get("/detections/rules", tags=["detections"], summary="The detection rules and their written contracts",
            response_model=None, dependencies=[Depends(require_permission("detection-rules"))])
async def list_rules() -> dict[str, Any]:
    return {"data": catalogue(), "meta": {"mode": "retrospective", "note": RETROSPECTIVE}, "error": None}


@router.post("/detections/runs", tags=["detections"], summary="Run every rule over one source's stored events",
             description=RETROSPECTIVE + " Running again is safe: alerts already stored are counted, not duplicated.",
             response_model=None)
async def start_run(
    body: RunRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("detections", action=RUN)),
) -> dict[str, Any]:
    if body.source_type not in ADAPTERS:
        raise RequestValidationError([{"loc": ("body", "source_type"), "type": "value_error",
                                       "msg": f"is not a known source type; known: {', '.join(sorted(ADAPTERS))}"}])
    try:
        report = await engine.run_detections(db, source_type=body.source_type, source_id=body.source_id,
                                             origin="api", triggered_by=user.email)
    except engine.RunTooLarge as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return {"data": report.as_dict(), "error": None}


@router.get("/detections/runs/{run_id}", tags=["detections"], summary="One detection run",
            response_model=None, dependencies=[Depends(_READ)])
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    run = await engine.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"data": run, "error": None}


@router.get("/detections/alerts", tags=["detections"], summary="Alerts in trigger-time order",
            description="Page with `cursor`: pass back `meta.next_cursor` until it is null. " + RETROSPECTIVE,
            response_model=None, dependencies=[Depends(_READ)])
async def list_alerts(
    rule_id: str | None = Query(None, max_length=20),
    severity: str | None = Query(None, max_length=10),
    actor_id: str | None = Query(None, max_length=512),
    source_type: str | None = Query(None, max_length=40),
    source_id: str | None = Query(None, max_length=120),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=400),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    filters = {"rule_id": rule_id, "severity": severity, "actor_id": actor_id,
               "source_type": source_type, "source_id": source_id}
    try:
        rows, next_cursor = await engine.list_alerts(db, filters=filters, order=order, limit=limit, cursor=cursor)
    except ValueError:
        raise RequestValidationError([{"loc": ("query", "cursor"), "type": "value_error",
                                       "msg": "is not a cursor returned by this endpoint"}]) from None
    return {"data": rows, "meta": {"count": len(rows), "limit": limit, "order": order,
                                   "next_cursor": next_cursor, "mode": "retrospective"}, "error": None}


@router.get("/detections/alerts/{alert_id}", tags=["detections"],
            summary="One alert with every event it cites and each event's source-record hash",
            response_model=None, dependencies=[Depends(_READ)])
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    alert = await engine.get_alert(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"data": alert, "error": None}
