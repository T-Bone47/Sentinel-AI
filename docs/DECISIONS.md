# Architecture decisions

## ADR-001 — One permission matrix, default deny (2026-11-16)

**Decision.** All authorization comes from `sentinel-ai-backend/app/core/permissions.py`.
Routes declare the datasets they return rows from with `require_permission(...)`;
anything not written in the matrix is refused. The role is read from the user's
database row on every request, never from the token.

**Why.** Before this, any valid token could read every dataset. A single table is
reviewable and testable; per-route role lists drift.

**Consequences.**
- Compound endpoints (detail views, graph, dashboard, AI) either require every
  dataset they read or withhold the sections the caller may not see and list
  them in `withheld`.
- The AI query engine receives the caller's readable tables and refuses plans
  that touch any other table, including through a join.
- The `employee` role is row-scoped to its own `employee_id`. An account with no
  linked employee sees nothing.
- Sentinel is single-tenant. This separates roles and people, not tenants.

## ADR-002 — Bearer tokens stay in localStorage for now (2026-11-16)

**Decision.** Keep tokens in `localStorage`; limit the damage of theft on the server:
15-minute access tokens bound to a revocable session row, single-use rotating
refresh tokens, and reuse of a rotated token ends the session.

**Why not HttpOnly cookies yet.** The deployed shape in the repo is a separate
frontend and API origin. Cookies there need `SameSite=None` plus CSRF protection,
and that cannot be tested without the real deployment. Migrating untested would
trade a known risk for an unknown one.

**Residual risk.** Script injected into the page (XSS) can read both tokens and
act as the user until the session is revoked or the stolen refresh token collides
with the real one. No `dangerouslySetInnerHTML` is used today; there is no CSP.

**Revisit when** the deployment topology is decided (owner decision).

## ADR-003 — Configuration fails closed (2026-11-16)

**Decision.** `ENVIRONMENT` defaults to `production`. Outside `development` and
`test` the app will not start with the public demo secret, a secret shorter than
32 characters, the demo database credentials, or debug on.

**Why.** A deployment that forgot `SECRET_KEY` previously ran with a published
key, which allows forging tokens for any user.

**Cost.** Local work needs `ENVIRONMENT=development` (already in `.env.example`);
CI sets `ENVIRONMENT=test`.

## ADR-004 — Login throttle and AI conversation memory are in-process (2026-11-16)

**Decision.** Both are bounded in-memory structures, not database tables.

**Ceiling.** Lost on restart and counted per worker process. Acceptable for a
single-process local deployment; move both to a shared store before running more
than one worker. Lockout can be triggered deliberately against a known email
(15-minute denial of sign-in) — accepted in exchange for stopping password guessing.

## ADR-005 — Events are identified by where they came from; the first write wins (2026-11-16)

**Decision.** An event's id is the SHA-256 of its source type, source id and the
source's own record id. Storing an event is insert-if-absent. A later record with
the same id and different content is logged as a conflict and discarded; the
stored event is never rewritten. A database trigger refuses `UPDATE`.

**Why.** It makes ingestion idempotent without coordination: replays, retries and
overlapping exports are all harmless. And an evidence store that can be edited is
not evidence.

**Consequences.**
- If a source legitimately corrects a record under the same id, we keep the first
  version. The correction is visible only as a logged conflict.
- The source record is stored in canonical JSON form, not byte-for-byte.
- The stored hash detects accidental change, not deliberate tampering by someone
  with database access. Full rules: `docs/EVENT_CONTRACT.md`.

## ADR-006 — Ingestion is inline and bounded; there is no queue (2026-11-16)

**Decision.** Records are validated and stored in the caller's request or
command, in chunks of 500, one transaction each. No broker, no worker, no
background loop.

**Why.** Nothing yet needs asynchronous processing, and every moving part is
something to secure, monitor and explain. Because ingestion is idempotent, the
retry mechanism is "run the same input again".

**Revisit when** a real source produces more than a request or a nightly file can
carry, or when detection must run within a bounded delay of ingestion.

## ADR-007 — Ground-truth labels are never stored with events (2026-11-16)

