# Plan — M1 / Gate 3: detection engine on synthetic data

*Implements milestone M1 of `docs/PRD_CVP_DEFENSE_ACCESS.md`. Written
2026-11-17 by Claude Opus 5.5, before any Gate 3 code. Status: IMPLEMENTED and
tested on SQLite (2026-11-17); PostgreSQL pending. Results and handoff are in
`docs/PROGRESS.md`.*

> **Amended 2026-11-17, before pre-registration (S1).**
> - **One trigger per alert.** The alert id now hashes the rule, its version and
>   one trigger event. Grouping several triggers into one alert would give an
>   alert a new id whenever more activity arrived later, so a re-run would create
>   a second, overlapping alert for the same incident. Grouping alerts into an
>   incident is the case workflow's job (Gate 4). Effect: S04-P1's two trigger
>   events now produce two alerts, so the fixture expects 7 alerts, not 6.
> - **IA-003 alerts only the first success after a burst.** A second success
>   inside the same window would otherwise alert again. This is boundary case B-15.
> - **IA-004 applies state changes after the actions at the same instant.** A
>   disable or enable affects only strictly later events, so the result never
>   depends on how simultaneous events happen to be sorted.
> - **Runs report alerts they would no longer raise.** If a late event (for
>   example an approval) means a rule would not raise a stored alert today, the
>   alert stays and the run counts it in `alerts_no_longer_raised`.

## 1. Goal and exit criteria

Five detectors over the event contract, each with a written contract. They
produce immutable alerts that cite the exact events behind them, from a run that
is deterministic and safe to repeat. The rules are evaluated against the fixture
labels and compared with Sentinel's current monitoring logic. A screen states
plainly that this is retrospective batch analysis, not live monitoring.

Gate 3 passes when every row below holds. The first five come from `CLAUDE.md`;
the last two are Gate 2 conditions that could not be met before alerts existed.

| Condition | Proof |
|---|---|
| Positive and negative cases for every detector | The fixture's suspicious and benign scenarios, plus the boundary fixture (§5); per-detector tests |
| Repeatable results | Same events and rule versions give the same alert set; a second run creates 0 alerts; the self-contained benchmark gives identical metrics twice, apart from timestamps |
| Every alert traceable to source evidence | Every cited event resolves through the events API, and its stored hash verifies |
| Severity and confidence separate; ATT&CK only where defensible | Rule contracts; mappings checked against the technique pages, otherwise `unmapped` |
| Monitoring states retrospective vs live accurately | The Detections screen label, and the wording fix for finding F8 |
| Replaying the fixture twice gives zero unintended duplicate alerts | Re-ingest, re-run, 0 new alerts |
| Each alert's originating records can be explained | Alert detail lists every cited event, its role and its source record hash |

## 2. Starting point (verified 2026-11-17)

- Event contract v1 and event store, with an update trigger and replay-safe ingestion.
- Fixture `identity-access-v1`: 194 events and 19 scenarios, with 7 trigger events
  and 12 decoys.
- Backend: 507 passed, 2 skipped on SQLite. PostgreSQL is BLOCKED (Docker engine
  off). The project is not under version control.

## 3. Decisions

Each becomes an ADR when implemented.

**D-1 — Rules are small Python functions, not a rule language.**
- Five rules don't justify a language and an interpreter. Functions are easy to
  test and review.
- Each rule's human-readable contract is a TOML file in `research/rules/`, read
  with the standard library's `tomllib`, so no new dependency.
- The code is the source of truth for parameters. A test fails if a contract's id,
  version, parameters, severity or confidence differ from the code.
- These are not Sigma rules and won't be called that. Sigma drafts for upstream
  projects come in M3 and are validated with Sigma's own tooling.

**D-2 — Detectors are pure and never read the clock.**
- A detector receives the events of one source, ordered by `(occurred_at,
  event_id)`, and returns findings.
- It never reads the clock, the database or another source.
- Events at the same instant are never treated as ordered: "after" always means
  strictly later (event contract §5).

**D-3 — Alerts are immutable and identified by what they found.**
- Every alert has exactly one trigger event. `alert_id` is the SHA-256 of the
  rule id, the rule version and that event's id (see the amendment above).
- Storing an alert is insert-if-absent, so re-running is a no-op.
- A new rule version produces new alerts; old ones stay attributable to the
  version that raised them.
