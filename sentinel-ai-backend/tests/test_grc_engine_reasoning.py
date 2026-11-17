"""
Tests for app/services/grc_engine/reasoning_service.py — the orchestrator.

The layers underneath (query_compiler, metrics_catalog, understanding_service)
already have their own focused test files; these tests are about ORCHESTRATION:
which path gets taken and does the response make sense, not re-proving e.g.
that query_compiler rejects fake joins (test_grc_engine_query.py already does).
"""
from __future__ import annotations

import pytest

from app.database.session import AsyncSessionLocal, engine
from app.services.grc_engine import reasoning_service
from app.services.grc_engine.query_dsl import Filter, JoinStep, QueryPlan, ReasoningPlan


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()


class TestFallbackToExistingCopilot:
    """With no LLM_API_KEY configured (true in this sandbox and in CI),
    understand() always returns None, so answer() must fall all the way
    through to the existing, unmodified CopilotService — proving the
    general engine's absence never means no answer."""

    async def test_falls_back_and_still_answers_a_mandatory_question(self, db):
        result = await reasoning_service.answer(db, "Are we audit ready?")
        assert result.answer
        assert result.engine == "deterministic_fallback_v1"
        assert result.llm_used is False
        assert result.legacy_result is not None
        assert result.legacy_result["intent"] == "audit_readiness"

    async def test_fallback_preserves_the_old_contract_fields(self, db):
        result = await reasoning_service.answer(db, "What are our top risks?")
        legacy = result.legacy_result
        for key in ("question", "intent", "intent_label", "answer", "supporting_data",
                    "related_entities", "recommendations", "sources", "confidence",
                    "engine", "llm_used", "suggested_questions"):
            assert key in legacy, f"missing {key}"


class TestGeneralEngineMetricsPath:
    async def test_metrics_only_plan_returns_real_numbers(self, db):
        plan = ReasoningPlan(question_type="analytical", metrics_needed=["vendor_risk"])
        result = await reasoning_service._run_general_engine(db, "Which vendors are riskiest?", plan)
        assert "vendor_risk" in result.metrics
        assert result.metrics["vendor_risk"]["total"] == 100  # real, ingested count
        assert result.datasets_used == ["vendor_risk"]
        assert result.engine == "deterministic_fallback_v1"  # no LLM key in this sandbox

    async def test_multiple_metric_namespaces_all_come_back(self, db):
        plan = ReasoningPlan(question_type="executive", metrics_needed=["risks", "findings", "evidence_coverage"])
        result = await reasoning_service._run_general_engine(db, "Give me our GRC posture summary", plan)
        assert set(result.datasets_used) == {"risks", "findings", "evidence_coverage"}


class TestGeneralEngineRowQueryPath:
    async def test_row_query_returns_real_evidence_with_ids(self, db):
        plan = ReasoningPlan(
            question_type="list",
            row_query=QueryPlan(
                base_table="devices",
                joins=[JoinStep(from_table="devices", from_column="employee_id", to_table="employees", to_column="employee_id")],
                filters=[Filter(table="devices", column="encryption_enabled", op="eq", value=False)],
                limit=5,
            ),
        )
        result = await reasoning_service._run_general_engine(db, "Which devices lack encryption?", plan)
        assert result.records_analyzed <= 5
        assert result.records_analyzed > 0
        assert all("device_id" in e for e in result.evidence)
        assert "devices" in result.datasets_used
        assert "employees" in result.datasets_used  # the join target is tracked too

    async def test_row_query_with_no_matches_is_honest_not_empty(self, db):
        plan = ReasoningPlan(
            question_type="list",
            row_query=QueryPlan(
                base_table="vendors",
                filters=[Filter(table="vendors", column="vendor_name", op="eq", value="Definitely Not A Real Vendor Inc")],
            ),
        )
        result = await reasoning_service._run_general_engine(db, "anything", plan)
        assert "no records" in result.answer.lower() or "no matching" in result.answer.lower()
        assert result.records_analyzed == 0


class TestInsufficientDataPath:
    async def test_llm_declared_insufficient_data_is_rendered_honestly(self, db):
        plan = ReasoningPlan(
            question_type="unsupported",
            insufficient_data_reason="vendors has no foreign key to risks or personal_data_inventory.",
            missing_data="A vendor-to-risk or vendor-to-application relationship.",
            available_data="Vendor risk_rating and certifications alone.",
        )
        result = await reasoning_service._run_general_engine(db, "Which vendors caused which risks?", plan)
        assert result.engine == "insufficient_data_v1"
        assert "vendor-to-risk" in result.answer
        assert "risk_rating" in result.answer

    async def test_fake_table_in_row_query_degrades_to_insufficient_data_not_a_crash(self, db):
        """Simulates the LLM getting it wrong despite the prompt — proves
        the orchestrator's try/except around query_compiler actually
        converts a QueryValidationError into an honest answer end to end,
        not just that query_compiler itself raises (already proven in
        test_grc_engine_query.py)."""
        plan = ReasoningPlan(question_type="list", row_query=QueryPlan(base_table="ssn_records", limit=5))
        result = await reasoning_service._run_general_engine(db, "anything", plan)
        assert result.engine == "insufficient_data_v1"
        assert "ssn_records" in result.answer or "doesn't exist" in result.answer

    async def test_fabricated_join_in_row_query_degrades_gracefully(self, db):
        plan = ReasoningPlan(
            question_type="list",
            row_query=QueryPlan(
                base_table="vendors",
                joins=[JoinStep(from_table="vendors", from_column="vendor_id", to_table="risks", to_column="risk_id")],
            ),
        )
        result = await reasoning_service._run_general_engine(db, "anything", plan)
        assert result.engine == "insufficient_data_v1"


class TestRowIdentity:
    def test_row_identity_never_raises_for_any_real_table(self, db):
        # Pure/sync helper — exercised across every table name to catch a
        # KeyError from a typo'd column list before it ever reaches a live
        # request.
        from app.services.grc_engine.schema_graph import TABLES

        class _FakeRow:
            def __getattr__(self, name):
                return "x"

        for table in TABLES:
            identity = reasoning_service._row_identity(table, _FakeRow())
            assert identity["table"] == table
            assert len(identity) >= 2  # at least the primary key + something
