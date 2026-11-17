"""
Gate 2 — the security-event contract, ingestion and provenance.

What these tests pin down:
  * a record either becomes exactly one immutable event or is rejected with a
    reason — never silently dropped, never partly stored;
  * ingesting the same data again changes nothing (replay is a no-op);
  * the result does not depend on the order records arrive in;
  * every stored event can be traced to its source record and ingestion batch;
  * only permitted roles can read events, and only an admin can ingest them.

Everything here runs against the migrated database (SQLite in the fast suite,
PostgreSQL when DATABASE_URL points at one). Each test ingests under its own
throwaway source id and removes its rows afterwards.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import random
import subprocess
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from tests.test_gate1_security import API, _as

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
FIXTURE_DIR = REPO_ROOT / "research" / "fixtures" / "identity-access-v1"
GENERATOR = REPO_ROOT / "research" / "scripts" / "build_identity_access_fixture.py"
NATIVE = "sentinel.native"


def rec(n: int, **overrides) -> dict:
    """A valid record in the native wire format."""
    base = {
        "source_event_id": f"e-{n:04d}",
        "occurred_at": f"2026-09-01T08:{n % 60:02d}:00Z",
        "actor": {"type": "user", "id": "lab-user-001"},
        "target": {"type": "application", "id": "lab-app-wiki"},
        "action": "auth.login",
        "outcome": "success",
        "src_ip": "198.51.100.10",
        "attributes": {"mfa_used": True, "privileged": False},
    }
    base.update(overrides)
    return base


@pytest.fixture
async def db():
    from app.database.session import AsyncSessionLocal, engine

    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def new_source(sync_engine):
    """Factory for unique source ids; their events, rejects and batches are deleted afterwards."""
    from app.models import EventIngestBatch, EventIngestReject, SecurityEvent

    made: list[str] = []

    def make() -> str:
        made.append(f"t-{uuid.uuid4().hex[:16]}")
        return made[-1]

    yield make

    with Session(sync_engine) as session:
        for source_id in made:
            batch_ids = select(EventIngestBatch.id).where(EventIngestBatch.source_id == source_id)
            session.execute(delete(SecurityEvent).where(SecurityEvent.source_id == source_id))
            session.execute(delete(EventIngestReject).where(EventIngestReject.batch_id.in_(batch_ids)))
            session.execute(delete(EventIngestBatch).where(EventIngestBatch.source_id == source_id))
        session.commit()


async def _ingest(db, source_id: str, records, source_type: str = NATIVE):
    from app.events.store import ingest

    return await ingest(db, source_type=source_type, source_id=source_id, records=records, origin="test")


async def _rows(db, source_id: str) -> list:
    from app.models import SecurityEvent

    stmt = (
        select(SecurityEvent).where(SecurityEvent.source_id == source_id).order_by(SecurityEvent.event_id)
        # Re-read from the database every time. Without this the session
        # would hand back the objects it already holds, and a test comparing
        # "before" and "after" would be comparing an object with itself.
        .execution_options(populate_existing=True)
    )
    return list((await db.execute(stmt)).scalars().all())


def _content(row) -> tuple:
    """Everything about a stored event that must not depend on when, in what
    order, or under which source id it was ingested."""
    return (
        row.source_event_id, row.occurred_at, row.actor_type, row.actor_id, row.target_type,
        row.target_id, row.action, row.source_action, row.outcome, row.src_ip,
        json.dumps(row.attributes, sort_keys=True), row.normalizer, row.schema_version,
        row.raw_canonical, row.raw_sha256,
    )


# --------------------------------------------------------------------------
# 1. The contract (pure functions, no database)
# --------------------------------------------------------------------------

def _normalize(record: dict, source_type: str = NATIVE):
    from app.events.adapters import ADAPTERS

    return ADAPTERS[source_type].normalize(record)


def test_native_record_normalizes_to_the_contract():
    event = _normalize(rec(1, source_action="idp.signin"))
    assert event.source_event_id == "e-0001"
    assert event.occurred_at == datetime(2026, 9, 1, 8, 1, tzinfo=timezone.utc)
    assert (event.actor.type, event.actor.id) == ("user", "lab-user-001")
    assert (event.target.type, event.target.id) == ("application", "lab-app-wiki")
    assert (event.action, event.source_action, event.outcome) == ("auth.login", "idp.signin", "success")
    assert event.src_ip == "198.51.100.10"
    assert event.attributes == {"mfa_used": True, "privileged": False}


def test_source_action_defaults_to_the_normalized_action():
    assert _normalize(rec(1)).source_action == "auth.login"


def test_timestamps_are_converted_to_utc():
    event = _normalize(rec(1, occurred_at="2026-09-01T13:31:00+05:30"))
    assert event.occurred_at == datetime(2026, 9, 1, 8, 1, tzinfo=timezone.utc)
    assert event.occurred_at.utcoffset().total_seconds() == 0


@pytest.mark.parametrize("label,record", [
    ("naive timestamp", rec(1, occurred_at="2026-09-01T08:00:00")),
    ("numeric timestamp", rec(1, occurred_at=1756713600)),
    ("not a timestamp", rec(1, occurred_at="yesterday")),
    ("unknown action", rec(1, action="auth.teleport")),
    ("unknown outcome", rec(1, outcome="maybe")),
    ("unknown actor type", rec(1, actor={"type": "wizard", "id": "x"})),
    ("empty actor id", rec(1, actor={"type": "user", "id": ""})),
    ("invalid ip", rec(1, src_ip="999.1.1.1")),
    ("unknown attribute", rec(1, attributes={"shoe_size": 9})),
    ("attribute of the wrong type", rec(1, attributes={"mfa_used": "yes"})),
    ("int is not a bool", rec(1, attributes={"mfa_used": 1})),
    ("attribute outside its vocabulary", rec(1, attributes={"sensitivity": "top-secret"})),
    ("unexpected top-level field", {**rec(1), "label": "suspicious"}),
    ("unexpected nested field", rec(1, actor={"type": "user", "id": "x", "name": "Alice"})),
    ("missing id", {k: v for k, v in rec(1).items() if k != "source_event_id"}),
    ("missing time", {k: v for k, v in rec(1).items() if k != "occurred_at"}),
    ("control character in id", rec(1, source_event_id="e-1\x1fx")),
    # Invisible formatting characters make an identifier display as something
    # it is not, which matters for evidence a person reads.
    ("bidi override in id", rec(1, source_event_id="e-1‮x")),
    ("bidi isolate in actor id", rec(1, actor={"type": "user", "id": "lab-user⁦-001"})),
    ("zero-width space in attribute", rec(1, attributes={"approval_ref": "CHG​-1041"})),
    ("C1 control character in id", rec(1, source_event_id="e-1\x85x")),
])
def test_invalid_records_are_refused_by_the_contract(label, record):
    from app.events.contract import ContractError

    with pytest.raises(ContractError) as excinfo:
        _normalize(record)
    assert excinfo.value.reason == "invalid_record", label


def test_contract_errors_name_the_field_but_never_echo_the_value():
    from app.events.contract import ContractError

    secret = "Sup3r-Secret-" + uuid.uuid4().hex
    with pytest.raises(ContractError) as excinfo:
        _normalize(rec(1, attributes={"mfa_used": secret}, outcome=secret))
    assert "mfa_used" in excinfo.value.detail and "outcome" in excinfo.value.detail
    assert secret not in excinfo.value.detail


def test_event_id_is_deterministic_and_unique_per_source():
    from app.events.contract import event_id_for

    first = event_id_for(NATIVE, "feed-a", "e-1")
    assert first == event_id_for(NATIVE, "feed-a", "e-1")
    assert len(first) == 64 and int(first, 16) >= 0
    assert len({first, event_id_for(NATIVE, "feed-b", "e-1"), event_id_for("aws.cloudtrail", "feed-a", "e-1"),
                event_id_for(NATIVE, "feed-a", "e-2")}) == 4
    # The separator cannot be forged by moving characters between the parts.
    assert event_id_for(NATIVE, "a", "b-c") != event_id_for(NATIVE, "a-b", "c")


def test_canonical_form_ignores_formatting_but_not_content():
    from app.events.contract import canonical_json, sha256_hex

    a = json.loads('{"b": 1, "a": {"y": [1, 2], "x": "é"}}')
    b = json.loads('{ "a": {"x": "\\u00e9", "y": [1,2]},\n  "b": 1 }')
    assert canonical_json(a) == canonical_json(b) == '{"a":{"x":"é","y":[1,2]},"b":1}'
    assert sha256_hex(canonical_json(a)) == hashlib.sha256('{"a":{"x":"é","y":[1,2]},"b":1}'.encode()).hexdigest()
    assert canonical_json({**a, "b": 2}) != canonical_json(a)


def test_events_table_has_no_place_for_ground_truth_labels():
    """Labels live only in the fixture's labels file. If they were stored next
    to the events, a detector could read the answer."""
    from app.events.contract import ATTRIBUTE_TYPES
    from app.models import SecurityEvent

    forbidden = {"label", "scenario_id", "scenario", "is_malicious", "ground_truth"}
    assert not forbidden & set(SecurityEvent.__table__.columns.keys())
    assert not forbidden & set(ATTRIBUTE_TYPES)


# --------------------------------------------------------------------------
# 2. Ingestion: exactly-once, order-independent, fully accounted for
# --------------------------------------------------------------------------

async def test_valid_records_are_stored_with_provenance(db, new_source):
    from app.events.contract import canonical_json, event_id_for, sha256_hex
    from app.models import EventIngestBatch

    source_id = new_source()
    before = datetime.now(timezone.utc)
    report = await _ingest(db, source_id, [rec(1), rec(2, occurred_at="2026-09-01T13:32:00+05:30")])

    assert (report.received, report.inserted, report.duplicates, report.conflicts, report.rejected) == (2, 2, 0, 0, 0)
    rows = {row.source_event_id: row for row in await _rows(db, source_id)}
    first = rows["e-0001"]
    assert first.event_id == event_id_for(NATIVE, source_id, "e-0001")
    assert first.raw_canonical == canonical_json(rec(1))
    assert first.raw_sha256 == sha256_hex(first.raw_canonical)
    assert first.normalizer == "sentinel.native@1" and first.schema_version == 1
    assert first.ingest_batch_id == report.batch_id
    assert first.ingested_at.utcoffset().total_seconds() == 0 and first.ingested_at >= before.replace(microsecond=0)
    # The +05:30 input is stored as the same instant in UTC.
    assert rows["e-0002"].occurred_at == datetime(2026, 9, 1, 8, 2, tzinfo=timezone.utc)

    batch = (await db.execute(select(EventIngestBatch).where(EventIngestBatch.id == report.batch_id))).scalar_one()
    assert (batch.status, batch.received, batch.inserted, batch.origin) == ("completed", 2, 2, "test")
    assert batch.finished_at is not None


async def test_replaying_the_same_records_changes_nothing(db, new_source):
    source_id = new_source()
    records = [rec(n) for n in range(1, 31)]
    await _ingest(db, source_id, records)
    before = [(_content(r), r.event_id, r.ingested_at, r.ingest_batch_id) for r in await _rows(db, source_id)]

    replay = await _ingest(db, source_id, records)

    assert (replay.received, replay.inserted, replay.duplicates, replay.conflicts, replay.rejected) == (30, 0, 30, 0, 0)
    after = [(_content(r), r.event_id, r.ingested_at, r.ingest_batch_id) for r in await _rows(db, source_id)]
    assert after == before


async def test_result_does_not_depend_on_arrival_order_or_batching(db, new_source):
    records = [rec(n, occurred_at=f"2026-09-{1 + n % 9:02d}T{n % 24:02d}:15:00Z") for n in range(1, 61)]
    shuffled = records[:]
    random.Random(7).shuffle(shuffled)

    in_order, out_of_order = new_source(), new_source()
    await _ingest(db, in_order, records)
    for start in range(0, 60, 7):                      # different batch boundaries too
        await _ingest(db, out_of_order, shuffled[start:start + 7])

    assert sorted(_content(r) for r in await _rows(db, in_order)) == \
        sorted(_content(r) for r in await _rows(db, out_of_order))


async def test_duplicate_inside_one_batch_is_stored_once(db, new_source):
    source_id = new_source()
    report = await _ingest(db, source_id, [rec(1), rec(2), rec(1)])
    assert (report.inserted, report.duplicates) == (2, 1)
    assert len(await _rows(db, source_id)) == 2


async def test_conflicting_resend_never_overwrites_the_original(db, new_source):
    from app.models import EventIngestReject

    source_id = new_source()
    await _ingest(db, source_id, [rec(1)])
    original = _content((await _rows(db, source_id))[0])

    report = await _ingest(db, source_id, [rec(1, src_ip="203.0.113.99")])   # same id, different content

    assert (report.inserted, report.duplicates, report.conflicts, report.rejected) == (0, 0, 1, 0)
    assert report.rejects[0]["reason"] == "conflicting_duplicate"
    assert _content((await _rows(db, source_id))[0]) == original
    stored = (await db.execute(
        select(EventIngestReject).where(EventIngestReject.batch_id == report.batch_id)
    )).scalar_one()
    assert stored.reason == "conflicting_duplicate" and stored.source_event_id == "e-0001"
    assert stored.raw_sha256 != (await _rows(db, source_id))[0].raw_sha256   # the hash of what was refused


async def test_stored_events_cannot_be_modified(db, new_source):
    """Enforced by the database, not only by the absence of an update function."""
    from app.models import SecurityEvent

    source_id = new_source()
    await _ingest(db, source_id, [rec(1)])
    with pytest.raises(DBAPIError):
        await db.execute(update(SecurityEvent).where(SecurityEvent.source_id == source_id).values(outcome="failure"))
        await db.commit()
    await db.rollback()
    assert (await _rows(db, source_id))[0].outcome == "success"


async def test_bad_records_are_rejected_individually_and_fully_accounted_for(db, new_source):
    from app.events.contract import MAX_RECORD_BYTES
    from app.events.store import InvalidRecord

    source_id = new_source()
    records = [
        rec(1),
        rec(2, action="auth.teleport"),                                  # schema violation
        ["not", "an", "object"],
        rec(3, occurred_at="2099-01-01T00:00:00Z"),                      # implausible future
        rec(4, attributes={"role": "x" * (MAX_RECORD_BYTES + 1)}),       # too large
        InvalidRecord("invalid_json", "line is not valid JSON"),         # what the file reader yields
        rec(5),
    ]
    report = await _ingest(db, source_id, records)

    assert (report.received, report.inserted, report.rejected) == (7, 2, 5)
    assert report.received == report.inserted + report.duplicates + report.conflicts + report.rejected
    assert [(r["index"], r["reason"]) for r in report.rejects] == [
        (1, "invalid_record"), (2, "not_an_object"), (3, "timestamp_in_future"),
        (4, "record_too_large"), (5, "invalid_json"),
    ]
    assert sorted(r.source_event_id for r in await _rows(db, source_id)) == ["e-0001", "e-0005"]


async def test_reject_reports_do_not_contain_the_rejected_content(db, new_source):
    from app.models import EventIngestReject

    source_id = new_source()
    secret = "Sup3r-Secret-" + uuid.uuid4().hex
    report = await _ingest(db, source_id, [rec(1, outcome=secret, attributes={"role": secret, "mfa_used": secret})])

    stored = (await db.execute(
        select(EventIngestReject).where(EventIngestReject.batch_id == report.batch_id)
    )).scalar_one()
    assert secret not in json.dumps(report.rejects) and secret not in stored.detail
    assert stored.raw_sha256 and len(stored.raw_sha256) == 64   # identifies the record without keeping it


async def test_adapter_crash_on_one_record_does_not_lose_the_rest_of_the_batch(db, new_source, monkeypatch):
    from app.events import adapters

    def fragile(record):
        if record["source_event_id"] == "e-0002":
            raise RuntimeError("adapter bug")
        return adapters.normalized(record)

    monkeypatch.setitem(adapters.ADAPTERS, NATIVE, adapters.Adapter(NATIVE, 1, fragile))
    source_id = new_source()
    report = await _ingest(db, source_id, [rec(1), rec(2), rec(3)])

    assert (report.inserted, report.rejected) == (2, 1)
    assert [(r["index"], r["reason"]) for r in report.rejects] == [(1, "normalizer_error")]
    assert "adapter bug" not in json.dumps(report.rejects)      # internals stay in the server log


async def test_unknown_source_type_is_refused_before_anything_is_written(db, new_source):
    from app.models import EventIngestBatch

    source_id = new_source()
    with pytest.raises(ValueError):
        await _ingest(db, source_id, [rec(1)], source_type="made.up")
    count = (await db.execute(
        select(func.count()).select_from(EventIngestBatch).where(EventIngestBatch.source_id == source_id)
    )).scalar_one()
    assert count == 0


async def test_large_input_is_processed_in_bounded_chunks(db, new_source, monkeypatch):
    from app.events import store

    monkeypatch.setattr(store, "CHUNK_SIZE", 10)
    source_id = new_source()
    report = await store.ingest(
        db, source_id=source_id, source_type=NATIVE, origin="test",
        records=(rec(n, source_event_id=f"g-{n}") for n in range(95)),   # a generator: never fully in memory
    )
    assert (report.received, report.inserted) == (95, 95)
    assert len(await _rows(db, source_id)) == 95


async def test_racing_writer_is_resolved_as_a_duplicate_not_an_error(db, new_source, monkeypatch):
    """If another ingest stores the same event between our check and our
    insert, the primary key refuses ours; the chunk is retried and the event
    is then correctly counted as a duplicate."""
    from app.events import store

    source_id = new_source()
    await _ingest(db, source_id, [rec(1)])

    real_lookup, calls = store._existing_hashes, {"n": 0}

    async def stale_once(session, event_ids):
        calls["n"] += 1
        return {} if calls["n"] == 1 else await real_lookup(session, event_ids)

    monkeypatch.setattr(store, "_existing_hashes", stale_once)
    report = await _ingest(db, source_id, [rec(1), rec(2)])

    assert calls["n"] == 2
    assert (report.inserted, report.duplicates) == (1, 1)
    assert len(await _rows(db, source_id)) == 2


# --------------------------------------------------------------------------
# 3. Reading: event-time order and loss-free pagination
# --------------------------------------------------------------------------

async def _page_all(db, source_id: str, limit: int, order: str, between_pages=None) -> list[str]:
    from app.events.store import list_events

    seen, cursor = [], None
    while True:
        rows, cursor = await list_events(db, filters={"source_id": source_id}, order=order, limit=limit, cursor=cursor)
        seen.extend(row.source_event_id for row in rows)
        if cursor is None:
            return seen
        if between_pages:
            await between_pages()


async def test_events_are_listed_in_event_time_order_whatever_order_they_arrived_in(db, new_source):
    source_id = new_source()
    times = {"late": "2026-09-01T09:00:00Z", "early": "2026-09-01T07:00:00Z", "middle": "2026-09-01T08:00:00Z"}
    await _ingest(db, source_id, [rec(i, source_event_id=name, occurred_at=t) for i, (name, t) in enumerate(times.items())])

    assert await _page_all(db, source_id, limit=10, order="asc") == ["early", "middle", "late"]
    assert await _page_all(db, source_id, limit=10, order="desc") == ["late", "middle", "early"]


async def test_pagination_returns_every_event_exactly_once_even_with_identical_timestamps(db, new_source):
    source_id = new_source()
    same_instant = [rec(n, source_event_id=f"tie-{n:02d}", occurred_at="2026-09-01T08:00:00Z") for n in range(12)]
    others = [rec(n, source_event_id=f"x-{n:02d}") for n in range(13)]
    await _ingest(db, source_id, same_instant + others)

    for order in ("asc", "desc"):
        seen = await _page_all(db, source_id, limit=4, order=order)
        assert len(seen) == 25 and len(set(seen)) == 25, order


async def test_pagination_is_stable_while_new_events_arrive(db, new_source):
    source_id = new_source()
    await _ingest(db, source_id, [rec(n, source_event_id=f"a-{n:02d}") for n in range(20)])
    arrivals = iter(range(100, 110))

    async def more_arrive():
        n = next(arrivals)
        await _ingest(db, source_id, [rec(n, source_event_id=f"b-{n}", occurred_at="2026-08-01T00:00:00Z")])

    seen = await _page_all(db, source_id, limit=6, order="desc", between_pages=more_arrive)
    assert len(seen) == len(set(seen))                       # nothing repeated
    assert {f"a-{n:02d}" for n in range(20)} <= set(seen)     # nothing that existed at the start is skipped


async def test_garbage_cursor_is_refused(db, new_source):
    from app.events.store import list_events

    with pytest.raises(ValueError):
        await list_events(db, filters={"source_id": new_source()}, order="asc", limit=5, cursor="not-a-cursor")


# --------------------------------------------------------------------------
# 4. File ingestion and the command line
# --------------------------------------------------------------------------

def test_jsonl_reader_reports_unreadable_lines_instead_of_stopping(tmp_path):
    from app.events.contract import MAX_RECORD_BYTES
    from app.events.store import InvalidRecord, read_jsonl

    path = tmp_path / "in.jsonl"
    path.write_bytes(
        json.dumps(rec(1)).encode() + b"\n"
        + b"\n"                                              # blank line: skipped
        + b'{"source_event_id": "broken", \n'                # not JSON
        + b'{"a": "' + b"x" * (MAX_RECORD_BYTES + 10) + b'"}\n'   # too long to even parse
        + b"\xff\xfe not utf-8\n"
        + json.dumps(rec(2)).encode()                        # no trailing newline
    )
    items = list(read_jsonl(path))

    assert [type(i).__name__ for i in items] == ["dict", "InvalidRecord", "InvalidRecord", "InvalidRecord", "dict"]
    assert [i.reason for i in items if isinstance(i, InvalidRecord)] == ["invalid_json", "record_too_large", "invalid_json"]
    assert items[0] == rec(1) and items[-1] == rec(2)


def test_command_line_ingests_a_file_and_prints_the_report(tmp_path, new_source):
    source_id = new_source()
    path = tmp_path / "events.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in [rec(1), rec(2), rec(1), {"nope": 1}]) + "\n", encoding="utf-8")

    def run():
        done = subprocess.run(
            [sys.executable, "-m", "app.events", "ingest", str(path), "--source-type", NATIVE, "--source-id", source_id],
            cwd=BACKEND_ROOT, env=os.environ.copy(), capture_output=True, text=True, timeout=120,
        )
        assert done.returncode == 0, done.stderr[-2000:]
        return json.loads(done.stdout)

    first, second = run(), run()
    assert {k: first[k] for k in ("received", "inserted", "duplicates", "conflicts", "rejected")} == \
        {"received": 4, "inserted": 2, "duplicates": 1, "conflicts": 0, "rejected": 1}
    assert (second["inserted"], second["duplicates"], second["rejected"]) == (0, 3, 1)
    assert first["rejects"][0]["reason"] == "invalid_record" and first["rejects"][0]["index"] == 3


# --------------------------------------------------------------------------
# 5. The frozen synthetic fixture
# --------------------------------------------------------------------------

def _manifest() -> dict:
    return json.loads((FIXTURE_DIR / "MANIFEST.json").read_text(encoding="utf-8"))


def test_fixture_files_match_their_manifest_hashes():
    manifest = _manifest()
    assert manifest["synthetic"] is True
    for name, info in manifest["files"].items():
        assert hashlib.sha256((FIXTURE_DIR / name).read_bytes()).hexdigest() == info["sha256"], name


def test_fixture_generator_reproduces_the_frozen_files_byte_for_byte():
    spec = importlib.util.spec_from_file_location("build_identity_access_fixture", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    built = module.build()
    assert sorted(built) == sorted(p.name for p in FIXTURE_DIR.iterdir() if p.name != "README.md")
    for name, content in built.items():
        assert content == (FIXTURE_DIR / name).read_bytes(), name


def test_fixture_labels_cover_every_event_and_stay_out_of_the_events_file():
    events = [json.loads(line) for line in (FIXTURE_DIR / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    labels = [json.loads(line) for line in (FIXTURE_DIR / "labels.jsonl").read_text(encoding="utf-8").splitlines()]
    event_ids = {e["source_event_id"] for e in events}

    assert {l["source_event_id"] for l in labels} == event_ids
    assert len(labels) == len(event_ids)                                  # exactly one label per event
    assert {l["label"] for l in labels} == {"suspicious", "benign"}
    assert all(set(e) <= {"source_event_id", "occurred_at", "actor", "target", "action", "source_action",
                          "outcome", "src_ip", "attributes"} for e in events)
    scenarios = {s["id"]: s for s in _manifest()["scenarios"]}
    assert {l["scenario_id"] for l in labels} == set(scenarios)
    # Every suspicious scenario has at least one benign counterpart in the same family.
    families = {}
    for s in scenarios.values():
        families.setdefault(s["family"], set()).add(s["label"])
    assert all(kinds == {"suspicious", "benign"} for family, kinds in families.items() if family != "background")


def test_fixture_is_not_sorted_so_it_exercises_out_of_order_arrival():
    times = [json.loads(line)["occurred_at"] for line in (FIXTURE_DIR / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    parsed = [datetime.fromisoformat(t) for t in times]
    assert parsed != sorted(parsed)


async def test_fixture_ingests_exactly_as_the_manifest_says_and_replays_cleanly(db, new_source):
    from app.events.store import ingest, read_jsonl

    expected, source_id = _manifest()["expected"], new_source()

    async def run(name: str) -> dict:
        report = await ingest(db, source_type=NATIVE, source_id=source_id, origin="test",
                              records=read_jsonl(FIXTURE_DIR / name))
        reasons: dict[str, int] = {}
        for reject in report.rejects:
            reasons[reject["reason"]] = reasons.get(reject["reason"], 0) + 1
        return {"received": report.received, "inserted": report.inserted, "duplicates": report.duplicates,
                "conflicts": report.conflicts, "rejected": report.rejected, "reject_reasons": reasons}

    assert await run("events.jsonl") == expected["events.jsonl"]
    stored = len(await _rows(db, source_id))
    assert await run("events.jsonl") == expected["events.jsonl (replayed)"]
    assert len(await _rows(db, source_id)) == stored                     # zero unintended duplicates
    assert await run("replay-conflict.jsonl") == expected["replay-conflict.jsonl"]
    assert await run("malformed.jsonl") == expected["malformed.jsonl"]


# --------------------------------------------------------------------------
# 6. AWS CloudTrail adapter (synthetic records in the published record shape)
# --------------------------------------------------------------------------

CLOUDTRAIL = "aws.cloudtrail"


def trail(**overrides) -> dict:
    base = {
        "eventVersion": "1.09",
        "eventID": "3f0c2a52-1111-4222-8333-444455556666",
        "eventTime": "2026-09-02T10:20:30Z",
        "eventSource": "iam.amazonaws.com",
        "eventName": "AttachUserPolicy",
        "awsRegion": "us-east-1",
        "sourceIPAddress": "203.0.113.7",
        "userIdentity": {"type": "IAMUser", "arn": "arn:aws:iam::123456789012:user/lab-admin", "userName": "lab-admin"},
        "requestParameters": {"userName": "lab-dev", "policyArn": "arn:aws:iam::aws:policy/AdministratorAccess"},
    }
    base.update(overrides)
    return base


def test_cloudtrail_privilege_grant():
    event = _normalize(trail(), CLOUDTRAIL)
    assert event.source_event_id == "3f0c2a52-1111-4222-8333-444455556666"
    assert event.occurred_at == datetime(2026, 9, 2, 10, 20, 30, tzinfo=timezone.utc)
    assert (event.action, event.source_action, event.outcome) == ("privilege.grant", "iam:AttachUserPolicy", "success")
    assert (event.actor.type, event.actor.id) == ("user", "arn:aws:iam::123456789012:user/lab-admin")
    assert (event.target.type, event.target.id) == ("principal", "lab-dev")
    assert event.attributes == {"role": "arn:aws:iam::aws:policy/AdministratorAccess"}
    assert event.src_ip == "203.0.113.7"


@pytest.mark.parametrize("response,mfa,outcome,mfa_used", [
    ("Success", "Yes", "success", True),
    ("Success", "No", "success", False),
    ("Failure", "No", "failure", False),
])
def test_cloudtrail_console_login(response, mfa, outcome, mfa_used):
    event = _normalize(trail(
        eventSource="signin.amazonaws.com", eventName="ConsoleLogin", requestParameters=None,
        responseElements={"ConsoleLogin": response}, additionalEventData={"MFAUsed": mfa},
    ), CLOUDTRAIL)
    assert (event.action, event.source_action, event.outcome) == ("auth.login", "signin:ConsoleLogin", outcome)
    assert event.attributes["mfa_used"] is mfa_used and event.target is None


def test_cloudtrail_error_code_means_the_call_failed():
    event = _normalize(trail(errorCode="AccessDenied", errorMessage="User is not authorized"), CLOUDTRAIL)
    assert event.outcome == "failure" and event.attributes["failure_reason"] == "AccessDenied"


def test_cloudtrail_unmapped_call_is_kept_as_other_with_its_native_name():
    event = _normalize(trail(eventSource="s3.amazonaws.com", eventName="GetObject", requestParameters={"bucketName": "b"}),
                       CLOUDTRAIL)
    assert (event.action, event.source_action, event.target, event.attributes) == ("other", "s3:GetObject", None, {})


def test_cloudtrail_identity_types_and_non_ip_callers():
    role = _normalize(trail(
        userIdentity={"type": "AssumedRole", "arn": "arn:aws:sts::123456789012:assumed-role/lab-role/session"},
        sourceIPAddress="cloudformation.amazonaws.com",
    ), CLOUDTRAIL)
    assert role.actor.type == "role" and role.src_ip is None

    root = _normalize(trail(userIdentity={"type": "Root", "arn": "arn:aws:iam::123456789012:root"}), CLOUDTRAIL)
    assert root.actor.type == "user" and root.attributes["privileged"] is True

    service = _normalize(trail(userIdentity={"type": "AWSService", "invokedBy": "config.amazonaws.com"}), CLOUDTRAIL)
    assert (service.actor.type, service.actor.id) == ("service", "config.amazonaws.com")

    nobody = _normalize(trail(userIdentity={"type": "SomethingNew"}), CLOUDTRAIL)
    assert nobody.actor is None


@pytest.mark.parametrize("broken", [
    {k: v for k, v in trail().items() if k != "eventID"},
    {k: v for k, v in trail().items() if k != "eventTime"},
    trail(eventTime="2026-09-02 10:20:30"),
    trail(eventName=None),
    trail(userIdentity="lab-admin"),
])
def test_cloudtrail_records_missing_required_fields_are_refused(broken):
    from app.events.contract import ContractError

    with pytest.raises(ContractError):
        _normalize(broken, CLOUDTRAIL)


async def test_cloudtrail_records_ingest_idempotently(db, new_source):
    source_id = new_source()
    records = [trail(), trail(eventID="9b1d7c10-aaaa-4bbb-8ccc-ddddeeeeffff", eventName="CreateUser")]
    first = await _ingest(db, source_id, records, source_type=CLOUDTRAIL)
    second = await _ingest(db, source_id, records, source_type=CLOUDTRAIL)
    assert (first.inserted, second.inserted, second.duplicates) == (2, 0, 2)
    assert {r.normalizer for r in await _rows(db, source_id)} == {"aws.cloudtrail@1"}


REAL_SAMPLES = REPO_ROOT / "research" / "external" / "splunk-attack-data"
REAL_CLOUDTRAIL = REAL_SAMPLES / "T1110.001-aws_login_failure" / "aws_cloudtrail_events.json"


@pytest.mark.skipif(not REAL_CLOUDTRAIL.is_file(),
                    reason="public sample not downloaded; see docs/M2_DATASET_SHORTLIST.md")
def test_cloudtrail_adapter_reads_real_console_login_failures():
    """The adapter's first real CloudTrail records: Splunk attack_data (Apache 2.0),
    seven console sign-in failures. Pinned by hash, so a changed file fails loudly."""
    data = REAL_CLOUDTRAIL.read_bytes()
    assert hashlib.sha256(data).hexdigest() == "d9d0ebbaf9a6aebd504b03f665eb1f35dfee4e34c0c6a5cf1c5318b7a12c1e9b"
    events = [_normalize(json.loads(line), CLOUDTRAIL) for line in data.decode("utf-8").splitlines() if line.strip()]
    assert len(events) == 7
    assert {(e.action, e.outcome, e.source_action) for e in events} == {("auth.login", "failure", "signin:ConsoleLogin")}
    assert all(isinstance(e.attributes.get("mfa_used"), bool) for e in events)


def _real_sample(relative: str, sha256: str) -> list[dict]:
    """A downloaded public sample's records (JSON Lines), checked against its pinned hash."""
    path = REAL_SAMPLES / relative
    if not path.is_file():
        pytest.skip("public sample not downloaded; see docs/M2_DATASET_SHORTLIST.md")
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == sha256, "sample changed; re-check it before re-pinning"
    return [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]