- The database refuses `UPDATE`, as it does for events.

**D-4 — An alert is not a triage decision.**
- Gate 3 stores what a rule found.
- Analyst state (status, assignee, suppression, notes) changes over time, belongs to
  the case workflow, and is built in Gate 4 in separate tables.
- This defers `CLAUDE.md`'s "suppression state, triage status" on purpose, to avoid
  making alerts mutable.

**D-5 — Severity and confidence are separate.**
- Both are categorical (low, medium, high, critical for severity; low, medium, high
  for confidence).
- Both are fixed per rule, with a written reason.
- No numeric probabilities (compare finding F10).

**D-6 — One source per run, over that source's whole history.**
- Correlating across sources is out of scope.
- The boundary fixture records the detection this misses.

**D-7 — Runs are bounded.**
- A run refuses a source with more than 50,000 events and says why.
- `# ponytail: whole-source load; upgrade path is per-actor streaming state.`

**D-8 — Evaluation happens outside the database.**
- A research script joins exported alerts to `labels.jsonl`.
- Labels never enter the backend (ADR-007).

## 4. The five detectors

Parameters are written into the contracts before any code (step S1) and frozen
before M2.

Every rule runs per source and needs `outcome == "success"` on the triggering
event unless stated otherwise. When a rule needs an attribute the event doesn't
have, the event is counted as **not evaluable** — never as negative.

### IA-001 — Privileged access granted without approval

- **Fires on:** `privilege.grant` with `privileged == true` and no `approval_ref`.
- **Doesn't fire when:**
  - an approval reference is present;
  - `privileged` is false;
  - `privileged` is absent (counted as not evaluable).
- **Alert:** the grant is the trigger.
- **Severity:** high — administrative access granted outside the change process.
- **Confidence:** medium — depends on the source attaching approval references
  whenever approvals exist.
- **ATT&CK candidate:** T1098 Account Manipulation (verify).
- **On the fixture:**
  - Fires on S01-P1 and S01-P2.
  - Stays silent on S01-B1 and S01-B2, and on the three non-privileged grants in S05.

### IA-002 — Privileged sign-in without MFA

- **Fires on:** `auth.login` with `privileged == true` and `mfa_used == false`.
- **Doesn't fire when:**
  - MFA was used;
  - the account is not privileged;
  - the sign-in failed;
  - either attribute is absent (not evaluable).
- **Alert:** the sign-in is the trigger.
- **Severity:** medium — a control failure, not by itself evidence of an attacker.
- **Confidence:** high wherever both attributes are present.
- **ATT&CK:** `unmapped` — a control weakness, not an adversary technique.
- **On the fixture:** fires on S02-P1; silent on S02-B1, B2 and B3.

### IA-003 — Repeated failed sign-ins, then success

- **Fires on:** the first successful `auth.login` by actor A after a burst: the
  30 minutes before it (`[t − 30 min, t)`) contain at least 5 failed
  `auth.login` events by A, from any address, and no earlier success by A
  followed the last of them.
- **Doesn't fire when:**
  - there are fewer than 5 failures in the window;
  - an approved `credential.change` targeting A falls strictly between the last
    failure and the success;
  - the failures belong to a different account.
- **Alert:** the success is the trigger; the failures in the window are context.
- **Severity:** high.
- **Confidence:** medium — password managers with stale passwords and shared
  addresses produce bursts too.
- **ATT&CK candidate:** T1110.001 Password Guessing (verify).
- **Why 30 minutes, not 10:** in S03-B2 the successful sign-in comes 22 min 40 s
  after the last failure, with the approved reset 17 min 11 s after it. With a
  10-minute window, the window alone would silence it, and the fixture would never
  test the reset exclusion. This choice was made by reading the
  fixture. That is acceptable for a conformance fixture, and it is recorded here —
  which is exactly why the parameters freeze before M2.
- **On the fixture:**
  - Fires on S03-P1: six failures, then a success 68 seconds later.
  - Stays silent on S03-B1 (2 failures).
  - Stays silent on S03-B2 (silenced by the approved reset — the exclusion is exercised).
  - Stays silent on S03-B3 (1 failure in the window).

### IA-004 — Activity by a disabled account

