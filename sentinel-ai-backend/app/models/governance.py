"""Governance domain — dataset6 (Security Policies), dataset7 (Compliance Controls)."""
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.mixins import IngestionProvenanceMixin, SoftDeleteMixin, TimestampMixin


class Policy(Base, TimestampMixin, SoftDeleteMixin, IngestionProvenanceMixin):
    __tablename__ = "policies"

    policy_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    policy_name: Mapped[str] = mapped_column(String(200), nullable=False)
    framework: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(10), nullable=False)
    owner_department: Mapped[str] = mapped_column(String(100), nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)


class Control(Base, TimestampMixin, SoftDeleteMixin, IngestionProvenanceMixin):
    __tablename__ = "controls"

    control_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    policy_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("policies.policy_id", ondelete="CASCADE"), nullable=False, index=True
    )
    control_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    automation_possible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evidence_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