**Decision.** Labels and scenario ids exist only in a fixture's `labels.jsonl`.
The events table has no column for them and the contract no attribute. Event ids
in fixtures are random-looking.

**Why.** If the answer sits next to the data, a detector — or a later convenience
join — can read it, and every reported metric becomes meaningless.

**Consequence.** The evaluator must join detections to labels itself, outside the
database. That is the intended place for it.

## ADR-008 — Trust score history is written only by explicit measurements (2026-11-16)

**Decision.** Reading the trust score never writes. A history row is written by
`POST /intelligence/trust/measurements`, by `scripts/record_trust_measurement.py`,
or at the end of a dataset load, and only if the score or its components changed.
Each row records why (`trigger`) and by whom (`recorded_by`).

**Why.** Every read used to store a row, so the history recorded page views, and
the "change since last time" was the change since someone last looked.

**Consequences.**
- Rows written by the old behaviour are kept and marked `legacy_on_read`.
- An unchanged score leaves no trace however often it is measured. The history is
  a list of changes, not a heartbeat.
- There is no scheduler inside the application. When to measure is an operations
  decision, made with cron or Task Scheduler.

## ADR-009 — The legacy `audit_logs` table is not backfilled into the event store (2026-11-16)

**Decision.** The 10,000 rows in `audit_logs` stay where they are.

**Why.** Their origin is undocumented, their timestamps carry no timezone, their
actions and scores are close to uniformly random, and they have no labels.
Ingesting them would give the new pipeline volume without meaning, and would
require inventing a timezone.

**Revisit if** the dataset's provenance is established (`docs/DATA_PROVENANCE.md`,
still PLANNED).

## ADR-010 — Detection rules are Python functions with written contracts (2026-11-17)

**Decision.** Each rule is a pure function over one source's events
(`app/detections/rules.py`). Its human-readable contract is a TOML file in
`research/rules/`, parsed with the standard library. The code is the source of
truth for parameters; a test fails if the contract's id, version, title,
severity, confidence, parameters or ATT&CK techniques differ.

**Why.** Five rules don't justify a rule language and its interpreter, and
functions are easy to test. Contracts written and hashed before the code make
later changes to expectations visible.

**Not Sigma.** Sigma versions for upstream projects (PRD milestone M3) will be
validated with Sigma's own tooling before being called Sigma.

## ADR-011 — Alerts are immutable, with one trigger each (2026-11-17)

**Decision.** An alert's id is the SHA-256 of rule id, rule version and its one
trigger event. Storing is insert-if-absent. Update triggers refuse changes to
alerts and their event links, on SQLite and PostgreSQL.

**Why.** Re-running the rules, or replaying their input, must never duplicate or
rewrite an alert. With several triggers per alert, later activity would change
the id and create overlapping alerts.

**Consequence.** One incident can produce several alerts (S04-P1 gives two).
Grouping them is the case workflow's job (Gate 4).

## ADR-012 — An alert is a finding, not a verdict; stored alerts are not retracted (2026-11-17)

**Decision.**
- Triage state (status, assignee, suppression, notes) is not stored on alerts.
  It comes in Gate 4, in separate tables.
- When later events mean a rule would no longer raise a stored alert (for
  example an approval that arrives late), the alert stays. The run reports it in
  `alerts_no_longer_raised`.

**Why.** Keeping alerts immutable keeps the record of what a rule found at the
time. Deciding what a stale alert means is a human judgement.

## ADR-013 — Evaluation runs outside the backend, in one command (2026-11-17)

**Decision.** `research/scripts/run_detection_benchmark.py` does the whole
benchmark in a throwaway SQLite database: it migrates, ingests both fixtures,
runs the rules twice (the second time as a replay check) and scores the alerts
against `labels.jsonl` with `evaluate_detections.py`.

**Why.**
- Labels never enter the backend (ADR-007).
- The configured database is never touched.
- `metrics.json` is identical between runs apart from its `metadata` block,
  which a test checks.

**Limit.** Synthetic fixtures by the same author: the results measure
conformance to the contracts, not real-world performance (PRD milestone M2).
