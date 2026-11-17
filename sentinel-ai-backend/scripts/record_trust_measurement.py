"""
Record the current trust score in its history. For schedulers (cron, Windows
Task Scheduler) and for operators.

    python scripts/record_trust_measurement.py                # trigger: scheduled
    python scripts/record_trust_measurement.py --trigger manual

Writes a row only if the score or its components changed since the last
recorded measurement, so running it often is harmless. Prints the outcome as
JSON. There is deliberately no scheduler inside the application: when and how
often to measure is an operations decision, made outside the process.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.session import AsyncSessionLocal, engine  # noqa: E402
from app.services.trust_intelligence import MEASUREMENT_TRIGGERS, TrustIntelligenceService  # noqa: E402


async def _record(trigger: str) -> dict:
    try:
        async with AsyncSessionLocal() as session:
            return await TrustIntelligenceService(session).record_measurement(trigger=trigger, recorded_by="cli")
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--trigger", default="scheduled", choices=MEASUREMENT_TRIGGERS)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(_record(args.trigger)), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
