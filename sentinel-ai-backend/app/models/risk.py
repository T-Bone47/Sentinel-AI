"""Risk domain — dataset8 (Risk Register), dataset10 (Evidence Repository), dataset11 (Compliance Findings)."""
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.mixins import IngestionProvenanceMixin, SoftDeleteMixin, TimestampMixin


class Risk(Base, TimestampMixin, SoftDeleteMixin, IngestionProvenanceMixin):
    __tablename__ = "risks"

    risk_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    risk_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    business_impact: Mapped[str] = mapped_column(String(200), nullable=False)
    likelihood: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    owner_department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    mapped_control_id: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("controls.control_id", ondelete="SET NULL"), nullable=True, index=True
    )
    current_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)


class Evidence(Base, TimestampMixin, SoftDeleteMixin, IngestionProvenanceMixin):
    __tablename__ = "evidence"

    evidence_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    control_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("controls.control_id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    evidence_location: Mapped[str] = mapped_column(String(500), nullable=False)
    collected_date: Mapped[date] = mapped_column(Date, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    collected_automatically: Mapped[bool] = mapped_column(Boolean, nullable=False)


class Finding(Base, TimestampMixin, SoftDeleteMixin, IngestionProvenanceMixin):
    __tablename__ = "findings"

    finding_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    control_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("controls.control_id", ondelete="CASCADE"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_id: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("evidence.evidence_id", ondelete="SET NULL"), nullable=True, index=True
    )
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