def _alerts(events) -> dict[str, int]:
    """Findings per rule when the rules run over normalized events, in memory."""
    from app.detections.rules import EventView, evaluate

    views = [EventView(event_id=f"{i:064x}", occurred_at=e.occurred_at, action=e.action, outcome=e.outcome,
                       actor_id=e.actor.id if e.actor else None, target_id=e.target.id if e.target else None,
                       attributes=e.attributes) for i, e in enumerate(events)]
    return {rule_id: len(result.findings) for rule_id, result in evaluate(views).items()}


REAL_IAM_DELETIONS = {
    # file: (SHA-256, records, distinct eventIDs, failures by errorCode)
    "T1098-aws_iam_delete_policy/aws_iam_delete_policy.json": (
        "862f9c73569bcdd38006b242bcdcd82b1424cabaaee01c4f931732e5f4c04b33", 116, 110,
        {"NoSuchEntityException": 29, "DeleteConflictException": 6, "AccessDenied": 3}),
    "T1098-aws_iam_successful_group_deletion/aws_iam_successful_group_deletion.json": (
        "6f526a69b82e0d53ef733e79f44e6422bd599af51d2f31896b853ded069c3396", 93, 85, {}),
    "T1098-aws_iam_failure_group_deletion/aws_iam_failure_group_deletion.json": (
        "3dae36751402bc19f86cecfac3f622ac41ef6d4c4ede6f334e3b7fbcde35a991", 50, 50,
        {"NoSuchEntityException": 44, "DeleteConflictException": 5, "AccessDenied": 1}),
}


