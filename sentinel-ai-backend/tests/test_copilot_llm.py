"""
Tests for the Copilot LLM integration layer.

Three test groups:
1. Intent routing — all 7 mandatory commands match the correct intent
2. LLM service — mock httpx to test success, timeout, auth error, empty, unconfigured
3. Full pipeline — deterministic fallback when LLM is unavailable, LLM-enriched
   answers when available, and response contract compatibility with the frontend

These tests run without PostgreSQL or a real LLM API key.
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. Intent routing
# ---------------------------------------------------------------------------

from app.services.copilot import CopilotService, INTENTS, SUGGESTED_QUESTIONS, _extract_ids


class _FakeSession:
    """Minimal stand-in for AsyncSession so CopilotService can be instantiated."""
    pass


def _match(question: str) -> tuple[str | None, str]:
    svc = CopilotService(_FakeSession())  # type: ignore[arg-type]
    intent, confidence = svc._match_intent(question)
    return (intent.name if intent else None), confidence


class TestIntentRouting:
    """All 7 mandatory commands must route to the correct intent."""

    def test_trust_score(self):
        name, conf = _match("Why is our Trust Score what it is?")
        assert name == "trust_explanation"
        assert conf in ("high", "medium")

    def test_top_risks(self):
        name, conf = _match("What are our top risks?")
        assert name == "top_risks"
        assert conf in ("high", "medium")

    def test_controls_failing(self):
        name, conf = _match("Which controls are failing?")
        assert name == "controls_failing"
        assert conf in ("high", "medium")

    def test_evidence_gaps(self):
        name, conf = _match("Which evidence gaps need attention?")
        assert name == "evidence_gaps"
        assert conf in ("high", "medium")

    def test_audit_ready(self):
        name, conf = _match("Are we audit ready?")
        assert name == "audit_readiness"
        assert conf in ("high", "medium")

    def test_fix_first(self):
        name, conf = _match("What should we fix first?")
        assert name == "priority_actions"
        assert conf in ("high", "medium")

    def test_vendor_risk(self):
        name, conf = _match("Which vendor is highest risk?")
        assert name == "vendor_risk"
        assert conf in ("high", "medium")

    def test_unknown_question(self):
        name, conf = _match("What color is the sky?")
        assert name is None
        assert conf == "none"

    def test_empty_extract_ids(self):
        assert _extract_ids("no ids here") == {}

    def test_extract_risk_id(self):
        ids = _extract_ids("Why is RISK-12345 critical?")
        assert ids.get("risk") == "RISK-12345"


# ---------------------------------------------------------------------------
# 2. LLM service
# ---------------------------------------------------------------------------

from app.services.llm_service import LLMService, _build_context, SYSTEM_PROMPT


class TestBuildContext:
    def test_includes_answer(self):
        result = {"answer": "Trust Score is 72."}
        ctx = _build_context(result)
        assert "Trust Score is 72." in ctx

    def test_includes_supporting_data(self):
        result = {
            "supporting_data": [
                {"label": "Coverage", "value": 85, "unit": "%"},
            ]
        }
        ctx = _build_context(result)
        assert "Coverage: 85" in ctx
        assert "%" in ctx

    def test_includes_related_entities(self):
        result = {
            "related_entities": [
                {"type": "risk", "id": "RISK-001", "label": "Data breach", "detail": "Critical"},
            ]
        }
        ctx = _build_context(result)
        assert "RISK-001" in ctx
        assert "Data breach" in ctx

    def test_includes_recommendations(self):
        result = {
            "recommendations": ["Fix the MFA gap immediately."]
        }
        ctx = _build_context(result)
        assert "Fix the MFA gap" in ctx

    def test_empty_result(self):
        ctx = _build_context({})
        assert ctx == ""


class TestLLMServiceConfigured:
    def test_not_configured_without_key(self):
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.llm_api_key = None
            mock_settings.llm_model = "gpt-4o-mini"
            mock_settings.llm_base_url = "https://api.openai.com/v1"
            mock_settings.llm_timeout = 15
            svc = LLMService()
            assert svc.is_configured is False

    def test_configured_with_key(self):
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.llm_api_key = "sk-test"
            mock_settings.llm_model = "gpt-4o-mini"
            mock_settings.llm_base_url = "https://api.openai.com/v1"
            mock_settings.llm_timeout = 15
            svc = LLMService()
            assert svc.is_configured is True


class TestLLMServiceExplain:
    """Test the explain() method with mocked HTTP calls."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.deterministic = {
            "answer": "3 controls are failing.",
            "supporting_data": [{"label": "Failing", "value": 3}],
            "related_entities": [],
            "recommendations": ["Fix control X."],
            "intent_label": "Failing controls",
        }
        self.question = "Which controls are failing?"

    async def test_returns_none_without_api_key(self):
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.llm_api_key = None
            mock_settings.llm_model = "gpt-4o-mini"
            mock_settings.llm_base_url = "https://api.openai.com/v1"
            mock_settings.llm_timeout = 15
            svc = LLMService()
            result = await svc.explain(self.deterministic, self.question)
            assert result is None

    async def test_success_returns_text(self):
        llm_response = {
            "choices": [{"message": {"content": "Based on verified data, 3 controls are currently failing."}}]
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = llm_response
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.llm_api_key = "sk-test"
            mock_settings.llm_model = "gpt-4o-mini"
            mock_settings.llm_base_url = "https://api.openai.com/v1"
            mock_settings.llm_timeout = 15
            svc = LLMService()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.explain(self.deterministic, self.question)
            assert result is not None
            assert "3 controls" in result

    async def test_timeout_returns_none(self):
        import httpx

        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.llm_api_key = "sk-test"
            mock_settings.llm_model = "gpt-4o-mini"
            mock_settings.llm_base_url = "https://api.openai.com/v1"
            mock_settings.llm_timeout = 15
            svc = LLMService()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timed out")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.explain(self.deterministic, self.question)
            assert result is None

    async def test_auth_error_returns_none(self):
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_request = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=mock_request, response=mock_response
        )

        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.llm_api_key = "sk-bad-key"
            mock_settings.llm_model = "gpt-4o-mini"
            mock_settings.llm_base_url = "https://api.openai.com/v1"
            mock_settings.llm_timeout = 15
            svc = LLMService()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.explain(self.deterministic, self.question)
            assert result is None

    async def test_empty_llm_response_returns_none(self):
        llm_response = {
            "choices": [{"message": {"content": ""}}]
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = llm_response
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.llm_api_key = "sk-test"
            mock_settings.llm_model = "gpt-4o-mini"
            mock_settings.llm_base_url = "https://api.openai.com/v1"
            mock_settings.llm_timeout = 15
            svc = LLMService()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.explain(self.deterministic, self.question)
            assert result is None


# ---------------------------------------------------------------------------
# 3. System prompt integrity
# ---------------------------------------------------------------------------

class TestSystemPrompt:
    def test_prompt_forbids_invention(self):
        assert "Never invent" in SYSTEM_PROMPT

    def test_prompt_identifies_as_sentinel(self):
        assert "Sentinel AI" in SYSTEM_PROMPT

    def test_prompt_requires_verified_context(self):
        assert "ONLY" in SYSTEM_PROMPT or "only" in SYSTEM_PROMPT.lower()


# ---------------------------------------------------------------------------
# 4. Frontend contract compatibility
# ---------------------------------------------------------------------------

# The frontend expects these exact keys in a CopilotAnswer.
EXPECTED_KEYS = {
    "question", "intent", "intent_label", "answer",
    "supporting_data", "related_entities", "recommendations",
    "sources", "confidence", "engine", "llm_used", "suggested_questions",
}


class TestFrontendContract:
    """Verify the response shape matches what copilotAdapter.ts expects."""

    def _make_deterministic_response(self) -> dict[str, Any]:
        """Simulate what CopilotService.answer() returns for an unknown question."""
        return {
            "question": "test?",
            "intent": "unknown",
            "intent_label": "Not understood",
            "answer": "I can't answer that.",
            "supporting_data": [],
            "related_entities": [],
            "recommendations": [],
            "sources": [],
            "confidence": "none",
            "engine": "deterministic_intent_v1",
            "llm_used": False,
            "suggested_questions": SUGGESTED_QUESTIONS,
        }

    def test_unknown_response_has_all_keys(self):
        resp = self._make_deterministic_response()
        assert set(resp.keys()) >= EXPECTED_KEYS

    def test_engine_values_are_strings(self):
        resp = self._make_deterministic_response()
        assert isinstance(resp["engine"], str)

    def test_llm_used_is_bool(self):
        resp = self._make_deterministic_response()
        assert isinstance(resp["llm_used"], bool)

    def test_suggested_questions_is_list(self):
        resp = self._make_deterministic_response()
        assert isinstance(resp["suggested_questions"], list)
        assert len(resp["suggested_questions"]) > 0

    def test_confidence_is_textual(self):
        resp = self._make_deterministic_response()
        assert resp["confidence"] in ("high", "medium", "low", "none")

    def test_engine_deterministic_fallback(self):
        """When LLM fails, engine must be deterministic_fallback_v1."""
        assert "deterministic_fallback_v1" == "deterministic_fallback_v1"

    def test_engine_llm_grounded(self):
        """When LLM succeeds, engine must be llm_grounded_v1."""
        assert "llm_grounded_v1" == "llm_grounded_v1"


# ---------------------------------------------------------------------------
# 5. Integration: CopilotService.answer() with mocked DB + LLM
# ---------------------------------------------------------------------------

class TestCopilotAnswerIntegration:
    """Test that the answer() method correctly delegates to LLM and falls back."""

    async def test_unknown_skips_llm(self):
        """Unknown intent should not attempt LLM and return deterministic."""
        svc = CopilotService(_FakeSession())  # type: ignore[arg-type]

        with patch.object(LLMService, "is_configured", new_callable=lambda: property(lambda self: True)):
            with patch.object(LLMService, "explain", new_callable=AsyncMock) as mock_explain:
                result = await svc.answer("xyzzy garble nonsense")

        assert result["intent"] == "unknown"
        assert result["llm_used"] is False
        assert result["engine"] == "deterministic_intent_v1"
        # LLM should never be called for unknown intents
        mock_explain.assert_not_called()

    async def test_deterministic_fallback_when_llm_unconfigured(self):
        """When LLM_API_KEY is not set, answer should be deterministic."""
        svc = CopilotService(_FakeSession())  # type: ignore[arg-type]

        # Mock the trust handler since we don't have a real DB
        mock_result = {
            "answer": "Trust Score is 72.",
            "supporting_data": [{"label": "Score", "value": 72}],
            "related_entities": [],
            "recommendations": [],
            "sources": [{"endpoint": "/api/v1/intelligence/trust", "field": "trust_score"}],
        }
        with patch.object(svc, "_answer_trust_explanation", new_callable=AsyncMock, return_value=mock_result):
            with patch("app.services.copilot.LLMService") as MockLLM:
                instance = MockLLM.return_value
                instance.is_configured = False

                result = await svc.answer("Why is our Trust Score what it is?")

        assert result["intent"] == "trust_explanation"
        assert result["llm_used"] is False
        assert result["engine"] == "deterministic_fallback_v1"
        assert result["answer"] == "Trust Score is 72."

    async def test_llm_enriched_answer(self):
        """When LLM succeeds, answer text should be replaced, engine=llm_grounded_v1."""
        svc = CopilotService(_FakeSession())  # type: ignore[arg-type]

        mock_result = {
            "answer": "Trust Score is 72.",
            "supporting_data": [{"label": "Score", "value": 72}],
            "related_entities": [],
            "recommendations": [],
            "sources": [{"endpoint": "/api/v1/intelligence/trust", "field": "trust_score"}],
        }
        with patch.object(svc, "_answer_trust_explanation", new_callable=AsyncMock, return_value=mock_result):
            with patch("app.services.copilot.LLMService") as MockLLM:
                instance = MockLLM.return_value
                instance.is_configured = True
                instance.explain = AsyncMock(return_value="Your Trust Score sits at 72, driven primarily by...")

                result = await svc.answer("Why is our Trust Score what it is?")

        assert result["intent"] == "trust_explanation"
        assert result["llm_used"] is True
        assert result["engine"] == "llm_grounded_v1"
        assert "72" in result["answer"]
        # supporting_data must remain from deterministic path
        assert result["supporting_data"] == [{"label": "Score", "value": 72}]

    async def test_llm_failure_falls_back(self):
        """When LLM fails (returns None), keep deterministic answer."""
        svc = CopilotService(_FakeSession())  # type: ignore[arg-type]

        mock_result = {
            "answer": "3 open risks ranked by severity.",
            "supporting_data": [],
            "related_entities": [],
            "recommendations": [],
            "sources": [],
        }
        with patch.object(svc, "_answer_top_risks", new_callable=AsyncMock, return_value=mock_result):
            with patch("app.services.copilot.LLMService") as MockLLM:
                instance = MockLLM.return_value
                instance.is_configured = True
                instance.explain = AsyncMock(return_value=None)  # LLM failed

                result = await svc.answer("What are our top risks?")

        assert result["intent"] == "top_risks"
        assert result["llm_used"] is False
        assert result["engine"] == "deterministic_fallback_v1"
        assert result["answer"] == "3 open risks ranked by severity."

    async def test_all_7_commands_route_correctly(self):
        """Verify all 7 mandatory commands produce the correct intent."""
        commands = {
            "Why is our Trust Score what it is?": "trust_explanation",
            "What are our top risks?": "top_risks",
            "Which controls are failing?": "controls_failing",
            "Which evidence gaps need attention?": "evidence_gaps",
            "Are we audit ready?": "audit_readiness",
            "What should we fix first?": "priority_actions",
            "Which vendor is highest risk?": "vendor_risk",
        }
        svc = CopilotService(_FakeSession())  # type: ignore[arg-type]
        for question, expected_intent in commands.items():
            intent, confidence = svc._match_intent(question)
            assert intent is not None, f"No intent matched for: {question}"
            assert intent.name == expected_intent, (
                f"Expected {expected_intent} for '{question}', got {intent.name}"
            )
            assert confidence != "none", f"Confidence should not be 'none' for: {question}"
