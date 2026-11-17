"""add detection runs, alerts and the events each alert cites

Revision ID: d4f7b0c3e5a6
Revises: c3e6a9b2d4f5
Create Date: 2026-11-17

Additive only: three new tables. detection_alerts and detection_alert_events
are immutable — a BEFORE UPDATE trigger refuses changes on PostgreSQL and
SQLite, as for security_events. detection_runs is not: a run's status and
counts are filled in as it runs.

detection_alert_events.event_id references security_events with no cascade, so
on PostgreSQL an event an alert cites cannot be deleted from under it. A future
retention purge must deal with alerts first (docs/EVENT_CONTRACT.md §10).

Rollback (`alembic downgrade c3e6a9b2d4f5`) drops the three tables and every
alert in them. Events are untouched, and re-running the rules recreates the
same alerts with the same ids.
"""
from alembic import op
import sqlalchemy as sa


revision = "d4f7b0c3e5a6"
down_revision = "c3e6a9b2d4f5"
branch_labels = None
depends_on = None

IMMUTABLE_TABLES = ("detection_alerts", "detection_alert_events")
MESSAGE = "detection alerts are immutable"


def upgrade() -> None:
    op.create_table(
        "detection_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("origin", sa.String(length=20), nullable=False),
        sa.Column("triggered_by", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rule_versions", sa.JSON(), nullable=False),
        sa.Column("events_considered", sa.Integer(), nullable=False),
        sa.Column("alerts_created", sa.Integer(), nullable=False),
        sa.Column("alerts_existing", sa.Integer(), nullable=False),
        sa.Column("alerts_no_longer_raised", sa.Integer(), nullable=False),
        sa.Column("not_evaluable", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_detection_runs_source_id"), "detection_runs", ["source_id"], unique=False)

    op.create_table(
        "detection_alerts",
        sa.Column("alert_id", sa.String(length=64), nullable=False),
        sa.Column("rule_id", sa.String(length=20), nullable=False),
        sa.Column("rule_version", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("confidence", sa.String(length=10), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("actor_id", sa.String(length=512), nullable=True),
        sa.Column("trigger_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["detection_runs.id"]),
        sa.PrimaryKeyConstraint("alert_id"),
    )
    op.create_index(op.f("ix_detection_alerts_rule_id"), "detection_alerts", ["rule_id"], unique=False)
    op.create_index(op.f("ix_detection_alerts_run_id"), "detection_alerts", ["run_id"], unique=False)
    op.create_index("ix_detection_alerts_source", "detection_alerts", ["source_type", "source_id"], unique=False)
    op.create_index("ix_detection_alerts_trigger_at_alert_id", "detection_alerts", ["trigger_at", "alert_id"], unique=False)

    op.create_table(
        "detection_alert_events",
        sa.Column("alert_id", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["detection_alerts.alert_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["security_events.event_id"]),
        sa.PrimaryKeyConstraint("alert_id", "event_id"),
    )
    op.create_index(op.f("ix_detection_alert_events_event_id"), "detection_alert_events", ["event_id"], unique=False)

    postgres = op.get_bind().dialect.name == "postgresql"
    if postgres:
        op.execute(
            f"""
            CREATE FUNCTION detection_alerts_refuse_update() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION '{MESSAGE}';
            END;
            $$ LANGUAGE plpgsql
            """
        )
    for table in IMMUTABLE_TABLES:
        if postgres:
            op.execute(
                f"CREATE TRIGGER {table}_immutable BEFORE UPDATE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION detection_alerts_refuse_update()"
            )
        else:  # SQLite
            op.execute(
                f"CREATE TRIGGER {table}_immutable BEFORE UPDATE ON {table} "
                f"BEGIN SELECT RAISE(ABORT, '{MESSAGE}'); END"
            )


def downgrade() -> None:
    postgres = op.get_bind().dialect.name == "postgresql"
    for table in IMMUTABLE_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable" + (f" ON {table}" if postgres else ""))
    if postgres:
        op.execute("DROP FUNCTION IF EXISTS detection_alerts_refuse_update()")
    op.drop_index(op.f("ix_detection_alert_events_event_id"), table_name="detection_alert_events")
    op.drop_table("detection_alert_events")
    op.drop_index("ix_detection_alerts_trigger_at_alert_id", table_name="detection_alerts")
    op.drop_index("ix_detection_alerts_source", table_name="detection_alerts")
    op.drop_index(op.f("ix_detection_alerts_run_id"), table_name="detection_alerts")
    op.drop_index(op.f("ix_detection_alerts_rule_id"), table_name="detection_alerts")
    op.drop_table("detection_alerts")
    op.drop_index(op.f("ix_detection_runs_source_id"), table_name="detection_runs")
    op.drop_table("detection_runs")
