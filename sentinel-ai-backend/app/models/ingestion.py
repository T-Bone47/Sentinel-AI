"""
Ingestion lineage tables. Platform-internal (not from a source dataset),
UUID PK. Every ingested row across the 15 dataset tables carries an
ingestion_job_id pointing back here — this is Phase 1's data lineage
and repeatability trail (approved architecture Section 13).
"""
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.session import Base
from app.models.enums import DatasetType, IngestionLogLevel, IngestionStatus
from app.models.mixins import UUIDPKMixin


class IngestionJob(Base, UUIDPKMixin):
    __tablename__ = "ingestion_jobs"

    dataset_type: Mapped[DatasetType] = mapped_column(
        Enum(DatasetType, name="dataset_type", native_enum=False, length=40), nullable=False, index=True
    )
    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[IngestionStatus] = mapped_column(
        Enum(IngestionStatus, name="ingestion_status", native_enum=False, length=20),
        nullable=False,
        default=IngestionStatus.RUNNING,
    )
    rows_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_errored: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class IngestionLog(Base, UUIDPKMixin):
    __tablename__ = "ingestion_logs"

    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ingestion_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    level: Mapped[IngestionLogLevel] = mapped_column(
        Enum(IngestionLogLevel, name="ingestion_log_level", native_enum=False, length=10), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_row: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
