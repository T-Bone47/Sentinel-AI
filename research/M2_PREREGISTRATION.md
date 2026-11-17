# M2 pre-registration: IA-003 on LANL authentication data

*Registered 2026-11-17 by Claude Opus 5.5, before any rule ran on LANL data.
Its SHA-256 is recorded in `docs/PROGRESS.md`, so any later edit shows up as a
mismatch. Deviations are reported with the results, never edited in here.*

## 1. Question

Does rule IA-003, unchanged since its Gate 3 registration, detect the red-team
compromise authentications in LANL's enterprise data? And how often does it
fire on activity that is not labelled red team?

## 2. Predictions

- **P1:** IA-003 detects few or none of the red-team records: strict recall
  (§6) below 0.10. Red teams mostly sign in with valid stolen credentials
  rather than by guessing passwords, and IA-003 looks only for guessing.
- **P2:** none. There is no basis for predicting the false-alarm rate; it is
  measured.

Either outcome is reported. A low recall is the expected and useful result: a
rule that is correct on its own terms can still miss the attack that happened.

## 3. What was seen before registering

**LANL:**
- the file names, sizes and SHA-256 hashes (§4);
- the line count of `auth.txt`, 1,051,430,459. It comes from one full
  decompression that reported no error, which shows the download is complete;
- the first three lines of `auth.txt`, read to confirm its format;
- summary counts of `redteam.txt`: 749 records, 104 users, 4 source computers,
  301 destination computers, and times from 150,885 to 2,557,047.

**Not seen:** no authentication event has been joined to a red-team record, and
no rule has run on LANL data.

**Splunk samples:** all five were read through the adapters and the rules, so
the result is already known: no rule fires on any of them (§9).

**Rules:** written and registered before any public data was seen, and frozen
at version 1.

## 4. Data

| File | Bytes | SHA-256 |
|---|---|---|
| `auth.txt.gz` | 7,626,505,158 | `9c6b0cc261b0edd19324f6fd1839743224938a7f644ed202ca70bd70a89bf672` |
| `redteam.txt.gz` | 4,846 | `606635837c684ad11e464075ecf97bc5df325ff7d7f64614d2d8c8af18051669` |

- **Source:** LANL, "Comprehensive, Multi-Source Cyber-Security Events",
  csr.lanl.gov/data/cyber1/. Licence CC0 1.0, as recorded in
  `docs/M2_DATASET_SHORTLIST.md`.
- **Storage:** the owner downloaded the files on 2026-11-17. They are kept
  outside the repository and are never committed or redistributed.
- **What is published:** derived counts and LANL line numbers only.
- **Credit:** A. D. Kent, "Cybersecurity Data Sources for Dynamic Network
  Research," in *Dynamic Networks in Cybersecurity*, Imperial College Press,
  2015. This is the paper the dataset page asks users to cite.

## 5. Method

### Adapter `lanl.auth@1`

It is built after registration, as written here. Each line of `auth.txt`
becomes one event:

| Event field | From |
|---|---|
| `source_event_id` | The line's number in `auth.txt`, counting from 1. Lines have no id of their own, and identical lines are separate events |
| `occurred_at` | 1970-01-01T00:00:00Z plus the line's time in seconds. LANL's real start date is undisclosed, so only intervals mean anything |
| actor | The source user. Type `user` for `U<digits>@…` accounts, otherwise `unknown` |
| target | The destination computer, type `resource` |
| action | `auth.login` when the orientation is `LogOn`; otherwise `other`, with the orientation as `source_action` |
| outcome | `Success` → success; `Fail` → failure; anything else → unknown |

Only `LogOn` counts as a sign-in:
- Kerberos ticket lines (`TGT`, `TGS`) accompany many sign-ins, so counting
  them would count one sign-in several times.
- `LogOff` is not a sign-in.

Measure 4 (§6) counts failures in every orientation, so this choice cannot
hide a burst of failures.

### Ground truth

A red-team record gives a time, a user, a source computer and a destination
computer. It matches every `auth.txt` line with the same time, source user,
source computer and destination computer. Matching is exact, with no fallback,
and duplicate red-team records count once.

Each record falls into one class:

| Class | Meaning |
|---|---|
| (a) | No matching line |
| (b) | Matching lines, but none is a successful `LogOn`, so IA-003 cannot alert on it |
| (c) | At least one matching line is a successful `LogOn`: **evaluable** |
| (d) | Evaluable, but its window was excluded for size (below) |

A research script writes the labels; they are never ingested (ADR-007).

### Windows

- **Window and scoring region.** A record at time *t* has the window
  [*t* − 3600 s, *t* + 3600 s) and the scoring region [*t* − 1800 s, *t* + 3600 s).
  Every success scored in the region therefore has its full 30-minute
  look-back inside the window.
- **Red-team windows.** Each record's window holds every line whose source user
  is the record's user.
- **Comparison windows.** For each distinct red-team record, in file order, one
  `random.Random(20261117)` generator draws 3 accounts:
  - The draw is `sample` from the sorted list of accounts that match
    `U<digits>@…`, are not among the 104 red-team users, and are the source
    user of at least one `LogOn` line in the record's window.
  - If fewer than 3 accounts qualify, all of them are taken.
  - Each drawn account's lines in that window form a comparison window.
  - The seed is the registration date; it was not tuned.
- **Merging and runs.** Overlapping windows of the same account are merged.
  Each merged window is one ingestion source and one detection run.
- **Size limit.** A merged window with more than 50,000 events (the engine's
  limit) is excluded, not truncated, and counted.

### Engine

- Each source is ingested with `lanl.auth@1`, and all five rules run through
  the normal engine.
- IA-003 runs at version 1: `min_failures` 5, `window_minutes` 30. Its contract
  SHA-256 is `c7609340c864df65f9badf48fe2341fa6d4fa5b434b8f9661b05cf7209f6a466`,
  as registered for Gate 3.
- Its approved-reset exclusion never applies, because LANL has no credential
  changes.

## 6. Measures

### Primary

1. **Strict recall:** class (c) records detected ÷ class (c) records, with a
   Wilson 95% interval. A record counts as detected when an IA-003 alert's
   trigger is one of its matched lines.
2. **Comparison alert rate:** IA-003 alerts whose trigger falls in a
   comparison scoring region. It is reported two ways:
   - per 1,000 comparison windows, counting one window per account drawn for
     each record;
   - per 10,000 successful `LogOn` events in those regions.

### Secondary (descriptive)

3. The number of records in each of classes (a) to (d).
4. For every red-team record, the failed lines by its user in
   [*t* − 1800 s, *t*), in any orientation, bucketed as 0, 1–4, and 5 or
   more. This shows whether any failure burst preceded the attack, whatever
   the mapping.
5. IA-003 alerts on red-team accounts that trigger on an unlabelled line. They
   are listed for review and counted neither as hits nor as false alarms,
   because the labels cover only red-team activity.
6. Run accounting:
   - lines read, events ingested, rejects and duplicates;
   - windows excluded for size;
   - engine runs;
   - alerts from IA-001, IA-002, IA-004 and IA-005. These rules lack their
     inputs on LANL, so any alert from them is an anomaly to investigate.

### Not reported

- **Precision as a population figure,** because the design sets the class
  balance.
- **IA-001, IA-002, IA-004 and IA-005,** because LANL has no grant, MFA,
  privilege, disable or sensitivity data. They are reported as not evaluable
  on LANL.

Here a "false alarm" means an alert on activity that is not labelled red team.
LANL's labels cover the red team only.

## 7. Reproducibility

One documented command regenerates everything from the two files. Results go
to `research/results/m2/<UTC time>/` and include:
- data and script hashes;
- the seed;
- Python and package versions;
- raw alert exports;
- the metrics as JSON.

There is no commit hash, because the folder is not a git repository.

## 8. Deviations and changes

- If any part of this plan cannot be followed (for example, the adapter meets
  a line it cannot read), the change, its reason and its effect are reported
  with the results.
- A change to IA-003 made after seeing LANL results creates a version-2 rule.
  It is scored and reported separately from version 1.

## 9. The Splunk samples in M2

These are adapter tests, not detection evaluations, and nothing is scored on
them. The pinned tests in `tests/test_gate2_events.py` already show what they
can:
- the CloudTrail and Entra ID adapters read 296 real records with no rejects;
- no rule fires on any of them.

On public data, IA-002 cannot be tested, because sign-in logs carry no
privilege field. IA-005 stays synthetic-only.
