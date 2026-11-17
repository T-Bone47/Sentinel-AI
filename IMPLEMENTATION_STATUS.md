# Implementation Status

> **Note (2026-11-18):** this tracker predates the 2026-11-13 review.
> - "Real data" here means the repository's 15 CSV datasets. They are
>   fictional demo data, generated with ChatGPT (`docs/DATA_PROVENANCE.md`).
> - Current status is in `docs/PROGRESS.md`.

Honest tracker. If it's not marked DONE, treat it as not existing.
Updated at the end of session 2 (the Review-1 build).

**Headline: Phase 1 complete. Phase 2 (Trust, Risk) complete. Phase 2B (Evidence, Policy, Copilot) complete on the backend; frontend UI pending.**

---

## PHASE 1 — Backend Foundation + Real Dataset Integration

### Step 1 — Dataset Audit
- [x] **DONE** (session 1) — All 15 CSVs profiled. Output: `docs/profiling/profile_report.txt`.
- [x] **DONE** (session 1) — Data-quality scan. Zero issues found.

### Step 2 — Relationship Discovery
- [x] **DONE** (session 1) — Empirical value-overlap check. Output: `docs/profiling/relationships.txt`.
- [x] **DONE** (session 2) — Re-confirmed against the live database: zero orphans
      across all 14 verified FKs (`test_relationships_resolve_with_no_orphans`).

### Step 3 — Database Implementation
- [x] **DONE** — All 18 SQLAlchemy models (unchanged this session; they were correct).
- [x] **DONE** — Alembic revision `f6fd9ee3f6ac` generated and applied against a
      **real PostgreSQL 16.14**. 18 tables + `alembic_version` verified present.
- [ ] **TODO** — Indexes reviewed under real query patterns. Current indexes are
      first-pass choices on FK/filter columns; they have not been load-tested.
      Nothing is slow at 14,400 rows, so this is not urgent.

### Step 4 — Data Ingestion Engine
- [x] **DONE** — `app/ingestion/`: generic `DatasetIngestor`, declarative
      per-dataset configs in `configs/registry.py`, CLI in `run.py`.
- [x] **DONE** — Idempotent upsert via `INSERT ... ON CONFLICT (pk) DO UPDATE`,
      with inserted-vs-updated measured through Postgres `xmax` rather than guessed.
- [x] **DONE** — All 15 datasets loaded: **14,400 rows, 0 errors, 0 skipped**.
- [x] **DONE** — Re-run verified: 0 inserted, 14,400 updated, counts unchanged.
- [x] **DONE** — Lineage written to `ingestion_jobs` / `ingestion_logs`.

### Step 5 — Data Quality (ingestion-time)
- [x] **DONE** — Type coercion + required-field validation per column; rows that
      fail are logged and skipped, never silently dropped.
- [x] **DONE** — FK-aware loading: missing parent nulls a nullable FK, skips a
      non-nullable one, and warns-but-keeps for advisory links
      (`employees.device_id`).
- [x] **DONE** — In-file duplicate-PK handling (last row wins, earlier counted skipped).

### Step 6 — Backend Foundation
- [x] **DONE** — App factory, pydantic-settings config, CORS, `/api/v1/health`.
- [x] **DONE** — Async SQLAlchemy engine/session.
- [x] **DONE** — Router package structure built out under `app/api/v1/routers/`.
- [x] **DONE** — Exception handlers now wrap HTTP + validation errors in the same
      `{data, error}` envelope as successful responses.
- [ ] **TODO** — Structured JSON logging beyond `logging.basicConfig`. Not needed
      for Review 1.

### Step 7 — Authentication
- [x] **DONE** — bcrypt password hashing (`app/core/security.py`).
- [x] **DONE** — `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`,
      `GET /api/v1/auth/me`.
- [x] **DONE** — `get_current_user` dependency + `require_roles(...)` RBAC guard.
- [x] **DONE** — 5 demo users seeded, one per role (`scripts/seed_users.py`).
- [ ] **TODO** — `require_roles(...)` is not yet *applied* to any data endpoint.
      Deliberate: the Review-1 demo needs endpoints reachable without a login.
      One-line change per route when the frontend has auth.

### Step 8 — API Layer
- [x] **DONE** — 38 paths. 15 resource lists, 15 detail endpoints (7 of them
      enriched with real FK joins), 4 auth, health, dashboard, 2 framework,
      organization graph.
