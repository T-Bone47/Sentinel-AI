# Fixture: identity-access-v1

**Synthetic.** Every record here was invented by
`research/scripts/build_identity_access_fixture.py`. No real person, account,
host or address appears in it: identifiers carry a `lab-` prefix and IP
addresses come from the ranges reserved for documentation (RFC 5737, RFC 3849).

## What it is, and what it is not

A set of **constructed test vectors** for identity-and-access detection:
five families of suspicious activity, each with benign twins that differ in
exactly the fact that should decide the outcome, surrounded by routine
background activity.

It is **not** a sample of real activity. The ratio of suspicious to benign
events was chosen, not observed. Results on this fixture show whether a rule
does what its definition says. They do not estimate a false-positive rate, a
detection rate, or anything else about real environments.

## Files

| File | Ingested? | Purpose |
|---|---|---|
| `events.jsonl` | yes | 197 lines: 194 distinct events plus 3 re-sent copies, in an arrival order unrelated to event time |
| `labels.jsonl` | **never** | Ground truth, one line per event: `scenario_id`, `label`, `part` |
| `replay-conflict.jsonl` | yes, after `events.jsonl` | One record reusing an existing id with different content |
| `malformed.jsonl` | yes | 15 records: 13 that must be refused, each for a different reason, and 2 valid ones |
| `MANIFEST.json` | no | File hashes, the exact ingestion counts to expect, and the scenario list |

Labels are kept out of the event store on purpose. An event carries no
field that says which scenario it belongs to or whether it is suspicious, and
its id is random-looking, so a detector cannot read the answer.

## Labels

- `label`: `suspicious` or `benign` — the verdict on the whole scenario.
  194 events: 15 in suspicious scenarios, 179 in benign ones.
- `part`: the event's place in its scenario.
  - `trigger` (7): where a correct detection should fire.
  - `decoy` (12): where a careless rule would wrongly fire.
  - `context` (28): supporting events, such as the failed sign-ins before a success.
  - `background` (147): routine activity.

## Scenario families

| Family | Suspicious | Benign twins differ by |
|---|---|---|
| `privilege_grant_without_approval` | S01-P1, S01-P2 | approval reference present (B1); granted role not privileged (B2) |
| `privileged_login_without_mfa` | S02-P1 | second factor used (B1); account not privileged (B2); sign-in failed (B3) |
| `failed_privileged_logins_then_success` | S03-P1 | only two failures (B1); approved credential reset in between (B2); failures spread over nine hours (B3) |
| `activity_by_disabled_account` | S04-P1 | account re-enabled with approval first (B1); sign-in was refused (B2) |
| `permission_change_then_sensitive_access` | S05-P1 | grant was approved (B1); data accessed was not sensitive (B2) |

One-line summaries of all 19 scenarios are in `MANIFEST.json`.

## What the files deliberately exercise

- **Out-of-order arrival**: lines are shuffled; in S04-P1 the disable event and
  the later sign-in are far apart in the file.
- **Timezones**: 31 events give their time with a `+05:30` offset instead of `Z`.
- **Missing data**: 4 events have no actor (1 of them has no target either), and 1 has outcome `unknown`.
- **IPv6** source addresses on 9 events.
- **Re-sent records**: 2 byte-identical copies and 1 copy with different key order and spacing.
- **Events at the same instant**: none are constructed. Events with an identical
  `occurred_at` have no defined order in the store, so nothing here depends on one.

## Use

```bash
# from sentinel-ai-backend/, with the database migrated
python -m app.events ingest ../research/fixtures/identity-access-v1/events.jsonl \
    --source-type sentinel.native --source-id identity-access-v1
```

The printed counts must equal `expected` in `MANIFEST.json`
(`received` 197, `inserted` 194, `duplicates` 3). Running it again must report
`inserted` 0. `tests/test_gate2_events.py` checks both.

## Regenerating

```bash
python research/scripts/build_identity_access_fixture.py --check   # are the files what the script produces?
python research/scripts/build_identity_access_fixture.py           # rewrite them
```

The generator is deterministic (seed 20261117, standard library only). These
files are frozen: a change to the scenarios is a new fixture
(`identity-access-v2`) with a new source id, not an edit to this one.

## Known limitations

- Written by the same person who will write the detection rules, so the
  scenarios and the rules share assumptions. Independent data is needed
  before any claim about detection quality (planned: public datasets).
- Small: 7 trigger events. Too few for confidence intervals to mean much.
- Background activity is far more regular than real activity.
- Licence: not yet assigned — owner decision before publication.
