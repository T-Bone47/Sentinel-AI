"""
Security events over HTTP: ingestion, and read access to events and to the
ingestion batches that produced them.

Reading needs READ on "security-events" (internal staff: these are records of
what individual people did). Ingesting additionally needs INGEST (admin).
There is no update or delete endpoint: stored events are immutable.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.auth_router import require_permission
from app.core.permissions import INGEST
from app.database.session import get_db
from app.events.adapters import ADAPTERS
from app.events.contract import MAX_BATCH_RECORDS, MAX_BODY_BYTES, SOURCE_ID_PATTERN
from app.events.store import ingest, list_events
from app.models import EventIngestBatch, EventIngestReject, SecurityEvent, User
from app.schemas.common import ORMModel

router = APIRouter(dependencies=[Depends(require_permission("security-events"))])

MAX_REJECTS_SHOWN = 1000


class EventOut(ORMModel):
    event_id: str
    schema_version: int
    source_type: str
    source_id: str
    source_event_id: str
    occurred_at: datetime
    ingested_at: datetime
    actor_type: str | None
    actor_id: str | None
    target_type: str | None
    target_id: str | None
    action: str
    source_action: str
    outcome: str
    src_ip: str | None
    attributes: dict[str, Any]
    normalizer: str
    ingest_batch_id: str
    raw_sha256: str


class BatchOut(ORMModel):
    id: str
    source_type: str
    source_id: str
    origin: str
    origin_detail: str | None
    submitted_by: str | None
    status: str
    started_at: datetime
    finished_at: datetime | None
    received: int
    inserted: int
    duplicates: int
    conflicts: int
    rejected: int


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str = Field(description="Which adapter reads the records, e.g. `sentinel.native`.")
    source_id: str = Field(pattern=SOURCE_ID_PATTERN, description="Which feed the records belong to.")
    # Items are validated one by one, so a bad record is rejected on its own
    # instead of failing the whole request.
    records: list[Any] = Field(min_length=1, max_length=MAX_BATCH_RECORDS)


def _invalid(location: tuple[str, ...], message: str) -> RequestValidationError:
    return RequestValidationError([{"loc": location, "msg": message, "type": "value_error"}])


async def _read_body(request: Request) -> bytes:
    """The request body, refused with 413 as soon as it is known to exceed
    MAX_BODY_BYTES — before it is read when Content-Length says so, otherwise
    while streaming. The framework would read any size into memory."""
    too_large = HTTPException(status_code=413, detail=f"Request body is larger than {MAX_BODY_BYTES} bytes")
    declared = request.headers.get("content-length")
    if declared is not None and (not declared.isdigit() or int(declared) > MAX_BODY_BYTES):
        raise too_large
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            raise too_large
        chunks.append(chunk)
    return b"".join(chunks)


@router.post(
    "/security-events/ingest",
    tags=["security-events"],
    summary="Ingest a batch of source records",
    description=(
        f"Up to {MAX_BATCH_RECORDS} records and {MAX_BODY_BYTES} bytes per request. Each record is "
        "normalized by the adapter named in `source_type` and stored as one immutable event, or "
        "refused with a reason. The response always accounts for every record: "
        "`received == inserted + duplicates + conflicts + rejected`. Sending the same records again "
        "is safe; they are counted as `duplicates` and nothing changes."
    ),
    response_model=None,
    openapi_extra={"requestBody": {"required": True, "content": {"application/json": {"schema": IngestRequest.model_json_schema()}}}},
)
async def ingest_events(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("security-events", action=INGEST)),
) -> dict[str, Any]:
    body = await _read_body(request)
    try:
        payload = json.loads(body)
    except (ValueError, RecursionError):
        raise _invalid(("body",), "is not valid JSON") from None
    try:
        parsed = IngestRequest.model_validate(payload)
    except ValidationError as exc:
        raise RequestValidationError([{**error, "loc": ("body", *error["loc"])} for error in exc.errors()]) from None
    if parsed.source_type not in ADAPTERS:
        raise _invalid(("body", "source_type"), f"is not a known source type; known types: {', '.join(sorted(ADAPTERS))}")

    report = await ingest(db, source_type=parsed.source_type, source_id=parsed.source_id,
                          records=parsed.records, origin="api", submitted_by=user.email)
    return {"data": report.as_dict(), "error": None}


@router.get(
    "/security-events",
    tags=["security-events"],
    summary="List events in event-time order",
    description=(
        "Ordered by `occurred_at` (when the source says it happened), then `event_id`. "
        "Page with `cursor`: pass back `meta.next_cursor` until it is null. Pages do not repeat or "
        "skip events while new ones are being ingested. The source record itself is only returned "
        "by the detail endpoint."
    ),
    response_model=None,
)
async def list_security_events(
    source_type: str | None = Query(None, max_length=40),
    source_id: str | None = Query(None, max_length=120),
    actor_id: str | None = Query(None, max_length=512),
    target_id: str | None = Query(None, max_length=512),
    action: str | None = Query(None, max_length=40),
    outcome: str | None = Query(None, max_length=10),
    occurred_from: AwareDatetime | None = Query(None, description="Inclusive. Must include a UTC offset."),
    occurred_to: AwareDatetime | None = Query(None, description="Inclusive. Must include a UTC offset."),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=400),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    filters = {"source_type": source_type, "source_id": source_id, "actor_id": actor_id,
               "target_id": target_id, "action": action, "outcome": outcome}
    try:
        rows, next_cursor = await list_events(db, filters=filters, occurred_from=occurred_from,
                                              occurred_to=occurred_to, order=order, limit=limit, cursor=cursor)
    except ValueError:
        raise _invalid(("query", "cursor"), "is not a cursor returned by this endpoint") from None
    return {
        "data": [EventOut.model_validate(row).model_dump(mode="json") for row in rows],
        "meta": {"count": len(rows), "limit": limit, "order": order, "next_cursor": next_cursor},
        "error": None,
    }


@router.get(
    "/security-events/batches",
    tags=["security-events"],
    summary="Recent ingestion batches, newest first",
    response_model=None,
)
async def list_batches(
    source_id: str | None = Query(None, max_length=120),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    stmt = select(EventIngestBatch).order_by(EventIngestBatch.started_at.desc(), EventIngestBatch.id.desc()).limit(limit)
    if source_id is not None:
        stmt = stmt.where(EventIngestBatch.source_id == source_id)
    rows = (await db.execute(stmt)).scalars().all()
    return {"data": [BatchOut.model_validate(row).model_dump(mode="json") for row in rows], "error": None}


@router.get(
    "/security-events/batches/{batch_id}",
    tags=["security-events"],
    summary="One ingestion batch, with the reason for every record it did not store",
    response_model=None,
)
async def get_batch(batch_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    batch = (await db.execute(select(EventIngestBatch).where(EventIngestBatch.id == batch_id))).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    rejects = (await db.execute(
        select(EventIngestReject).where(EventIngestReject.batch_id == batch_id)
        .order_by(EventIngestReject.record_index, EventIngestReject.id).limit(MAX_REJECTS_SHOWN)
    )).scalars().all()
    data = BatchOut.model_validate(batch).model_dump(mode="json")
    data["rejects"] = [
        {"index": r.record_index, "reason": r.reason, "detail": r.detail,
         "source_event_id": r.source_event_id, "raw_sha256": r.raw_sha256}
        for r in rejects
    ]
    return {"data": data, "error": None}


@router.get(
    "/security-events/{event_id}",
    tags=["security-events"],
    summary="One event with its source record and provenance",
    description=(
        "`raw` is the source record as received. `raw_sha256` is the SHA-256 of its canonical JSON "
        "form (keys sorted, no insignificant whitespace, UTF-8), so the stored record can be checked "
        "against the hash."
    ),
    response_model=None,
)
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    row = (await db.execute(select(SecurityEvent).where(SecurityEvent.event_id == event_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    data = EventOut.model_validate(row).model_dump(mode="json")
    data["raw"] = json.loads(row.raw_canonical)
    return {"data": data, "error": None}