@pytest.mark.parametrize("relative", sorted(REAL_IAM_DELETIONS))
async def test_cloudtrail_adapter_reads_real_iam_deletions(db, new_source, relative):
    """Real IAM DeletePolicy and DeleteGroup calls (Splunk attack_data, T1098, Apache 2.0).
    Neither call grants, revokes or signs in, so every record is `other`, its outcome
    comes from `errorCode`, and no rule fires. Two of the files repeat records
    verbatim; ingest stores each once."""
    sha256, count, distinct, failures = REAL_IAM_DELETIONS[relative]
    records = _real_sample(relative, sha256)
    events = [_normalize(r, CLOUDTRAIL) for r in records]
    assert len(events) == count and all(e.actor is not None for e in events)
    assert {e.action for e in events} == {"other"}
    assert Counter(e.attributes["failure_reason"] for e in events if e.outcome == "failure") == failures
    assert sum(e.outcome == "success" for e in events) == count - sum(failures.values())
    assert set(_alerts(events).values()) == {0}

    report = await _ingest(db, new_source(), records, source_type=CLOUDTRAIL)
    stored = (report.inserted, report.duplicates, report.conflicts, report.rejected)
    assert stored == (distinct, count - distinct, 0, 0)


# --------------------------------------------------------------------------
# 6b. Entra ID sign-in adapter
# --------------------------------------------------------------------------

