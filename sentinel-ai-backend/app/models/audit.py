"""Audit domain — dataset9 (Audit Logs, 10,000 rows), dataset12 (Compliance Reports).

AuditLog deliberately does NOT use TimestampMixin/SoftDeleteMixin: it is
append-only and immutable by design (matches the approved architecture's
"append-only tables have no updated_at/deleted_at" convention) — only
created_at, set once.

Report has no verified FK to Findings/Controls in the source data; it is
a framework-level rollup snapshot (Framework is a shared vocabulary with
Policy.framework, not a joinable ID).
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func, text

from app.database.session import Base
from app.models.mixins import IngestionProvenanceMixin, SoftDeleteMixin, TimestampMixin


class AuditLog(Base, IngestionProvenanceMixin):
    __tablename__ = "audit_logs"

    log_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    employee_id: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("employees.employee_id", ondelete="SET NULL"), nullable=True, index=True
    )
    application_id: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("applications.application_id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    geo_location: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'), nullable=False
    )


class Report(Base, TimestampMixin, SoftDeleteMixin, IngestionProvenanceMixin):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    framework: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    generated_date: Mapped[date] = mapped_column(Date, nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    critical_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    medium_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    compliance_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
