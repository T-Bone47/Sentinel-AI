# Progress log

Status words: IMPLEMENTED (code exists), TESTED (automated test passes),
LIVE-VALIDATED (seen working in a real browser), BLOCKED, PLANNED.
Newest entry first.

## 2026-11-18 — Published; first CI run; Phase 1 docs (branch `feat/phase1-docs`)

- **Published.** With the owner's approval, `main` was force-pushed to the
  public `T-Bone47/Sentinel-AI`, replacing the October snapshot, which is kept
  locally as `refs/legacy/original-snapshot`.
  - Before the push, two local paths that showed the Windows username were
    removed from the docs and from both unpushed commits.
  - Pushed head: `dbb75b1`.
- **First CI run on GitHub for `dbb75b1`:**
  - Frontend CI: success.
  - Backend CI: **628 passed, 2 skipped** (SQLite), the same as locally.
  - GitHub detects the licence as Apache-2.0.
- **New docs:**
  - `SECURITY.md`: private reporting, scope, known open issues.
  - `docs/THREAT_MODEL.md`: STRIDE table with mitigations, evidence and
    residual risks, drawn from the code, the ADRs and findings R1–R10.
    Pending since S0.
  - README: the stale status block ("105 backend tests") replaced with a
    status table linked to its evidence.
