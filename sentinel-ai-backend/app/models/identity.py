"""
Identity domain — dataset1 (Employees), dataset2 (Devices),
dataset15 (Identity & Access Management).

All three use their real source ID as primary key (see mixins.py for why).
"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.mixins import IngestionProvenanceMixin, SoftDeleteMixin, TimestampMixin


class Employee(Base, TimestampMixin, SoftDeleteMixin, IngestionProvenanceMixin):
    __tablename__ = "employees"

    employee_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    designation: Mapped[str] = mapped_column(String(150), nullable=False)

    # Self-referential org hierarchy. Nullable — exactly 1 employee (the
    # apex of the org chart) has no manager, verified during profiling.
    manager_id: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("employees.employee_id", ondelete="SET NULL"), nullable=True, index=True
    )

    office_location: Mapped[str] = mapped_column(String(100), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(30), nullable=False)
    joining_date: Mapped[date] = mapped_column(Date, nullable=False)
    password_length: Mapped[int] = mapped_column(Integer, nullable=False)
    password_last_changed: Mapped[date] = mapped_column(Date, nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    account_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # Redundant with devices.employee_id (see Phase 1 report item D3) — kept
    # for fidelity to the source file, NOT enforced as a hard FK constraint
    # to avoid a circular dependency with the devices table on first load;
    # the ingestion validator cross-checks it opportunistically instead.
    device_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Device(Base, TimestampMixin, SoftDeleteMixin, IngestionProvenanceMixin):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    employee_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    operating_system: Mapped[str] = mapped_column(String(30), nullable=False)
    os_version: Mapped[str] = mapped_column(String(50), nullable=False)
    encryption_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    firewall_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    antivirus_installed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    edr_installed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    compliance_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    last_patch_date: Mapped[date] = mapped_column(Date, nullable=False)


class IAMRecord(Base, TimestampMixin, SoftDeleteMixin, IngestionProvenanceMixin):
    """dataset15 — an application/system-identity record per employee,
    distinct from the platform login in models/auth.py::User."""
    __tablename__ = "iam_records"

    iam_user_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    employee_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    privileges: Mapped[str] = mapped_column(Text, nullable=False)
    privileged_account: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    inactive_days: Mapped[int] = mapped_column(Integer, nullable=False)
    last_privilege_review: Mapped[date] = mapped_column(Date, nullable=False)
