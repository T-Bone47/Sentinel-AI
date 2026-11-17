"""
Detection runs and the alerts they raise.

  detection_runs          one row per run of the rules over one source. It is
                          updated as the run progresses (status, counts).
  detection_alerts        what a rule found. Written once and never modified:
                          a database trigger refuses UPDATE.
  detection_alert_events  the events an alert cites — exactly one trigger and
                          any number of context events. Also immutable.

An alert records a rule's finding, not anyone's judgement of it. Triage
(status, assignee, suppression, notes) changes over time and will be kept in
separate tables in Gate 4 (docs/DECISIONS.md, ADR-011 and ADR-012).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.events import UTCDateTime
from app.models.mixins import UUIDPKMixin


class DetectionRun(Base, UUIDPKMixin):
    __tablename__ = "detection_runs"

    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    origin: Mapped[str] = mapped_column(String(20), nullable=False)            # api | cli | benchmark | test
    triggered_by: Mapped[str | None] = mapped_column(String(255), nullable=True)   # user email for API runs
    status: Mapped[str] = mapped_column(String(20), nullable=False)            # running | completed | failed
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    rule_versions: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    events_considered: Mapped[int] = mapped_column(Integer, nullable=False)
    alerts_created: Mapped[int] = mapped_column(Integer, nullable=False)
    alerts_existing: Mapped[int] = mapped_column(Integer, nullable=False)
    # Alerts stored by earlier runs that these rule versions would not raise
    # today, for example because an approval arrived late. They are kept.
    alerts_no_longer_raised: Mapped[int] = mapped_column(Integer, nullable=False)
    not_evaluable: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)


class DetectionAlert(Base):
    __tablename__ = "detection_alerts"
    __table_args__ = (
        Index("ix_detection_alerts_trigger_at_alert_id", "trigger_at", "alert_id"),
        Index("ix_detection_alerts_source", "source_type", "source_id"),
    )

    # SHA-256 of (rule id, rule version, trigger event id): the same finding
    # always has the same id, which is what makes re-running harmless.
    alert_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    rule_version: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(512), nullable=True)   # actor of the trigger event
    trigger_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)  # when the trigger event occurred
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("detection_runs.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)


class DetectionAlertEvent(Base):
    __tablename__ = "detection_alert_events"

    alert_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("detection_alerts.alert_id", ondelete="CASCADE"), primary_key=True
    )
    # No cascade: on PostgreSQL an event an alert cites cannot be deleted from
    # under it. A retention purge must handle alerts first.
    event_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("security_events.event_id"), primary_key=True, index=True
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)        # trigger | context
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)        # 0 = trigger, then context oldest first
