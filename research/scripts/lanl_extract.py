"""
The M2 windows of LANL's auth.txt, selected exactly as
research/M2_PREREGISTRATION.md §5 registers them. Standard library only.

There are two streaming passes over auth.txt.gz. Each stops once the last
window has ended, and the file is never unpacked to disk.

Pass 1 does two things:
  * It keeps every line by a red-team user that falls inside one of that
    user's windows.
  * It notes each other user account's latest `LogOn`. When a record's window
    ends, the accounts whose latest `LogOn` falls inside the window are that
    record's comparison candidates.

Then, for each record in file order, one seeded generator draws 3 candidates.
Pass 2 keeps the drawn accounts' lines inside their windows.
"""
from __future__ import annotations

import bisect
import gzip
import random
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

BEFORE = AFTER = 3600            # a record at t has the window [t - 3600, t + 3600)
LOOKBACK = 1800                  # and the scoring region [t - 1800, t + 3600)
DRAWS, SEED = 3, 20261117
USER = re.compile(rb"U\d+@")

Record = tuple[int, str, str, str]          # time, user, source computer, destination computer


def read_redteam(path: Path) -> tuple[list[Record], int]:
    """Distinct red-team records in file order, and the number of lines read."""
    distinct: dict[Record, None] = {}
    lines = 0
    with gzip.open(path, "rt", encoding="ascii") as f:
        for line in f:
            if line.strip():
                lines += 1
                t, user, src, dst = line.strip().split(",")
                distinct.setdefault((int(t), user, src, dst))
    return list(distinct), lines


def _scan(path: Path, stop: int) -> Iterator[tuple[int, int, bytes]]:
    """(line number from 1, time, line) for each line until the first with time >= stop."""
    previous = 0
    with gzip.open(path, "rb") as f:
        for number, line in enumerate(f, 1):
            t = int(line[:line.index(b",")])
            if t < previous:
                raise ValueError(f"auth.txt is not in time order at line {number}")
            if t >= stop:
                return
            previous = t
            yield number, t, line


def _merge(windows: list[tuple[int, int, int]]) -> list[dict[str, Any]]:
    """One account's overlapping [start, end) windows merged; each keeps the records it covers."""
    merged: list[dict[str, Any]] = []
    for start, end, record in sorted(windows):
        if merged and start < merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], end)
            merged[-1]["records"].append(record)
        else:
            merged.append({"start": start, "end": end, "records": [record], "lines": []})
    return merged


def _windows(records: list[Record], accounts: dict[str, list[int]]) -> dict[str, list[dict[str, Any]]]:
    """account -> its merged windows, from the records it is attached to."""
    return {account: _merge([(records[i][0] - BEFORE, records[i][0] + AFTER, i) for i in indices])
            for account, indices in sorted(accounts.items())}


def _keeper(table: dict[str, list[dict[str, Any]]]):
    index = {account.encode("ascii"): ([w["start"] for w in ws], ws) for account, ws in table.items()}

    def keep(user: bytes, number: int, t: int, line: bytes) -> bool:
        """Store the line if it falls in one of the user's windows. True if the user is tracked at all."""
        found = index.get(user)
        if found is None:
            return False
        starts, windows = found
        j = bisect.bisect_right(starts, t) - 1
        if j >= 0 and t < windows[j]["end"]:
            windows[j]["lines"].append([number, line.rstrip(b"\r\n").decode("ascii")])
        return True

    return keep


def extract(path: Path, records: list[Record]) -> dict[str, Any]:
    by_user: dict[str, list[int]] = {}
    for i, record in enumerate(records):
        by_user.setdefault(record[1], []).append(i)
    redteam = _windows(records, by_user)
    keep = _keeper(redteam)
    first = min(r[0] for r in records) - BEFORE
    ending = sorted(range(len(records)), key=lambda i: records[i][0])   # all windows are equally long
    candidates: list[list[str]] = [[] for _ in records]
    latest_logon: dict[bytes, int] = {}

    def close(i: int) -> None:
        low = records[i][0] - BEFORE
        candidates[i] = sorted(a.decode("ascii") for a, seen in latest_logon.items() if seen >= low)

    k = read = 0
    for read, t, line in _scan(path, max(r[0] for r in records) + AFTER):
        while k < len(ending) and t >= records[ending[k]][0] + AFTER:
            close(ending[k])
            k += 1
        if t < first:
            continue
        user = line.split(b",", 2)[1]
        if not keep(user, read, t, line) and USER.match(user):
            fields = line.split(b",")
            if len(fields) == 9 and fields[7] == b"LogOn":
                latest_logon[user] = t
    for i in ending[k:]:                        # windows still open when the scan stopped
        close(i)

    rng = random.Random(SEED)
    draws = [found if len(found) <= DRAWS else rng.sample(found, DRAWS) for found in candidates]
    drawn: dict[str, list[int]] = {}
    for i, accounts in enumerate(draws):
        for account in accounts:
            drawn.setdefault(account, []).append(i)
    comparison = _windows(records, drawn)
    keep = _keeper(comparison)
    stop = max((w["end"] for ws in comparison.values() for w in ws), default=0)
    for number, t, line in _scan(path, stop):
        if t >= first:
            keep(line.split(b",", 2)[1], number, t, line)

    sources = []
    for kind, table in (("rt", redteam), ("cmp", comparison)):
        windows = [(account, w) for account, ws in table.items() for w in ws]
        sources += [{"id": f"lanl-{kind}-{n:04d}", "kind": kind, "account": account, **w}
                    for n, (account, w) in enumerate(windows, 1)]
    return {"lines_read": read, "candidates": [len(c) for c in candidates], "draws": draws, "sources": sources}