ENTRA = "entra.signin"


def signin(error_code: int = 0, **properties) -> dict:
    """A hand-written sign-in in the Azure Monitor export shape (synthetic values)."""
    return {"time": "2026-09-03T08:00:00.1234567Z", "category": "SignInLogs", "properties": {
        "id": "5e0c7d2a-1111-4222-8333-444455556666", "createdDateTime": "2026-09-03T08:00:00.1234567+00:00",
        "userPrincipalName": "lab-user@example.test", "userId": "0d6f3c8e-aaaa-4bbb-8ccc-ddddeeeeffff",
        "appId": "00000000-0000-4000-8000-00000000a001", "ipAddress": "203.0.113.9",
        "status": {"errorCode": error_code}, "authenticationRequirement": "multiFactorAuthentication",
        **properties}}


def test_entra_signin_maps_outcome_actor_and_mfa():
    event = _normalize(signin(), ENTRA)
    assert (event.action, event.source_action, event.outcome) == ("auth.login", "SignInLogs", "success")
    assert (event.actor.type, event.actor.id) == ("user", "lab-user@example.test")
    assert (event.target.type, event.src_ip) == ("application", "203.0.113.9")
    assert event.occurred_at == datetime(2026, 9, 3, 8, 0, 0, 123456, tzinfo=timezone.utc)
    assert event.attributes == {"mfa_used": True}
    single = signin(authenticationRequirement="singleFactorAuthentication")
    assert _normalize(single, ENTRA).attributes == {"mfa_used": False}
    # A requirement is what the sign-in needed; on a failure nothing shows it was met.
    assert _normalize(signin(50126), ENTRA).attributes == {"failure_reason": "50126"}
    for unknown in (None, "somethingNew", ["multiFactorAuthentication"]):
        assert _normalize(signin(authenticationRequirement=unknown), ENTRA).attributes == {}
    assert _normalize(signin(userPrincipalName=""), ENTRA).actor.id == "0d6f3c8e-aaaa-4bbb-8ccc-ddddeeeeffff"
    assert _normalize(signin(userPrincipalName=None, userId=""), ENTRA).actor is None
    assert _normalize(signin(ipAddress="not-an-ip"), ENTRA).src_ip is None


