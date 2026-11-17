"""
The security-event store.

Three tables, three different kinds of thing — kept apart on purpose:

  security_events        what a source system said happened. Written once,
                         never modified (a database trigger refuses UPDATE).
  event_ingest_batches   one row per ingestion run: who, when, what counts.
  event_ingest_rejects   one row per record that was NOT stored, with a
                         reason — never the record's content.

Nothing derived (alerts, scores, labels) lives here. Those are computed from
events and stored elsewhere, so the raw record of what happened can never be
confused with an interpretation of it. The full contract is in
docs/EVENT_CONTRACT.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.database.session import Base
from app.models.mixins import UUIDPKMixin


class UTCDateTime(TypeDecorator):
    """A timestamp that is always timezone-aware UTC in Python.

    SQLite has no timezone-aware type and hands back naive values, PostgreSQL
    hands back values in the session's zone. Normalising at this boundary
    means every comparison and every ordering in the event store is done on
    one unambiguous timeline, on both databases. Naive values are refused on
    the way in rather than guessed at.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime: event-store timestamps must carry a timezone")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class EventIngestBatch(Base, UUIDPKMixin):
    __tablename__ = "event_ingest_batches"

    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    origin: Mapped[str] = mapped_column(String(20), nullable=False)          # "api" | "file" | "test"
    origin_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)   # file name, for "file"
    # Email of the user who called the API; NULL for local command-line runs.
    submitted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)          # running | completed | failed
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    # received == inserted + duplicates + conflicts + rejected, always.
    received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conflicts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class EventIngestReject(Base, UUIDPKMixin):
    __tablename__ = "event_ingest_rejects"

    batch_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("event_ingest_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    record_index: Mapped[int] = mapped_column(Integer, nullable=False)       # 0-based position in the input
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    detail: Mapped[str] = mapped_column(String(300), nullable=False)         # field names and rules, never values
    # SHA-256 of the refused record's canonical form: identifies it without keeping it.
    raw_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_event_id: Mapped[str | None] = mapped_column(String(200), nullable=True)


class SecurityEvent(Base):
    __tablename__ = "security_events"
    __table_args__ = (
        Index("ix_security_events_occurred_at_event_id", "occurred_at", "event_id"),
        Index("ix_security_events_source", "source_type", "source_id"),
    )

    # SHA-256 of (source_type, source_id, source_event_id): the same source
    # record always gets the same id, which is what makes re-ingestion a no-op.
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- where it came from -------------------------------------------
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    source_event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    ingest_batch_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("event_ingest_batches.id"), nullable=False, index=True
    )
    normalizer: Mapped[str] = mapped_column(String(60), nullable=False)      # adapter@version that read it

    # --- when ---------------------------------------------------------
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)   # per the source
    ingested_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)   # per this system

    # --- what, normalized ---------------------------------------------
    actor_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    target_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    source_action: Mapped[str] = mapped_column(String(200), nullable=False)
    outcome: Mapped[str] = mapped_column(String(10), nullable=False)
    src_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # --- the source record itself -------------------------------------
    # Canonical JSON text of the record as received, and the SHA-256 of
    # exactly that text. Recomputing the hash shows whether the stored text
    # changed; it is not protection against someone who can write to the
    # database, since they could change both.
    raw_canonical: Mapped[str] = mapped_column(Text, nullable=False)
    raw_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
