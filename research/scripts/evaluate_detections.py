"""
Scores exported detection alerts against a fixture's ground-truth labels.

    python research/scripts/evaluate_detections.py --fixture research/fixtures/identity-access-v1 --alerts alerts.jsonl

Prints the metrics as JSON. run_detection_benchmark.py builds every input in a
throwaway database and calls evaluate_fixture() directly.

Definitions (docs/PLAN_GATE3_DETECTIONS.md §7)
  * Unit of truth: an event labelled part = "trigger" in a suspicious scenario.
  * For a rule whose contract names fixture family F:
      TP  F's trigger events the rule cited as an alert's trigger
      FN  F's trigger events it did not cite
      FP  any other event it cited as a trigger, split by kind: another
          family's trigger, a decoy, context or background
  * Precision and recall are None where undefined. No confidence intervals:
    with this few trigger events they would mean nothing.
  * Conformance: each contract test vector says how many alerts a rule should
    raise in one scenario; the observed count must match exactly.

Comparisons, computed from the fixture's own records under the same labels
  * legacy_failure_only: Sentinel's earlier monitoring flagged
    "risk_score >= 80 OR result == 'Failure'". Events carry no risk score, so
    only the second half applies: every failed event is flagged.
  * naive: each IA rule with its exclusions and thresholds removed.

Ground-truth labels are read here and nowhere in the backend (ADR-007).
"""
from __future__ import annotations

import argparse
import json
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

EVALUATOR_VERSION = 1
RULES_DIR = Path(__file__).resolve().parents[1] / "rules"


@dataclass
class Fixture:
    name: str
    manifest: dict[str, Any]
    records: dict[str, dict[str, Any]]     # source_event_id -> first occurrence
    labels: dict[str, dict[str, Any]]      # source_event_id -> label


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_fixture(folder: Path) -> Fixture:
    folder = Path(folder)
    manifest = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))
    name = manifest.get("fixture", folder.name)
    records: dict[str, dict[str, Any]] = {}
    for file in manifest.get("sources", {"events.jsonl": name}):
        for record in _jsonl(folder / file):
            records.setdefault(record["source_event_id"], record)
    labels = {label["source_event_id"]: label for label in _jsonl(folder / "labels.jsonl")}
    return Fixture(name, manifest, records, labels)


def load_contracts(rules_dir: Path = RULES_DIR) -> dict[str, dict[str, Any]]:
    return {p.stem: tomllib.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(rules_dir).glob("*.toml"))}


def _score(cited: list[str], family_triggers: set[str], all_triggers: set[str], fx: Fixture) -> dict[str, Any]:
    cited_set = set(cited)
    false = cited_set - family_triggers
    kinds: Counter = Counter()
    for sid in false:
        if sid in all_triggers:
            kinds["other_family_trigger"] += 1
        else:
            kinds[fx.labels[sid]["part"] if sid in fx.labels else "unlabelled"] += 1
    tp, fp, fn = len(cited_set & family_triggers), len(false), len(family_triggers - cited_set)
    return {"alerts": len(cited), "tp": tp, "fp": fp, "fn": fn, "fp_by_kind": dict(sorted(kinds.items())),
            "precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None,
            "missed": sorted({fx.labels[sid]["scenario_id"] for sid in family_triggers - cited_set})}


# --- comparison rules, over the fixture's own records ----------------------------
# ponytail: quadratic scans; the fixtures are a few hundred events.

def _t(r):
    return datetime.fromisoformat(r["occurred_at"])


def _actor(r):
    return (r.get("actor") or {}).get("id")


def _target(r):
    return (r.get("target") or {}).get("id")


def _attrs(r):
    return r.get("attributes") or {}


def _ok(r):
    return r["outcome"] == "success"


def _naive_any_grant(rs):
    return [r["source_event_id"] for r in rs if r["action"] == "privilege.grant" and _ok(r)]


def _naive_any_login_without_mfa(rs):
    return [r["source_event_id"] for r in rs if r["action"] == "auth.login" and _attrs(r).get("mfa_used") is False]


