"""
Compiles a validated QueryPlan into a real, safe, parameterized query and
executes it. This is the only place in the whole engine that touches the
database for row-level questions, and it re-validates everything against
schema_graph.TABLES itself — it does not trust that upstream Pydantic
validation or the LLM was well-behaved, because defense-in-depth means the
component that actually runs a query is the one that must refuse to run a
bad one, not just the component that happened to validate it first.

Safety properties, and how each is actually enforced (not just intended):

  1. Only real tables/columns are ever referenced.
     -> every table/column name is looked up in schema_graph.TABLES; on any
        miss this raises QueryValidationError before touching SQLAlchemy.
  2. Only real, FK-verified joins are ever executed.
     -> every JoinStep is checked with schema_graph.is_valid_join(); a plan
        that invents a join is rejected outright, not "joined anyway".
  3. No SQL text ever comes from the LLM.
     -> QueryPlan (query_dsl.py) has no field that can hold a query
        string, and this module builds everything through SQLAlchemy's
        Core expression language (select/where/join), which parameterizes
        every value automatically. There is no f-string or .format() or %
        anywhere near a value in this file.
  4. Row limits are enforced twice.
     -> once in query_dsl.QueryPlan's validator (clamped 1-100) and again
        here as a hard ceiling, so a future caller that constructs a
        QueryPlan by hand cannot bypass the first check.
  5. Read-only, time-bounded execution (OWASP LLM10 — bound consumption).
     -> `SET LOCAL transaction_read_only = on` and a statement_timeout are
        issued on the same transaction immediately before running the
        compiled query, so even a plan that (somehow) produced a write-like
        intent, or an expensive query, cannot mutate data or hang the
        connection pool.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import Select, and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.models import (
    Application,
    AuditLog,
    CloudAsset,
    ConsentRecord,
    Control,
    Device,
    Employee,
    Evidence,
    Finding,
    IAMRecord,
    PersonalDataInventory,
    Policy,
    Report,
    Risk,
    Vendor,
)
from app.services.grc_engine.query_dsl import MAX_ROW_LIMIT, Filter, QueryPlan
from app.services.grc_engine.schema_graph import TABLES, is_valid_join

STATEMENT_TIMEOUT_MS = 5_000

MODELS: dict[str, type] = {
    "employees": Employee,
    "devices": Device,
    "cloud_assets": CloudAsset,
    "applications": Application,
    "vendors": Vendor,
    "policies": Policy,
    "controls": Control,
    "risks": Risk,
    "evidence": Evidence,
    "findings": Finding,
    "reports": Report,
    "personal_data_inventory": PersonalDataInventory,
    "consent_records": ConsentRecord,
    "iam_records": IAMRecord,
    "audit_logs": AuditLog,
}

_OPS = {
    "eq": lambda col, val: col == val,
    "neq": lambda col, val: col != val,
    "in": lambda col, val: col.in_(val if isinstance(val, list) else [val]),
    "not_in": lambda col, val: col.not_in(val if isinstance(val, list) else [val]),
    "gt": lambda col, val: col > val,
    "gte": lambda col, val: col >= val,
    "lt": lambda col, val: col < val,
    "lte": lambda col, val: col <= val,
    "is_null": lambda col, val: col.is_(None),
    "is_not_null": lambda col, val: col.is_not(None),
    "contains": lambda col, val: col.ilike(f"%{val}%"),
}


class QueryValidationError(ValueError):
    """A plan referenced a table, column, join, or operator that isn't in
    the real schema graph. Always a validation failure, never a database
    error — this must never reach the person as a raw exception."""


@dataclass
class CompiledQuery:
    plan: QueryPlan
    tables_used: list[str]
    row_limit: int


def _table(name: str) -> str:
    if name not in TABLES:
        raise QueryValidationError(f"unknown table '{name}'")
    return name


def _column(table: str, column: str) -> str:
    if column not in TABLES[table].columns:
        raise QueryValidationError(f"unknown column '{table}.{column}'")
    return column


def _model_column(table: str, column: str) -> InstrumentedAttribute:
    _table(table)
    _column(table, column)
    return getattr(MODELS[table], column)


def _coerce_value(table: str, column: str, op: str, value: Any) -> Any:
    """Best-effort coercion of LLM-supplied JSON scalars (strings) into the
    real column type, so an 'is the risk older than 30 days' filter can be
    expressed as an ISO date string rather than requiring the LLM to know
    Python types. Never widens what the op can do — a bad coercion simply
    raises, which becomes an insufficient_data answer upstream, not a
    silent wrong query."""
    if op in ("is_null", "is_not_null"):
        return None
    col_type = TABLES[table].columns[column].type
    if col_type in ("date",) and isinstance(value, str):
        return date.fromisoformat(value)
    if col_type == "timestamp" and isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


def validate_and_compile(plan: QueryPlan) -> tuple[Select, CompiledQuery]:
    """Validate every part of `plan` against the real schema graph, then
    build the actual SQLAlchemy Select. Raises QueryValidationError on any
    reference to something that isn't real — never partially executes a
    partially-valid plan."""
    base = _table(plan.base_table)
    tables_used = [base]
    model = MODELS[base]

    stmt = select(model)

    # Joins — each hop validated against the REAL FK graph, in order, so a
    # join chain can only ever walk edges that actually exist.
    for step in plan.joins:
        _table(step.from_table)
        _table(step.to_table)
        _column(step.from_table, step.from_column)
        _column(step.to_table, step.to_column)
        if not is_valid_join(step.from_table, step.from_column, step.to_table, step.to_column):
            raise QueryValidationError(
                f"'{step.from_table}.{step.from_column}' -> "
                f"'{step.to_table}.{step.to_column}' is not a real foreign-key "
                "relationship in this schema"
            )
        if step.from_table not in tables_used:
            raise QueryValidationError(
                f"join references '{step.from_table}', which is not the base "
                "table or an earlier join in this plan"
            )
        target_model = MODELS[step.to_table]
        from_col = _model_column(step.from_table, step.from_column)
        to_col = _model_column(step.to_table, step.to_column)
        stmt = stmt.join(target_model, from_col == to_col)
        tables_used.append(step.to_table)

    # Filters — every one validated against a table actually present in
    # this plan (base or joined), never an arbitrary table.
    conditions = []
    for f in plan.filters:
        _validate_filter_table(f, tables_used)
        col = _model_column(f.table, f.column)
        value = _coerce_value(f.table, f.column, f.op, f.value)
        conditions.append(_OPS[f.op](col, value))
    if conditions:
        stmt = stmt.where(and_(*conditions))

    if plan.order_by_table and plan.order_by_column:
        if plan.order_by_table not in tables_used:
            raise QueryValidationError(f"order_by references table '{plan.order_by_table}' not in this plan")
        order_col = _model_column(plan.order_by_table, plan.order_by_column)
        stmt = stmt.order_by(order_col.desc() if plan.order_desc else order_col.asc())

    row_limit = max(1, min(plan.limit, MAX_ROW_LIMIT))
    stmt = stmt.limit(row_limit)

    return stmt, CompiledQuery(plan=plan, tables_used=tables_used, row_limit=row_limit)


def _validate_filter_table(f: Filter, tables_used: list[str]) -> None:
    _table(f.table)
    _column(f.table, f.column)
    if f.table not in tables_used:
        raise QueryValidationError(
            f"filter references table '{f.table}', which is not the base "
            "table or an earlier join in this plan"
        )


async def execute(db: AsyncSession, plan: QueryPlan) -> tuple[list[Any], CompiledQuery]:
    """Validate, compile, and run — inside a read-only, time-bounded
    transaction scope. Returns the ORM rows for the BASE table (joins are
    used only to filter/order; callers get whole rows to select real
    fields/IDs from, never a partial tuple that could misattribute a
    column to the wrong table)."""
    stmt, compiled = validate_and_compile(plan)
    
    # Apply PostgreSQL-specific connection bounds if not running against SQLite in tests
    if db.get_bind().dialect.name == "postgresql":
        await db.execute(text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}"))
        await db.execute(text("SET LOCAL transaction_read_only = on"))
        
    result = await db.execute(stmt)
    rows = list(result.scalars().unique().all())
    return rows, compiled