@pytest.mark.parametrize("broken", [
    {**signin(), "category": "AuditLogs"},
    {**signin(), "properties": "not an object"},
    signin(status=None),
    signin(status={"errorCode": "0"}),
    signin(status={"errorCode": True}),
    signin(id=None),
    signin(createdDateTime="2026-09-03T08:00:00"),       # no timezone
])
def test_entra_records_the_adapter_cannot_read_are_refused(broken):
    from app.events.contract import ContractError

    with pytest.raises(ContractError):
        _normalize(broken, ENTRA)


async def test_entra_adapter_reads_real_failed_password_sign_ins(db, new_source):
    """Its only real data so far: 30 failed password sign-ins of one user within 11
    seconds (Splunk attack_data, T1110.001, Apache 2.0). The file holds no successful
    sign-in, so no rule can fire: this tests the adapter, not a rule."""
    records = _real_sample(
        "T1110.001-azure_ad_high_number_of_failed_authentications_for_user/azuread.log",
        "1d5c729dc5e864ca2894cceae832ff4119f17a709e1ec33838b3f60baab3af87")
    events = [_normalize(r, ENTRA) for r in records]
    assert len(events) == 30 and len({e.actor.id for e in events}) == 1
    assert {(e.action, e.outcome) for e in events} == {("auth.login", "failure")}
    assert {e.attributes["failure_reason"] for e in events} == {"50126"}
    assert all(e.src_ip and e.target is not None for e in events)
    assert set(_alerts(events).values()) == {0}

    report = await _ingest(db, new_source(), records, source_type=ENTRA)
    assert (report.inserted, report.duplicates, report.rejected) == (30, 0, 0)