def _naive_any_success_after_a_failure(rs):
    window = timedelta(minutes=30)
    return [r["source_event_id"] for r in rs if r["action"] == "auth.login" and _ok(r) and any(
        f["action"] == "auth.login" and f["outcome"] == "failure" and _actor(f) == _actor(r)
        and _t(r) - window <= _t(f) < _t(r) for f in rs)]


def _naive_anything_after_a_disable(rs):
    disabled_at: dict[str, datetime] = {}
    for r in rs:
        if r["action"] == "account.disable" and _ok(r) and _target(r):
            disabled_at.setdefault(_target(r), _t(r))
    return [r["source_event_id"] for r in rs if _actor(r) in disabled_at and _t(r) > disabled_at[_actor(r)]]


def _naive_sensitive_access_after_any_grant(rs):
    grants: dict[str, list[datetime]] = {}
    for r in rs:
        if r["action"] == "privilege.grant" and _ok(r) and _target(r):
            grants.setdefault(_target(r), []).append(_t(r))
    return [r["source_event_id"] for r in rs
            if r["action"] in ("resource.read", "resource.export") and _ok(r)
            and _attrs(r).get("sensitivity") in ("confidential", "restricted")
            and any(g < _t(r) <= g + timedelta(minutes=60) for g in grants.get(_actor(r), []))]


NAIVE = {"IA-001": _naive_any_grant, "IA-002": _naive_any_login_without_mfa,
         "IA-003": _naive_any_success_after_a_failure, "IA-004": _naive_anything_after_a_disable,
         "IA-005": _naive_sensitive_access_after_any_grant}


def _legacy_failure_only(fx: Fixture, all_triggers: set[str]) -> dict[str, Any]:
    flagged = sorted(sid for sid, r in fx.records.items() if r.get("outcome") == "failure")
    kinds = Counter(fx.labels[sid]["part"] if sid in fx.labels else "unlabelled" for sid in flagged)
    return {"flagged": len(flagged), "trigger_events_flagged": len(set(flagged) & all_triggers),
            "triggers_total": len(all_triggers), "flagged_by_kind": dict(sorted(kinds.items())),
            "scenarios_flagged": sorted({fx.labels[sid]["scenario_id"] for sid in flagged if sid in fx.labels})}


def evaluate_fixture(folder: Path, alerts: list[dict[str, Any]], contracts: dict[str, dict[str, Any]],
                     not_evaluable: dict[str, int] | None = None) -> dict[str, Any]:
    fx = load_fixture(folder)
    scenario_info = {s["id"]: s for s in fx.manifest["scenarios"]}
    triggers_by_family: dict[str, set[str]] = {}
    for sid, label in fx.labels.items():
        if label["part"] == "trigger" and label["label"] == "suspicious":
            triggers_by_family.setdefault(scenario_info[label["scenario_id"]]["family"], set()).add(sid)
    all_triggers = set().union(*triggers_by_family.values())

    cited: dict[str, list[str]] = {}
    for alert in alerts:
        for event in alert["events"]:
            if event["role"] == "trigger":
                cited.setdefault(alert["rule_id"], []).append(event["source_event_id"])

    rules = {rule_id: {"family": c["fixture_family"],
                       **_score(cited.get(rule_id, []), triggers_by_family.get(c["fixture_family"], set()), all_triggers, fx),
                       "not_evaluable": (not_evaluable or {}).get(rule_id, 0)}
             for rule_id, c in contracts.items()}
    every_citation = [sid for rule_id in contracts for sid in cited.get(rule_id, [])]

    observed: Counter = Counter()
    for rule_id, sids in cited.items():
        for sid in sids:
            if sid in fx.labels:
                observed[(rule_id, fx.labels[sid]["scenario_id"])] += 1
    conformance = [
        {"rule": rule_id, "scenario": v["scenario"], "expected_alerts": v["expected_alerts"],
         "observed_alerts": observed[(rule_id, v["scenario"])],
         "as_pre_registered": observed[(rule_id, v["scenario"])] == v["expected_alerts"],
         "known_miss": bool(v.get("known_miss", False)), "note": v.get("note", "")}
        for rule_id, c in contracts.items() for v in c.get("test_vectors", []) if v["fixture"] == fx.name]

    alerted_by: dict[str, set[str]] = {}
    for rule_id, scenario in observed:
        alerted_by.setdefault(scenario, set()).add(rule_id)
    ordered = sorted(fx.records.values(), key=lambda r: (_t(r), r["source_event_id"]))
    return {
        "fixture": fx.name, "events": len(fx.records), "trigger_events": len(all_triggers),
        "rules": rules, "all_rules": _score(every_citation, all_triggers, all_triggers, fx),
        "conformance": conformance,
        "scenarios": {sid: {"family": s["family"], "label": s.get("label"), "alerted_by": sorted(alerted_by.get(sid, ()))}
                      for sid, s in scenario_info.items()},
        "comparisons": {
            "legacy_failure_only": _legacy_failure_only(fx, all_triggers),
            "naive": {rule_id: _score(fn(ordered), triggers_by_family.get(contracts[rule_id]["fixture_family"], set()),
                                      all_triggers, fx)
                      for rule_id, fn in NAIVE.items() if rule_id in contracts},
        },
    }