- [x] **DONE** — Pagination, search, filtering, sorting on every list endpoint.
- [x] **DONE** — Range filters on audit logs (`date_from`, `date_to`, `min_risk_score`).
- [ ] **TODO** — POST/PATCH/DELETE. Read-only was sufficient for Review 1.

### Step 9 — Dashboard API
- [x] **DONE** — `GET /api/v1/dashboard`, every figure a live aggregate query.
- [x] **DONE** — Trust Score + Audit Readiness as **transparent deterministic**
      scores that publish their own weights, components and formula, labelled
      `engine: "deterministic_phase1"`. `?scores=off` returns explicit nulls.
      This is not an AI score and does not pretend to be. See HANDOFF.md §12.
- [x] **DONE** — Framework rollup aggregated live (there is no frameworks table).

### Step 10 — Frontend Contract
- [x] **DONE** — Every frontend tab except *Sentinel AI* and *Settings* has a
      backing endpoint. Response shapes documented in HANDOFF.md §9 and live at
      `/api/docs`.
- [ ] **N/A** — No frontend code written, correctly, per instructions.

### Step 11 — Testing
- [x] **DONE** — 61 tests, all passing. Covers every required critical test
      including the re-ingestion duplicate check.
- [ ] **TODO** — No unit tests for individual services in isolation. The suite is
      deliberately integration-first: it asserts real data reaches the API, which
      is what the review actually depends on.

### Step 12 — Phase 2 Guard
- [x] **RESPECTED** — No AI agent, Trust Score engine, Copilot, RAG, Qdrant,
      predictive analytics, LLM call, or remediation logic exists anywhere in
      this repo. Verified by inspection at the end of the session.

### Phase 1 Completion Checklist (original brief, honest status)

- [x] All 15 datasets inspected
- [x] Dataset profiling completed
- [x] Relationships identified
- [x] PostgreSQL database running
- [x] Alembic migrations working
- [x] All 15 datasets imported (14,400 rows)
- [x] Duplicate-safe ingestion working (verified twice: manually and by test)
- [x] Data validation working
- [x] Relationships resolved in the DB — zero orphans
- [x] Backend starts successfully
- [x] Authentication works
- [x] APIs work (38 paths)
- [x] Dashboard API works
- [x] OpenAPI documentation works
- [x] Critical tests pass (61/61)
- [x] Frontend can consume the APIs

**Phase 1 is COMPLETE** for Review-1 scope. The open TODOs above (write
endpoints, applied RBAC, index tuning, structured logging) are deliberate
deferrals, not gaps in what was asked for.

---

## PHASE 2 — AI Intelligence + Risk + Trust + Evidence

**NOT STARTED.** Must not begin until explicitly instructed. Scope: Policy
Agent, Monitoring Agent, Risk Agent, Evidence Agent, Trust Score Agent
(deterministic scoring + LLM narrative — it replaces the Phase 1 score, it does
not wrap it), Compliance Copilot, Remediation Agent, Agent Orchestrator, RAG
over Qdrant.

---

## PHASE 3 — Frontend Integration + Demo Polish

**NOT STARTED.** Backend-only repo. This phase is about the frontend team
consuming the API contract without back-and-forth, plus demo rehearsal.

---

# PHASE 2 STATUS UPDATE (this session)

| # | Priority | Status |
|---|---|---|
| 1 | Trust Intelligence Engine | **DONE** — verified live against real data |
| 2 | Risk Intelligence Engine | **DONE** — verified live against real data |
| 3 | Evidence Intelligence | **TODO** — not started |
| 4 | Policy Intelligence | **TODO** — not started |
| 5 | Compliance Copilot | **TODO** — not started |
| 6 | Remediation Intelligence | **DONE** — verified live against real data |
| 7 | Continuous Monitoring Engine | **DONE** — verified live against real data |
| 8 | Sentinel Orchestrator | **DONE** — implemented and verified |
| 9 | RAG / Knowledge Layer | **TODO** — not started |
| — | Frontend wiring for the 2 new endpoints | **TODO** — endpoints exist and are verified; no UI consumes them yet |

