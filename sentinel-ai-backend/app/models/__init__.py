"""
Import every model module here so Base.metadata is complete when Alembic
(or anything else) introspects it. This is the single place that must be
kept up to date whenever a new model module is added.
"""
from app.models.assets import Application, CloudAsset, Vendor  # noqa: F401
from app.models.audit import AuditLog, Report  # noqa: F401
from app.models.auth import AuthSession, User  # noqa: F401
from app.models.events import EventIngestBatch, EventIngestReject, SecurityEvent  # noqa: F401
from app.models.detections import DetectionAlert, DetectionAlertEvent, DetectionRun  # noqa: F401
from app.models.governance import Control, Policy  # noqa: F401
from app.models.identity import Device, Employee, IAMRecord  # noqa: F401
from app.models.ingestion import IngestionJob, IngestionLog  # noqa: F401
from app.models.privacy import ConsentRecord, PersonalDataInventory  # noqa: F401
from app.models.risk import Evidence, Finding, Risk  # noqa: F401
from app.models.trust import TrustScoreSnapshot  # noqa: F401

__all__ = [
    "Application",
    "AuditLog",
    "AuthSession",
    "CloudAsset",
    "ConsentRecord",
    "Control",
    "DetectionAlert",
    "DetectionAlertEvent",
    "DetectionRun",
    "Device",
    "Employee",
    "EventIngestBatch",
    "EventIngestReject",
    "Evidence",
    "Finding",
    "IAMRecord",
    "IngestionJob",
    "IngestionLog",
    "PersonalDataInventory",
    "Policy",
    "Report",
    "Risk",
    "SecurityEvent",
    "TrustScoreSnapshot",
    "User",
    "Vendor",
]
