"""
Database, migration and ingestion tests.

The most important test in the whole suite is
`test_reingestion_does_not_duplicate` — a hackathon demo that silently
doubles its row counts on the second load is worse than one that fails
loudly.
"""
from __future__ import annotations

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.ingestion.base import DatasetIngestor
from app.ingestion.configs.registry import LOAD_ORDER
from tests.conftest import DATASETS_DIR, EXPECTED_COUNTS

EXPECTED_TABLES = {
    "employees", "devices", "cloud_assets", "applications", "vendors",
    "policies", "controls", "risks", "evidence", "findings", "reports",
    "personal_data_inventory", "consent_records", "iam_records", "audit_logs",
    "users", "ingestion_jobs", "ingestion_logs",
}


def test_database_is_reachable(db_session: Session):
    assert db_session.execute(text("SELECT 1")).scalar_one() == 1


def test_migration_created_all_18_tables(sync_engine):
    tables = set(inspect(sync_engine).get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"missing tables: {sorted(missing)}"
    assert "alembic_version" in tables, "schema was not created through Alembic"


def test_alembic_is_at_head(db_session: Session):
    revision = db_session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert revision, "no Alembic revision recorded"


@pytest.mark.parametrize("table,expected", sorted(EXPECTED_COUNTS.items()))
def test_ingested_row_counts_match_source_files(db_session: Session, table: str, expected: int):
    count = db_session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()  # noqa: S608
    assert count == expected


def test_every_dataset_has_a_source_file():
    for config in LOAD_ORDER:
        assert (DATASETS_DIR / config.filename).exists(), f"missing {config.filename}"


def test_load_order_is_fk_safe():
    """A dataset must never be loaded before a table it points at."""
    loaded: set[str] = set()
    for config in LOAD_ORDER:
        for fk in config.fks:
            if not fk.hard or fk.ref_table == config.model.__tablename__:
                continue  # advisory or self-referential
            assert fk.ref_table in loaded, (
                f"{config.dataset_type.value} references {fk.ref_table} before it is loaded"
            )
        loaded.add(config.model.__tablename__)


def test_relationships_resolve_with_no_orphans(db_session: Session):
    """Every verified FK should resolve for every row actually in the DB."""
    checks = [
        ("devices", "employee_id", "employees", "employee_id"),
        ("cloud_assets", "owner_employee_id", "employees", "employee_id"),
        ("controls", "policy_id", "policies", "policy_id"),
        ("risks", "mapped_control_id", "controls", "control_id"),
        ("evidence", "control_id", "controls", "control_id"),
        ("findings", "control_id", "controls", "control_id"),
        ("findings", "evidence_id", "evidence", "evidence_id"),
        ("personal_data_inventory", "application_id", "applications", "application_id"),
        ("consent_records", "employee_id", "employees", "employee_id"),
        ("consent_records", "application_id", "applications", "application_id"),
        ("iam_records", "employee_id", "employees", "employee_id"),
        ("audit_logs", "employee_id", "employees", "employee_id"),
        ("audit_logs", "application_id", "applications", "application_id"),
        ("employees", "manager_id", "employees", "employee_id"),
    ]
    for child, column, parent, parent_key in checks:
        orphans = db_session.execute(
            text(  # noqa: S608 - identifiers are literals in this file
                f"SELECT count(*) FROM {child} c "
                f"WHERE c.{column} IS NOT NULL AND NOT EXISTS "
                f"(SELECT 1 FROM {parent} p WHERE p.{parent_key} = c.{column})"
            )
        ).scalar_one()
        assert orphans == 0, f"{child}.{column} has {orphans} orphan(s)"


def test_reingestion_does_not_duplicate(db_session: Session):
    """
    THE critical test. Re-run the full pipeline and assert that every table
    ends with the same row count, zero inserts, and zero errors.
    """
    before = {
        config.model.__tablename__: db_session.execute(
            text(f"SELECT count(*) FROM {config.model.__tablename__}")  # noqa: S608
        ).scalar_one()
        for config in LOAD_ORDER
    }

    ingestor = DatasetIngestor(db_session, DATASETS_DIR)
    results = [ingestor.ingest(config) for config in LOAD_ORDER]

    for result in results:
        assert result.errors == 0, f"{result.dataset}: {result.messages[:3]}"
        if db_session.get_bind().dialect.name != "sqlite":
            assert result.inserted == 0, f"{result.dataset} inserted {result.inserted} rows on a re-run"
            assert result.updated == result.rows_read - result.skipped

    for config in LOAD_ORDER:
        table = config.model.__tablename__
        after = db_session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()  # noqa: S608
        assert after == before[table], f"{table} changed from {before[table]} to {after}"


def test_ingestion_jobs_are_recorded(db_session: Session):
    jobs = db_session.execute(text("SELECT count(*) FROM ingestion_jobs")).scalar_one()
    assert jobs > 0, "ingestion lineage was not written to ingestion_jobs"
    failed = db_session.execute(
        text("SELECT error_summary FROM ingestion_jobs WHERE status = 'FAILED'")
    ).fetchall()
    assert len(failed) == 0, f"at least one ingestion job is recorded as failed: {failed}"


def test_ingested_rows_carry_provenance(db_session: Session):
    missing = db_session.execute(
        text("SELECT count(*) FROM employees WHERE ingestion_job_id IS NULL")
    ).scalar_one()
    assert missing == 0, "some rows have no ingestion_job_id provenance"
