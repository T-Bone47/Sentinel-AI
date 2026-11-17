"""NVIDIA NIM provider adapter for Sentinel AI's Copilot.

This module is the *only* place that knows about NVIDIA's HTTP contract.
Everything else in the application talks to ``LLMService`` (see
``app.services.llm_service``), which delegates here.  Keeping the
provider-specific code isolated means the Copilot orchestration, intent
routing, database access and trust-score calculations never need to change
when the model or endpoint changes.

The adapter speaks the OpenAI-compatible chat-completions contract that
NVIDIA NIM exposes at ``https://integrate.api.nvidia.com/v1``.  It is
deliberately read-only: it never executes tools, never touches the
database, and never mutates application state.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger("sentinel.nvidia")

# Sensible upper bounds so a misconfigured client cannot ask for an
# unbounded amount of work from the provider.
_MAX_INPUT_CHARS = 12000
_MAX_OUTPUT_TOKENS_CEILING = 2048
_DEFAULT_TIMEOUT = 30
_DEFAULT_MAX_TOKENS = 800
_DEFAULT_TEMPERATURE = 0.2

# HTTP statuses that are worth a bounded retry.  401/403/404 are never
# retried: they will not become successes by repeating the request.
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 1


class NvidiaProviderError(Exception):
    """Raised internally for non-retryable provider failures.

    The adapter never lets this escape to callers: ``complete()`` converts
    every failure into ``None`` so the Copilot can fall back to its
    deterministic answer.  The class exists so tests can assert on the
    *category* of failure when they want to.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class NvidiaProvider:
    """Thin, async, read-only wrapper around NVIDIA NIM chat completions."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        model: str,
        timeout_seconds: int,
        max_tokens: int,
        temperature: float,
    ) -> None:
        self._api_key = api_key.strip() if isinstance(api_key, str) and api_key.strip() else None
        self._base_url = (base_url or "").rstrip("/")
        self._model = model
        self._timeout = max(1, int(timeout_seconds or _DEFAULT_TIMEOUT))
        self._max_tokens = min(
            max(1, int(max_tokens or _DEFAULT_MAX_TOKENS)),
            _MAX_OUTPUT_TOKENS_CEILING,
        )
        self._temperature = float(temperature if temperature is not None else _DEFAULT_TEMPERATURE)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key) and bool(self._base_url) and bool(self._model)

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str | None:
        """Run one chat completion.  Returns text or ``None`` on any
        failure (no key, timeout, HTTP error, empty/malformed response).
        Never raises."""
        if not self.is_configured:
            logger.debug("NVIDIA provider not configured - skipping call")
            return None

        # Guard the prompt size so we never ship an enormous payload to the
        # provider (or pay for tokens we did not intend to send).
        if len(system_prompt) + len(user_message) > _MAX_INPUT_CHARS:
            logger.warning(
                "NVIDIA request context too large (%d chars) - truncating",
                len(system_prompt) + len(user_message),
            )
            user_message = user_message[: _MAX_INPUT_CHARS - len(system_prompt)]

        temp = self._temperature if temperature is None else float(temperature)
        tokens = self._max_tokens if max_tokens is None else min(
            max(1, int(max_tokens)), _MAX_OUTPUT_TOKENS_CEILING
        )

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temp,
            "max_tokens": tokens,
        }

        # GLM models default to a large reasoning budget on this endpoint,
        # which makes them very slow and can consume the whole token budget
        # before any answer text is produced.  For the Copilot we want a
        # concise grounded answer, so request a low reasoning budget and ask
        # the template to clear the (hidden) thinking trace from the reply.
        model_lower = (self._model or "").lower()
        if "glm" in model_lower:
            payload["reasoning_effort"] = "low"
            payload["chat_template_kwargs"] = {"clear_thinking": True}

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(_MAX_RETRIES + 1):
                try:
                    response = await client.post(url, headers=headers, json=payload)
                except httpx.TimeoutException:
                    if attempt < _MAX_RETRIES:
                        logger.warning(
                            "NVIDIA request timed out (attempt %d) - retrying", attempt + 1
                        )
                        continue
                    logger.warning("NVIDIA request timed out after %ds", self._timeout)
                    return None
                except httpx.RequestError as exc:
                    # Network-level failure (DNS, connection refused, ...).
                    if attempt < _MAX_RETRIES:
                        logger.warning(
                            "NVIDIA network error (attempt %d): %s", attempt + 1, type(exc).__name__
                        )
                        await asyncio.sleep(1)
                        continue
                    logger.warning("NVIDIA network error: %s", type(exc).__name__)
                    return None

                if response.status_code in _RETRYABLE_STATUSES and attempt < _MAX_RETRIES:
                    wait = 2 ** attempt
                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait = min(int(retry_after), 10)
                    logger.warning(
                        "NVIDIA HTTP %d (attempt %d) - retrying in %ds",
                        response.status_code,
                        attempt + 1,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                if response.status_code >= 400:
                    # Log status + a short, secret-free excerpt only.
                    logger.warning(
                        "NVIDIA HTTP %d: %s",
                        response.status_code,
                        response.text[:200],
                    )
                    return None

                try:
                    body = response.json()
                except ValueError:
                    logger.warning("NVIDIA returned non-JSON body")
                    return None

                content = (
                    (body.get("choices") or [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                if not isinstance(content, str) or not content.strip():
                    logger.warning("NVIDIA returned empty content - falling back")
                    return None

                # Some builds return a list of content parts instead of a
                # string; normalise to plain text.
                if isinstance(content, list):
                    content = " ".join(
                        part.get("text", "") if isinstance(part, dict) else str(part)
                        for part in content
                    ).strip()
                    if not content:
                        return None

                logger.info("NVIDIA completion generated (%d chars)", len(content))
                return content.strip()

        return None
