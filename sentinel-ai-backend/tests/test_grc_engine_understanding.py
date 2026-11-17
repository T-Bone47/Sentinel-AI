"""
Tests for the LLM-driven question understanding layer
(app/services/grc_engine/understanding_service.py).

Mocks httpx exactly the way tests/test_copilot_llm.py already does, for the
same reason: no real LLM API key or network path exists in CI/this
sandbox, so every success/failure branch of `understand()` has to be
provable through a mocked transport, not a live call.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.grc_engine.query_dsl import ReasoningPlan
from app.services.grc_engine.understanding_service import _build_system_prompt, _strip_fences, understand
from app.services.llm_service import LLMService


def _mock_llm_response(content: str) -> MagicMock:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": content}}]}
    mock_response.raise_for_status = MagicMock()
    return mock_response


def _configured_settings(mock_settings) -> None:
    mock_settings.llm_api_key = "sk-test"
    mock_settings.llm_model = "gpt-4o-mini"
    mock_settings.llm_base_url = "https://api.openai.com/v1"
    mock_settings.llm_timeout = 15


VALID_METRIC_PLAN = json.dumps({
    "question_type": "analytical",
    "metrics_needed": ["vendor_risk"],
    "row_query": None,
    "reasoning_notes": "Vendor risk breakdown answers this directly.",
    "insufficient_data_reason": None,
    "missing_data": None,
    "available_data": None,
})

VALID_ROW_QUERY_PLAN = json.dumps({
    "question_type": "list",
    "metrics_needed": [],
    "row_query": {
        "base_table": "devices",
        "joins": [{"from_table": "devices", "from_column": "employee_id", "to_table": "employees", "to_column": "employee_id"}],
        "filters": [{"table": "employees", "column": "department", "op": "eq", "value": "Engineering"}],
        "select_columns": None,
        "order_by_table": None,
        "order_by_column": None,
        "order_desc": False,
        "limit": 25,
    },
    "reasoning_notes": "Needs specific device rows for Engineering employees.",
    "insufficient_data_reason": None,
    "missing_data": None,
    "available_data": None,
})

INSUFFICIENT_DATA_PLAN = json.dumps({
    "question_type": "unsupported",
    "metrics_needed": [],
    "row_query": None,
    "reasoning_notes": "The question asks for a vendor<->personal-data link.",
    "insufficient_data_reason": "vendors has no foreign key to personal_data_inventory or risks.",
    "missing_data": "A vendor-to-application or vendor-to-risk relationship.",
    "available_data": "Vendor risk_rating and certification status alone.",
})


class TestUnderstandBasics:
    async def test_returns_none_when_unconfigured(self):
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.llm_api_key = None
            mock_settings.llm_model = "gpt-4o-mini"
            mock_settings.llm_base_url = "https://api.openai.com/v1"
            mock_settings.llm_timeout = 15
            result = await understand("Which vendors are highest risk?")
        assert result is None

    async def test_valid_metrics_plan_parses(self):
        with patch("app.services.llm_service.settings") as mock_settings:
            _configured_settings(mock_settings)
            with patch("httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.post.return_value = _mock_llm_response(VALID_METRIC_PLAN)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                MockClient.return_value = mock_client

                result = await understand("Which vendors are riskiest?")

        assert isinstance(result, ReasoningPlan)
        assert result.metrics_needed == ["vendor_risk"]
        assert result.row_query is None

    async def test_valid_row_query_plan_parses_with_join(self):
        with patch("app.services.llm_service.settings") as mock_settings:
            _configured_settings(mock_settings)
            with patch("httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.post.return_value = _mock_llm_response(VALID_ROW_QUERY_PLAN)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                MockClient.return_value = mock_client

                result = await understand("List engineering employees' devices")

        assert result.row_query is not None
        assert result.row_query.base_table == "devices"
        assert result.row_query.joins[0].to_table == "employees"

    async def test_insufficient_data_plan_parses_as_first_class_result(self):
        """A plan that honestly declines to answer is a SUCCESSFUL parse,
        not a failure — understand() must return it, not None, so the
        caller can render the honest explanation rather than silently
        falling back to the deterministic matcher."""
        with patch("app.services.llm_service.settings") as mock_settings:
            _configured_settings(mock_settings)
            with patch("httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.post.return_value = _mock_llm_response(INSUFFICIENT_DATA_PLAN)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                MockClient.return_value = mock_client

                result = await understand("Which vendors handle our most sensitive personal data?")

        assert result is not None
        assert result.insufficient_data_reason is not None
        assert "foreign key" in result.insufficient_data_reason


class TestUnderstandMalformedOutput:
    """Every one of these must degrade to None, never raise — this is the
    exact 'malformed LLM output must trigger deterministic fallback'
    contract carried over from the original Copilot brief."""

    async def test_non_json_text_returns_none(self):
        with patch("app.services.llm_service.settings") as mock_settings:
            _configured_settings(mock_settings)
            with patch("httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.post.return_value = _mock_llm_response("Sure! Vendor risk is high because...")
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                MockClient.return_value = mock_client

                result = await understand("Which vendors are riskiest?")
        assert result is None

    async def test_json_missing_required_field_returns_none(self):
        broken = json.dumps({"metrics_needed": ["vendor_risk"]})  # no question_type
        with patch("app.services.llm_service.settings") as mock_settings:
            _configured_settings(mock_settings)
            with patch("httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.post.return_value = _mock_llm_response(broken)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                MockClient.return_value = mock_client

                result = await understand("Which vendors are riskiest?")
        assert result is None

    async def test_invalid_question_type_enum_returns_none(self):
        broken = json.dumps({"question_type": "vibes_based", "metrics_needed": [], "row_query": None})
        with patch("app.services.llm_service.settings") as mock_settings:
            _configured_settings(mock_settings)
            with patch("httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.post.return_value = _mock_llm_response(broken)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                MockClient.return_value = mock_client

                result = await understand("Which vendors are riskiest?")
        assert result is None

    async def test_response_wrapped_in_markdown_fence_still_parses(self):
        """LLMs frequently wrap JSON in ```json fences despite explicit
        instructions not to — this must not be treated as malformed."""
        fenced = f"```json\n{VALID_METRIC_PLAN}\n```"
        with patch("app.services.llm_service.settings") as mock_settings:
            _configured_settings(mock_settings)
            with patch("httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.post.return_value = _mock_llm_response(fenced)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                MockClient.return_value = mock_client

                result = await understand("Which vendors are riskiest?")
        assert result is not None
        assert result.metrics_needed == ["vendor_risk"]

    async def test_timeout_returns_none(self):
        import httpx

        with patch("app.services.llm_service.settings") as mock_settings:
            _configured_settings(mock_settings)
            with patch("httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.post.side_effect = httpx.TimeoutException("timed out")
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                MockClient.return_value = mock_client

                result = await understand("Which vendors are riskiest?")
        assert result is None


class TestUnderstandDefenseInDepth:
    async def test_a_plan_naming_a_fake_table_still_parses_here(self):
        """understand() only validates JSON SHAPE (Pydantic), not whether
        table/column names are real — that is query_compiler's job,
        checked independently against schema_graph. This test documents
        and locks in that division of responsibility: two layers, not
        one, so a bug in either doesn't silently remove the other's
        protection."""
        plan_with_fake_table = json.dumps({
            "question_type": "list",
            "metrics_needed": [],
            "row_query": {
                "base_table": "totally_made_up_table",
                "joins": [], "filters": [], "select_columns": None,
                "order_by_table": None, "order_by_column": None,
                "order_desc": False, "limit": 25,
            },
            "reasoning_notes": "x", "insufficient_data_reason": None,
            "missing_data": None, "available_data": None,
        })
        with patch("app.services.llm_service.settings") as mock_settings:
            _configured_settings(mock_settings)
            with patch("httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.post.return_value = _mock_llm_response(plan_with_fake_table)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                MockClient.return_value = mock_client

                result = await understand("anything")
        # Pydantic has no opinion on whether "totally_made_up_table" is
        # real, so this SUCCEEDS here...
        assert result is not None
        assert result.row_query.base_table == "totally_made_up_table"
        # ...and it is query_compiler.validate_and_compile, exercised in
        # test_grc_engine_query.py, that is the actual enforcement point.
        from app.services.grc_engine.query_compiler import QueryValidationError, validate_and_compile
        with pytest.raises(QueryValidationError):
            validate_and_compile(result.row_query)


class TestSystemPromptIntegrity:
    def test_prompt_contains_real_schema_facts(self):
        prompt = _build_system_prompt()
        assert "vendors" in prompt
        assert "island" in prompt.lower()
        assert "iam_records" in prompt

    def test_prompt_forbids_inventing_joins(self):
        prompt = _build_system_prompt()
        assert "Never invent" in prompt or "never invent" in prompt.lower()

    def test_prompt_lists_metric_namespaces(self):
        prompt = _build_system_prompt()
        assert "vendor_risk" in prompt
        assert "trust_score" in prompt

    def test_prompt_never_leaks_raw_row_data_instruction(self):
        prompt = _build_system_prompt()
        assert "never see actual database rows" in prompt.lower() or "you only choose" in prompt.lower()


class TestStripFences:
    def test_plain_json_untouched(self):
        assert _strip_fences('{"a": 1}') == '{"a": 1}'

    def test_json_fence_stripped(self):
        assert _strip_fences('```json\n{"a": 1}\n```') == '{"a": 1}'

    def test_bare_fence_stripped(self):
        assert _strip_fences('```\n{"a": 1}\n```') == '{"a": 1}'


class TestConversationContext:
    async def test_context_reaches_the_user_message(self):
        captured = {}

        async def capture_post(url, headers=None, json=None):
            captured["payload"] = json
            return _mock_llm_response(VALID_METRIC_PLAN)

        with patch("app.services.llm_service.settings") as mock_settings:
            _configured_settings(mock_settings)
            with patch("httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.post.side_effect = capture_post
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                MockClient.return_value = mock_client

                await understand(
                    "Which one is the worst?",
                    conversation_context="Previous: 'Which vendors are high risk?' -> 5 vendors, worst is Trident Partners (VEN6328).",
                )

        user_msg = captured["payload"]["messages"][1]["content"]
        assert "Trident Partners" in user_msg
        assert "Which one is the worst?" in user_msg