- **Fires on:** a successful action by actor A strictly after a successful
  `account.disable` targeting A, with no successful `account.enable` of A in
  between.
- **One alert per successful action in the disabled period.** The action is the
  trigger; the disable that started the period is context. A disable or enable
  affects only events strictly after it.
- **Doesn't fire when:**
  - the account was re-enabled first (any re-enable ends the period — a design
    choice; an unapproved re-enable is a different rule);
  - the action failed, meaning the control worked;
  - the action happened at the same instant as the disable.
- **Severity:** high.
- **Confidence:** high — the disable and the activity come from the same source (D-6).
- **ATT&CK candidate:** T1078 Valid Accounts. It is `unmapped` unless the
  technique text covers use of an account that should no longer work.
- **On the fixture:**
  - Fires on S04-P1, with both the sign-in and the confidential read as triggers.
  - Stays silent on S04-B1 and S04-B2.

### IA-005 — Unapproved permission change, then sensitive access

- **Fires on:** a `privilege.grant` to principal P with no `approval_ref` at time g,
  followed by a `resource.read` or `resource.export` by P, with
  `sensitivity ∈ {confidential, restricted}`, at time t where `g < t ≤ g + 60 min`.
- **Doesn't fire when:**
  - the grant was approved;
  - the data accessed was public or internal;
  - the access falls outside the window;
  - the access was by someone other than the grantee;
  - `sensitivity` is absent (not evaluable).
- **Alert:** the access is the trigger; the grant is context.
- **Severity:** high.
- **Confidence:** medium.
- **ATT&CK candidate:** T1098 for the grant (verify). The access has no single technique.
- **On the fixture:** fires on S05-P1; silent on S05-B1 and S05-B2.

### Expected on `identity-access-v1` (pre-registered)

- **Exactly 7 alerts:** IA-001 ×2, IA-004 ×2, and one each of IA-002, IA-003 and
  IA-005.
- **Coverage:** the alerts cite exactly the 7 trigger events as triggers, one each.
  No decoy, context or background event is cited as a trigger.
- **How to read it:** this is conformance by construction. It shows the rules do
  what their contracts say. It says nothing about real-world performance (§7).
- **Checked on 2026-11-17:** a throwaway script implementing exactly these
  definitions reproduced the 7 trigger events on the real fixture (as 6 alerts
  under the original grouping), and the §7 baseline figures. That checks this
  plan's arithmetic; it is not the implementation.

## 5. Boundary fixture `identity-access-boundary-v1` (pre-registered)

Written in step S1, before any detector code. Each case's expected outcome and its
SHA-256 are recorded in `docs/PROGRESS.md` first. The fixture is still synthetic
and has the same author, so this is a weak form of pre-registration, not
independence.

| Case | Rule | Situation | Expected |
|---|---|---|---|
| B-01 | IA-003 | Exactly 4 failures, then success | silent |
| B-02 | IA-003 | 5 failures, the first exactly 30 min 00 s before the success | fires |
| B-03 | IA-003 | As B-02, but the first failure 30 min 01 s before | silent |
| B-04 | IA-003 | 5 failures from 5 different addresses, then success | fires |
| B-05 | IA-003 | Failures by account A, success by account B | silent |
| B-06 | IA-005 | Sensitive export exactly 60 min 00 s after the grant | fires |
| B-07 | IA-005 | Export 60 min 01 s after the grant | silent |
| B-08 | IA-005 | Unapproved grant to P, sensitive access by Q | silent |
| B-09 | IA-004 | Disable and sign-in at the same instant | silent |
| B-10 | IA-004 | The disabled account's sign-in is written earlier in the file than the disable | fires |
| B-11 | IA-004 | Re-enabled without approval, then active | silent (design choice) |
| B-12 | IA-004 | The disable is recorded in a different source than the sign-in | **silent — known miss, D-6** |
| B-13 | IA-001 | Privileged grant where the source omits `privileged` | **silent — known miss, not evaluable** |
| B-14 | IA-002 | Privileged sign-in where the source omits `mfa_used` | **silent — known miss, not evaluable** |
| B-15 | IA-003 | 5 failures, then two successes a minute apart | fires once, on the first success |

Cases B-12 to B-14 are real gaps and are reported as missed detections. They are
the evaluation's built-in negative result.

