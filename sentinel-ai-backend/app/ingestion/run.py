"""
Ingestion CLI.

    python -m app.ingestion.run                    # all 15 datasets, FK-safe order
    python -m app.ingestion.run --dataset risks    # one dataset (repeatable flag)
    python -m app.ingestion.run --list             # show dataset names and exit
    python -m app.ingestion.run --counts           # show live table counts and exit

Safe to run repeatedly: every table upserts on its natural-key primary key,
so a second run updates in place rather than duplicating.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ingestion.base import DatasetIngestor, DatasetResult, table_counts
from app.ingestion.configs.registry import BY_NAME, LOAD_ORDER

logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
logger = logging.getLogger("sentinel.ingestion.run")

DEFAULT_DATASETS_DIR = Path(__file__).resolve().parents[2] / "datasets"


def _print_summary(results: list[DatasetResult]) -> None:
    header = f"{'Dataset':<26}{'Read':>8}{'Inserted':>10}{'Updated':>9}{'Skipped':>9}{'Errors':>8}"
    print("\n" + "=" * len(header))
    print("INGESTION SUMMARY")
    print("=" * len(header))
    print(header)
    print("-" * len(header))
    totals = dict(read=0, inserted=0, updated=0, skipped=0, errors=0)
    for r in results:
        print(
            f"{r.dataset:<26}{r.rows_read:>8}{r.inserted:>10}{r.updated:>9}{r.skipped:>9}{r.errors:>8}"
        )
        totals["read"] += r.rows_read
        totals["inserted"] += r.inserted
        totals["updated"] += r.updated
        totals["skipped"] += r.skipped
        totals["errors"] += r.errors
    print("-" * len(header))
    print(
        f"{'TOTAL':<26}{totals['read']:>8}{totals['inserted']:>10}"
        f"{totals['updated']:>9}{totals['skipped']:>9}{totals['errors']:>8}"
    )
    print("=" * len(header))

    warned = [r for r in results if r.warnings]
    if warned:
        print("\nWarnings (advisory, rows still loaded):")
        for r in warned:
            print(f"  {r.dataset}: {r.warnings}")
            for msg in r.messages[:3]:
                print(f"      {msg}")

    failed = [r for r in results if not r.ok]
    if failed:
        print("\nDatasets with errors:")
        for r in failed:
            print(f"  {r.dataset}: {r.errors} error(s)")
            for msg in r.messages[:5]:
                print(f"      {msg}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.ingestion.run")
    parser.add_argument(
        "--dataset", action="append", dest="datasets",
        help="ingest only this dataset (repeatable). See --list for names.",
    )
    parser.add_argument("--datasets-dir", default=str(DEFAULT_DATASETS_DIR))
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--list", action="store_true", help="list dataset names and exit")
    parser.add_argument("--counts", action="store_true", help="print live table row counts and exit")
    args = parser.parse_args(argv)

    if args.list:
        for config in LOAD_ORDER:
            print(f"{config.dataset_type.value:<26} {config.filename}")
        return 0

    engine = create_engine(settings.database_url_sync, future=True)

    if args.counts:
        with Session(engine) as session:
            for table, count in table_counts(session).items():
                print(f"{table:<26}{count:>8}")
        return 0

    if args.datasets:
        unknown = [d for d in args.datasets if d not in BY_NAME]
        if unknown:
            parser.error(f"unknown dataset(s): {', '.join(unknown)}. Use --list.")
        # Keep FK-safe order even for a hand-picked subset.
        selected = [c for c in LOAD_ORDER if c.dataset_type.value in set(args.datasets)]
    else:
        selected = list(LOAD_ORDER)

    datasets_dir = Path(args.datasets_dir)
    logger.info("Ingesting %d dataset(s) from %s", len(selected), datasets_dir)

    results: list[DatasetResult] = []
    with Session(engine) as session:
        ingestor = DatasetIngestor(session, datasets_dir, chunk_size=args.chunk_size)
        for config in selected:
            logger.info("-> %s (%s)", config.dataset_type.value, config.filename)
            results.append(ingestor.ingest(config))

    _print_summary(results)
    if not all(r.ok for r in results):
        return 1
    return 0 if _record_trust_measurement() else 1


def _record_trust_measurement() -> bool:
    """The trust score is computed from the tables just loaded, so a completed
    load is the moment its history should gain a point (if anything changed).
    This is what keeps the history tied to changes in the data rather than to
    how often someone looks at the score."""
    import asyncio

    from app.database.session import AsyncSessionLocal
    from app.database.session import engine as async_engine
    from app.services.trust_intelligence import TrustIntelligenceService

    async def record() -> dict:
        try:
            async with AsyncSessionLocal() as session:
                return await TrustIntelligenceService(session).record_measurement(
                    trigger="dataset_ingestion", recorded_by="cli"
                )
        finally:
            await async_engine.dispose()

    try:
        outcome = asyncio.run(record())
    except Exception:  # noqa: BLE001 - the load itself succeeded; say exactly what did not
        logger.exception(
            "Datasets loaded, but the trust measurement could not be recorded. "
            "Is the database migrated (alembic upgrade head)?"
        )
        return False
    print(f"\nTrust measurement: {'recorded' if outcome['recorded'] else 'not recorded'} ({outcome['reason']}).")
    return True


if __name__ == "__main__":
    sys.exit(main())