# --------------------------------------------------------------------------
# 6c. LANL authentication adapter (mapping registered in research/M2_PREREGISTRATION.md §5)
# --------------------------------------------------------------------------

LANL = "lanl.auth"
LANL_LINE = "151036,U748@DOM1,U748@DOM1,C17693,C305,NTLM,Network,LogOn,Success"


def test_lanl_auth_maps_a_line_as_registered():
    event = _normalize({"line": 7, "text": LANL_LINE}, LANL)
    assert (event.source_event_id, event.action, event.source_action, event.outcome) == (
        "7", "auth.login", "LogOn", "success")
    assert event.occurred_at == datetime(1970, 1, 2, 17, 57, 16, tzinfo=timezone.utc)   # 151,036 s after the origin
    assert (event.actor.type, event.actor.id, event.target.type, event.target.id) == ("user", "U748@DOM1", "resource", "C305")
    assert (event.src_ip, event.attributes) == (None, {})
    logoff = _normalize({"line": 8, "text": "1,C101$@DOM1,C101$@DOM1,C988,C988,?,Network,LogOff,Fail"}, LANL)
    assert (logoff.action, logoff.source_action, logoff.outcome, logoff.actor.type) == ("other", "LogOff", "failure", "unknown")
    assert _normalize({"line": 9, "text": "1,U1@DOM1,U1@DOM1,C1,C2,?,?,TGT,?"}, LANL).outcome == "unknown"