## 6. Interfaces and permissions

**Permission matrix**
- `detection-rules`: READ for all staff (the rule catalogue holds no personal data).
- `detections`: READ for internal staff (alerts cite per-person events), and a new
  RUN action for admin and security analyst.
- Employees are denied everything here. The existing test that empties the matrix
  covers the new routes automatically.

**API** (under `/api/v1/detections`)

| Method and path | Who | Returns |
|---|---|---|
| `GET /rules` | `detection-rules` READ | Catalogue from the code registry: id, version, title, severity, confidence, ATT&CK, parameters, limitations |
| `POST /runs` with `{source_type, source_id}` | `detections` RUN | Run report: events considered, alerts created, alerts already present |
| `GET /runs/{run_id}` | `detections` READ | One run |
| `GET /alerts` | `detections` READ | Filters by rule, severity, actor and source; cursor paging by `(first_event_at, alert_id)` |
| `GET /alerts/{alert_id}` | `detections` READ | Each cited event with its role, time, action, outcome, `raw_sha256`, and its `/security-events/{id}` path |

**Command line**
- `python -m app.detections run --source-type … --source-id …`
- `python -m app.detections export --source-id …` — JSON Lines on stdout, for the evaluator.

**Tables** (one reversible migration)

| Table | Contents |
|---|---|
| `detection_runs` | id, start and end, status, source, rule versions, events considered, alerts created and already existing, triggered by |
| `detection_alerts` | `alert_id`, rule id and version, severity, confidence, source, actor, summary, first and last event time, run id. The summary is a fixed template using ids only |
| `detection_alert_events` | `(alert_id, event_id, role)`, with a foreign key to `security_events`. A future purge must remove alerts first; that is already noted in the event contract §10 |

Both alert tables get an update trigger.

## 7. Evaluation

The evaluator lives in `research/scripts/`. It reads the alert export, `labels.jsonl`
and `MANIFEST.json`.

**Unit of truth:** trigger events (`part = trigger`) in suspicious scenarios.

**Per detector**
- **TP:** its family's trigger events that it cited as triggers.
- **FN:** its family's trigger events it didn't cite.
- **FP:** any other event it cited as a trigger. Cross-family hits are reported
  separately.
- Precision, recall and the count of not-evaluable events.
- No confidence intervals: with 7 trigger events they would mean nothing, and the
  report says so.

**Per scenario:** which suspicious scenarios were detected, and which benign
scenarios drew any alert.

**Comparisons, under the same labels:**
1. **Sentinel's current monitoring logic.**
   - The existing `/intelligence/monitoring/anomalies` criterion is
     `risk_score >= 80 OR result == 'Failure'`. Events have no risk score, so only
     the failure half applies.
   - Pre-registered expectation: it flags S03-P1's failures but not its successful
     sign-in, and no event at all of S01, S02-P1, S04-P1 or S05-P1.
   - At event level that is 0 of 7 trigger events. It flags 35 events in total;
     apart from S03-P1's six failures, all of them are in benign scenarios or
     background activity.
2. **Ablation.** Each rule with its exclusions and thresholds removed. This shows
   what the exclusions buy on the 12 decoys.

**Self-contained benchmark — one command**

`python research/scripts/run_detection_benchmark.py`:
- builds a temporary SQLite database with `alembic upgrade head`;
- ingests both fixtures, runs the detectors, exports the alerts and evaluates them;
- writes `research/results/<fixture>/<UTC timestamp>/metrics.json` and `report.md`;
- never touches the configured database.

Metadata recorded with every result: script version, fixture hashes, rule versions,
Python version, platform, UTC time, and the commit SHA — or "not a git repository".

**What the results will and won't mean**
- On `identity-access-v1`, expect complete conformance. That is by construction,
  not evidence of quality.
- The boundary fixture shows three misses by design.
- The comparisons show what Sentinel's existing logic misses, and what the
  exclusions buy.
- Any claim about real-world performance waits for M2.

## 8. Tests (written first, watched failing)

1. **Contracts:**
   - every registered detector has a TOML contract;
   - the contract's id, version, parameters, severity and confidence equal the
     code's;
   - every field a rule needs exists in event contract v1.
