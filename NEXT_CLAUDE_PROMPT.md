You are continuing **Sentinel AI**. Two things now exist side by side:

1. The original **Compliance Copilot** (`CopilotService`, 12 fixed
   intents) — complete, tested, live-verified, still wired to
   `POST /copilot/query` and the frontend `/copilot` page. Unchanged this
   session.
2. A new **general-purpose GRC reasoning engine**
   (`app/services/grc_engine/`) that answers arbitrary GRC questions, not
   just the fixed 12 — wired to a NEW, additive `POST /api/v1/ai/query`.
   Falls back to (1) whenever it can't understand a question.

**Read `HANDOFF.md`'s last section first** — it has the full story,
including exactly what was and wasn't verified, and why. The one-sentence
version: everything downstream of "the LLM produced a correct query plan"
is proven against real data (245 passed, 1 skipped, 0 failed, including a
42-question battery); whether a real LLM reliably produces that correct
plan from raw question text could not be tested in that sandbox (no
`LLM_API_KEY`, no network path to a provider) and is unverified.

## Read first

- `HANDOFF.md` — both new sections since your last read: the frontend
  E2E-testing session (a real, now-fixed bug in failure-state precedence)
  and the general engine session (this one).
- `IMPLEMENTATION_STATUS.md` — new "General-purpose GRC reasoning engine"
  section; check every unchecked box before assuming this is finished.

## Bring it up

Same as before (`bash scripts/setup_postgres.sh` — the daemon does not
survive a sandbox restart, the data does), plus:

```bash
python -m pytest tests/test_grc_engine_*.py    # expect 103 passed
python -m pytest                                # expect 245 passed, 1 skipped

curl -X POST http://localhost:8000/api/v1/ai/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "Which vendors have contracts expiring soon?"}'
  # no LLM_API_KEY -> falls back to the old Copilot; understand() always
  # returns None without a key, so this is EXPECTED, not broken
```

## First priority: verify the one thing that couldn't be verified

Set a real `LLM_API_KEY` (+ `LLM_MODEL`/`LLM_BASE_URL` if not OpenAI's
default). Ask `/api/v1/ai/query` a genuinely novel question — not one of
the 12 fixed intents, not one of the 42 battery questions in
`tests/test_grc_engine_question_battery.py` (those prove the pipeline, so
testing them again proves nothing new about the LLM itself). Check:

- Does `understanding_service.understand()` return a plan at all, or does
  it silently fall back (check the server log for "did not return valid
  JSON" or "failed schema validation" warnings — `LLMService._complete()`
  swallows every failure by design, so the reason never reaches the HTTP
  response, only the log)?
- Is the plan's `row_query`/`metrics_needed` actually a reasonable read of
  the question, or is the model inventing a join that
  `schema_graph.describe_for_llm()` didn't offer? (query_compiler will
  reject a fabricated one — check it's landing on `insufficient_data_v1`
  for the RIGHT reason, not because a real, valid plan got rejected by a
  bug.)
- Does the final `answer` read as real prose, not leaked JSON (the exact
  bug this session's fake-LLM test caught and had to fix in the *test
  harness* — make sure it isn't also a bug in the real system prompt
  distinction, which it shouldn't be, but hasn't been checked against a
  real model that might behave differently from either the mocks or the
  fake server).

If this works well: consider whether `/copilot/query` should start
delegating through the general engine (a bigger, separate decision this
session deliberately did not make unilaterally — see HANDOFF.md's
reasoning). If it doesn't work well: the system prompt in
`understanding_service._SYSTEM_PROMPT_TEMPLATE` is the thing to iterate on,
not the compiler or the schema graph, which are already proven correct
against real data.

## Hard rules — everything from before still applies, plus:

- **The schema graph is ground truth, not a suggestion.** If you add a
  table/column/relationship to `schema_graph.py`, re-verify it against
  `information_schema` the same way this session did — don't copy a
  relationship from a docstring or a variable name. `vendors` and
  `reports` really do have zero foreign keys; don't "fix" that by adding
  one that doesn't exist in the actual database.
- **Do not let the LLM's JSON become a second, laxer validation path.**
  Every table/column/join name must still be checked against
  `schema_graph.TABLES` in `query_compiler.py` regardless of what
  `ReasoningPlan`'s Pydantic validation already allowed — that's the whole
  point of the two-layer design (see `TestUnderstandDefenseInDepth` in
  `tests/test_grc_engine_understanding.py`).
- **Don't add subquery/anti-join/custom-ordering support casually.** It's
  a real, useful next step (see HANDOFF.md's "known limitations") but
  changes the compiler's safety argument — a `NOT EXISTS` subquery is a
  second surface to validate — so give it the same care this session gave
  the rest of the DSL, not a quick bolt-on.
- **142 (Copilot) + 61 (general engine) = 203 baseline non-battery tests,
  245 total. Don't weaken or delete any to make a change pass.**

## Do these, in order

1. **Verify the live LLM understanding quality** (above) — highest value,
   the one thing genuinely unverified.
2. Decide, with the person, whether `/copilot/query` should migrate to the
   general engine or stay as-is.
3. If the DSL's row-list gaps (no evidence, custom severity ordering)
   matter for real usage, extend `query_dsl.py`/`query_compiler.py`
   deliberately, with the same validate-independently-at-every-layer
   discipline, and its own test pass.
4. Authentication on `intelligence_router.py` (pre-existing gap, not new).
5. Remediation Intelligence (Priority 4), Continuous Monitoring
   (Priority 5) — unchanged from before, still not started.
6. Optional, not urgent: 57 pre-existing `tsc --noEmit` errors in unrelated
   pages (`CommandCenter.tsx`, `CloudAssets.tsx`, etc.) — untouched again
   this session, still out of scope.

## Checkpoint discipline

Still true, more so now: this session built a genuinely large amount in
one sitting. Checkpoint at the halfway point of any substantial session,
not just at the end — exclude `node_modules`, `dist`, `.env`, `__pycache__`,
`.pytest_cache`, `*.egg-info`, and verify by extracting to a clean
directory and re-running the suite, not by assuming yesterday's numbers
still hold.
