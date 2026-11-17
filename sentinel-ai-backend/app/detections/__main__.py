"""
Command line for the detection engine.

    python -m app.detections run --source-type sentinel.native --source-id my-feed
    python -m app.detections export --source-id my-feed          # JSON Lines on stdout

`run` prints the run report as JSON; running again is safe (alerts already
stored are counted in alerts_existing). `export` prints one alert per line with
the events it cites — the input research/scripts/evaluate_detections.py reads.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.events.adapters import ADAPTERS


async def _with_session(work):
    from app.database.session import AsyncSessionLocal, engine

    try:
        async with AsyncSessionLocal() as session:
            return await work(session)
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.detections", description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run_cmd = commands.add_parser("run", help="run every rule over one source's stored events")
    run_cmd.add_argument("--source-type", required=True, choices=sorted(ADAPTERS))
    run_cmd.add_argument("--source-id", required=True)
    export_cmd = commands.add_parser("export", help="print stored alerts as JSON Lines")
    export_cmd.add_argument("--source-type", choices=sorted(ADAPTERS))
    export_cmd.add_argument("--source-id")
    args = parser.parse_args(argv)

    from app.detections.engine import export_alerts, run_detections

    if args.command == "run":
        try:
            report = asyncio.run(_with_session(lambda db: run_detections(
                db, source_type=args.source_type, source_id=args.source_id, origin="cli")))
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(report.as_dict(), indent=2))
    else:
        alerts = asyncio.run(_with_session(lambda db: export_alerts(
            db, source_type=args.source_type, source_id=args.source_id)))
        for alert in alerts:
            print(json.dumps(alert, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
