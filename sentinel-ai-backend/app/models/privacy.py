"""Privacy domain — dataset13 (DPDP Personal Data Inventory), dataset14 (Consent Records).

Note (Phase 1 report item D5): DataID and ConsentID are NOT linked to each
other by any FK in the source data — both connect only via a shared
ApplicationID. Do not join them directly; join through applications.
"""
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.mixins import IngestionProvenanceMixin, SoftDeleteMixin, TimestampMixin


class PersonalDataInventory(Base, TimestampMixin, SoftDeleteMixin, IngestionProvenanceMixin):
    __tablename__ = "personal_data_inventory"

    data_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    application_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False, index=True
    )
    data_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    purpose_of_processing: Mapped[str] = mapped_column(String(100), nullable=False)
    retention_period: Mapped[str] = mapped_column(String(50), nullable=False)
    third_party_sharing: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    encryption_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    consent_required: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)


class ConsentRecord(Base, TimestampMixin, SoftDeleteMixin, IngestionProvenanceMixin):
    __tablename__ = "consent_records"

    consent_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    employee_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False, index=True
    )
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    consent_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
