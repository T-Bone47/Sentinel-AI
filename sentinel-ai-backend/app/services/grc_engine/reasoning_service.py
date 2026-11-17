"""
Reasoning orchestrator — the general-purpose pipeline described in the
brief's Section 21:

    question -> understanding -> {metrics fetch, row query} ->
    correlation -> deterministic template -> LLM polish -> formatted answer

Fallback chain, in order, and why each step exists:

  1. Try the general engine's understanding step. If the LLM is
     unconfigured, times out, errors, or returns something that doesn't
     parse into a ReasoningPlan, `understand()` returns None (see
     understanding_service.py) and this module falls through to (2).
  2. Fall back to the EXISTING, already-tested, deterministic 12-intent
     CopilotService. This is not a lesser answer — for the 7+5 questions it
     already covers, it is exactly as correct as it always was; this
     engine only adds generality ON TOP, it does not replace or weaken
     what already worked. This is the concrete meaning of "refactor rather
     than duplicate" for this codebase: the new engine's fallback path
     *is* the old engine, unmodified.
  3. If the general engine understood the question but the data it asked
     for doesn't exist or the row_query referenced something unreal
     (caught as QueryValidationError — should be rare, since
     understanding_service's own prompt lists only real names, but an LLM
     can still get it wrong), return an honest insufficient-data answer,
     never a raw exception and never a silent empty answer.

Every path through this module ends in one of exactly three engines, and
the caller always knows which one actually produced the answer:

    "llm_grounded_v1"           general engine understood + LLM polished
    "deterministic_fallback_v1" general engine understood, no LLM polish
                                 OR general engine unavailable, old Copilot
                                 answered (both cases are "no LLM narrated
                                 this specific answer" — the same meaning
                                 the original Copilot contract already
                                 gives that string)
    "insufficient_data_v1"      the honest "I don't have enough data"
                                 outcome — new, because the general engine
                                 can hit this from genuine open-ended
                                 questions in a way the fixed 12-intent
                                 matcher structurally could not
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.copilot import CopilotService
from app.services.grc_engine import metrics_catalog, query_compiler, understanding_service
from app.services.grc_engine.query_compiler import QueryValidationError
from app.services.grc_engine.query_dsl import ReasoningPlan
from app.services.llm_service import LLMService

logger = logging.getLogger("sentinel.grc_engine.reasoning")

MAX_ENTITIES_SHOWN = 12

# --- Authorization -------------------------------------------------------
# Callers pass `readable_tables`: the database tables the asking user's role
# may read every row of (see app/api/v1/resources.py). The engine reads on
# that user's behalf, so it must never return a row they could not have
# fetched themselves. `None` means "no restriction" and is for internal use
# and unit tests only — every HTTP entry point passes a real set.

# Tables the deterministic Copilot returns individual records from.
COPILOT_TABLES = frozenset({"controls", "evidence", "findings", "policies", "risks", "vendors"})

# Metric namespaces that embed individual records, not only counts.
_NAMESPACE_ROW_TABLES: dict[str, frozenset[str]] = {
    "recent_audit_activity": frozenset({"audit_logs"}),
}


def copilot_permitted(readable_tables: frozenset[str] | None) -> bool:
    return readable_tables is None or COPILOT_TABLES <= readable_tables


def _plan_tables(query: Any) -> set[str]:
    """Every table a row query touches, including ones used only to join,
    filter or sort — reading through a table is still reading it."""
    tables = {query.base_table, *(f.table for f in query.filters)}
    for step in query.joins:
        tables |= {step.from_table, step.to_table}
    if query.order_by_table:
        tables.add(query.order_by_table)
    return tables


@dataclass
class GeneralAnswer:
    question: str
    question_type: str
    answer: str
    datasets_used: list[str] = field(default_factory=list)
    records_analyzed: int = 0
    evidence: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    engine: str = "insufficient_data_v1"
    llm_used: bool = False
    reasoning_notes: str = ""
    missing_data: str | None = None
    available_data: str | None = None
    # Present only when this fell all the way through to the old Copilot,
    # so /copilot/query can still hand back its exact original contract.
    legacy_result: dict[str, Any] | None = None


def _row_identity(table: str, row: Any) -> dict[str, Any]:
    """A compact, safe-to-serialize identity for one ORM row: primary key
    plus a small number of human-readable columns, never every column
    (avoid leaking unrelated fields into a response shaped by a question
    that didn't ask for them)."""
    from app.services.grc_engine.schema_graph import TABLES

    info = TABLES[table]
    preferred = [info.primary_key] + [
        c for c in info.columns
        if c != info.primary_key and any(k in c for k in ("name", "severity", "status", "risk", "rating", "level"))
    ]
    seen: dict[str, Any] = {}
    for col in preferred:
        if col in info.columns and col not in seen:
            seen[col] = getattr(row, col, None)
        if len(seen) >= 5:
            break
    return {"table": table, **seen}


def _access_denied(question: str, question_type: str = "unsupported") -> GeneralAnswer:
    return GeneralAnswer(
        question=question,
        question_type=question_type,
        answer="Your role does not have access to the data needed to answer that question.",
        confidence=1.0,  # certain about the refusal, not about any data
        engine="access_denied_v1",
        llm_used=False,
    )


async def _run_general_engine(
    db: AsyncSession,
    question: str,
    plan: ReasoningPlan,
    readable_tables: frozenset[str] | None = None,
) -> GeneralAnswer:
    if readable_tables is not None:
        # Checked before anything is fetched, and independently of whatever
        # produced the plan (an LLM proposes plans; it does not get a say here).
        if plan.row_query is not None and not _plan_tables(plan.row_query) <= readable_tables:
            return _access_denied(question, plan.question_type)
        plan = plan.model_copy(update={
            "metrics_needed": [
                name for name in plan.metrics_needed
                if _NAMESPACE_ROW_TABLES.get(name, frozenset()) <= readable_tables
            ]
        })

    if plan.insufficient_data_reason:
        return GeneralAnswer(
            question=question,
            question_type=plan.question_type,
            answer=_insufficient_data_prose(plan),
            confidence=1.0,  # confident that we honestly don't have this, not confident in a guess
            engine="insufficient_data_v1",
            llm_used=True,
            reasoning_notes=plan.reasoning_notes,
            missing_data=plan.missing_data,
            available_data=plan.available_data,
        )

    metrics: dict[str, Any] = {}
    rows: list[Any] = []
    datasets_used: list[str] = []
    row_table = None

    try:
        if plan.metrics_needed:
            metrics = await metrics_catalog.fetch(db, plan.metrics_needed)
            datasets_used.extend(metrics.keys())
        if plan.row_query:
            rows, compiled = await query_compiler.execute(db, plan.row_query)
            datasets_used.extend(compiled.tables_used)
            row_table = compiled.tables_used[0] if compiled.tables_used else plan.row_query.base_table
    except QueryValidationError as exc:
        logger.warning("General engine plan referenced an invalid schema element: %s", exc)
        return GeneralAnswer(
            question=question,
            question_type=plan.question_type,
            answer=(
                "I can't answer that from a real relationship in the data — "
                f"the query I would need referenced something that doesn't exist ({exc}). "
                "I won't approximate a join that isn't really there."
            ),
            confidence=1.0,
            engine="insufficient_data_v1",
            llm_used=False,
            reasoning_notes=plan.reasoning_notes,
        )

    if not metrics and not rows:
        return GeneralAnswer(
            question=question,
            question_type=plan.question_type,
            answer="I found no records matching that question in the current data.",
            datasets_used=datasets_used,
            confidence=0.6,
            engine="deterministic_fallback_v1",
        )

    entities = [_row_identity(row_table, r) for r in rows[:MAX_ENTITIES_SHOWN]] if row_table else []
    deterministic_answer = _template_answer(plan, metrics, rows)

    deterministic_result = {
        "answer": deterministic_answer,
        "supporting_data": [
            {"label": k, "value": v} for k, v in _flatten_metric_headline(metrics).items()
        ],
        "related_entities": [
            {"type": e["table"], "id": e.get(list(e.keys())[1], "?"), "label": e.get(list(e.keys())[1], "?"), "detail": ""}
            for e in entities
        ],
        "recommendations": [],
        "intent_label": plan.question_type.replace("_", " ").title(),
    }

    llm = LLMService()
    llm_text = await llm.explain(deterministic_result, question) if llm.is_configured else None

    return GeneralAnswer(
        question=question,
        question_type=plan.question_type,
        answer=llm_text or deterministic_answer,
        datasets_used=sorted(set(datasets_used)),
        records_analyzed=len(rows) if rows else sum(_count_hint(m) for m in metrics.values()),
        evidence=entities,
        metrics=metrics,
        confidence=0.85 if llm_text else 0.7,
        engine="llm_grounded_v1" if llm_text else "deterministic_fallback_v1",
        llm_used=llm_text is not None,
        reasoning_notes=plan.reasoning_notes,
    )


def _count_hint(metric_block: Any) -> int:
    if isinstance(metric_block, dict) and isinstance(metric_block.get("total"), int):
        return metric_block["total"]
    return 0


def _flatten_metric_headline(metrics: dict[str, Any], limit: int = 8) -> dict[str, Any]:
    """A small, flat set of the most relevant numbers across whichever
    metric namespaces were fetched, for supporting_data — not a dump of
    every nested breakdown, which would blow past what a chat answer
    should show."""
    out: dict[str, Any] = {}
    for namespace, block in metrics.items():
        if not isinstance(block, dict):
            continue
        for key in ("trust_score", "total", "open", "critical", "coverage_pct", "pass_rate_pct", "privileged_without_mfa"):
            if key in block and len(out) < limit:
                out[f"{namespace}.{key}"] = block[key]
    return out


def _template_answer(plan: ReasoningPlan, metrics: dict[str, Any], rows: list[Any]) -> str:
    parts: list[str] = []
    if rows:
        parts.append(f"Found {len(rows)} matching record(s).")
    for namespace, block in metrics.items():
        if isinstance(block, dict) and "total" in block:
            parts.append(f"{namespace.replace('_', ' ')}: {block['total']} total.")
    if not parts:
        parts.append("No matching data found.")
    return " ".join(parts)


def _insufficient_data_prose(plan: ReasoningPlan) -> str:
    lines = ["I don't have enough data to determine this."]
    if plan.missing_data:
        lines.append(f"Missing data: {plan.missing_data}")
    if plan.available_data:
        lines.append(f"Available instead: {plan.available_data}")
    if plan.insufficient_data_reason:
        lines.append(plan.insufficient_data_reason)
    return " ".join(lines)


async def answer(
    db: AsyncSession,
    question: str,
    *,
    conversation_context: str | None = None,
    readable_tables: frozenset[str] | None = None,
) -> GeneralAnswer:
    """Entry point. Always returns a GeneralAnswer — never raises for a
    question-understanding or data problem (only genuine infra failures,
    e.g. the database itself being down, propagate, exactly like the
    existing CopilotService)."""
    plan = await understanding_service.understand(question, conversation_context=conversation_context)

    if plan is not None:
        return await _run_general_engine(db, question, plan, readable_tables)

    if not copilot_permitted(readable_tables):
        return _access_denied(question)

    # General engine unavailable end to end (no key / down / bad output) —
    # fall back to the existing, unmodified, already-tested deterministic
    # Copilot rather than ever showing nothing.
    legacy = await CopilotService(db).answer(question)
    return GeneralAnswer(
        question=question,
        question_type="factual",
        answer=legacy["answer"],
        datasets_used=[],
        recommendations=legacy.get("recommendations", []),
        confidence={"high": 0.9, "medium": 0.7, "low": 0.5, "none": 0.2}.get(legacy.get("confidence"), 0.5),
        engine=legacy.get("engine", "deterministic_fallback_v1"),
        llm_used=legacy.get("llm_used", False),
        legacy_result=legacy,
    )