@pytest.mark.parametrize("broken", [
    {"text": LANL_LINE},                                          # no line number
    {"line": 0, "text": LANL_LINE},
    {"line": True, "text": LANL_LINE},
    {"line": 1, "text": "151036,U748@DOM1,C17693,C305,LogOn,Success"},
    {"line": 1, "text": "x" + LANL_LINE},
    {"line": 1, "text": "151036,,U748@DOM1,C17693,C305,NTLM,Network,LogOn,Success"},   # no source user
])
def test_lanl_lines_the_adapter_cannot_read_are_refused(broken):
    from app.events.contract import ContractError

    with pytest.raises(ContractError):
        _normalize(broken, LANL)


# --------------------------------------------------------------------------
# 7. API: authorization, limits, traceability
# --------------------------------------------------------------------------

async def _post_ingest(client, role: str, source_id: str, records, source_type: str = NATIVE):
    return await client.post(
        f"{API}/security-events/ingest",
        json={"source_type": source_type, "source_id": source_id, "records": records},
        headers=await _as(client, role),
    )


@pytest.mark.parametrize("role,expected", [
    ("admin", 200), ("security", 200), ("compliance", 200), ("auditor", 403), ("employee", 403),
])
async def test_only_internal_staff_can_read_events(unauth_client, role, expected):
    headers = await _as(unauth_client, role)
    for path in ("/security-events", "/security-events/batches"):
        assert (await unauth_client.get(f"{API}{path}", headers=headers)).status_code == expected, path


