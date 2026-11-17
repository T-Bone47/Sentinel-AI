"""
Tests for the constrained query DSL + compiler (app/services/grc_engine/).

Split deliberately into two groups:

  - Validation tests need no database at all: validate_and_compile() is a
    pure function over Pydantic models and the schema_graph constant, so
    every rejection case (fake table, fake column, fake join, wrong-table
    filter) is tested fast and without any Postgres dependency.
  - Execution tests run the compiled query against the real, fully
    ingested database, because "the compiler builds a Select that looks
    right" and "the compiler builds a Select that returns the right real
    rows" are different claims, and only the second one is the one that
    matters.
"""
from __future__ import annotations

import pytest

from app.database.session import AsyncSessionLocal, engine
from app.services.grc_engine.query_compiler import (
    QueryValidationError,
    execute,
    validate_and_compile,
)
from app.services.grc_engine.query_dsl import Filter, JoinStep, QueryPlan
from app.services.grc_engine.schema_graph import (
    METRIC_NAMESPACES,
    TABLES,
    describe_for_llm,
    is_valid_join,
    table_names,
)

# NOT `pytestmark = pytest.mark.asyncio` here: pyproject.toml already sets
# asyncio_mode = auto (confirmed via `pytest -o addopts=""` header output),
# which detects async def tests automatically; this file also has plain
# sync tests (schema_graph needs no event loop at all), and applying the
# marker unconditionally to every test in the module warns on those.


@pytest.fixture
async def db():
    """Function-scoped and disposes the engine after each test for the
    same reason tests/conftest.py's `client` fixture does: pytest-asyncio
    gives every test its own event loop, and a reused asyncpg pool holds
    connections bound to whichever loop first touched it, so anything
    session-scoped fails with 'attached to a different loop' as soon as a
    second test runs."""
    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()


# --------------------------------------------------------------------------
# schema_graph
# --------------------------------------------------------------------------

def test_schema_graph_has_all_fifteen_business_tables():
    assert table_names() == {
        "employees", "devices", "cloud_assets", "applications", "vendors",
        "policies", "controls", "risks", "evidence", "findings", "reports",
        "personal_data_inventory", "consent_records", "iam_records", "audit_logs",
    }


def test_infrastructure_tables_are_absent():
    # users / ingestion_jobs / ingestion_logs / trust_score_snapshots are
    # not GRC data and must never be selectable from this engine.
    for infra in ("users", "ingestion_jobs", "ingestion_logs", "trust_score_snapshots", "alembic_version"):
        assert infra not in TABLES


def test_island_tables_have_no_foreign_keys():
    """vendors and reports were verified against the live DB catalog to
    have zero FKs to anything else — confirmed independently against the
    repo's own docs/profiling/relationships.txt overlap analysis."""
    assert TABLES["vendors"].foreign_keys == {}
    assert TABLES["reports"].foreign_keys == {}


def test_known_real_joins_are_valid():
    real_edges = [
        ("devices", "employee_id", "employees", "employee_id"),
        ("evidence", "control_id", "controls", "control_id"),
        ("findings", "evidence_id", "evidence", "evidence_id"),
        ("controls", "policy_id", "policies", "policy_id"),
        ("risks", "mapped_control_id", "controls", "control_id"),
        ("consent_records", "application_id", "applications", "application_id"),
        ("personal_data_inventory", "application_id", "applications", "application_id"),
    ]
    for edge in real_edges:
        assert is_valid_join(*edge), f"{edge} should be a valid real join"


def test_known_fake_joins_are_rejected():
    """These are exactly the relationships the brief's example questions
    assume exist, and empirically do not: vendor<->risk, vendor<->personal
    data, iam_records<->applications."""
    fake_edges = [
        ("vendors", "vendor_id", "risks", "risk_id"),
        ("vendors", "vendor_id", "personal_data_inventory", "data_id"),
        ("iam_records", "iam_user_id", "applications", "application_id"),
        ("reports", "report_id", "findings", "finding_id"),
        ("personal_data_inventory", "data_id", "consent_records", "consent_id"),
    ]
    for edge in fake_edges:
        assert not is_valid_join(*edge), f"{edge} must NOT be treated as a real join"


def test_describe_for_llm_mentions_every_table_and_the_key_gaps():
    desc = describe_for_llm()
    for table in TABLES:
        assert table in desc
    assert "island" in desc.lower() or "Vendors are" in desc or "ISLAND TABLE" in desc
    for namespace in METRIC_NAMESPACES:
        assert namespace in desc


# --------------------------------------------------------------------------
# validate_and_compile — pure, no DB
# --------------------------------------------------------------------------

async def test_compiles_simple_base_table_query():
    plan = QueryPlan(base_table="risks", filters=[Filter(table="risks", column="severity", op="eq", value="Critical")])
    stmt, compiled = validate_and_compile(plan)
    assert compiled.tables_used == ["risks"]
    assert "risks" in str(stmt).lower()


async def test_compiles_query_with_real_join():
    plan = QueryPlan(
        base_table="devices",
        joins=[JoinStep(from_table="devices", from_column="employee_id", to_table="employees", to_column="employee_id")],
        filters=[Filter(table="employees", column="department", op="eq", value="Engineering")],
    )
    stmt, compiled = validate_and_compile(plan)
    assert compiled.tables_used == ["devices", "employees"]


