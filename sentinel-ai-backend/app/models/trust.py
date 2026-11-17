"""
Trust domain — new in Phase 2 (Priority 1, Trust Intelligence).

TrustScoreSnapshot is the ONLY new table this session adds. It exists for
one honest reason: `score_change` in the Trust Intelligence output must be
a real delta, not an invented one, and Phase 1 never persisted a score —
`/dashboard` recomputes it live on every call and throws it away. This
table stores each computed score so the next call has something real to
diff against. First-ever call has no prior snapshot; the service reports
that explicitly rather than inventing a baseline.
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func, text

from app.database.session import Base
from app.models.mixins import UUIDPKMixin


class TrustScoreSnapshot(Base, UUIDPKMixin):
    __tablename__ = "trust_score_snapshots"

    trust_score: Mapped[float] = mapped_column(Float, nullable=False)
    audit_readiness: Mapped[float] = mapped_column(Float, nullable=False)
    components: Mapped[dict] = mapped_column(JSON, nullable=False)
    engine: Mapped[str] = mapped_column(String(40), nullable=False, default="deterministic_phase1")
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False, index=True
    )
    # Why this row exists: "manual", "scheduled" or "dataset_ingestion".
    # "legacy_on_read" (the database default) marks rows that existed before
    # migration c3e6a9b2d4f5, when every read of the score stored one as a
    # side effect.
    trigger: Mapped[str] = mapped_column(String(30), nullable=False, default="manual", server_default="legacy_on_read")
    # Email of the user who recorded it, "cli" for command-line runs, NULL for legacy rows.
    recorded_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
