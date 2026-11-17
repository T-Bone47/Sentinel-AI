# M2 report: the detection rules on public data

*2026-11-17. Model: Claude Opus 5.5. No independent review yet. The LANL part
follows the pre-registration in `research/M2_PREREGISTRATION.md` (SHA-256
`3d977e98…dd82c`), which was recorded before any rule ran on LANL data. The raw
outputs are in `research/results/m2/20261117T183312Z/`. Every number below is
measured; none is estimated.*

## Summary

- **The main result is negative.** The real attack activity in LANL was
  almost never preceded by failed sign-ins. IA-003 (five or more failed
  sign-ins by an account in 30 minutes, then a success) was unchanged since it
  was written for synthetic data. It caught **5 of 701** red-team compromise
  sign-ins in LANL's enterprise data: recall **0.0071**, Wilson 95% interval
  0.0031–0.0166. The registered prediction was recall below 0.10, and it held.
- **The adapters read 459,470 real records** from three public sources and
  refused none.
- **Public data can properly test only one of the five rules.**

## 1. IA-003 on LANL

### Data

LANL, "Comprehensive, Multi-Source Cyber-Security Events" (CC0 1.0):
- `auth.txt.gz`: 1,051,430,459 authentication events over 58 days;
- `redteam.txt.gz`: 749 lines, of which 715 are distinct red-team records.

Both files are pinned by SHA-256 in the pre-registration. They are not
redistributed.

### Method, as registered

- **Events.** Each `auth.txt` line becomes one event (adapter `lanl.auth@1`).
  Only `LogOn` lines count as sign-ins.
- **Ground truth.** A red-team record matches the lines with the same time,
  source user, source computer and destination computer.
- **What the rules see.**
  - For each record: every line of that account in a two-hour window around
    it.
  - For comparison: 3 other user accounts drawn at random (fixed seed) from
    those active in the same window.
- **Engine.** Windows are ingested and run through the normal engine: event
  store, five rules, stored alerts.

### Results

| Measure | Result |
|---|---|
| Red-team records with a successful `LogOn` among their lines (evaluable) | 701 of 715. The other 14 had no matching line |
| **Recall on evaluable records** | **5 of 701 = 0.0071** (95%: 0.0031–0.0166) |
| **IA-003 alerts on comparison accounts** | 12 in 2,145 two-hour windows, which is 5.6 per 1,000 windows, or 2.0 per 10,000 successful sign-ins |
| Failures of any kind by the account in the 30 minutes before a red-team record | None before 513 records (72%), 1–4 before 170, and 5 or more before 32 |
| IA-003 alerts on red-team accounts at unlabelled moments | 22 |
| Alerts from the other four rules | 0. Their inputs (grants, MFA, privilege, disables, classification) do not exist in LANL |

### What it shows

1. **A password-guessing rule is the wrong tool for this kind of attack.** In
   LANL the red team mostly signed in with credentials that worked first
   time: nearly three quarters of its sign-ins had no failure of any kind just
   before them.
2. **Counting only `LogOn` lines is not the cause of the miss.** Even a
   version of IA-003 that counted every kind of failed authentication could
   have caught at most 31 of the 701 (4.4%).
3. **The 5 detections each followed 5 to 16 failed sign-ins.** The labels do
   not say whether the red team caused those failures. A user mistyping a
   password looks the same.
4. **The comparison rate is not a precision figure.** The design fixed how
   much comparison data there is. It shows the rule fires rarely, but not
   never, on activity not labelled as the red team's. LANL labels only the red
   team, so "not labelled" does not prove "benign".
5. **Exploratory, not registered:** the 22 alerts on red-team accounts at
   unlabelled moments are either benign or unlabelled red-team activity. They
   are listed by line number in `alerts.jsonl` for review.

## 2. Coverage: what public data can test

| Rule | What it needs | Public data | Status after M2 |
|---|---|---|---|
| IA-001 privileged grant without approval | grants, a privilege flag, approval references | CloudTrail has grants; no public log has approval references | Synthetic only |
| IA-002 privileged sign-in without MFA | sign-ins with MFA and privilege fields | Entra ID sign-in logs give MFA but no privilege field; LANL has neither | Synthetic only |
| IA-003 failed sign-ins, then success | sign-ins with account and outcome | LANL | **Evaluated: recall 0.0071** |
| IA-004 activity by a disabled account | disable events and later activity from the same source | None verified | Synthetic only |
| IA-005 unapproved grant, then sensitive access | grants, and data access with a classification | None found | Synthetic only |

## 3. Adapters on real records

| Adapter | Real records | Refused | Notes |
|---|---|---|---|
| `aws.cloudtrail@1` | 266: 7 console sign-in failures and 259 IAM deletions (Splunk attack_data, Apache 2.0) | 0 | Two files repeat 14 records word for word, so there are 245 distinct events. Ingest stored each once |
| `entra.signin@1` | 30 failed sign-ins of one user (Splunk attack_data) | 0 | No successful sign-in, so it cannot test a rule |
| `lanl.auth@1` | 459,174 lines in the benchmark windows | 0 | — |

The Splunk files are pinned by hash in `tests/test_gate2_events.py`.

## 4. Limitations

- **One dataset.** LANL is a single enterprise, captured in 2015. Its labels
  cover only the red team.
- **One author.** The rules, the registration, the code and this report have
  the same author.
- **One run.** It used rule version 1 with no tuning, on SQLite only. The
  production target, PostgreSQL, is not yet validated.
- **Comparison accounts are user accounts only.** Machine accounts were not
  sampled.
- **14 red-team records matched no authentication line.** As registered, they
  were not matched any other way.
- **Time is relative.** LANL's real start date is undisclosed, so only
  intervals are meaningful.

**Deviation from the registration.** The raw alert export names accounts, so
it is kept outside the repository. The results folder holds the same 44
alerts reduced to line numbers.

## 5. Reproduce

1. Download `auth.txt.gz` and `redteam.txt.gz` from
   csr.lanl.gov/data/cyber1/. The site asks for an email address and an
   intended use.
2. Install the backend's Python dependencies.
3. Run:

   ```bash
   python research/scripts/run_lanl_benchmark.py PATH/auth.txt.gz PATH/redteam.txt.gz --work PATH/m2-work
   ```

- The script refuses files whose SHA-256 differs from the registered values.
- It took 42 minutes on a Windows 11 machine, and the work folder grew to
  373 MB.
- Results are written to `research/results/m2/<UTC time>/`.

## Citation

A. D. Kent, "Cybersecurity Data Sources for Dynamic Network Research," in
*Dynamic Networks in Cybersecurity*, Imperial College Press, 2015.
