# Threat model

*Written 2026-11-18 by Claude Opus 5.5 from the code, the ADRs in
`docs/DECISIONS.md` and the findings in `docs/PROGRESS.md`. It describes the
system as it is, not as planned. No independent review yet.*

## 1. Scope and assumptions

- **Single-tenant and local:** one organisation's demo deployment. There is no
  multi-tenant isolation, and none is claimed.
- **Never deployed.** `render.yaml` exists but is known to be broken (R5).
- **The data is fictional** (`docs/DATA_PROVENANCE.md`), but the system is
  designed as if it held real per-person activity records.

## 2. Assets

| Asset | Why it matters |
|---|---|
| Per-person records: employees, identity and access, consent, audit logs | Personal data in a real deployment |
| Security events and their raw source records | Evidence. Must be immutable and traceable |
| Detection alerts | Findings about named people; wrong or forged alerts mislead analysts |
| Sessions and refresh tokens | Possession means acting as that user |
| `SECRET_KEY` (signs access tokens) | Anyone holding it can forge any user's token |
| Optional LLM API keys | Cost, and a path for data to leave the system |

## 3. Principals and trust boundaries

| Principal | Trust |
|---|---|
| Anonymous network client | None. Only `/auth/login`, `/auth/refresh` and health checks are reachable |
| Signed-in staff: admin, security analyst, compliance officer, auditor | Per the permission matrix (ADR-001, default deny); role read from the database on every request |
| Employee | Own records only |
| Local operator (command-line ingestion and detection runs) | Full trust: has the machine and the database URL |
| Event sources (anything an admin ingests) | **Untrusted content**, even when the uploader is trusted |
| Optional LLM provider (NVIDIA, or a Google-compatible endpoint) | External; **off by default** (`copilot_llm_enabled = False`) |

**Boundaries:**
- browser ↔ API, over HTTP with bearer tokens;
- API ↔ database;
- API ↔ the optional LLM provider;
- source file ↔ adapter: the contract boundary of `app/events/contract.py`.

## 4. Threats and mitigations (STRIDE)

| # | Threat | Mitigation in place | Evidence | Residual risk |
|---|---|---|---|---|
| S1 | Spoofing: guessing passwords | Account lockout after repeated failures (15 min); bcrypt checks run in a thread (R1) | Gate 1 tests; R1 and R2 fixes | Per-address limit added (R6, fixed 2026-11-18: 20 failures per 15 min). Both counters are per process (ADR-004); behind a reverse proxy all clients share one address, so rate-limit at the proxy too |
| S2 | Spoofing: stolen or forged token | Access tokens last 15 min; refresh tokens rotate atomically, reuse is detected, sign-out revokes; startup refuses a known or default `SECRET_KEY` outside development (ADR-003) | Gate 1 tests | Tokens live in `localStorage`, so XSS could steal them (ADR-002, accepted for now) |
| S3 | Spoofing: confirming a password on a disabled account | A disabled account gets the same 401 as a wrong password, and the attempt counts as a failure (R8, fixed 2026-11-18) | `test_a_disabled_account_answers_like_a_wrong_password` | — |
| T1 | Tampering: editing or deleting stored events or alerts | The database refuses `UPDATE` on events, alerts and alert links (triggers; validated on PostgreSQL 2026-11-18); events are identified by their source and the first write wins (ADR-005) | Gate 2 and Gate 3 tests, on SQLite and PostgreSQL | Anyone with database-owner access can drop the triggers |
| T2 | Tampering: malicious content in an event | Strict contract: unknown fields and wrong types refused; control and invisible formatting characters refused (R4); size limits | Gate 2 tests | Adapters cover only fields they know; the raw record is stored as-is |
| R1 | Repudiation: "I never did that" | Every ingestion batch and detection run is recorded with origin and actor; refresh-token reuse and lockouts are logged (R3) | Gate 2 and Gate 3 tests | Logs are local files; no tamper-evident log store |
| I1 | Information disclosure across roles | One permission matrix; employee rows scoped to the user; per-person sections withheld from auditors in detail, dashboard and graph views | Gate 1 tests (160+) and the review pass | Coverage is the enumerated cases, not a proof |
| I2 | Disclosure through errors | Validation errors never echo submitted input; contract errors name fields, never values | Gate 1 and Gate 2 tests | API docs and the schema are served only in development and test (R7, fixed 2026-11-18) |
| I3 | Disclosure through the AI Copilot | Deterministic query plans over an allow-listed table set; events not on the list; conversations private per user | Gate 1 tests | Each user is capped at 20 conversations inside the 500 total, so one user cannot push out another's history (R10, fixed 2026-11-18) |
| I4 | Data leaving through the optional LLM | Off by default | Configuration | When enabled, question context goes to an external provider: **not yet disclosed in the UI (finding F9, open)** |
| D1 | Denial of service: huge or many uploads | Request, batch and record size limits; detection runs capped at 50,000 events | Gate 2 and Gate 3 tests | No request rate limit (R6); volume attacks out of scope |
| E1 | Elevation: a role reaching another role's actions | Default-deny matrix; role from the database, not the token; only admin may ingest, only admin and security analyst may run detections | Gate 1–3 tests; guard-removal checks | — |
| E2 | Elevation: prompt injection through ingested text | Event text is never given to an LLM in the default configuration; the Copilot plans queries, it does not run free text | Design | Gate 5 (grounded LLM answers with injection tests) is not built |

## 5. Known weaknesses, in priority order

1. **F9:** the optional LLM's data egress is not disclosed in the UI.
2. **R9:** trust measurements are deduplicated by check-then-insert, so two
   simultaneous measurements can write identical rows.
3. **ADR-002:** tokens in `localStorage`. Revisit with cookie auth and CSRF
   protection.
4. **The in-process counters (R6) do not cover a multi-worker or proxied
   deployment.** Rate-limit at the reverse proxy before any deployment.

R6, R7, R8 and R10 were fixed on 2026-11-18, each with a regression test; see
`docs/PROGRESS.md`.

## 6. When to update this file

When a new route, data source, external service or role is added; when a
finding above is fixed; or after any independent review.
