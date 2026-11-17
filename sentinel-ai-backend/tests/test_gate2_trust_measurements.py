"""
Gate 2 — trust score history is produced by explicit measurements, never as a
side effect of someone looking at the score.

Before this, every GET /intelligence/trust wrote a snapshot row, so the
"history" recorded page views, not changes.
"""
from __future__ import annotations

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import TrustScoreSnapshot
from tests.test_gate1_security import API, _as

MEASUREMENTS = f"{API}/intelligence/trust/measurements"


def _count(sync_engine) -> int:
    with Session(sync_engine) as session:
        return session.execute(select(func.count()).select_from(TrustScoreSnapshot)).scalar_one()


def _latest(sync_engine) -> TrustScoreSnapshot:
    with Session(sync_engine) as session:
        return session.execute(
            select(TrustScoreSnapshot).order_by(TrustScoreSnapshot.computed_at.desc(), TrustScoreSnapshot.id.desc()).limit(1)
        ).scalar_one()


@pytest.fixture
def stale_snapshot(sync_engine):
    """A latest snapshot whose values differ from the live score, so the next
    measurement is a real change. Removed afterwards."""
    from datetime import datetime, timezone

    with Session(sync_engine) as session:
        row = TrustScoreSnapshot(trust_score=-1.0, audit_readiness=-1.0, components={},
                                 computed_at=datetime.now(timezone.utc))
        session.add(row)
        session.commit()
        row_id = row.id
    yield
    with Session(sync_engine) as session:
        session.execute(delete(TrustScoreSnapshot).where(TrustScoreSnapshot.id == row_id))
        session.commit()


async def test_reading_the_trust_score_never_writes_history(unauth_client, sync_engine, stale_snapshot):
    # `stale_snapshot` matters: the latest row differs from the live score, so
    # if a read ever recorded a measurement again, de-duplication could not
    # hide it and a new row would appear here.
    admin = await _as(unauth_client, "admin")
    before = _count(sync_engine)
    for path in ("/intelligence/trust", "/intelligence/trust", "/dashboard", "/intelligence/orchestrator/summary"):
        assert (await unauth_client.get(f"{API}{path}", headers=admin)).status_code == 200
    assert _count(sync_engine) == before


async def test_measurement_is_recorded_once_per_change_and_says_who_and_why(unauth_client, sync_engine, stale_snapshot):
    compliance = await _as(unauth_client, "compliance")
    before = _count(sync_engine)

    first = (await unauth_client.post(MEASUREMENTS, headers=compliance)).json()["data"]
    assert first["recorded"] is True
    assert _count(sync_engine) == before + 1
    row = _latest(sync_engine)
    assert (row.trigger, row.recorded_by) == ("manual", "compliance@sentinel.ai")
    assert row.trust_score == first["measurement"]["trust_score"] >= 0

    # Nothing changed since: asking again must not add a row.
    again = (await unauth_client.post(MEASUREMENTS, headers=compliance)).json()["data"]
    assert again["recorded"] is False and "unchanged" in again["reason"]
    assert again["measurement"]["id"] == first["measurement"]["id"]
    assert _count(sync_engine) == before + 1


async def test_score_change_compares_against_the_latest_measurement(unauth_client):
    admin = await _as(unauth_client, "admin")
    await unauth_client.post(MEASUREMENTS, headers=admin)          # history now reflects the live score

    for _ in range(2):                                             # and reading it twice says the same thing
        data = (await unauth_client.get(f"{API}/intelligence/trust", headers=admin)).json()["data"]
        change = data["score_change"]
        assert change["status"] == "compared against the most recent recorded measurement"
        assert change["delta"] == 0.0 and change["prior_score"] == data["trust_score"]


@pytest.mark.parametrize("role,expected", [
    ("admin", 200), ("compliance", 200), ("security", 403), ("auditor", 403), ("employee", 403),
])
async def test_only_admin_and_compliance_can_record_a_measurement(unauth_client, sync_engine, role, expected):
    before = _count(sync_engine)
    response = await unauth_client.post(MEASUREMENTS, headers=await _as(unauth_client, role))
    assert response.status_code == expected
    if expected == 403:
        assert _count(sync_engine) == before


async def test_measurement_history_is_readable_and_newest_first(unauth_client, stale_snapshot):
    admin = await _as(unauth_client, "admin")
    await unauth_client.post(MEASUREMENTS, headers=admin)
    history = (await unauth_client.get(f"{MEASUREMENTS}?limit=5", headers=await _as(unauth_client, "auditor"))).json()["data"]

    assert 1 <= len(history) <= 5
    assert history[0]["trigger"] == "manual" and history[0]["recorded_by"] == "admin@sentinel.ai"
    assert [m["computed_at"] for m in history] == sorted((m["computed_at"] for m in history), reverse=True)


async def test_rows_written_by_the_old_read_path_are_labelled_as_such(sync_engine):
    """Existing history was produced by page views. It is kept, but marked."""
    from sqlalchemy import inspect

    columns = {c["name"]: c for c in inspect(sync_engine).get_columns("trust_score_snapshots")}
    assert {"trigger", "recorded_by"} <= set(columns)
    assert "legacy_on_read" in str(columns["trigger"]["default"])
