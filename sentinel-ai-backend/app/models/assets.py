"""Asset domain — dataset3 (Cloud Assets), dataset4 (Applications), dataset5 (Vendors).

Vendor has no verified FK to any other dataset (empirically confirmed
during relationship discovery — Risk Register mentions vendors only in
free text, e.g. "Third-Party Vendor Data Mishandling", not via an ID
column). It is intentionally an island table in Phase 1.
"""
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.mixins import IngestionProvenanceMixin, SoftDeleteMixin, TimestampMixin


class CloudAsset(Base, TimestampMixin, SoftDeleteMixin, IngestionProvenanceMixin):
    __tablename__ = "cloud_assets"

    resource_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    cloud_provider: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    owner_employee_id: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("employees.employee_id", ondelete="SET NULL"), nullable=True, index=True
    )
    public_access: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    encryption_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    logging_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    criticality: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)


class Application(Base, TimestampMixin, SoftDeleteMixin, IngestionProvenanceMixin):
    __tablename__ = "applications"

    application_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    application_name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    owner_department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    authentication_method: Mapped[str] = mapped_column(String(50), nullable=False)
    uses_mfa: Mapped[bool] = mapped_column(Boolean, nullable=False)
    encryption_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    data_classification: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    internet_facing: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)


class Vendor(Base, TimestampMixin, SoftDeleteMixin, IngestionProvenanceMixin):
    __tablename__ = "vendors"

    vendor_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    vendor_name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    service_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    iso27001_certified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    soc2_certified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    dpdp_compliant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    risk_rating: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    contract_expiry: Mapped[date] = mapped_column(Date, nullable=False)