- **Not done:** GitHub's private vulnerability reporting must be switched on
  in the repository settings (the owner's decision); `SECURITY.md` relies on
  it.

## 2026-11-18 — M0: PostgreSQL validation (branch `fix/pg-date-filter-utc`)

- **Environment:** a throwaway `postgres:16-alpine` container on
  `127.0.0.1:55432`, with in-memory storage and `--rm`; it was removed
  afterwards. Database timezone UTC, machine timezone IST.
- **Steps:** `alembic upgrade head`, the dataset load and the user seed all
  succeeded. `alembic check` found no drift.
- **First full run: 627 passed, 1 failed, 1 skipped.**
  - The failure was real, and only PostgreSQL shows it.
    `_parse_dt` (`resource_router.py`) built a *naive* datetime from
    `date_from` and `date_to`.
  - asyncpg reads a naive value as the server's local time, so on this IST
    machine "from 2026-07-01" became 30 June 18:30 UTC, and June rows leaked
    into a July query. SQLite compares strings, so it never showed this.
- **Fix:** the parser now returns UTC-aware datetimes; stored timestamps are
  UTC. The regression test `test_date_filters_are_read_as_utc` was watched
  failing before the fix.
- **After the fix:**

  | Database | Passed | Skipped | Failed |
  |---|---|---|---|
  | PostgreSQL | 629 | 1 | 0 |
  | SQLite | 628 | 2 | 0 |

  On PostgreSQL the immutability triggers, the Gate 2 and Gate 3 migrations
  and the alert store ran for the first time. The one PostgreSQL-only test
  that SQLite skips now runs and passes.
- **Gates 1–3:** the PostgreSQL condition is now met for the enumerated tests.
  Still not covered:
  - two real concurrent writers (the concurrency paths are still simulated);
  - CI on GitHub;
  - a deployment;
  - an independent review.
- **Noticed, not fixed:** a date-only `date_to=2026-07-31` means midnight at
  the start of 31 July, so the rest of that day is excluded. That is a
  separate behaviour change, needing its own decision.

## 2026-11-18 — M0: version control

- **First commit.** `git init` on branch `main`; the first commit holds this
  entry. It is local only: there is no remote and nothing was pushed.
  Rollback: delete `.git/`.
- **`.gitignore`:**
  - adds `*.egg-info/` and `.pytest_cache/`;
  - adds an exception that keeps the shipped Splunk `.log` sample, which the
    existing `*.log` rule would have dropped;
  - the backend's `.gitignore` was saved in UTF-16, which git cannot read. It
    is now UTF-8, with the same single rule.
- **`.gitattributes`:** `research/** -text`.
  - The pre-registration, the rule contracts, the fixtures and the Splunk
    samples are all pinned by SHA-256.
  - This machine's git converts line endings (`core.autocrlf=true`), which
    would change those hashes on checkout.
- **Secret scan** before the commit, reporting file names and counts only:
  - no private keys, provider tokens, JWTs or AWS secret keys;
  - AWS access-key IDs appear only in the Splunk CloudTrail samples: public
    lab data, with no secrets beside them;
  - the `dev-only` placeholder secret appears in `.env.example` and in tests
    that prove startup refuses it outside development;
  - the demo password is in `scripts/seed_users.py`, as documented;
  - every API-key entry in the `.env.example` files is empty.
- **Not committed:**
  - `node_modules/`, `dist/`, caches, `*.egg-info`, databases and `.env`
    files;
  - LANL, the M2 work folder and the email-domain backup, which live outside
    the repository.
- **From here,** work happens on `security/`, `feat/`, `research/` or `fix/`
  branches (CLAUDE.md §2).

## 2026-11-18 — M0: data provenance review

Done by Claude Opus 5.5. Local scripts printed schemas and aggregate counts
only: no dataset row was shown to an AI model or sent anywhere.

- **`docs/DATA_PROVENANCE.md` (new)** covers every kind of data in the
  repository.
  - **The 15 legacy CSVs (14,400 rows):** there is no record of their origin,
    licence or consent. There are strong signs of program generation, which do
    not prove it:
    - emails are `first.last@` one domain;
    - 500 names pair only 100 first names with 70 last names;
    - the audit-log IPs use 12 first octets, matching 12 locations;
    - referential integrity is perfect;
    - all dates end in early August 2026.
  - **Open risks:**
    - the email domain is a non-reserved `.com`;
    - vendor names may match real companies;
    - the logs hold public IP addresses.
  - **The other data:** the fixtures are seeded and reproducible (tested); the
    Splunk samples are Apache 2.0; LANL is CC0 and stays outside the
    repository; the frontend mock data was not reviewed.
- **"Real records" corrected** (CLAUDE.md finding 8):
  - corrected in the root and backend READMEs, `pyproject.toml`, the FastAPI
    description, one endpoint summary, and the ingestion, model and schema
    docstrings;
  - HANDOFF and IMPLEMENTATION_STATUS keep their history under a dated banner;
  - "real" was left where it means something else: a source's real id, the LLM
    planner prompt, and the genuinely real Splunk records.
- **Checks:** the edited modules import; nothing else ran (no behaviour changed).

**Owner decision, the same day.** The owner confirmed that the 15 datasets are
demo data they generated with ChatGPT, so they were kept rather than
regenerated.
- **Email domain:** replaced with the reserved `meridianfintech.example` in
  every text file: the employee CSV (500 replacements), `docs/profiling/` (14)
  and `docs/API_CONTRACT.md` (3). Binary files were skipped. The originals are
  backed up outside the repository.
- **Notice:** the new `sentinel-ai-backend/datasets/README.md` marks the data
  as fictional. The READMEs and the historical banners now say the same.
- **Checked:**
  - the test database was reloaded and holds 0 old-domain emails and 500 new
    ones;
  - full `pytest` (SQLite): **627 passed, 2 skipped, 0 failed**.

Any existing local database still holds the old domain until
`python -m app.ingestion.run` is run against it.

**Licence:** the owner chose Apache 2.0, and `LICENSE` is at the repository
root.
- The text was copied from the `bcrypt` package's distribution. The
  `opentelemetry-api` package ships the same wording; the two differ only in
  whitespace.
- The README now has a License section.
- Not done: `pyproject.toml` and `package.json` have no `license` field yet.

**Splunk samples:** the owner chose to ship them, with attribution.
- They are unmodified, with an attribution note in
  `research/external/splunk-attack-data/README.md`. Its file sizes and SHA-256
  values were checked against the files.
- The upstream repository has no `NOTICE` file: `NOTICE`, `NOTICE.txt` and
  `NOTICE.md` all return 404 on `master`.
- `.gitattributes` now marks `research/external/**` as `-text`, as it already
  did for the fixtures, so a Windows clone cannot change the pinned bytes.

**Still open:** a `.gitignore`, written before the first commit.

## 2026-11-17 — M2 results: IA-003 on LANL

```text
SENTINEL AI — M2 HANDOFF
Date/time (UTC): 2026-11-17T19:15Z. The run took 18:33–19:15: about
  35 minutes of extraction, then 7 minutes of scoring.
Model actually used: Claude Opus 5.5. No independent review.
Repository/branch/commit: not a git repository — no SHA.
Scope: build lanl.auth@1 and the benchmark exactly as registered in
  research/M2_PREREGISTRATION.md (SHA-256 3d977e98…), run it once, and report.
Environment: Windows 11, Python 3.12 venv, a new SQLite database for the run.
```

### Built

- **`lanl.auth@1`** in `app/events/adapters.py`, mapped as registered (§5).
- **`research/scripts/lanl_extract.py`:** the registered windows and seeded
  draws. It makes two streaming passes and uses the standard library only.
- **`research/scripts/run_lanl_benchmark.py`:** one command.
  - It refuses data or a registration whose SHA-256 differs from the
    registered value.
  - It caches the extraction, then ingests and runs the engine in a
    throwaway database.
  - It writes `metrics.json`, `records.jsonl` and `alerts.jsonl`. These hold
    line numbers and counts only.
- **Tests:**
  - the adapter's mapping, plus 6 refusals;
  - the extraction and measures on a hand-made miniature: window edges,
    candidate rules, the seeded draw, matching classes and every measure.
    Two deliberate breaks (a window starting one second late; a 60-minute
    look-back) were each caught.

### Results — `research/results/m2/20261117T183312Z/`

| Measure | Result |
|---|---|
| Red-team records | 749 lines, 715 distinct. 701 are evaluable (class c) and 14 have no matching line (class a). Classes b and d are empty |
| **Strict recall (primary)** | **5 of 701 = 0.0071** (Wilson 95%: 0.0031–0.0166) |
| **Comparison alert rate (primary)** | 12 alerts in 2,145 comparison windows, which is 5.6 per 1,000 windows, or 2.0 per 10,000 successful `LogOn` events (59,377) |
| Prediction P1 (recall below 0.10) | **Held** |
| Failures (any type) by the account in the 30 minutes before a red-team record | None before 513 records, 1–4 before 170, and 5 or more before 32 (of 715) |
| IA-003 alerts on red-team accounts that are not on a labelled line | 22, listed in `alerts.jsonl` for review |
| Other rules | 0 alerts. IA-002 was not evaluable on 184,828 successful sign-ins, as expected: LANL has no privilege data |
| Accounting | 502,698,003 lines read, up to the end of the last window. 459,174 lines kept and ingested: 0 rejected, 0 duplicates, 0 conflicts. 2,335 windows (216 red-team, 2,119 comparison), none over 50,000 events, so 2,335 engine runs |

### What it means

- **IA-003 version 1 misses almost every red-team compromise sign-in in LANL.**
  At the upper end of the 95% interval it still misses over 98%. This is the
  negative result the registration predicted.
- **Counting only `LogOn` is not the cause.**
  - No failed authentication of any kind preceded 72% of red-team records
    (513 of 715) by 30 minutes or less.
  - Only 31 of the 701 evaluable records had five or more failures in that
    time.
  - So a version that counted every kind of failure would detect at most
    4.4%.
- **The 5 detections followed 5, 5, 7, 5 and 16 failed `LogOn`s.** The labels
  do not say whether the red team caused those failures. A user mistyping, or
  a stale stored password, looks the same.
- **Exploratory, not registered:** IA-003 raised 27 alerts on red-team
  accounts (5 on labelled lines, 22 not) and 12 on comparison accounts in
  their scoring regions. No rate is claimed from that contrast. The 22 are
  either benign or unlabelled red-team activity, and need a look.

### Deviation from the registration

**Raw alert export.** §7 put it in the results folder, but §4 publishes only
counts and line numbers, and the export names accounts. It is kept in the work
folder beside the data, outside the repository. The results folder holds the
same 44 alerts as rule, window, trigger line and context lines. No other
deviation was found.

### Test results (measured)

| Check | Result |
|---|---|
| Backend `pytest` (SQLite) | **627 passed, 2 skipped, 0 failed** (619 + 8 new) |
| Benchmark | Exit 0. All three registered hashes verified before the run |
| PostgreSQL | **BLOCKED** (deferred by the owner) |

### Known gaps

- The rules, the registration and the code have the same author; nothing has
  been reviewed independently.
- SQLite only. One run, at version-1 parameters, with no tuning.
- Comparison accounts are user accounts active in the same windows. Machine
  accounts were not sampled.
- The 14 unmatched red-team records were not investigated. As registered,
  there is no fallback matching.

**Report:** `research/M2_REPORT.md` covers the LANL result, which rules public
data can test, and the adapters on real records. The PRD marks M2 complete on
SQLite.

**Next (PRD §8):**
1. M0 data-publication decision: Claude writes `docs/DATA_PROVENANCE.md`; the
   owner decides.
2. Version control.
3. PostgreSQL.
4. M3 upstream contributions.
5. An independent look at the 5 hits and the 22 unlabelled alerts.

## 2026-11-17 — M2 pre-registration (LANL)

Recorded at 2026-11-17T18:14Z by Claude Opus 5.5. This was **before** the LANL
adapter existed, before any extraction, and before any rule ran on LANL data.
Any later change to the file must show up as a hash mismatch against this entry.

```text
3d977e98ed5f17e5f3c1b370dcffddbe19efcf5bd7ca43ad8c0c258ed8cdd82c  research/M2_PREREGISTRATION.md
```

**Data pinned.** The owner downloaded both files on 2026-11-17; they are kept
outside the repository.

```text
9c6b0cc261b0edd19324f6fd1839743224938a7f644ed202ca70bd70a89bf672  auth.txt.gz     7,626,505,158 bytes, 1,051,430,459 lines
606635837c684ad11e464075ecf97bc5df325ff7d7f64614d2d8c8af18051669  redteam.txt.gz  4,846 bytes, 749 records
```

`auth.txt.gz` decompressed end to end with no error, which shows the download
is complete.

- **Rules unchanged:** the contracts IA-001 to IA-005 and the rules README still
  match their Gate 3 hashes, checked at registration.
- **Registered prediction:** IA-003 recall on evaluable red-team records is
  below 0.10. No prediction is made for the false-alarm rate.
- **Seen before registering** (the document's §3 lists it):
  - file metadata and the line count;
  - three format lines;
  - red-team summary counts.

  No authentication event was joined to a red-team record.
- **Change from the shortlist's outline:** only `LogOn` lines become sign-ins.
  Failures in every orientation are still counted, as a separate measure. The
  document supersedes the outline.
- **Caveat:** the plan and the rules have the same author. Registration makes
  later changes visible; it does not make the evaluation independent.

**Next:**
1. Build `lanl.auth@1` exactly as §5 specifies.
2. Then the extraction and a one-command benchmark, with results in
   `research/results/m2/`.

## 2026-11-17 — M2 groundwork: real-data tests pinned, Entra ID adapter

```text
Date/time (UTC): 2026-11-17T10:40Z
Model actually used: Claude Opus 5.5. No independent review.
Repository/branch/commit: not a git repository — no SHA.
Scope: the three steps handed over by the previous session —
  (1) pin the three IAM CloudTrail checks as tests,
  (2) build the Entra ID adapter,
  (3) write and hash the M2 pre-registration once LANL is available.
Environment: Windows 11, Python 3.12 venv recreated in the session scratchpad,
  SQLite scratch database; no new migration.
```

### What was built

- **Pinned tests.** `test_cloudtrail_adapter_reads_real_iam_deletions` runs once
  per IAM file. It checks the SHA-256, the record count, the `other` mapping,
  failures counted by `errorCode`, that no rule fires, and the ingest counts.
- **Adapter `entra.signin@1`** in `app/events/adapters.py`, with its mapping in
  `docs/EVENT_CONTRACT.md` §7.
  - The command line, the ingest API and detection runs pick it up from the
    adapter registry (the command line's `--help` lists it).
  - Tested on hand-built records (mapping, and 7 refusals) and on the real
    Splunk file, pinned by hash.
- **Refactor.** CloudTrail's IP check moved into a helper shared by both
  adapters. Behaviour is unchanged and the CloudTrail tests are untouched.

### Findings

- **Duplicate records.** Two IAM files repeat records verbatim (same `eventID`,
  identical content). The 259 records hold 245 distinct events, so ingest
  stores 245 and counts 14 duplicates. The shortlist said "all 259 normalized";
  it is corrected there.
- **IA-002 has no public test data.** Entra ID sign-in logs give MFA
  (`authenticationRequirement`) but no privilege field, so IA-002 cannot be
  evaluated on them alone. The shortlist had assumed it could; also corrected.
- **The Entra file cannot test a rule.** It holds 30 failed password sign-ins
  (code 50126) by one user within 11 seconds, and no success, so IA-003 cannot
  fire on it. It tests the adapter only.

### Test results (measured)

| Check | Result |
|---|---|
| Backend `pytest` (SQLite) | **619 passed, 2 skipped, 0 failed**: 606 at the S3 handoff, plus the ConsoleLogin test added after it, plus 12 new |
| Mutation check | 2 deliberate breaks, each caught: MFA mapping swapped (fails the mapping test); `DeleteGroup` mapped to `privilege.revoke` (fails both group-deletion tests) |
| Lint | Not run: ruff is not installed in the venv |
| Frontend | Not changed, not re-run |
| PostgreSQL | **BLOCKED** (deferred by the owner) |

### Step 3: BLOCKED (cleared later the same day; see the entry above)

LANL is not on this machine. the planned LANL dataset folder does not exist, and
no `auth.txt*` or `redteam.txt*` is in Downloads or on the Desktop. As
instructed, the M2 pre-registration was not written.

### Known gaps

- Entra success and MFA mappings have seen hand-written records only.
- Entra gives interrupted sign-ins a non-zero code (for example 50074, an MFA
  prompt), and the adapter maps every non-zero code to `failure`. IA-003 could
  therefore count MFA prompts as failed sign-ins. Not measured on real data.
- No rule has been scored on public data, and no rule changed.

### Owner actions

- **New:** download LANL `auth.txt.gz` and `redteam.txt.gz` (the form asks for
  your email and intended use) and tell me the path.
- **As before:** PostgreSQL, `git init`, independent review, fixture licence.

**Gate verdicts unchanged** (Gate 3 CONDITIONAL). This entry is M2 groundwork
and closes no gate.

**Next:** once LANL is on disk, write and hash the M2 pre-registration before
any LANL scoring, then build `lanl.auth@1`.

## 2026-11-17 — Sprint S3: detection engineering (Gate 3)

```text
SENTINEL AI — SPRINT S3 HANDOFF
Date/time (UTC): 2026-11-17T09:55Z
Model actually used: Claude Opus 5.5 for every step, including the screen
  (the plan assigned S9 to Fable). No independent review of Gate 3 yet.
Repository/branch/commit: not a git repository — no SHA.
Goal and scope: PRD milestone M1 — five detection rules with pre-registered
  contracts, immutable alerts that cite their events, a deterministic engine,
  an evaluation against labels, a Detections screen, and finding F8.
Environment: Windows 11, Python 3.12 venv, SQLite scratch database at Alembic
  head d4f7b0c3e5a6, Node 26.12.1.
```

### What was built

- **Rules:** IA-001 to IA-005 (`app/detections/rules.py`), each with a contract
  in `research/rules/`, pre-registered and hashed before any code (entry below).
- **Alert store:** `detection_runs`, `detection_alerts` and
  `detection_alert_events` (migration `d4f7b0c3e5a6`). Alerts and their links
  refuse `UPDATE`.
- **Engine:** `app/detections/engine.py`. It is deterministic, replay-safe and
  bounded at 50,000 events per run, and it records every run, including failed
  ones.
- **Interfaces:**
  - command line `python -m app.detections run|export`;
  - API `/api/v1/detections/{rules,runs,alerts}`;
  - a Detections screen.
- **Permissions:** two new matrix resources. `detection-rules` is readable by
  all staff. `detections` is readable by internal staff, and only admin and
  security analyst may start a run.
- **Boundary fixture:** `identity-access-boundary-v1`, with 15 edge cases and 3
  known misses.
- **Evaluation:** an evaluator and a one-command benchmark
  (`research/scripts/run_detection_benchmark.py`).
- **Finding F8 fixed:**
  - the monitoring API no longer returns `monitoring_status: "Active"`;
  - the service docstring no longer claims real-time;
  - the header's pulsing **"Live"** badge now reads "Retrospective analysis".

### Gate 3 pass conditions

| Condition | Status | Evidence |
|---|---|---|
| Positive and negative cases for every detector | TESTED | 33 contract test vectors over two fixtures, plus unit tests on hand-built events |
| Repeatable results | TESTED | The benchmark run twice gives identical metrics; a second run creates 0 alerts; shuffled input gives the same findings |
| Alerts traceable to source evidence | TESTED, LIVE-VALIDATED | Every cited event resolves through the events API and its hash recomputes; the screen shows trigger and context with hashes |
| Severity and confidence separate; ATT&CK only where defensible | DONE | Contracts; mappings checked against ATT&CK v20.1, IA-002 `unmapped` |
| Monitoring states retrospective vs live accurately | TESTED, LIVE-VALIDATED | F8 fixes above |
| Gate 2 alert-level conditions: replay gives zero duplicate alerts; every alert's records explained | TESTED | Benchmark replay: 0 events inserted, 0 alerts created |

### Results

Run: `research/results/gate3/20261117T094848Z/`.

| | Result |
|---|---|
| Pre-registered test vectors | **33 of 33** hold |
| `identity-access-v1` | 7 alerts citing exactly the 7 trigger events. Every rule's precision and recall is 1.00 — **conformance by construction**, not accuracy |
| Sentinel's earlier failure-only monitoring | Flags 35 events and catches **0 of 7** trigger events |
| Rules with their exclusions removed | Still find all 7, with far more false alarms: IA-002 38 alerts (37 false), IA-003 17 (16 false), IA-001 7 (5 false) |
| `identity-access-boundary-v1` | 5 alerts as pre-registered. The 3 known misses (B-12 cross-source, B-13 and B-14 missing attributes) appear as measured misses: recall IA-004 0.50, IA-001 0.00, IA-002 0.00 |

These are synthetic fixtures written by the same author as the rules. No claim is
made about real-world performance.

### Test results (measured)

| Check | Result |
|---|---|
| Backend `pytest` (SQLite) | **606 passed, 2 skipped, 0 failed** (507 + 99 new) |
| Guard-removal check | 13 guards removed one at a time; each caught |
| `alembic check` | No drift |
| Frontend | `tsc` 0, lint 0 errors (4 existing warnings), build OK |
| Browser | Security analyst signed in, ran the rules on `identity-access-v1` (196 events, 7 new alerts) and opened an alert's evidence; no console errors |
| PostgreSQL | **BLOCKED** (deferred by the owner) |

### Changes worth knowing

- `tests/test_intelligence.py` asserted the inaccurate
  `monitoring_status: "Active"`; it now asserts `mode: "retrospective"`.
- **Plan amendment:** before pre-registration the plan was amended to one
  trigger per alert, so the main fixture expects 7 alerts instead of 6. The
  reasons are at the top of the plan.

### Known gaps and unverified claims

- PostgreSQL: none of the three new tables, their triggers, or the alert-insert
  retry path has run on PostgreSQL.
- Correlation across sources is not supported (known miss B-12).
- No triage, suppression or case workflow: Gate 4.
- No purge, and alerts restrict event deletion on PostgreSQL by design.
- The screen lists at most 200 alerts and has no paging; it was checked by
  scripted clicks with the preview pane hidden, with no keyboard-only or mobile
  check.
- The fixtures and the rules have the same author. M2 (public data) is the real
  test.

### Owner actions

As before:
- run on PostgreSQL;
- decide on `git init`;
- arrange an independent review;
- choose a licence for the fixtures and rules.

New: existing local databases need `alembic upgrade head`.

**Gate verdict: CONDITIONAL** — every Gate 3 condition is met and tested on
SQLite; PostgreSQL validation and independent review are outstanding.

**Next:** PRD milestone M2, evaluation on a licensed public dataset. That needs
your approval for the dataset download and a licence check first.

## 2026-11-17 — Gate 3 pre-registration (step S1)

Recorded at 2026-11-17T09:30Z, **before** any detection code or the boundary
fixture existed. Changing any of these files later must be visible as a hash
mismatch against this entry.

```text
9803e0d63cbdcde44548dfdc9de73e51ee54240f0235df6271471ff187335f35  research/rules/IA-001.toml
c870dd629d5670d7b325e933e07e2f6f1c64c12c6bb6da5987798b90c2d44aba  research/rules/IA-002.toml
c7609340c864df65f9badf48fe2341fa6d4fa5b434b8f9661b05cf7209f6a466  research/rules/IA-003.toml
415961299b42b9fd52e5af7ee042f3b3470c9b367a6d41cf4421828f92b99182  research/rules/IA-004.toml
7cf327ad20b7d50ee2c20886536487d7679305c2b2d825dc99c0773a3a546f3c  research/rules/IA-005.toml
aad0dd98eb9c5954eedd37097a0990eb60b3d9254fcca4ade7eecad25abaef0e  research/rules/README.md
```

**Pre-registered expectations:**
- **`identity-access-v1`:** 7 alerts.
- **`identity-access-boundary-v1`:** 5 alerts, with 3 known misses (B-12, B-13, B-14).
- **Test vectors:** 33 across the five rules.

**ATT&CK:** checked against content v20.1. The plan was amended once beforehand,
with the reasons stated at the top of `docs/PLAN_GATE3_DETECTIONS.md`.

**Caveat:** the same author wrote the fixtures and the rules. Pre-registration
makes later changes visible; it does not make the evaluation independent.

## 2026-11-17 — Review pass: Gates 1 and 2

```text
SENTINEL AI — REVIEW HANDOFF
Model actually used: Claude Opus 5.5, reviewing code written by Claude Fable 5.2.
  Same conversation, so the reviewer could see the author's reasoning. This is
  a separate model pass, not an independent review by another person.
Repository/branch/commit: not a git repository — no SHA.
```

**Scope reviewed:** sign-in, sessions and refresh rotation; the permission matrix
and every route guard; employee row scoping; section withholding in the detail,
dashboard and graph views; the AI engine's table gate; the event contract, store
and API; startup configuration.

**Not reviewed:** the frontend beyond the session code, and the CloudTrail mapping
against real data (none is available). PostgreSQL is still not run.

**Checked and found sound:** no per-person data reaches the auditor through the
dashboard, Copilot answers, the aggregated graph or risk explanations; the role is
always read from the database; refresh rotation is atomic; the events API cannot
modify events.

### Findings

| ID | Severity | Finding | Status |
|---|---|---|---|
| R1 | P2 | The bcrypt password check ran on the event loop. One sign-in attempt stalled every other request for ~0.25 s, and Gate 1's dummy hash made that true for unknown emails too, so a few requests per second could freeze the API | TESTED fixed: runs in a thread. Measured before the fix: a health check waited 0.60 s behind one slowed check |
| R2 | P2 | Lockout bypass: the throttle evicted its oldest entry when full, so failing on 10,000 throwaway emails lifted any lock | TESTED fixed: active locks are evicted last |
| R3 | P2 | Refresh-token reuse and account lockouts were handled but never logged | TESTED fixed: warnings on logger `sentinel.auth` with user/session UUIDs or a 12-character email hash; no tokens or emails |
| R4 | P3 | Event text accepted invisible formatting characters (bidirectional overrides, zero-width spaces, C1 controls) that make an id display as something else | TESTED fixed: refused by the contract |
| R5 | P2 | `render.yaml` sets no `DATABASE_URL_SYNC` and passes Render's `postgres://` URL unconverted. It could not migrate before Gate 1; now the app also refuses to start, because the sync URL falls back to the demo credentials | OPEN — owner decision on deployment |
| R6 | P2 | Each sign-in attempt still costs one bcrypt check of CPU, and there is no per-address rate limit | OPEN — rate-limit at the reverse proxy before any deployment (ADR-004) |
| R7 | P3 | API docs and the OpenAPI schema are public in every environment | OPEN |
| R8 | P3 | A disabled account answers 403 only after a correct password, which confirms the password | OPEN |
| R9 | P3 | Trust measurement de-duplication is check-then-insert; two simultaneous measurements can write two identical rows | OPEN |
| R10 | P3 | The AI conversation store's 500-entry bound is shared, so one user can push out another's conversations | OPEN |

### Test results

| Check | Result |
|---|---|
| Backend `pytest` (SQLite) | **507 passed, 2 skipped, 0 failed** (499 + 8 new) |
| New tests watched failing first | 7 of 8; the eighth (zero-width space) was not selected by the filter on the first run and passes now |
| Fixture `--check` | Up to date |
| PostgreSQL | **BLOCKED** — the Docker engine was not running (client present, no server) |

API behaviour changes: none for callers. Text containing the characters in R4 is now
rejected as `invalid_record`.

**Verdicts unchanged:** Gates 1 and 2 remain CONDITIONAL on PostgreSQL validation.

**Next:** program requirements are in `docs/PRD_CVP_DEFENSE_ACCESS.md`; the next
build is milestone M1 (Gate 3), planned step by step in
`docs/PLAN_GATE3_DETECTIONS.md`. Nothing in that plan has started.

## 2026-11-16 — Sprint S2: event contract, ingestion and provenance

```text
SENTINEL AI — SPRINT S2 HANDOFF
Date/time (UTC): 2026-11-16T23:40Z
Model actually used: Claude Fable 5.2 for all of this sprint. CLAUDE.md assigns
  the Gate 2 pipeline to Opus; no independent review of this work has happened.
Repository/branch/commit: not a git repository — no branch, no commit, no SHA.
  Rollback: Sentinel-AI-main.zip in the Downloads folder is the pre-Gate 1
  state. There is no snapshot of the state after Gate 1.
Goal and scope: Gate 2 — a versioned security-event contract, idempotent
  ingestion with provenance, a labelled synthetic fixture, and trust history
  written only by explicit measurements.
Environment: Windows 11, Python 3.12 venv, SQLite scratch database at Alembic
  head c3e6a9b2d4f5. The frontend was not changed and not re-run this sprint.
```

### What was implemented

- **Event contract v1** (`docs/EVENT_CONTRACT.md`, `app/events/contract.py`):
  strict fields, a 14-action vocabulary, 7 typed attributes, timestamps that
  must carry a timezone.
- **Event store** (`app/models/events.py`, `app/events/store.py`): one immutable
  row per source record, an id derived from the record's source, canonical JSON
  of the source record with its SHA-256, one batch row per ingestion run, one
  reject row per refused record.
- **Two adapters** (`app/events/adapters.py`): `sentinel.native@1` and
  `aws.cloudtrail@1`.
- **Ingestion paths**: `POST /api/v1/security-events/ingest` (admin) and
  `python -m app.events ingest FILE.jsonl` (local operator).
- **Read API**: event list in event-time order with cursor paging, event detail
  with the source record, ingestion batches with reject reasons.
- **Fixture** `identity-access-v1` and its deterministic generator.
- **Trust history fix** (finding F7): reads no longer write; measurements are
  explicit, de-duplicated and attributed.

### Gate 2 pass conditions

| Condition | Status | Evidence |
|---|---|---|
| Replay the same fixture twice with zero unintended duplicates | TESTED for events. **Not applicable to alerts yet**: no detector exists until Gate 3 | First run 197 received / 194 inserted / 3 duplicates; second run 0 inserted / 197 duplicates |
| Explain every alert's originating records | Groundwork TESTED: every event traces to its source record, batch, adapter version and hash. Alert-level: Gate 3 | `test_event_can_be_traced_from_the_api_back_to_its_source_record` |
| Migrations reversible or well documented | TESTED on SQLite | Downgrade to `a1c4e7d90b12` and re-upgrade on a copy: tables and trigger removed and restored, 58 trust-history rows preserved; `alembic check` reports no drift |
| No cross-role data leaks | TESTED on the enumerated cases | Auditor and employee get 403 on events and batches; only admin can ingest; events are not on the AI engine's table list |

### Findings status

| ID | Finding | Status |
|---|---|---|
| F7 | Reading Trust Intelligence wrote a snapshot | TESTED fixed. Old rows kept and marked `legacy_on_read` |
| F8 | "Real-time" wording for retrospective queries | OPEN (P2), Gate 3 |
| F9 | Optional LLM egress undisclosed | OPEN (P2) |
| F10 | Hard-coded confidence values | OPEN (P2) |

### Files

New (backend): `app/models/events.py`, `app/events/{__init__,contract,adapters,store,__main__}.py`,
`app/api/v1/routers/events_router.py`,
`migrations/versions/b2d5f8a1c3e4_add_security_events.py`,
`migrations/versions/c3e6a9b2d4f5_trust_measurement_provenance.py`,
`scripts/record_trust_measurement.py`, `tests/test_gate2_events.py`,
`tests/test_gate2_trust_measurements.py`.

New (research and docs): `research/scripts/build_identity_access_fixture.py`,
`research/fixtures/identity-access-v1/{events.jsonl,labels.jsonl,malformed.jsonl,replay-conflict.jsonl,MANIFEST.json,README.md}`,
`docs/EVENT_CONTRACT.md`, `.gitattributes`.

Changed: `app/models/__init__.py`, `app/models/trust.py`, `app/core/permissions.py`,
`app/main.py`, `app/api/v1/routers/intelligence_router.py`,
`app/services/trust_intelligence.py`, `app/ingestion/run.py`,
`tests/test_intelligence.py`, `docs/DECISIONS.md` (ADR-005 to ADR-009), this file.

### Test results (measured, this environment)

| Check | Result |
|---|---|
| Backend `pytest` (SQLite) | **499 passed, 2 skipped, 0 failed** (409 before this sprint + 90 new) |
| Guard-removal check | 13 guards removed one at a time; each made the new tests fail |
| `alembic check` | No difference between models and migrations |
| Fixture generator | Reproduces the frozen files byte for byte |
| Fixture through the command line | Counts equal `MANIFEST.json`; a second run inserts 0; batch totals balance (425 received = 196 stored + 202 duplicates + 1 conflict + 26 rejected) |
| Dataset loader | Ends with a trust-measurement line; exit 0 |
| PostgreSQL | **BLOCKED** — see below |
| Frontend | Unchanged; not re-run |

### Research results and fixture ids

- Fixture `identity-access-v1`, generator version 1, seed 20261117.
  `events.jsonl` SHA-256 `9c9e1b7f8f0053b58c8987d45f4118a92e8db46f209900f0fb6893aaa4112e5f`.
- 194 events, 19 scenarios in 5 families plus background; 15 events in
  suspicious scenarios and 179 in benign ones; 7 trigger events, 12 decoys.
- **No detection metrics exist.** There are no detectors yet, so nothing has been
  scored against these labels.

### Security and privacy decisions

- Events are per-person activity records: readable by admin, compliance officer
  and security analyst only. Only an admin can ingest through the API.
- Rejected records are never stored or echoed, only their hash, position and the
  names of the fields that broke the contract.
- Ground-truth labels are never ingested (ADR-007).
- The legacy `audit_logs` data is not carried into the new pipeline (ADR-009).

API contract changes: new `/security-events*` endpoints; new `POST` and `GET
/intelligence/trust/measurements`; the `score_change.status` strings returned by
`GET /intelligence/trust` changed. `python -m app.ingestion.run` now exits 1 if the
data loaded but the trust measurement could not be recorded (for example on an
unmigrated database).

### Known failures and unverified claims

- **PostgreSQL: BLOCKED.** A disposable `postgres:16-alpine` container was to be
  used (the image is already on this machine), but the Docker engine was not
  running when validation was attempted. The PostgreSQL version of the
  immutability trigger, both new migrations and the concurrent-writer path have
  never run on PostgreSQL. The Gate 1 PostgreSQL items are still open too.
- The CloudTrail adapter has only seen hand-written synthetic records.
- The concurrent-writer path is tested by simulating a stale look-up, not with
  two real writers.
- No screen shows events yet; they are reachable through the API only.
- No purge, and no rate limit on the ingest endpoint.
- One existing test, `test_trust_intelligence_score_change_is_real_not_fabricated`,
  was rewritten because it asserted the write-on-read behaviour.
- The test suite adds measurement rows to the trust history of whatever database
  it runs against.
- The fixture and the rules that will be tested on it have the same author.
- Still PLANNED from S0: `THREAT_MODEL.md`, `DATA_PROVENANCE.md`, the other audit
  documents, and correcting "real records" in the README.

### Owner action required

1. Start Docker Desktop (or provide a disposable PostgreSQL) so the suite can run
   on PostgreSQL. This clears the BLOCKED items for Gates 1 and 2.
2. Decide whether to `git init` and commit. There is still no version history.
3. Arrange an independent review (Opus pass) of the Gate 1 and Gate 2 code.
4. Existing local databases: run `alembic upgrade head`.
5. Choose a licence for the fixture before anything is published.

**Gate verdict: CONDITIONAL** — every event-level condition is met and tested on
SQLite. The two alert-level conditions cannot be met before detectors exist, and
PostgreSQL validation and independent review are outstanding.

**Next safest task:** Gate 3 — a small rule engine over this contract, one
written rule contract per fixture family, alerts that cite `event_id`s, and an
evaluator that joins alerts to `labels.jsonl` outside the database.

## 2026-11-16 — Sprint S1: identity, authorization, session isolation

```text
SENTINEL AI — SPRINT S1 HANDOFF
Date/time (UTC): 2026-11-16T18:25Z
Model actually used: Claude Fable 5.2 for all implementation in this sprint.
  (The S0 review on 2026-11-13 ran on Claude Opus 5.5.) CLAUDE.md assigns
  Gate 1 to Opus; no independent Opus review of this work has happened.
Repository/branch/commit: not a git repository — no branch, no commit, no SHA.
  Rollback: the original Sentinel-AI-main.zip in the Downloads folder.
Goal and scope: Gate 1 — remove auto-admin sign-in, enforce role and
  object-level authorization on every route, revocable sessions, brute-force
  control, startup config validation, private AI conversation memory.
Environment: Windows 11, Python 3.12 venv, Node 26.12.1 / npm 11.20.0,
  SQLite scratch database (alembic head a1c4e7d90b12 + ingestion + seed).
```

### Findings status (IDs from the 2026-11-13 review)

| ID | Finding | Status | Evidence |
|---|---|---|---|
| F1 | Frontend silently signed in as admin | TESTED, LIVE-VALIDATED | `src/App.tsx`; built bundle contains neither the demo password nor the admin email (grep, 0 files) |
| F2 | No role or object authorization | TESTED | `app/core/permissions.py`; 160 tests in `tests/test_gate1_security.py` |
| F3 | Insecure defaults, no startup validation | TESTED | `app/core/config.py`; ADR-003 |
| F4 | No logout, no revocation, no brute-force control | TESTED | `auth_sessions` table, `app/core/login_throttle.py` |
| F5 | Tokens in `localStorage` | MITIGATED, not removed | ADR-002 |
| F6 | AI conversation memory shared across users | TESTED | `app/services/conversation_store.py` |
| — | Validation errors echoed submitted input (password) | TESTED | `app/main.py` |
| F7 | Reading Trust Intelligence writes a snapshot | OPEN (P2) | not touched |
| F8 | "Real-time" wording for retrospective queries | OPEN (P2) | not touched |
| F9 | Optional LLM egress undisclosed | OPEN (P2) | not touched |
| F10 | Hard-coded confidence values | OPEN (P2) | not touched |

### Files

New: `app/core/permissions.py`, `app/core/login_throttle.py`,
`app/services/conversation_store.py`,
`migrations/versions/a1c4e7d90b12_add_auth_sessions.py`,
`tests/test_gate1_security.py`, `src/contexts/AuthContext.tsx`,
`src/pages/Login.tsx`, `docs/DECISIONS.md`, `docs/PROGRESS.md`.

Changed (backend): `app/core/config.py`, `app/core/security.py`, `app/main.py`,
`app/models/auth.py`, `app/models/__init__.py`, `app/repositories/base.py`,
`app/services/resource.py`, `app/services/grc_engine/reasoning_service.py`,
`app/api/v1/resources.py`, `app/api/v1/routers/{auth,resource,detail,dashboard,intelligence}_router.py`,
`scripts/seed_users.py`, `tests/conftest.py`, `.env.example`.

Changed (frontend and CI): `src/App.tsx`, `src/services/{http,api,types}.ts`,
`src/components/layout/{Header,Sidebar}.tsx`, `src/data/navigation.ts`,
`.github/workflows/backend-ci.yml`.

### Test results (measured, this environment)

| Check | Result |
|---|---|
| Backend `pytest` (SQLite) | **409 passed, 2 skipped, 0 failed** (249 existing + 160 new) |
| Mutation check | 6 guards removed one at a time; each made the new tests fail |
| `npx tsc --noEmit` | exit 0 |
| `npm run lint` | exit 0; 0 errors, 4 `react-refresh` warnings |
| `npm run build` | exit 0 |
| Browser (dev servers, built-in browser) | deep link `/risk` shows sign-in; wrong password shows an error; admin signs in and lands on `/risk`; sign-out returns to sign-in and the old token gets 401; employee sees 6 nav items, 403 message on `/risk`, 1 employee record |

API contract changes: `/auth/refresh` now also returns `refresh_token` (rotated);
new `POST /auth/logout`, `DELETE /ai/conversations/{id}`; `/auth/me` adds
`permissions`; `/ai/query` adds `conversation_id`; employee and application
detail add `withheld`. Rollback of the schema change: `alembic downgrade 3e5422bdcfdf`.

### Known failures and unverified claims

- **PostgreSQL: BLOCKED.** Nothing here has run against PostgreSQL. The new
  migration and the atomic refresh rotation are untested there.
- **CI: unverified.** The workflow edit has not run on GitHub.
- Browser run: the preview pane was hidden, so the forms were filled through the
  page and submitted by script, not by real clicks. No keyboard-only or mobile check.
- Coverage is the enumerated cases in the test file, not a proof of every
  input. Staff roles differ only where the matrix says; aggregates (counts,
  rollups) are visible to every staff role by design.
- Profile, Settings and the sidebar still show an invented person and company
  ("Dana Okafor", "Northwind"); nav badges "4" and "23" are hard-coded.
- No structured logging or PII redaction in logs yet (Gate 1 item 7, partial).
- `docs/THREAT_MODEL.md`, `DATA_PROVENANCE.md` and the other S0 audit files
  are still PLANNED.

### Owner action required

1. Decide whether to `git init` and commit — there is no version history.
2. Provide a disposable PostgreSQL to clear the BLOCKED items.
3. Arrange an independent review (Opus pass) of the authorization code.
4. Existing local setups: add `ENVIRONMENT=development` to `sentinel-ai-backend/.env`
   and run `alembic upgrade head`.

**Gate verdict: CONDITIONAL** — all Gate 1 behaviours are implemented and tested
on SQLite; PostgreSQL validation, independent review and log redaction remain.

**Next safest task:** S0 leftovers (`THREAT_MODEL.md`, `DATA_PROVENANCE.md`,
correcting "real records" in the README), then Gate 2 event contract.