async def test_rejects_unknown_table():
    plan = QueryPlan(base_table="ssn_numbers")
    with pytest.raises(QueryValidationError, match="unknown table"):
        validate_and_compile(plan)


async def test_rejects_unknown_column():
    plan = QueryPlan(base_table="risks", filters=[Filter(table="risks", column="ssn", op="eq", value="x")])
    with pytest.raises(QueryValidationError, match="unknown column"):
        validate_and_compile(plan)


async def test_rejects_fabricated_join():
    plan = QueryPlan(
        base_table="vendors",
        joins=[JoinStep(from_table="vendors", from_column="vendor_id", to_table="risks", to_column="risk_id")],
    )
    with pytest.raises(QueryValidationError, match="not a real foreign-key"):
        validate_and_compile(plan)


async def test_rejects_join_from_table_not_yet_in_plan():
    """A join step whose from_table is neither the base table nor an
    earlier join must be rejected — it would silently reference a table
    that was never brought into the query."""
    plan = QueryPlan(
        base_table="risks",
        joins=[JoinStep(from_table="devices", from_column="employee_id", to_table="employees", to_column="employee_id")],
    )
    with pytest.raises(QueryValidationError, match="not the base table"):
        validate_and_compile(plan)


async def test_rejects_filter_on_table_not_in_plan():
    plan = QueryPlan(base_table="risks", filters=[Filter(table="vendors", column="risk_rating", op="eq", value="High")])
    with pytest.raises(QueryValidationError, match="not the base table"):
        validate_and_compile(plan)


async def test_rejects_unknown_operator_shaped_input():
    with pytest.raises(Exception):
        Filter(table="risks", column="severity", op="drop_table", value="x")


async def test_limit_is_clamped_not_rejected():
    plan = QueryPlan(base_table="risks", limit=99999)
    assert plan.limit == 100  # DSL-level clamp
    stmt, compiled = validate_and_compile(plan)
    assert compiled.row_limit == 100


async def test_negative_limit_is_clamped_up_to_one():
    plan = QueryPlan(base_table="risks", limit=-5)
    assert plan.limit == 1


async def test_filter_value_rejects_object_shapes():
    with pytest.raises(Exception):
        Filter(table="risks", column="severity", op="eq", value={"$ne": None})


# --------------------------------------------------------------------------
# execute — real database, real rows
# --------------------------------------------------------------------------

async def test_execute_returns_real_rows_matching_filter(db):
    plan = QueryPlan(
        base_table="risks",
        filters=[Filter(table="risks", column="severity", op="eq", value="Critical")],
        limit=5,
    )
    rows, compiled = await execute(db, plan)
    assert 0 < len(rows) <= 5
    assert all(r.severity == "Critical" for r in rows)


async def test_execute_respects_row_limit_ceiling(db):
    plan = QueryPlan(base_table="risks", limit=3)
    rows, _ = await execute(db, plan)
    assert len(rows) <= 3


async def test_execute_with_real_join_and_filter(db):
    """Employees in Engineering whose devices are not encrypted —
    a genuine two-table question over a real FK."""
    plan = QueryPlan(
        base_table="devices",
        joins=[JoinStep(from_table="devices", from_column="employee_id", to_table="employees", to_column="employee_id")],
        filters=[
            Filter(table="employees", column="department", op="eq", value="Engineering"),
            Filter(table="devices", column="encryption_enabled", op="eq", value=False),
        ],
        limit=10,
    )
    rows, compiled = await execute(db, plan)
    assert compiled.tables_used == ["devices", "employees"]
    assert all(r.encryption_enabled is False for r in rows)


async def test_execute_contains_operator_is_case_insensitive_substring(db):
    plan = QueryPlan(base_table="vendors", filters=[Filter(table="vendors", column="vendor_name", op="contains", value="a")], limit=5)
    rows, _ = await execute(db, plan)
    assert all("a" in r.vendor_name.lower() for r in rows)


async def test_execute_is_null_operator(db):
    plan = QueryPlan(base_table="risks", filters=[Filter(table="risks", column="mapped_control_id", op="is_null")], limit=50)
    rows, _ = await execute(db, plan)
    assert all(r.mapped_control_id is None for r in rows)


async def test_execute_date_filter_coerces_iso_string(db):
    plan = QueryPlan(
        base_table="vendors",
        filters=[Filter(table="vendors", column="contract_expiry", op="lt", value="2020-01-01")],
        limit=50,
    )
    rows, _ = await execute(db, plan)  # must not raise — proves date coercion works
    assert all(r.contract_expiry is not None and r.contract_expiry.isoformat() < "2020-01-01" for r in rows)


async def test_execute_transaction_is_actually_read_only(db):
    """Defense in depth: even though QueryPlan cannot express a write,
    confirm the SET LOCAL transaction_read_only pragma this module issues
    really does make the transaction reject a write, in case a future
    change to this module ever tried to run one."""
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    plan = QueryPlan(base_table="risks", limit=1)
    rows, _ = await execute(db, plan)
    assert rows
    
    if db.get_bind().dialect.name != "postgresql":
        pytest.skip("SQLite test dialect does not apply read-only transaction bounds")
        
    with pytest.raises(DBAPIError, match="read-only"):
        await db.execute(text("DELETE FROM risks WHERE risk_id = :id"), {"id": rows[0].risk_id})
    await db.rollback()
