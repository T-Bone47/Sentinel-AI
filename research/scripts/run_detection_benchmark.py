"""
The Gate 3 benchmark in one command: a throwaway database, the frozen fixtures
ingested, the detection rules run, the alerts scored.

    python research/scripts/run_detection_benchmark.py              # writes research/results/gate3/<UTC time>/
    python research/scripts/run_detection_benchmark.py --out DIR

Never touches the database configured in your environment: before anything
from the backend is imported, DATABASE_URL is pointed at a new SQLite file in
a temporary folder that is deleted afterwards. Needs the backend's Python
dependencies (sentinel-ai-backend/pyproject.toml).

Writes metrics.json (identical from run to run, except the `metadata` block)
and report.md. Exits 1 if any pre-registered test vector does not hold.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "sentinel-ai-backend"
FIXTURES = REPO / "research" / "fixtures"
FIXTURE_NAMES = ("identity-access-v1", "identity-access-boundary-v1")
BENCHMARK_VERSION = 1
NATIVE = "sentinel.native"

sys.path.insert(0, str(Path(__file__).resolve().parent))   # also works under `python -I`
import evaluate_detections as evaluation  # noqa: E402


def _git_revision() -> str:
    try:
        done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return "git not available"
    return done.stdout.strip() if done.returncode == 0 else "not a git repository"


def _use_database(path: Path) -> None:
    url = path.as_posix()
    os.environ.update(DATABASE_URL=f"sqlite+aiosqlite:///{url}", DATABASE_URL_SYNC=f"sqlite:///{url}", ENVIRONMENT="test")
    sys.path.insert(0, str(BACKEND))


def _migrate() -> None:
    from alembic import command
    from alembic.config import Config

    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    command.upgrade(config, "head")


async def _run_all() -> dict[str, Any]:
    from app.database.session import AsyncSessionLocal, engine
    from app.detections.engine import export_alerts, run_detections
    from app.detections.rules import RULES
    from app.events.store import ingest, read_jsonl

    contracts = evaluation.load_contracts()
    fixtures: dict[str, Any] = {}
    run_ids: list[str] = []
    replay = {"events_inserted_on_reingest": 0, "alerts_created_on_rerun": 0}
    try:
        async with AsyncSessionLocal() as db:
            for name in FIXTURE_NAMES:
                folder = FIXTURES / name
                manifest = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))
                ingestion, alerts, not_evaluable = {}, [], {}
                for file, source_id in manifest.get("sources", {"events.jsonl": name}).items():
                    async def load():
                        return await ingest(db, source_type=NATIVE, source_id=source_id, records=read_jsonl(folder / file),
                                            origin="file", origin_detail=file)
                    first = await load()
                    counts = {k: getattr(first, k) for k in ("received", "inserted", "duplicates", "conflicts", "rejected")}
                    expected = {k: v for k, v in manifest["expected"][file].items() if k != "reject_reasons"}
                    if counts != expected:
                        raise SystemExit(f"{name}/{file}: ingestion gave {counts}; MANIFEST.json expects {expected}")
                    ingestion[file] = counts
                    run = await run_detections(db, source_type=NATIVE, source_id=source_id, origin="benchmark")
                    for rule_id, n in run.not_evaluable.items():
                        not_evaluable[rule_id] = not_evaluable.get(rule_id, 0) + n
                    # Replay: the same file again, then the rules again, must change nothing.
                    again = await load()
                    rerun = await run_detections(db, source_type=NATIVE, source_id=source_id, origin="benchmark")
                    run_ids += [run.run_id, rerun.run_id]
                    replay["events_inserted_on_reingest"] += again.inserted
                    replay["alerts_created_on_rerun"] += rerun.alerts_created
                    alerts += await export_alerts(db, source_type=NATIVE, source_id=source_id)
                metrics = evaluation.evaluate_fixture(folder, alerts, contracts, not_evaluable)
                metrics["files"] = {f: hashlib.sha256((folder / f).read_bytes()).hexdigest() for f in sorted(manifest["files"])}
                metrics["ingestion"] = ingestion
                fixtures[name] = metrics
    finally:
        await engine.dispose()
    return {"fixtures": fixtures, "replay": replay, "run_ids": run_ids,
            "rule_versions": {rule.id: rule.version for rule in RULES.values()}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, help="output folder (default: research/results/gate3/<UTC time>)")
    args = parser.parse_args(argv)
    started = datetime.now(timezone.utc)
    out = args.out or REPO / "research" / "results" / "gate3" / started.strftime("%Y%m%dT%H%M%SZ")

    with tempfile.TemporaryDirectory(prefix="sentinel-benchmark-", ignore_cleanup_errors=True) as scratch:
        _use_database(Path(scratch) / "benchmark.db")
        _migrate()
        outcome = asyncio.run(_run_all())

    conformance = [c for m in outcome["fixtures"].values() for c in m["conformance"]]
    held = sum(c["as_pre_registered"] for c in conformance)
    metrics = {
        "benchmark": "gate3-detections", "benchmark_version": BENCHMARK_VERSION,
        "evaluator_version": evaluation.EVALUATOR_VERSION, "synthetic_only": True,
        "rule_versions": outcome["rule_versions"],
        "summary": {"conformance": {"vectors": len(conformance), "as_pre_registered": held},
                    "known_misses": sorted(f"{c['rule']} {c['scenario']}" for c in conformance if c["known_miss"])},
        "replay": outcome["replay"],
        "fixtures": outcome["fixtures"],
        "metadata": {"generated_at": started.isoformat(), "python": platform.python_version(),
                     "platform": platform.platform(), "git": _git_revision(), "run_ids": outcome["run_ids"]},
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "report.md").write_text(evaluation.render_report(metrics), encoding="utf-8")
    print(f"conformance: {held} of {len(conformance)} test vectors as pre-registered")
    print(f"replay: {outcome['replay']}")
    print(f"wrote {out}")
    return 0 if held == len(conformance) else 1


if __name__ == "__main__":
    sys.exit(main())
