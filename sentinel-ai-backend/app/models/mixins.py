"""
Shared mixins applied to every ingested-dataset model.

Adjustment vs. the originally approved architecture (documented in the
Phase 1 report, item D1): the approved architecture specified UUID
primary keys + created_by/updated_by audit columns on every table. Once
the datasets arrived, every one of them ships its own globally
unique, stable, human-readable natural key (EMP0001, CTRL-53203, ...)
and is populated by bulk ingestion jobs rather than individual user
actions. Introducing a surrogate UUID and a user-attribution column
would add a translation layer with no Phase 1 benefit — so ingested
tables use the natural source ID as the primary key, and
`ingestion_job_id` (not `created_by`) as their provenance column, which
is the more meaningful attribution for a bulk-loaded row. Platform-
internal tables we invented ourselves (users, ingestion_jobs) still use
UUIDs, per the original architecture, since they have no natural key.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    """
    deleted_at is set (not the row hard-deleted) when a source row present
    in a prior ingestion job is absent from a later one — preserves history
    instead of silently losing records on a re-import.
    """
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IngestionProvenanceMixin:
    """Which ingestion job (re-)wrote this row — the bulk-load equivalent of created_by."""
    ingestion_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ingestion_jobs.id", ondelete="SET NULL"), nullable=True
    )


class UUIDPKMixin:
    """For platform-internal tables with no natural business key. Stored as
    CHAR(36) text rather than the Postgres-native UUID type so the same
    model works unmodified against the SQLite in-memory DB used in tests."""
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