**Test baseline: 67 passed, 1 skipped, 68 total collected** (was 61/61 at
the start of this session; nothing weakened or removed, 7 new tests added
for the intelligence layer, 6 of which run and pass — the 7th documents
and correctly skips a graceful-degradation case the current dataset
doesn't happen to contain).

**Database: 20 tables** (19 application tables + `alembic_version`),
**14,400 real records confirmed twice** in this session (once after the
initial migration+ingestion, once again after the Postgres service
process was restarted mid-session — zero data loss).

Per the brief's own stopping rule ("if only enough time remains for one
feature: Trust + Risk. If two: + Copilot.") — this session delivered
exactly the Trust + Risk baseline and stopped there deliberately, rather
than starting Evidence/Policy/Copilot and risking an unfinished, unzipped
state. See NEXT_CLAUDE_PROMPT.md for the recommended order to continue in.


---

# PHASE 2B — Evidence / Policy / Copilot

Updated end of session 4. **105 passed, 1 skipped** (was 67 / 1). Frontend `vite build` exits 0.

| # | Priority | Backend | Frontend |
|---|---|---|---|
| 1 | Evidence Intelligence | **DONE** | **DONE** |
| 2 | Policy Intelligence | **DONE** | **DONE** |
| 3 | Compliance Copilot | **DONE** | **DONE** |
| 4 | Remediation Intelligence | **DONE** | **DONE** |
| 5 | Continuous Monitoring | **DONE** | **DONE** |

## Priority 4 — Remediation Intelligence
- [x] `RemediationIntelligenceService` — deterministic step-by-step plans
- [x] 2 endpoints under `/api/v1/intelligence/remediation`
- [x] Verified rule-based plan generation
- [x] `RemediationDrawer` on Findings page
- [x] Top Remediations AI prioritization panel on Findings page

## Priority 1 — Evidence Intelligence
- [x] `EvidenceIntelligenceService` — coverage, gaps, per-control provability
- [x] 4 endpoints under `/api/v1/intelligence/`
- [x] Coverage formula documented in the response itself (`formula`, `adequacy_rule`)
- [x] Gap severity ranking, deterministic and explained per gap (`why`)
- [x] Per-framework coverage breakdown
- [x] Findings and risks linked per control via existing verified FKs
- [x] Freshness explicitly marked unavailable (`freshness_policy_available: false`)
- [x] 10 tests
- [x] `EvidenceCoveragePanel` on the Evidence page: coverage + formula +
      per-framework breakdown + ranked gaps with the backend's `why` text
- [x] Misleading expiry tiles replaced with real counts

## Priority 2 — Policy Intelligence
- [x] `PolicyIntelligenceService` with a swappable `RequirementExtractor` protocol
- [x] Rule-based obligation extraction (no LLM configured — declared in every response)
- [x] Lexical `ControlMatcher` with published match scores and a threshold
- [x] Unmappable requirements return "No verified control mapping found."
- [x] Stored policies use the real `controls.policy_id` FK, not text matching
- [x] Current state / gap / recommended action per requirement, from real evidence
- [x] 8 tests
- [x] `PolicyAnalysisPanel` on the Policies page: paste text -> requirements ->
      mapped controls with match scores -> current state -> recommended action
- [x] Engine disclosure (`rule_based_v1 · llm_used: false`) shown in the panel
- [x] "No verified control mapping found." rendered, not filtered
- [ ] PDF upload and text extraction
- [ ] `analyzeStoredPolicy()` bound but not yet used by a component

## Priority 3 — Compliance Copilot
- [x] `CopilotService` — 12 intents over the existing intelligence services
- [x] All 11 required questions route and answer from live data
- [x] Structured response: answer / intent / supporting_data / related_entities /
      recommendations / sources / confidence
- [x] Traceable `sources` on every answer
- [x] Out-of-scope questions decline rather than improvise
- [x] `/copilot/suggestions` for the suggested-questions UI
- [x] 12 tests
- [x] Copilot page on live data — seeded conversation and fake matcher removed
- [x] "Derived from" source panel; suggestions fetched from the backend
- [x] Invented header stats (91% confidence, 1.2s latency) replaced
- [ ] `getControlEvidence()` bound but not yet used by a component

## Priority 3B — LLM grounding layer (this session)
- [x] `LLMService` — OpenAI-compatible, server-side only, timeout/HTTP-error/
      empty-response/unconfigured all fall back to `None` rather than raising
- [x] `CopilotService.answer()` — LLM rewrites `answer` prose only; never
      touches `supporting_data` / `related_entities` / `recommendations` /
      `sources`; sets `engine` = `llm_grounded_v1` | `deterministic_fallback_v1`
      | `deterministic_intent_v1` (unmatched intent) and `llm_used` correctly
- [x] Stale test fixed: `test_copilot_routes_every_required_question` asserted
      a pre-LLM `engine` value on all 11 required questions — corrected, and
      the matching stale claim removed from `copilot.py`'s docstring and the
      `/copilot/query` OpenAPI description
- [x] Full suite verified against a real, freshly-ingested PostgreSQL
      database: 142 passed, 1 skipped, 0 failed (was 131/11/1 before the fix)
- [x] All 7 mandatory demo questions verified live over real HTTP against the
      real running server (not just the ASGI test client) — correct intent,
      full response contract present, real sources/confidence
- [x] Frontend now surfaces `engine`/`llm_used` honestly: header "Engine"
      stat + a per-answer "LLM grounded" / "Verified fallback" badge, never
      claiming "AI powered" when the LLM did not run
- [x] Thinking state replaced with the specified 4-stage progression,
      client-timed (no backend streaming exists), cleared the instant the
      real response returns
- [x] Fixed a real pre-existing type error (`EmptyState tone="danger"` isn't
      a valid tone) by switching to the existing `ErrorState` component,
      which also added a working retry
- [ ] **Not verifiable in this sandbox:** an actual successful
      `engine="llm_grounded_v1"` response. No `LLM_API_KEY` is configured
      here and this sandbox has no network path to an LLM provider. The
      success/timeout/error paths are covered by 37 mocked tests in
      `tests/test_copilot_llm.py`, which is the most this environment can
      verify — set `LLM_API_KEY` (+ `LLM_MODEL`, `LLM_BASE_URL` if not
      OpenAI's default) in a real environment to confirm the live path.

## Known, pre-existing, out of scope for this session
- [ ] `npx tsc --noEmit` reports 57 errors, none in any file this session
      touched (`Copilot.tsx`, `copilotAdapter.ts` are clean). All are in
      unrelated pages/components (`CommandCenter.tsx`, `CloudAssets.tsx`,
      `src/data/assets.ts`, etc.), mostly unused-import (`TS6133`) style
      issues that predate this session. `npm run build` (the actual Vite
      build, which doesn't gate on these) succeeds regardless.

## Not started
- Continuous Monitoring (Priority 5)
- RAG / Qdrant / multi-agent — correctly untouched

## General-purpose GRC reasoning engine (`app/services/grc_engine/`) — this session
- [x] Ground-truth schema graph (real FK catalog, cross-checked against
      `docs/profiling/relationships.txt`) — 15 business tables, every real
      join, every deliberately-missing relationship documented
- [x] Constrained query DSL (Pydantic) — LLM output is data, never SQL text
- [x] Query compiler — validates against the real schema independently of
      Pydantic, parameterized construction, read-only + 5s-timeout
      transaction scope (DELETE-rejection proven live, not assumed)
- [x] Metrics catalog — wraps existing DashboardService/TrustIntelligenceService
      rather than recomputing (no duplicated GRC math)
- [x] Question understanding (LLM) — extends LLMService via a shared
      `_complete()`, not a duplicate HTTP path; 37 pre-existing LLM tests
      re-verified unchanged
- [x] Reasoning orchestrator — falls back to the existing, unmodified
      12-intent CopilotService whenever the general engine can't understand
      a question (proven live, exact original contract intact)
- [x] New endpoint `POST /api/v1/ai/query`, additive — `/copilot/query`
      deliberately left untouched (see HANDOFF.md for why)
- [x] 61 new tests, 245 passed / 1 skipped / 0 failed backend-wide, zero
      regressions — includes a 42-question diverse battery (brief
      Section 27's 30-50 question requirement) covering every category the
      brief names, plus a real-network wiring proof against a local
      fake-LLM server (not part of the handoff)
- [ ] **Not verifiable in this sandbox, stated plainly:** real-model output
      quality for arbitrary question phrasing. Everything downstream of a
      correct plan is proven against real data; whether a real LLM reliably
      produces a correct plan from raw question text is the one link this
      environment cannot test. First priority with a real `LLM_API_KEY`.
- [ ] No authentication on `/ai/query` or `/copilot/query` (pre-existing —
      no endpoint in `intelligence_router.py` has auth; see HANDOFF.md)
- [ ] DSL has no subquery/anti-join support ("controls with NO evidence" as
      a specific list, not just a count) and no severity-aware custom
      ordering — documented scope boundaries, not bugs, in HANDOFF.md
