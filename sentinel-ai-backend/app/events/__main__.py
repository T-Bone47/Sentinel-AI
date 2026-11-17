"""
Command line for the event store.

    python -m app.events ingest FILE.jsonl --source-type sentinel.native --source-id my-feed

FILE is JSON Lines: one source record per line. Prints the batch report as
JSON on standard output. Safe to run again on the same file: events already
stored are counted as duplicates and nothing is changed.

Exit status is 0 when the batch completed, even if some records were
rejected — read the report. It is 2 for a usage error.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from app.events.adapters import ADAPTERS


async def _ingest_file(path: Path, source_type: str, source_id: str) -> dict[str, Any]:
    from app.database.session import AsyncSessionLocal, engine
    from app.events.store import ingest, read_jsonl

    try:
        async with AsyncSessionLocal() as session:
            report = await ingest(session, source_type=source_type, source_id=source_id,
                                  records=read_jsonl(path), origin="file", origin_detail=path.name)
        return report.as_dict()
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.events", description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    ingest_cmd = commands.add_parser("ingest", help="ingest a JSON Lines file of source records")
    ingest_cmd.add_argument("file", type=Path)
    ingest_cmd.add_argument("--source-type", required=True, choices=sorted(ADAPTERS))
    ingest_cmd.add_argument("--source-id", required=True, help="which feed these records belong to")
    args = parser.parse_args(argv)

    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")
    try:
        report = asyncio.run(_ingest_file(args.file, args.source_type, args.source_id))
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
