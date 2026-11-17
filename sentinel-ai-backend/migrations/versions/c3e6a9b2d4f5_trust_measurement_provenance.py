"""record why and by whom each trust score snapshot was taken

Revision ID: c3e6a9b2d4f5
Revises: b2d5f8a1c3e4
Create Date: 2026-11-17

Until now every GET of the trust score wrote a snapshot, so the history
recorded page views rather than changes. Snapshots are now written only by an
explicit measurement. Rows that already exist were produced by the old
behaviour; they are kept and labelled `legacy_on_read` so they can be told
apart from real measurements.

Additive: two columns on trust_score_snapshots, no data removed.
Rollback (`alembic downgrade b2d5f8a1c3e4`) drops the two columns.
"""
from alembic import op
import sqlalchemy as sa


revision = "c3e6a9b2d4f5"
down_revision = "b2d5f8a1c3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "trust_score_snapshots",
        sa.Column("trigger", sa.String(length=30), nullable=False, server_default="legacy_on_read"),
    )
    op.add_column("trust_score_snapshots", sa.Column("recorded_by", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("trust_score_snapshots", "recorded_by")
    op.drop_column("trust_score_snapshots", "trigger")
