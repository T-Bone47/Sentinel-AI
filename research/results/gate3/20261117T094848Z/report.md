# Gate 3 detection benchmark

Generated 2026-11-17T09:48:48.313543+00:00 · Python 3.12.10 · Windows-11-10.0.26220-SP0 · git: not a git repository

**What this shows:** whether each rule does what its pre-registered contract says, on synthetic fixtures written by the same author as the rules.

**What it does not show:** how the rules perform on real activity. That waits for public data (PRD milestone M2).

**Conformance:** 33 of 33 pre-registered test vectors hold.

**Replay:** re-ingesting every fixture inserted 0 events, and re-running the rules created 0 alerts.

**Known misses, by design:** IA-001 B-13, IA-002 B-14, IA-004 B-12.

## identity-access-v1

194 events, 7 trigger events.

| Rule | Alerts | TP | FP | FN | Precision | Recall | Not evaluable | False alarms |
|---|---|---|---|---|---|---|---|---|
| IA-001 | 2 | 2 | 0 | 0 | 1.00 | 1.00 | 0 | none |
| IA-002 | 1 | 1 | 0 | 0 | 1.00 | 1.00 | 0 | none |
| IA-003 | 1 | 1 | 0 | 0 | 1.00 | 1.00 | 0 | none |
| IA-004 | 2 | 2 | 0 | 0 | 1.00 | 1.00 | 0 | none |
| IA-005 | 1 | 1 | 0 | 0 | 1.00 | 1.00 | 0 | none |

| Rule | Scenario | Expected alerts | Observed | Result |
|---|---|---|---|---|
| IA-001 | S01-P1 | 1 | 1 | as pre-registered |
| IA-001 | S01-P2 | 1 | 1 | as pre-registered |
| IA-001 | S01-B1 | 0 | 0 | as pre-registered |
| IA-001 | S01-B2 | 0 | 0 | as pre-registered |
| IA-002 | S02-P1 | 1 | 1 | as pre-registered |
| IA-002 | S02-B1 | 0 | 0 | as pre-registered |
| IA-002 | S02-B2 | 0 | 0 | as pre-registered |
| IA-002 | S02-B3 | 0 | 0 | as pre-registered |
| IA-003 | S03-P1 | 1 | 1 | as pre-registered |
| IA-003 | S03-B1 | 0 | 0 | as pre-registered |
| IA-003 | S03-B2 | 0 | 0 | as pre-registered |
| IA-003 | S03-B3 | 0 | 0 | as pre-registered |
| IA-004 | S04-P1 | 2 | 2 | as pre-registered |
| IA-004 | S04-B1 | 0 | 0 | as pre-registered |
| IA-004 | S04-B2 | 0 | 0 | as pre-registered |
| IA-005 | S05-P1 | 1 | 1 | as pre-registered |
| IA-005 | S05-B1 | 0 | 0 | as pre-registered |
| IA-005 | S05-B2 | 0 | 0 | as pre-registered |

**Sentinel's earlier failure-only monitoring:** flags 35 events (background 13, context 20, decoy 2), catching 0 of 7 trigger events.

| Rule without its exclusions | Alerts | TP | FP | FN | False alarms |
|---|---|---|---|---|---|
| IA-001 | 7 | 2 | 5 | 0 | context 3, decoy 2 |
| IA-002 | 38 | 1 | 37 | 0 | background 13, context 20, decoy 3, other_family_trigger 1 |
| IA-003 | 17 | 1 | 16 | 0 | background 13, decoy 3 |
| IA-004 | 4 | 2 | 2 | 0 | decoy 2 |
| IA-005 | 2 | 1 | 1 | 0 | decoy 1 |

## identity-access-boundary-v1

53 events, 8 trigger events.

| Rule | Alerts | TP | FP | FN | Precision | Recall | Not evaluable | False alarms |
|---|---|---|---|---|---|---|---|---|
| IA-001 | 0 | 0 | 0 | 1 | — | 0.00 | 1 | none |
| IA-002 | 0 | 0 | 0 | 1 | — | 0.00 | 1 | none |
| IA-003 | 3 | 3 | 0 | 0 | 1.00 | 1.00 | 0 | none |
| IA-004 | 1 | 1 | 0 | 1 | 1.00 | 0.50 | 0 | none |
| IA-005 | 1 | 1 | 0 | 0 | 1.00 | 1.00 | 0 | none |

| Rule | Scenario | Expected alerts | Observed | Result |
|---|---|---|---|---|
| IA-001 | B-13 | 0 | 0 | as pre-registered (known miss) |
| IA-002 | B-14 | 0 | 0 | as pre-registered (known miss) |
| IA-003 | B-01 | 0 | 0 | as pre-registered |
| IA-003 | B-02 | 1 | 1 | as pre-registered |
| IA-003 | B-03 | 0 | 0 | as pre-registered |
| IA-003 | B-04 | 1 | 1 | as pre-registered |
| IA-003 | B-05 | 0 | 0 | as pre-registered |
| IA-003 | B-15 | 1 | 1 | as pre-registered |
| IA-004 | B-09 | 0 | 0 | as pre-registered |
| IA-004 | B-10 | 1 | 1 | as pre-registered |
| IA-004 | B-11 | 0 | 0 | as pre-registered |
| IA-004 | B-12 | 0 | 0 | as pre-registered (known miss) |
| IA-005 | B-06 | 1 | 1 | as pre-registered |
| IA-005 | B-07 | 0 | 0 | as pre-registered |
| IA-005 | B-08 | 0 | 0 | as pre-registered |

**Sentinel's earlier failure-only monitoring:** flags 29 events (context 29), catching 0 of 8 trigger events.

| Rule without its exclusions | Alerts | TP | FP | FN | False alarms |
|---|---|---|---|---|---|
| IA-001 | 4 | 1 | 3 | 0 | context 3 |
| IA-002 | 29 | 0 | 29 | 1 | context 29 |
| IA-003 | 6 | 3 | 3 | 0 | decoy 3 |
| IA-004 | 3 | 2 | 1 | 0 | decoy 1 |
| IA-005 | 1 | 1 | 0 | 0 | none |

