"""
The event store: ingestion and reading.

Ingestion guarantees
  * Exactly once. An event's id is derived from where it came from, so the
    same source record always maps to the same row and re-ingesting it is a
    no-op. Running an input twice, or resuming after a crash, is always safe.
  * First write wins. If a source later sends different content under an id
    we already hold, the stored event is kept and the new record is logged as
    a conflict (with its hash, not its content). Events are never rewritten.
  * Everything is accounted for. For every batch,
        received == inserted + duplicates + conflicts + rejected
    and each record that was not stored has a reason on file.
  * Bounded. Input is consumed in chunks of CHUNK_SIZE, one transaction each,
    so memory use does not grow with the size of the input.

Ingestion runs inline, in the caller's request or command. There is no queue
and no background worker: nothing here needs one yet, and a retry is simply
running the same input again (docs/DECISIONS.md, ADR-006).

Reading
  Events are ordered by (occurred_at, event_id) — the time the source says
  the event happened, not the time it arrived — and paged with a cursor, so
  pages stay consistent while new events are being ingested.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from itertools import islice
from pathlib import Path
from typing import Any

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.adapters import ADAPTERS, Adapter
from app.events.contract import (
    MAX_FUTURE_SKEW_SECONDS,
    MAX_RECORD_BYTES,
    SCHEMA_VERSION,
    SOURCE_ID_PATTERN,
    ContractError,
    NormalizedEvent,
    canonical_json,
    event_id_for,
    sha256_hex,
)
from app.models import EventIngestBatch, EventIngestReject, SecurityEvent

logger = logging.getLogger("sentinel.events")

CHUNK_SIZE = 500             # records per transaction
MAX_ATTEMPTS = 3             # per chunk, when another writer got there first
MAX_STORED_REJECTS = 1000    # reject rows kept per batch; beyond this they are only counted
MAX_REPORTED_REJECTS = 100   # rejects returned in a report

CONFLICT = "conflicting_duplicate"
_CONFLICT_DETAIL = "an event with this source_event_id is already stored with different content; the stored event was kept"

LIST_FILTERS = ("source_type", "source_id", "actor_id", "target_id", "action", "outcome")


@dataclass(frozen=True)
class InvalidRecord:
    """Stands in for an input record that could not even be read (for example
    a line of a file that is not JSON), so it is still counted and reported."""

    reason: str
    detail: str


@dataclass
class BatchReport:
    batch_id: str
    source_type: str
    source_id: str
    received: int = 0
    inserted: int = 0
    duplicates: int = 0
    conflicts: int = 0
    rejected: int = 0
    # Every record that was not stored and is not a plain duplicate (first
    # MAX_REPORTED_REJECTS): {"index", "reason", "detail", "source_event_id"}.
    rejects: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _NotStored:
    index: int
    reason: str
    detail: str
    raw_sha256: str | None = None
    source_event_id: str | None = None


@dataclass(frozen=True)
class _Candidate:
    index: int
    event: NormalizedEvent
    raw_canonical: str
    raw_sha256: str


@dataclass
class _Prepared:
    """One chunk after validation and normalization, before the database is consulted."""

    size: int = 0
    candidates: dict[str, _Candidate] = field(default_factory=dict)   # event_id -> first occurrence
    not_stored: list[_NotStored] = field(default_factory=list)
    duplicates: int = 0                                               # repeats inside the chunk


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _prepare(adapter: Adapter, source_type: str, source_id: str, chunk: list[tuple[int, Any]]) -> _Prepared:
    out = _Prepared(size=len(chunk))
    horizon = _now() + timedelta(seconds=MAX_FUTURE_SKEW_SECONDS)

    def refuse(index: int, reason: str, detail: str, raw_sha256: str | None = None, source_event_id: str | None = None) -> None:
        out.not_stored.append(_NotStored(index, reason, detail, raw_sha256, source_event_id))

    for index, item in chunk:
        if isinstance(item, InvalidRecord):
            refuse(index, item.reason, item.detail)
            continue
        if not isinstance(item, dict):
            refuse(index, "not_an_object", "each record must be a JSON object")
            continue
        try:
            canonical = canonical_json(item)
        except ContractError as exc:
            refuse(index, exc.reason, exc.detail)
            continue
        size = len(canonical.encode("utf-8"))
        if size > MAX_RECORD_BYTES:
            refuse(index, "record_too_large", f"record is {size} bytes in canonical form; the limit is {MAX_RECORD_BYTES}")
            continue
        raw_sha256 = sha256_hex(canonical)

        try:
            event = adapter.normalize(item)
        except ContractError as exc:
            refuse(index, exc.reason, exc.detail, raw_sha256)
            continue
        except Exception:  # noqa: BLE001 - one malformed record must not abort the batch
            # An adapter met input its author did not anticipate. Refuse the
            # record, keep going, and leave a trace for whoever owns the adapter.
            logger.exception("adapter %s failed on record %d of a batch", adapter.normalizer, index)
            refuse(index, "normalizer_error", "the adapter could not read this record (see the server log)", raw_sha256)
            continue
        if event.occurred_at > horizon:
            refuse(index, "timestamp_in_future", "occurred_at is more than 24 hours in the future",
                   raw_sha256, event.source_event_id)
            continue

        event_id = event_id_for(source_type, source_id, event.source_event_id)
        first = out.candidates.get(event_id)
        if first is None:
            out.candidates[event_id] = _Candidate(index, event, canonical, raw_sha256)
        elif first.raw_sha256 == raw_sha256:
            out.duplicates += 1
        else:
            refuse(index, CONFLICT, _CONFLICT_DETAIL, raw_sha256, event.source_event_id)
    return out


async def _existing_hashes(db: AsyncSession, event_ids: list[str]) -> dict[str, str]:
    """event_id -> raw_sha256 for the ids already stored."""
    if not event_ids:
        return {}
    rows = await db.execute(
        select(SecurityEvent.event_id, SecurityEvent.raw_sha256).where(SecurityEvent.event_id.in_(event_ids))
    )
    return {event_id: raw_sha256 for event_id, raw_sha256 in rows.all()}


def _row(event_id: str, c: _Candidate, adapter: Adapter, source_type: str, source_id: str,
         batch_id: str, ingested_at: datetime) -> SecurityEvent:
    e = c.event
    return SecurityEvent(
        event_id=event_id,
        schema_version=SCHEMA_VERSION,
        source_type=source_type,
        source_id=source_id,
        source_event_id=e.source_event_id,
        ingest_batch_id=batch_id,
        normalizer=adapter.normalizer,
        occurred_at=e.occurred_at,
        ingested_at=ingested_at,
        actor_type=e.actor.type if e.actor else None,
        actor_id=e.actor.id if e.actor else None,
        target_type=e.target.type if e.target else None,
        target_id=e.target.id if e.target else None,
        action=e.action,
        source_action=e.source_action,
        outcome=e.outcome,
        src_ip=e.src_ip,
        attributes=e.attributes,
        raw_canonical=c.raw_canonical,
        raw_sha256=c.raw_sha256,
    )


async def _store_chunk(db: AsyncSession, batch_id: str, adapter: Adapter, source_type: str, source_id: str,
                       prepared: _Prepared, report: BatchReport) -> None:
    """Classify the chunk against what is already stored and commit it, all or
    nothing. If another writer inserts one of the same events between our
    look-up and our insert, the primary key refuses the whole transaction; we
    roll back and classify again, now seeing their rows as duplicates."""
    for _ in range(MAX_ATTEMPTS):
        existing = await _existing_hashes(db, list(prepared.candidates))
        ingested_at = _now()
        new_rows: list[SecurityEvent] = []
        not_stored = list(prepared.not_stored)
        duplicates = prepared.duplicates
        for event_id, candidate in prepared.candidates.items():
            known = existing.get(event_id)
            if known is None:
                new_rows.append(_row(event_id, candidate, adapter, source_type, source_id, batch_id, ingested_at))
            elif known == candidate.raw_sha256:
                duplicates += 1
            else:
                not_stored.append(_NotStored(candidate.index, CONFLICT, _CONFLICT_DETAIL,
                                             candidate.raw_sha256, candidate.event.source_event_id))
        not_stored.sort(key=lambda r: r.index)
        conflicts = sum(1 for r in not_stored if r.reason == CONFLICT)
        totals = {
            "received": report.received + prepared.size,
            "inserted": report.inserted + len(new_rows),
            "duplicates": report.duplicates + duplicates,
            "conflicts": report.conflicts + conflicts,
            "rejected": report.rejected + len(not_stored) - conflicts,
        }

        room = max(0, MAX_STORED_REJECTS - (report.conflicts + report.rejected))
        db.add_all(new_rows)
        db.add_all(
            EventIngestReject(batch_id=batch_id, record_index=r.index, reason=r.reason, detail=r.detail,
                              raw_sha256=r.raw_sha256, source_event_id=r.source_event_id)
            for r in not_stored[:room]
        )
        await db.execute(update(EventIngestBatch).where(EventIngestBatch.id == batch_id).values(**totals))
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            continue

        for name, value in totals.items():
            setattr(report, name, value)
        report.rejects.extend(
            {"index": r.index, "reason": r.reason, "detail": r.detail, "source_event_id": r.source_event_id}
            for r in not_stored[: max(0, MAX_REPORTED_REJECTS - len(report.rejects))]
        )
        return
    raise RuntimeError(f"could not store a chunk of events after {MAX_ATTEMPTS} attempts")


async def ingest(
    db: AsyncSession,
    *,
    source_type: str,
    source_id: str,
    records: Iterable[Any],
    origin: str,
    origin_detail: str | None = None,
    submitted_by: str | None = None,
) -> BatchReport:
    """Ingest records from one source. `records` may be any iterable — a list
    from an API request or a generator reading a file — and is consumed
    lazily. Items are parsed JSON values, or `InvalidRecord` for input that
    could not be parsed. Raises ValueError before writing anything if the
    source type or id is not acceptable."""
    adapter = ADAPTERS.get(source_type)
    if adapter is None:
        raise ValueError(f"unknown source_type; known types: {', '.join(sorted(ADAPTERS))}")
    if not re.fullmatch(SOURCE_ID_PATTERN, source_id):
        raise ValueError("source_id must be 1 to 120 characters: letters, digits, '.', '_', ':' or '-'")

    batch_id = str(uuid.uuid4())
    db.add(EventIngestBatch(id=batch_id, source_type=source_type, source_id=source_id, origin=origin,
                            origin_detail=origin_detail, submitted_by=submitted_by, status="running",
                            started_at=_now()))
    await db.commit()

    report = BatchReport(batch_id=batch_id, source_type=source_type, source_id=source_id)
    numbered = enumerate(records)
    try:
        while chunk := list(islice(numbered, CHUNK_SIZE)):
            prepared = _prepare(adapter, source_type, source_id, chunk)
            await _store_chunk(db, batch_id, adapter, source_type, source_id, prepared, report)
    except Exception:
        # Chunks already committed stay committed (they are valid events); the
        # batch is marked failed so the gap is visible. Re-running the same
        # input finishes the job. A batch left "running" was killed outright.
        await db.rollback()
        await db.execute(update(EventIngestBatch).where(EventIngestBatch.id == batch_id)
                         .values(status="failed", finished_at=_now()))
        await db.commit()
        raise

    await db.execute(update(EventIngestBatch).where(EventIngestBatch.id == batch_id)
                     .values(status="completed", finished_at=_now()))
    await db.commit()
    return report


def read_jsonl(path: Path) -> Iterator[Any]:
    """Yield one item per non-blank line of a JSON Lines file: the parsed
    value, or an `InvalidRecord` for a line that is not valid UTF-8 JSON or
    is longer than MAX_RECORD_BYTES. Never holds more than one bounded line
    in memory, and never stops at a bad line."""
    with path.open("rb") as handle:
        while line := handle.readline(MAX_RECORD_BYTES + 1):
            if len(line) > MAX_RECORD_BYTES and not line.endswith(b"\n"):
                while (rest := handle.readline(MAX_RECORD_BYTES)) and not rest.endswith(b"\n"):
                    pass                                   # skip the remainder without keeping it
                yield InvalidRecord("record_too_large", f"line is longer than {MAX_RECORD_BYTES} bytes")
                continue
            if not line.strip():
                continue
            try:
                yield json.loads(line.decode("utf-8-sig"))
            except (ValueError, RecursionError):           # includes invalid UTF-8
                yield InvalidRecord("invalid_json", "line is not valid UTF-8 JSON")


# --- reading ------------------------------------------------------------------

def _encode_cursor(row: SecurityEvent) -> str:
    return base64.urlsafe_b64encode(f"{row.occurred_at.isoformat()}|{row.event_id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        stamp, event_id = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8").split("|")
        at = datetime.fromisoformat(stamp)
        if at.tzinfo is None or not re.fullmatch(r"[0-9a-f]{64}", event_id):
            raise ValueError
    except ValueError:                                     # also bad base64 and bad UTF-8
        raise ValueError("invalid cursor") from None
    return at, event_id


async def list_events(
    db: AsyncSession,
    *,
    filters: dict[str, str | None] | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    order: str = "desc",
    limit: int = 50,
    cursor: str | None = None,
) -> tuple[list[SecurityEvent], str | None]:
    """One page of events in event-time order, and the cursor for the next
    page (None when this is the last). Raises ValueError for a bad cursor."""
    at, event_id = SecurityEvent.occurred_at, SecurityEvent.event_id
    stmt = select(SecurityEvent)
    for name, value in (filters or {}).items():
        if name not in LIST_FILTERS:
            raise KeyError(name)
        if value is not None:
            stmt = stmt.where(getattr(SecurityEvent, name) == value)
    if occurred_from is not None:
        stmt = stmt.where(at >= occurred_from)
    if occurred_to is not None:
        stmt = stmt.where(at <= occurred_to)
    if cursor:
        last_at, last_id = _decode_cursor(cursor)
        stmt = stmt.where(
            or_(at > last_at, and_(at == last_at, event_id > last_id)) if order == "asc"
            else or_(at < last_at, and_(at == last_at, event_id < last_id))
        )
    stmt = stmt.order_by(at.asc(), event_id.asc()) if order == "asc" else stmt.order_by(at.desc(), event_id.desc())

    rows = list((await db.execute(stmt.limit(limit + 1))).scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    return rows, _encode_cursor(rows[-1]) if has_more else None