@pytest.mark.parametrize("role", ["security", "compliance", "auditor", "employee"])
async def test_only_an_admin_can_ingest_events(unauth_client, new_source, role):
    source_id = new_source()
    response = await _post_ingest(unauth_client, role, source_id, [rec(1)])
    assert response.status_code == 403
    listing = await unauth_client.get(
        f"{API}/security-events?source_id={source_id}", headers=await _as(unauth_client, "admin")
    )
    assert listing.json()["data"] == []


async def test_event_can_be_traced_from_the_api_back_to_its_source_record(unauth_client, new_source):
    from app.events.contract import canonical_json, sha256_hex

    source_id, admin = new_source(), await _as(unauth_client, "admin")
    submitted = rec(1, attributes={"mfa_used": False, "privileged": True, "approval_ref": "CHG-1041"})
    report = (await _post_ingest(unauth_client, "admin", source_id, [submitted, rec(2, action="nope")])).json()["data"]
    assert (report["inserted"], report["rejected"]) == (1, 1)

    listing = (await unauth_client.get(f"{API}/security-events?source_id={source_id}", headers=admin)).json()
    assert listing["meta"]["count"] == 1 and listing["meta"]["next_cursor"] is None
    summary = listing["data"][0]
    assert "raw" not in summary                                           # lists stay small

    detail = (await unauth_client.get(f"{API}/security-events/{summary['event_id']}", headers=admin)).json()["data"]
    assert detail["raw"] == submitted                                     # the source record, as received
    assert sha256_hex(canonical_json(detail["raw"])) == detail["raw_sha256"]   # and verifiably so
    assert detail["occurred_at"] == "2026-09-01T08:01:00Z"
    assert (detail["source_type"], detail["source_id"], detail["source_event_id"]) == (NATIVE, source_id, "e-0001")
    assert detail["normalizer"] == "sentinel.native@1" and detail["ingest_batch_id"] == report["batch_id"]

    batch = (await unauth_client.get(f"{API}/security-events/batches/{report['batch_id']}", headers=admin)).json()["data"]
    assert (batch["received"], batch["inserted"], batch["rejected"], batch["origin"]) == (2, 1, 1, "api")
    assert batch["submitted_by"] == "admin@sentinel.ai"
    assert [(r["index"], r["reason"]) for r in batch["rejects"]] == [(1, "invalid_record")]


async def test_list_filters_and_cursor_work_over_http(unauth_client, new_source):
    source_id, admin = new_source(), await _as(unauth_client, "admin")
    records = [rec(n, outcome="failure" if n % 2 else "success") for n in range(1, 8)]
    await _post_ingest(unauth_client, "admin", source_id, records)
    base = f"{API}/security-events?source_id={source_id}"

    failures = (await unauth_client.get(f"{base}&outcome=failure", headers=admin)).json()["data"]
    assert {e["outcome"] for e in failures} == {"failure"} and len(failures) == 4

    window = (await unauth_client.get(
        f"{base}&occurred_from=2026-09-01T08:03:00Z&occurred_to=2026-09-01T08:05:00Z&order=asc", headers=admin
    )).json()["data"]
    assert [e["source_event_id"] for e in window] == ["e-0003", "e-0004", "e-0005"]

    seen, cursor = [], ""
    while cursor is not None:
        page = (await unauth_client.get(f"{base}&limit=3&order=asc" + (f"&cursor={cursor}" if cursor else ""), headers=admin)).json()
        seen += [e["source_event_id"] for e in page["data"]]
        cursor = page["meta"]["next_cursor"]
    assert seen == [f"e-{n:04d}" for n in range(1, 8)]


@pytest.mark.parametrize("query", [
    "cursor=garbage", "limit=0", "limit=100000", "order=sideways",
    "occurred_from=2026-09-01T08:00:00",          # no offset: ambiguous, refused
    "occurred_from=yesterday",
])
async def test_bad_list_parameters_are_refused(unauth_client, query):
    response = await unauth_client.get(f"{API}/security-events?{query}", headers=await _as(unauth_client, "admin"))
    assert response.status_code == 422, query


async def test_ingest_request_limits(unauth_client, new_source):
    from app.events.contract import MAX_BATCH_RECORDS, MAX_BODY_BYTES

    admin = await _as(unauth_client, "admin")
    too_many = await _post_ingest(unauth_client, "admin", new_source(), [rec(n) for n in range(MAX_BATCH_RECORDS + 1)])
    assert too_many.status_code == 422

    huge = json.dumps({"source_type": NATIVE, "source_id": new_source(),
                       "records": [rec(1, source_action="x" * (MAX_BODY_BYTES + 1))]})
    too_big = await unauth_client.post(f"{API}/security-events/ingest", content=huge,
                                       headers={**admin, "Content-Type": "application/json"})
    assert too_big.status_code == 413

    for bad in ('{"source_type": ', json.dumps({"source_type": "made.up", "source_id": "x", "records": [rec(1)]}),
                json.dumps({"source_type": NATIVE, "source_id": "bad id!", "records": [rec(1)]}),
                json.dumps({"source_type": NATIVE, "source_id": "x", "records": []}),
                json.dumps({"source_type": NATIVE, "source_id": "x", "records": [rec(1)], "extra": 1})):
        response = await unauth_client.post(f"{API}/security-events/ingest", content=bad,
                                            headers={**admin, "Content-Type": "application/json"})
        assert response.status_code == 422, bad[:60]


async def test_unknown_event_and_batch_ids_are_404(unauth_client):
    admin = await _as(unauth_client, "admin")
    assert (await unauth_client.get(f"{API}/security-events/{'0' * 64}", headers=admin)).status_code == 404
    assert (await unauth_client.get(f"{API}/security-events/batches/{uuid.uuid4()}", headers=admin)).status_code == 404


async def test_events_are_not_reachable_through_the_ai_query_engine():
    """The AI engine only accepts tables on its own allow-list; raw security
    events must not become queryable through it by accident."""
    from app.api.v1.resources import readable_tables
    from app.models.enums import UserRole
    from app.services.grc_engine.schema_graph import TABLES

    assert "security_events" not in TABLES
    assert "security_events" not in readable_tables(UserRole.ADMIN)
