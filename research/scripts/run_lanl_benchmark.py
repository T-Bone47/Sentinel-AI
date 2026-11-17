"""
M2 in one command: rule IA-003 on LANL's authentication data, as registered in
research/M2_PREREGISTRATION.md.

    python research/scripts/run_lanl_benchmark.py AUTH.TXT.GZ REDTEAM.TXT.GZ --work DIR

  * Refuses the data, or a pre-registration, whose SHA-256 differs from the
    values recorded in docs/PROGRESS.md.
  * The extraction (lanl_extract.py) streams 1.05 billion lines and takes tens
    of minutes. It is cached in DIR/extract.json and redone whenever
    lanl_extract.py changes.
  * Ingests the windows and runs the rules in a new SQLite database in DIR,
    never in the database configured in your environment.
  * Writes metrics.json, records.jsonl and alerts.jsonl to
    research/results/m2/<UTC time>/. They hold line numbers and counts, never
    account names (§4).
  * Keeps the engine's raw alert export in DIR, because it names accounts.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import math
import platform
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))   # also works under `python -I`
import lanl_extract as lanl  # noqa: E402
import run_detection_benchmark as gate3  # noqa: E402  (throwaway-database helpers)

REPO = gate3.REPO
BACKEND = gate3.BACKEND
BENCHMARK_VERSION = 1
SOURCE_TYPE = "lanl.auth"
REGISTERED = {   # docs/PROGRESS.md, M2 pre-registration, 2026-11-17T18:14Z
    "preregistration": "3d977e98ed5f17e5f3c1b370dcffddbe19efcf5bd7ca43ad8c0c258ed8cdd82c",
    "auth": "9c6b0cc261b0edd19324f6fd1839743224938a7f644ed202ca70bd70a89bf672",
    "redteam": "606635837c684ad11e464075ecf97bc5df325ff7d7f64614d2d8c8af18051669",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float] | None:
    if n == 0:
        return None
    p, z2 = k / n, z * z
    centre, half = p + z2 / (2 * n), z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return [round((centre - half) / (1 + z2 / n), 4), round((centre + half) / (1 + z2 / n), 4)]


def _rate(count: int, exposure: int, per: int) -> float | None:
    return round(count * per / exposure, 4) if exposure else None


async def _score(sources: list[dict[str, Any]]) -> dict[str, Any]:
    from app.database.session import AsyncSessionLocal, engine
    from app.detections.engine import export_alerts, run_detections
    from app.events.store import ingest

    ingested = dict.fromkeys(("received", "inserted", "duplicates", "conflicts", "rejected"), 0)
    not_evaluable: Counter[str] = Counter()
    runs = 0
    try:
        async with AsyncSessionLocal() as db:
            for source in sources:
                if source["excluded"]:
                    continue
                report = await ingest(db, source_type=SOURCE_TYPE, source_id=source["id"], origin="file",
                                      origin_detail="auth.txt.gz",
                                      records=[{"line": n, "text": text} for n, text in source["lines"]])
                for key in ingested:
                    ingested[key] += getattr(report, key)
                run = await run_detections(db, source_type=SOURCE_TYPE, source_id=source["id"], origin="benchmark")
                not_evaluable.update(run.not_evaluable)
                runs += 1
            alerts = await export_alerts(db, source_type=SOURCE_TYPE)
    finally:
        await engine.dispose()
    return {"alerts": alerts, "ingested": ingested, "not_evaluable": dict(sorted(not_evaluable.items())), "runs": runs}


def _bucket(n: int) -> str:
    return "0" if n == 0 else "1-4" if n < 5 else "5+"


def measure(records: list[lanl.Record], redteam_lines: int, extraction: dict[str, Any],
            scored: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """The measures of pre-registration §6. Returns metrics, one row per record, one row per alert."""
    sources = {s["id"]: s for s in extraction["sources"]}
    fields = {n: text.split(",") for s in sources.values() for n, text in s["lines"]}
    window_of = {i: s for s in sources.values() if s["kind"] == "rt" for i in s["records"]}

    rows, labelled = [], {}
    for i, (t, user, src, dst) in enumerate(records):
        s = window_of[i]
        matched = [n for n, _ in s["lines"] if fields[n][:2] == [str(t), user] and fields[n][3:5] == [src, dst]]
        evaluable = [n for n in matched if fields[n][7:9] == ["LogOn", "Success"]]
        failures = sum(1 for n, _ in s["lines"] if fields[n][8] == "Fail" and t - lanl.LOOKBACK <= int(fields[n][0]) < t)
        rows.append({"record": i + 1, "class": "a" if not matched else "b" if not evaluable else "d" if s["excluded"] else "c",
                     "matched_lines": matched, "evaluable_lines": evaluable, "failures_before": failures})
        labelled.update(dict.fromkeys(matched, i))

    hits, comparison_alerts, unlabelled, alert_rows = set(), 0, 0, []
    for a in scored["alerts"]:
        s = sources[a["source_id"]]
        trigger = next(int(e["source_event_id"]) for e in a["events"] if e["role"] == "trigger")
        t = int(fields[trigger][0])
        in_region = any(records[i][0] - lanl.LOOKBACK <= t < records[i][0] + lanl.AFTER for i in s["records"])
        label = "comparison" if s["kind"] == "cmp" else "red-team" if trigger in labelled else "unlabelled"
        if a["rule_id"] == "IA-003":
            if label == "red-team":
                hits.add(labelled[trigger])
            comparison_alerts += label == "comparison" and in_region
            unlabelled += label == "unlabelled"
        alert_rows.append({"rule_id": a["rule_id"], "source": a["source_id"], "trigger_line": trigger,
                           "context_lines": [int(e["source_event_id"]) for e in a["events"] if e["role"] != "trigger"],
                           "label": label, "in_scoring_region": in_region})
    for row in rows:
        row["detected"] = row["class"] == "c" and row["record"] - 1 in hits

    windows = successes = 0
    for s in sources.values():
        if s["kind"] == "cmp" and not s["excluded"]:
            windows += len(s["records"])
            regions = [(records[i][0] - lanl.LOOKBACK, records[i][0] + lanl.AFTER) for i in s["records"]]
            successes += sum(1 for n, _ in s["lines"] if fields[n][7:9] == ["LogOn", "Success"]
                             and any(lo <= int(fields[n][0]) < hi for lo, hi in regions))

    evaluable = [r for r in rows if r["class"] == "c"]
    detected = sum(r["detected"] for r in evaluable)
    recall = round(detected / len(evaluable), 4) if evaluable else None
    by_kind = {kind: [s for s in sources.values() if s["kind"] == kind] for kind in ("rt", "cmp")}
    metrics = {
        "red_team": {"lines": redteam_lines, "distinct_records": len(records),
                     "classes": dict(sorted(Counter(r["class"] for r in rows).items()))},
        "primary": {
            "strict_recall": {"detected": detected, "evaluable": len(evaluable), "recall": recall,
                              "wilson_95": _wilson(detected, len(evaluable))},
            "comparison_alert_rate": {"alerts": comparison_alerts, "windows": windows,
                                      "per_1000_windows": _rate(comparison_alerts, windows, 1000),
                                      "successful_logons": successes,
                                      "per_10000_successful_logons": _rate(comparison_alerts, successes, 10_000)},
        },
        "secondary": {
            "failures_before_record": {
                "all": dict(sorted(Counter(_bucket(r["failures_before"]) for r in rows).items())),
                "evaluable": dict(sorted(Counter(_bucket(r["failures_before"]) for r in evaluable).items()))},
            "ia003_unlabelled_alerts_on_red_team_accounts": unlabelled,
        },
        "prediction_p1": {"registered": "strict recall below 0.10",
                          "held": None if recall is None else recall < 0.10},
        "accounting": {
            "auth_lines_read": extraction["lines_read"],
            "comparison_candidates": {"min": min(extraction["candidates"]), "max": max(extraction["candidates"]),
                                      "records_with_fewer_than_3": sum(c < lanl.DRAWS for c in extraction["candidates"])},
            "windows": {kind: len(found) for kind, found in by_kind.items()},
            "lines_kept": {kind: sum(len(s["lines"]) for s in found) for kind, found in by_kind.items()},
            "windows_excluded_for_size": {kind: sum(s["excluded"] for s in found) for kind, found in by_kind.items()},
            "ingested": scored["ingested"], "engine_runs": scored["runs"],
            "alerts_by_rule": dict(sorted(Counter(a["rule_id"] for a in scored["alerts"]).items())),
            "not_evaluable": scored["not_evaluable"],
        },
    }
    return metrics, rows, sorted(alert_rows, key=lambda r: (r["trigger_line"], r["rule_id"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("auth", type=Path, help="LANL auth.txt.gz")
    parser.add_argument("redteam", type=Path, help="LANL redteam.txt.gz")
    parser.add_argument("--work", type=Path, required=True, help="folder outside the repository (cache, database)")
    parser.add_argument("--out", type=Path, help="output folder (default: research/results/m2/<UTC time>)")
    args = parser.parse_args(argv)
    started = datetime.now(timezone.utc)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    out = args.out or REPO / "research" / "results" / "m2" / stamp

    found = {"preregistration": _sha256(REPO / "research" / "M2_PREREGISTRATION.md"),
             "auth": _sha256(args.auth), "redteam": _sha256(args.redteam)}
    wrong = sorted(k for k in REGISTERED if found[k] != REGISTERED[k])
    if wrong:
        raise SystemExit(f"SHA-256 differs from the registration for: {', '.join(wrong)}")

    records, redteam_lines = lanl.read_redteam(args.redteam)
    extractor = _sha256(HERE / "lanl_extract.py")
    cache = args.work / "extract.json"
    extraction = json.loads(cache.read_text(encoding="utf-8")) if cache.is_file() else None
    if not extraction or extraction.get("extractor_sha256") != extractor:
        print("extracting windows from auth.txt.gz (tens of minutes) ...", flush=True)
        extraction = {**lanl.extract(args.auth, records), "extractor_sha256": extractor}
        args.work.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(extraction), encoding="utf-8")

    gate3._use_database(args.work / f"m2-{stamp}.db")
    gate3._migrate()
    from app.detections.engine import MAX_EVENTS_PER_RUN
    from app.detections.rules import RULES
    for source in extraction["sources"]:
        source["excluded"] = len(source["lines"]) > MAX_EVENTS_PER_RUN   # one line is one event
    scored = asyncio.run(_score(extraction["sources"]))
    (args.work / f"alerts-raw-{stamp}.json").write_text(json.dumps(scored["alerts"], indent=1), encoding="utf-8")
    metrics, rows, alert_rows = measure(records, redteam_lines, extraction, scored)

    code = [HERE / "lanl_extract.py", Path(__file__).resolve()] + [
        BACKEND / "app" / part for part in ("events/adapters.py", "events/store.py", "detections/rules.py",
                                            "detections/engine.py")]
    metrics = {"benchmark": "m2-lanl", "benchmark_version": BENCHMARK_VERSION, **metrics,
               "rule_versions": {rule.id: rule.version for rule in RULES.values()},
               "parameters": {"window_seconds": [-lanl.BEFORE, lanl.AFTER],
                              "scoring_region_seconds": [-lanl.LOOKBACK, lanl.AFTER],
                              "draws": lanl.DRAWS, "seed": lanl.SEED, "max_events_per_run": MAX_EVENTS_PER_RUN},
               "metadata": {"generated_at": started.isoformat(), "finished_at": datetime.now(timezone.utc).isoformat(),
                            "inputs_sha256": found,
                            "code_sha256": {str(p.relative_to(REPO)).replace("\\", "/"): _sha256(p) for p in code},
                            "python": platform.python_version(), "platform": platform.platform(),
                            "packages": {p: importlib.metadata.version(p)
                                         for p in ("sqlalchemy", "pydantic", "alembic", "aiosqlite")},
                            "git": gate3._git_revision()}}
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name, items in (("records.jsonl", rows), ("alerts.jsonl", alert_rows)):
        (out / name).write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in items), encoding="utf-8")
    print(json.dumps({"primary": metrics["primary"], "classes": metrics["red_team"]["classes"]}, indent=2))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
