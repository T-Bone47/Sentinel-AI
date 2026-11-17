# Detection rule contracts

One TOML file per rule: what it detects, exactly when it fires and when it
doesn't, why it has its severity and confidence, what it can't see, its ATT&CK
mapping (or why there is none), and its test vectors.

| Rule | Title | Severity | Confidence | ATT&CK |
|---|---|---|---|---|
| IA-001 | Privileged access granted without approval | high | medium | T1098 |
| IA-002 | Privileged sign-in without MFA | medium | high | unmapped |
| IA-003 | Repeated failed sign-ins, then success | high | medium | T1110.001 |
| IA-004 | Activity by a disabled account | high | high | T1078 |
| IA-005 | Unapproved permission change, then sensitive access | high | medium | T1098 |

## How a contract relates to the code

- The executable rules are Python functions in
  `sentinel-ai-backend/app/detections/rules.py`. The code is the source of truth
  for parameters.
- `tests/test_gate3_detections.py` fails if a contract's id, version, title,
  severity, confidence, parameters or ATT&CK techniques differ from the code, or
  if it names a field the event contract doesn't have.
- The same tests check every test vector against both fixtures.

## Status

All five are `experimental`. They have been tested only on synthetic fixtures
written by the same author, so passing shows a rule does what its contract says
and nothing about real-world performance. They stay experimental until evaluated
on public data (PRD milestone M2).

## Pre-registration

These files were written, and their SHA-256 hashes recorded in
`docs/PROGRESS.md`, before any rule code or the boundary fixture existed. A test
vector marked `known_miss = true` is a case the rule is expected to miss by
design. It is reported as a missed detection, not hidden.

## These are not Sigma rules

The format is our own. Sigma versions written for upstream projects (PRD
milestone M3) will be validated with Sigma's own tooling before being called
Sigma.

## Changing a rule

Change the code and the contract together, and bump `version` in both. Stored
alerts keep the version that raised them, so a change never silently
reinterprets old alerts.