2. **Each detector, on hand-built events:**
   - it fires when it should;
   - each exclusion holds;
   - each boundary case from §5 behaves as pre-registered;
   - not-evaluable events are counted;
   - same-instant events are never treated as ordered;
   - shuffled input gives the same findings.
3. **Engine:**
   - the fixture gives exactly the 7 alerts and 7 triggers in §4;
   - a second run creates 0;
   - re-ingesting and re-running creates 0;
   - alert ids are identical across fresh databases;
   - a bumped rule version adds alerts and leaves old ones untouched;
   - the 50,000-event cap is refused cleanly;
   - a failed run is marked failed.
4. **Immutability:** the database refuses `UPDATE` on both alert tables.
5. **Traceability:** every cited event resolves through the events API, and its
   hash recomputes from the stored record.
6. **Authorization:**
   - an auditor can read rules but not alerts;
   - only admin and security analyst can run;
   - employees are denied everywhere;
   - anonymous requests get 401 and the empty matrix gives 403, through the
     existing tests.
7. **Evaluator:**
   - correct TP, FP and FN on a tiny hand-labelled set, including cross-family and
     not-evaluable cases;
   - baseline figures correct;
   - metadata complete;
   - the benchmark twice gives identical metrics apart from timestamps;
   - the configured database is untouched.
8. **Frontend:**
   - type-check, lint and build pass;
   - the screen shows the "retrospective" label;
   - every figure comes from the API.

## 9. Steps

Each step ends with the full backend suite green, so a pause for usage limits
never leaves the code broken.

| Step | Work | Model | Verify |
|---|---|---|---|
| S1 | Pre-register: five TOML contracts, the boundary case list with expected outcomes, and their SHA-256 recorded in `PROGRESS.md` | Opus | Hashes recorded before S2 |
| S2 | Boundary fixture generator and files | Opus | `--check` reproduces byte for byte |
| S3 | All tests from §8 for S4–S8, watched failing | Opus | Each fails for the right reason |
| S4 | Tables, migration, update triggers | Opus | `alembic check`; downgrade and upgrade round trip |
| S5 | The five detectors and their registry | Opus | Detector and contract tests green |
| S6 | Engine, alert store, command line | Opus | Engine and immutability tests green |
| S7 | API and permissions | Opus | Authorization tests green |
| S8 | Evaluator, comparisons, benchmark runner; run it; then a fresh-eyes review of S4–S8 | Opus | Results match §4 and §7, or the mismatch is reported as found |
| S9 | Detections screen (catalogue, alert queue, alert detail) and the F8 wording fix | Fable | Type-check, lint, build; browser check; keyboard and empty and error states |
| S10 | Full SQLite suite; PostgreSQL if Docker is running; guard-removal checks (at least one per exclusion, plus authorization and immutability); ADRs; handoff in the mandatory format | Opus | Recorded in `PROGRESS.md` |

**ATT&CK:** each candidate is checked against its technique page on
attack.mitre.org during S1, and the ATT&CK version is recorded. If the text
doesn't support the mapping, it is `unmapped`.

**Effort estimate:** S1–S8 about 2–3 working sessions, S9 about 1, S10 about 1.
This is an estimate, and it depends on usage limits.

## 10. Out of scope for M1

- Sigma conversion (M3).
- Streaming or real-time detection.
- Correlation across sources.
- Triage, suppression and cases (Gate 4).
- Machine learning or an LLM anywhere in detection.
- Event purge (needs Gate 4's handling of alerts).
- Any claim of performance on real data (M2).

## 11. Risks

| Risk | Mitigation |
|---|---|
| Rules fit the fixture because one author wrote both | Pre-registration (S1), known misses (B-12 to B-14), parameters frozen before M2 |
| A perfect fixture score is read as accuracy | The report states what the fixture can show (§7) |
| Contracts drift from the code | The contract-agreement test |
| Alert links complicate a future purge | Recorded in the event contract §10; resolved with Gate 4 |
| PostgreSQL behaviour still unverified | Run the suite on PostgreSQL in S10 if Docker is running; otherwise stays BLOCKED |
| A model declines detection work | Switch to Opus; record it only if it is a genuine block on authorized work |
| Scope creeps into Gate 4 | D-4: alerts stay immutable; analyst state waits |

**Rollback:** `alembic downgrade c3e6a9b2d4f5` removes the three detection tables.
Events and everything else are untouched.