# --- report ------------------------------------------------------------------------

def _num(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def _kinds(kinds: dict[str, int]) -> str:
    return ", ".join(f"{k} {v}" for k, v in kinds.items()) or "none"


def render_report(metrics: dict[str, Any]) -> str:
    meta, summary = metrics["metadata"], metrics["summary"]
    lines = [
        "# Gate 3 detection benchmark", "",
        f"Generated {meta['generated_at']} · Python {meta['python']} · {meta['platform']} · git: {meta['git']}", "",
        "**What this shows:** whether each rule does what its pre-registered contract says, on synthetic "
        "fixtures written by the same author as the rules.", "",
        "**What it does not show:** how the rules perform on real activity. That waits for public data "
        "(PRD milestone M2).", "",
        f"**Conformance:** {summary['conformance']['as_pre_registered']} of {summary['conformance']['vectors']} "
        "pre-registered test vectors hold.", "",
        f"**Replay:** re-ingesting every fixture inserted {metrics['replay']['events_inserted_on_reingest']} events, "
        f"and re-running the rules created {metrics['replay']['alerts_created_on_rerun']} alerts.", "",
        "**Known misses, by design:** " + (", ".join(summary["known_misses"]) or "none") + ".", "",
    ]
    for name, m in metrics["fixtures"].items():
        lines += [f"## {name}", "", f"{m['events']} events, {m['trigger_events']} trigger events.", "",
                  "| Rule | Alerts | TP | FP | FN | Precision | Recall | Not evaluable | False alarms |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for rule_id, r in m["rules"].items():
            lines.append(f"| {rule_id} | {r['alerts']} | {r['tp']} | {r['fp']} | {r['fn']} | {_num(r['precision'])} "
                         f"| {_num(r['recall'])} | {r['not_evaluable']} | {_kinds(r['fp_by_kind'])} |")
        lines += ["", "| Rule | Scenario | Expected alerts | Observed | Result |", "|---|---|---|---|---|"]
        for c in m["conformance"]:
            result = "as pre-registered" if c["as_pre_registered"] else "**differs**"
            if c["known_miss"]:
                result += " (known miss)"
            lines.append(f"| {c['rule']} | {c['scenario']} | {c['expected_alerts']} | {c['observed_alerts']} | {result} |")
        legacy = m["comparisons"]["legacy_failure_only"]
        lines += ["", "**Sentinel's earlier failure-only monitoring:** flags "
                  f"{legacy['flagged']} events ({_kinds(legacy['flagged_by_kind'])}), catching "
                  f"{legacy['trigger_events_flagged']} of {legacy['triggers_total']} trigger events.", "",
                  "| Rule without its exclusions | Alerts | TP | FP | FN | False alarms |", "|---|---|---|---|---|---|"]
        for rule_id, r in m["comparisons"]["naive"].items():
            lines.append(f"| {rule_id} | {r['alerts']} | {r['tp']} | {r['fp']} | {r['fn']} | {_kinds(r['fp_by_kind'])} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--alerts", type=Path, required=True, help="JSON Lines from `python -m app.detections export`")
    parser.add_argument("--rules", type=Path, default=RULES_DIR)
    args = parser.parse_args(argv)
    result = evaluate_fixture(args.fixture, _jsonl(args.alerts), load_contracts(args.rules))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
