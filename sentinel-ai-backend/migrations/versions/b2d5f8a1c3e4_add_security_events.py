"""add the security-event store (events, ingest batches, ingest rejects)

Revision ID: b2d5f8a1c3e4
Revises: a1c4e7d90b12
Create Date: 2026-11-17

Additive only: three new tables, no change to existing tables or data.

`security_events` rows are immutable. A BEFORE UPDATE trigger enforces that
in the database itself, on PostgreSQL and on SQLite, so no code path — and no
ad-hoc SQL session — can rewrite a stored event by accident. DELETE is not
blocked: removing whole events is how a retention policy will be applied.

Rollback (`alembic downgrade a1c4e7d90b12`) drops the three tables and
everything in them. Ingested events are lost; re-ingest from the source files.
"""
from alembic import op
import sqlalchemy as sa


revision = "b2d5f8a1c3e4"
down_revision = "a1c4e7d90b12"
branch_labels = None
depends_on = None

IMMUTABLE_MESSAGE = "security_events rows are immutable"


def upgrade() -> None:
    op.create_table(
        "event_ingest_batches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("origin", sa.String(length=20), nullable=False),
        sa.Column("origin_detail", sa.String(length=255), nullable=True),
        sa.Column("submitted_by", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received", sa.Integer(), nullable=False),
        sa.Column("inserted", sa.Integer(), nullable=False),
        sa.Column("duplicates", sa.Integer(), nullable=False),
        sa.Column("conflicts", sa.Integer(), nullable=False),
        sa.Column("rejected", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_event_ingest_batches_source_id"), "event_ingest_batches", ["source_id"], unique=False)

    op.create_table(
        "event_ingest_rejects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column("record_index", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("detail", sa.String(length=300), nullable=False),
        sa.Column("raw_sha256", sa.String(length=64), nullable=True),
        sa.Column("source_event_id", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["event_ingest_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_event_ingest_rejects_batch_id"), "event_ingest_rejects", ["batch_id"], unique=False)

    op.create_table(
        "security_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("source_event_id", sa.String(length=200), nullable=False),
        sa.Column("ingest_batch_id", sa.String(length=36), nullable=False),
        sa.Column("normalizer", sa.String(length=60), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_type", sa.String(length=20), nullable=True),
        sa.Column("actor_id", sa.String(length=512), nullable=True),
        sa.Column("target_type", sa.String(length=20), nullable=True),
        sa.Column("target_id", sa.String(length=512), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("source_action", sa.String(length=200), nullable=False),
        sa.Column("outcome", sa.String(length=10), nullable=False),
        sa.Column("src_ip", sa.String(length=45), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("raw_canonical", sa.Text(), nullable=False),
        sa.Column("raw_sha256", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["ingest_batch_id"], ["event_ingest_batches.id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(op.f("ix_security_events_actor_id"), "security_events", ["actor_id"], unique=False)
    op.create_index(op.f("ix_security_events_ingest_batch_id"), "security_events", ["ingest_batch_id"], unique=False)
    op.create_index("ix_security_events_occurred_at_event_id", "security_events", ["occurred_at", "event_id"], unique=False)
    op.create_index("ix_security_events_source", "security_events", ["source_type", "source_id"], unique=False)

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            f"""
            CREATE FUNCTION security_events_refuse_update() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION '{IMMUTABLE_MESSAGE}';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER security_events_immutable
            BEFORE UPDATE ON security_events
            FOR EACH ROW EXECUTE FUNCTION security_events_refuse_update()
            """
        )
    else:  # SQLite
        op.execute(
            f"""
            CREATE TRIGGER security_events_immutable
            BEFORE UPDATE ON security_events
            BEGIN
                SELECT RAISE(ABORT, '{IMMUTABLE_MESSAGE}');
            END
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS security_events_immutable ON security_events")
        op.execute("DROP FUNCTION IF EXISTS security_events_refuse_update()")
    else:
        op.execute("DROP TRIGGER IF EXISTS security_events_immutable")
    op.drop_index("ix_security_events_source", table_name="security_events")
    op.drop_index("ix_security_events_occurred_at_event_id", table_name="security_events")
    op.drop_index(op.f("ix_security_events_ingest_batch_id"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_actor_id"), table_name="security_events")
    op.drop_table("security_events")
    op.drop_index(op.f("ix_event_ingest_rejects_batch_id"), table_name="event_ingest_rejects")
    op.drop_table("event_ingest_rejects")
    op.drop_index(op.f("ix_event_ingest_batches_source_id"), table_name="event_ingest_batches")
    op.drop_table("event_ingest_batches")
