"""
The structured query plan the LLM is allowed to produce.

This is the "GOOD" side of the LLM-output-is-data-not-code split
(OWASP LLM05 / LLM06): the model never emits SQL text. It emits JSON that
Pydantic parses into this schema, which is the *only* shape query_compiler
knows how to execute — there is no field here, and no code path in the
compiler, that can express INSERT/UPDATE/DELETE/DDL, so "the LLM tricked the
validator into a write" is not a category of bug this design admits. Every
string field that names a table/column/operator is re-checked against
schema_graph.TABLES at compile time regardless of what Pydantic already
allowed, because Pydantic only proves shape, not that a name is real.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

MAX_ROW_LIMIT = 100
DEFAULT_ROW_LIMIT = 25

FilterOp = Literal[
    "eq", "neq", "in", "not_in", "gt", "gte", "lt", "lte",
    "is_null", "is_not_null", "contains",
]


class Filter(BaseModel):
    """A single WHERE condition. `table` names which table in the plan
    (base or joined) the column belongs to, so filters can target joined
    tables unambiguously."""

    table: str
    column: str
    op: FilterOp
    value: Any = None

    @field_validator("value")
    @classmethod
    def _value_is_scalar_or_list(cls, v: Any) -> Any:
        if isinstance(v, (dict,)):
            raise ValueError("filter value cannot be an object")
        if isinstance(v, list) and any(isinstance(x, (dict, list)) for x in v):
            raise ValueError("filter value list must contain only scalars")
        return v


class JoinStep(BaseModel):
    """One hop in a join chain. `from_table`/`from_column` must be the base
    table or an already-joined table earlier in the chain; validated
    against the REAL foreign-key graph in schema_graph, in either
    direction, at compile time."""

    from_table: str
    from_column: str
    to_table: str
    to_column: str


class QueryPlan(BaseModel):
    """A read-only, SELECT-shaped query plan. There is deliberately no way
    to express a write anywhere in this model."""

    base_table: str
    joins: list[JoinStep] = Field(default_factory=list)
    filters: list[Filter] = Field(default_factory=list)
    # None = compiler picks a sensible default column set for the table.
    select_columns: list[str] | None = None
    order_by_table: str | None = None
    order_by_column: str | None = None
    order_desc: bool = False
    limit: int = DEFAULT_ROW_LIMIT

    @field_validator("limit")
    @classmethod
    def _clamp_limit(cls, v: int) -> int:
        # Clamp rather than reject: an over-eager limit from the LLM
        # shouldn't fail the whole request when clamping is unambiguous
        # and safe (LLM10 — bound consumption).
        return max(1, min(v, MAX_ROW_LIMIT))


class MetricRequest(BaseModel):
    """A request for one namespace of already-computed, already-correct
    aggregate metrics (see metrics_catalog.py) — the preferred path for any
    count/rate/breakdown question, instead of recomputing via a row query."""

    namespace: str


class ReasoningPlan(BaseModel):
    """The full structured plan the Question Understanding step produces
    for one question. `insufficient_data_reason` is not an error case —
    it is a first-class, expected outcome (brief section 10: NO
    HALLUCINATION) and the formatter renders it as an honest answer, not a
    failure."""

    question_type: Literal[
        "factual", "analytical", "list", "investigation",
        "executive", "comparison", "trend", "prioritization", "unsupported",
    ]
    metrics_needed: list[str] = Field(default_factory=list)
    row_query: QueryPlan | None = None
    reasoning_notes: str = ""
    insufficient_data_reason: str | None = None
    missing_data: str | None = None
    available_data: str | None = None
