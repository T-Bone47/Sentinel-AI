# NVIDIA NIM grounded Copilot

## Overview

Sentinel AI's Copilot is a hybrid assistant:

1. Deterministic intent routing and database retrieval remain authoritative.
2. When NVIDIA NIM is configured, the retrieved verified context is sent to
   NVIDIA for a natural-language explanation.
3. Structured fields (`supporting_data`, `related_entities`,
   `recommendations`, `sources`) always come from the deterministic path.
4. The LLM may only rewrite the prose `answer` field and may not invent IDs.

## Configuration

Copy the supplied template `sentinel-ai-nvidia.env` into the backend directory
as `.env` (or merge its values into your existing `.env`). Required keys:

```
NVIDIA_API_KEY=
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=z-ai/glm-5.3-flash
NVIDIA_TIMEOUT_SECONDS=120
NVIDIA_MAX_TOKENS=1200
NVIDIA_TEMPERATURE=0.2
COPILOT_LLM_ENABLED=true
COPILOT_LLM_PROVIDER=nvidia
COPILOT_LLM_FALLBACK_ENABLED=true
```

Keep `.env` server-side only. It is git-ignored.

If `NVIDIA_API_KEY` is empty or `COPILOT_LLM_ENABLED=false`, the Copilot
runs in deterministic mode and never calls the provider.

## Model selection

The configured model is `z-ai/glm-5.3-flash` (NVIDIA NIM). It supports
instruction following, structured output, reasoning and tool calling. The
adapter sends `reasoning_effort=low` and `clear_thinking=true` for GLM
models to keep latency and token usage bounded.

The model ID is fully configurable via `NVIDIA_MODEL`; no other code path
hard-codes it.

## Request flow

```
POST /api/v1/copilot/query
  -> intent routing (CopilotService._match_intent)
  -> authorised DB retrieval via existing intelligence services
  -> deterministic answer + supporting records
  -> NVIDIA NIM prose rewrite (optional)
  -> ID validation against verified records
  -> response with engine/llm_used
```

## Grounding and source validation

- Numerical values and record IDs originate from PostgreSQL/SQLite via the
  existing services.
- The LLM receives only a compact, bounded context built from the
  deterministic result.
- Any identifier emitted by the LLM that was not present in the verified
  result causes the LLM text to be discarded in favour of the deterministic
  answer.
- Framework mapping is never described as certification.

## Security

- The API key is loaded server-side from `.env` and is never exposed to the
  frontend.
- User/tenant scope comes from the authenticated server context.
- Retrieved records are treated as untrusted data in the prompt.
- The integration is read-only: no mutations are performed.
- Prompts and retrieved records are not logged by default; only safe
  operational metadata is logged.

## Tests

Run:

```
python -m pytest tests/test_copilot_llm.py
python -m pytest tests/test_intelligence.py
```

Unit tests mock the provider transport and do not require a live key.

## Live smoke test

With a valid key configured:

```
python -m uvicorn app.main:app --reload --port 8000
curl -X POST http://localhost:8000/api/v1/copilot/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Why is our Trust Score what it is?"}'
```

A successful response has `"engine": "llm_grounded_v1"` and
`"llm_used": true`.

## Limitations

- NVIDIA NIM trial endpoints may be slow or rate-limited; timeouts are
  handled with bounded retries.
- The model may still produce plausible but unverified prose; the
  application mitigates this by preserving authoritative structured fields
  and validating cited IDs.
- Do not claim the provider never stores submitted prompts unless its
  official terms establish that.