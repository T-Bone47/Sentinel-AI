"""
Gate 3 — detection rules, the engine that runs them, and their evaluation.

Expectations come from three places, none of them the code under test:
  * the rule contracts in research/rules/ (hashed in docs/PROGRESS.md before
    any rule code existed) and their test vectors;
  * hand-built events written out in this file;
  * the frozen fixtures and their ground-truth labels.
"""
from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import itertools
import json
import os
import random
import subprocess
import sys
import tomllib
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from tests.test_gate1_security import API, _as

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
RULES_DIR = REPO_ROOT / "research" / "rules"
FIXTURES = REPO_ROOT / "research" / "fixtures"
SCRIPTS = REPO_ROOT / "research" / "scripts"
NATIVE = "sentinel.native"
RULE_IDS = ["IA-001", "IA-002", "IA-003", "IA-004", "IA-005"]
T0 = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
_SEQ = itertools.count(1)


def _contracts() -> dict[str, dict]:
    return {p.stem: tomllib.loads(p.read_text(encoding="utf-8")) for p in sorted(RULES_DIR.glob("IA-*.toml"))}


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module          # @dataclass looks its module up here
    spec.loader.exec_module(module)
    return module


def _labels(fixture: str) -> dict[str, dict]:
    lines = (FIXTURES / fixture / "labels.jsonl").read_text(encoding="utf-8").splitlines()
    return {label["source_event_id"]: label for label in map(json.loads, lines)}


# --------------------------------------------------------------------------
# 1. The rules, on hand-built events
# --------------------------------------------------------------------------

def ev(minutes, action, outcome="success", *, actor=None, target=None, seconds=0, **attributes):
    """One event. Ids increase in creation order, so a test controls how
    simultaneous events happen to sort."""
    from app.detections.rules import EventView

    return EventView(event_id=f"{next(_SEQ):064x}", occurred_at=T0 + timedelta(minutes=minutes, seconds=seconds),
                     action=action, outcome=outcome, actor_id=actor, target_id=target, attributes=attributes)


def run(rule_id, events):
    from app.detections.rules import evaluate

    return evaluate(events)[rule_id]


def triggers(rule_id, events) -> list[str]:
    return [f.trigger_id for f in run(rule_id, events).findings]


class TestIA001PrivilegedGrantWithoutApproval:
    def test_fires_on_a_privileged_grant_with_no_approval(self):
        grant = ev(0, "privilege.grant", actor="lab-admin", target="lab-user", privileged=True, role="db-admin")
        result = run("IA-001", [grant])
        assert [(f.trigger_id, f.context_ids) for f in result.findings] == [(grant.event_id, ())]
        assert "lab-admin" in result.findings[0].summary and "db-admin" in result.findings[0].summary

    @pytest.mark.parametrize("outcome,attributes", [
        ("success", {"privileged": True, "approval_ref": "CHG-1"}),
        ("success", {"privileged": False}),
        ("failure", {"privileged": True}),
    ])
    def test_silent_when_approved_unprivileged_or_failed(self, outcome, attributes):
        assert triggers("IA-001", [ev(0, "privilege.grant", outcome, actor="a", target="b", **attributes)]) == []

    def test_a_grant_without_the_privileged_flag_is_not_evaluable(self):
        result = run("IA-001", [ev(0, "privilege.grant", actor="a", target="b", role="db-admin")])
        assert result.findings == [] and result.not_evaluable == 1


class TestIA002PrivilegedSignInWithoutMFA:
    def test_fires_on_a_privileged_sign_in_without_mfa(self):
        login = ev(0, "auth.login", actor="lab-admin", privileged=True, mfa_used=False)
        assert triggers("IA-002", [login]) == [login.event_id]

    @pytest.mark.parametrize("outcome,attributes", [
        ("success", {"privileged": True, "mfa_used": True}),
        ("success", {"privileged": False, "mfa_used": False}),
        ("failure", {"privileged": True, "mfa_used": False}),
    ])
    def test_silent_with_mfa_unprivileged_or_failed(self, outcome, attributes):
        assert triggers("IA-002", [ev(0, "auth.login", outcome, actor="a", **attributes)]) == []

    @pytest.mark.parametrize("attributes", [{"privileged": True}, {"mfa_used": False}, {}])
    def test_missing_attributes_are_not_evaluable(self, attributes):
        result = run("IA-002", [ev(0, "auth.login", actor="a", **attributes)])
        assert result.findings == [] and result.not_evaluable == 1

    def test_an_unprivileged_sign_in_is_simply_out_of_scope(self):
        assert run("IA-002", [ev(0, "auth.login", actor="a", privileged=False)]).not_evaluable == 0


def burst(actor, success_minute, seconds_before):
    """Failed sign-ins the given numbers of seconds before a success."""
    fails = [ev(success_minute, "auth.login", "failure", actor=actor, seconds=-s) for s in seconds_before]
    return fails, ev(success_minute, "auth.login", actor=actor)


class TestIA003FailedSignInsThenSuccess:
    FIVE = [1800, 1200, 600, 300, 60]     # the first exactly 30 minutes before the success
    CLOSE = [300, 240, 180, 120, 60]      # all within the last five minutes

    def test_fires_after_five_failures_in_thirty_minutes(self):
        fails, win = burst("lab-a", 60, self.FIVE)
        result = run("IA-003", fails + [win])
        assert [f.trigger_id for f in result.findings] == [win.event_id]
        assert result.findings[0].context_ids == tuple(f.event_id for f in fails)   # oldest first

    def test_four_failures_are_not_enough(self):
        fails, win = burst("lab-a", 60, self.FIVE[1:])
        assert triggers("IA-003", fails + [win]) == []

    def test_a_failure_thirty_minutes_and_one_second_before_is_outside_the_window(self):
        fails, win = burst("lab-a", 60, [1801, 1200, 600, 300, 60])
        assert triggers("IA-003", fails + [win]) == []

    def test_a_failure_at_the_same_instant_as_the_success_does_not_count(self):
        fails, win = burst("lab-a", 60, [1200, 600, 300, 60, 0])
        assert triggers("IA-003", fails + [win]) == []

    def test_failures_by_another_account_do_not_count(self):
        fails, _ = burst("lab-a", 60, self.FIVE)
        assert triggers("IA-003", fails + [ev(60, "auth.login", actor="lab-b")]) == []

    def test_an_approved_reset_between_the_failures_and_the_success_explains_them(self):
        fails, win = burst("lab-a", 60, self.FIVE)
        reset = ev(60, "credential.change", actor="lab-helpdesk", target="lab-a", seconds=-30, approval_ref="INC-1")
        assert triggers("IA-003", fails + [reset, win]) == []

    @pytest.mark.parametrize("reset", [
        {"seconds": -30},                                  # no approval reference
        {"seconds": -3000, "approval_ref": "INC-1"},       # before the failures
        {"seconds": 0, "approval_ref": "INC-1"},           # at the same instant as the success: not between
    ])
    def test_resets_that_do_not_explain_the_failures(self, reset):
        fails, win = burst("lab-a", 60, self.FIVE)
        change = ev(60, "credential.change", actor="lab-helpdesk", target="lab-a", **reset)
        assert triggers("IA-003", fails + [change, win]) == [win.event_id]

    def test_only_the_first_success_after_a_burst_alerts(self):
        fails, first = burst("lab-a", 60, self.CLOSE)
        second = ev(61, "auth.login", actor="lab-a")      # its window still holds all five failures
        assert triggers("IA-003", fails + [first, second]) == [first.event_id]

    def test_a_sign_in_without_an_actor_is_not_evaluable(self):
        assert run("IA-003", [ev(0, "auth.login")]).not_evaluable == 1


class TestIA004ActivityByDisabledAccount:
    def test_fires_on_each_successful_action_after_the_disable(self):
        disable = ev(0, "account.disable", actor="lab-hr", target="lab-x")
        login = ev(60, "auth.login", actor="lab-x")
        read = ev(61, "resource.read", actor="lab-x", sensitivity="confidential")
        result = run("IA-004", [disable, login, read])
        assert [f.trigger_id for f in result.findings] == [login.event_id, read.event_id]
        assert all(f.context_ids == (disable.event_id,) for f in result.findings)

    def test_silent_once_the_account_is_enabled_again(self):
        events = [ev(0, "account.disable", target="lab-x"), ev(30, "account.enable", target="lab-x"),
                  ev(60, "auth.login", actor="lab-x")]
        assert triggers("IA-004", events) == []

    def test_failed_actions_do_not_count(self):
        events = [ev(0, "account.disable", target="lab-x"), ev(60, "auth.login", "failure", actor="lab-x")]
        assert triggers("IA-004", events) == []

    def test_activity_before_the_disable_does_not_count(self):
        events = [ev(0, "auth.login", actor="lab-x"), ev(60, "account.disable", target="lab-x")]
        assert triggers("IA-004", events) == []

    @pytest.mark.parametrize("login_first", [True, False])
    def test_an_action_at_the_same_instant_as_the_disable_is_not_after_it(self, login_first):
        login = lambda: ev(0, "auth.login", actor="lab-x")  # noqa: E731
        disable = lambda: ev(0, "account.disable", target="lab-x")  # noqa: E731
        events = [login(), disable()] if login_first else [disable(), login()]
        assert triggers("IA-004", events) == []

    @pytest.mark.parametrize("enable_sorts_first", [True, False])
    def test_an_enable_at_the_same_instant_as_an_action_does_not_precede_it(self, enable_sorts_first):
        disable = ev(0, "account.disable", target="lab-x")
        if enable_sorts_first:
            enable, login = ev(60, "account.enable", target="lab-x"), ev(60, "auth.login", actor="lab-x")
        else:
            login, enable = ev(60, "auth.login", actor="lab-x"), ev(60, "account.enable", target="lab-x")
        assert triggers("IA-004", [disable, enable, login]) == [login.event_id]

    def test_a_disable_without_a_target_is_not_evaluable(self):
        assert run("IA-004", [ev(0, "account.disable", actor="lab-hr")]).not_evaluable == 1


class TestIA005UnapprovedGrantThenSensitiveAccess:
    @staticmethod
    def grant(minutes=0, grantee="lab-p", **attributes):
        return ev(minutes, "privilege.grant", actor="lab-admin", target=grantee, role="finance-reader", **attributes)

    @staticmethod
    def access(minutes, who="lab-p", seconds=0, action="resource.export", **attributes):
        return ev(minutes, action, actor=who, target="lab-res-x", seconds=seconds, **attributes)

    def test_fires_on_sensitive_access_within_an_hour_of_an_unapproved_grant(self):
        grant, export = self.grant(), self.access(10, sensitivity="restricted")
        result = run("IA-005", [grant, export])
        assert [(f.trigger_id, f.context_ids) for f in result.findings] == [(export.event_id, (grant.event_id,))]

    def test_a_confidential_read_counts_too(self):
        read = self.access(10, action="resource.read", sensitivity="confidential")
        assert triggers("IA-005", [self.grant(), read]) == [read.event_id]

    def test_exactly_sixty_minutes_is_inside_the_window(self):
        export = self.access(60, sensitivity="restricted")
        assert triggers("IA-005", [self.grant(), export]) == [export.event_id]

    @pytest.mark.parametrize("case", ["60m01s", "same_instant", "approved", "internal", "other_principal"])
    def test_silent(self, case):
        grant = self.grant(approval_ref="CHG-9") if case == "approved" else self.grant()
        export = {
            "60m01s": lambda: self.access(60, seconds=1, sensitivity="restricted"),
            "same_instant": lambda: self.access(0, sensitivity="restricted"),
            "approved": lambda: self.access(10, sensitivity="restricted"),
            "internal": lambda: self.access(10, sensitivity="internal"),
            "other_principal": lambda: self.access(10, who="lab-q", sensitivity="restricted"),
        }[case]()
        assert triggers("IA-005", [grant, export]) == []

    def test_an_access_without_a_classification_is_not_evaluable(self):
        result = run("IA-005", [self.grant(), self.access(10)])
        assert result.findings == [] and result.not_evaluable == 1

    def test_two_unapproved_grants_give_one_alert_citing_both(self):
        first, second = self.grant(0), self.grant(5)
        export = self.access(10, sensitivity="restricted")
        result = run("IA-005", [first, second, export])
        assert [(f.trigger_id, f.context_ids) for f in result.findings] == [
            (export.event_id, (first.event_id, second.event_id))
        ]


def test_findings_do_not_depend_on_the_order_events_are_given_in():
    from app.detections.rules import evaluate

    events = [
        ev(0, "privilege.grant", actor="lab-admin", target="u1", privileged=True),
        ev(1, "auth.login", actor="u2", privileged=True, mfa_used=False),
        *burst("u3", 30, [300, 240, 180, 120, 60])[0], burst("u3", 30, [])[1],
        ev(40, "account.disable", target="u4"), ev(50, "auth.login", actor="u4"),
        ev(60, "privilege.grant", actor="lab-admin", target="u5"), ev(70, "resource.read", actor="u5", sensitivity="restricted"),
    ]
    snapshot = lambda result: {r: [(f.trigger_id, f.context_ids) for f in v.findings] for r, v in result.items()}  # noqa: E731
    expected = snapshot(evaluate(events))
    assert all(expected[r] for r in RULE_IDS), "every rule must fire, or this test proves nothing"
    for seed in range(10):
        shuffled = events[:]
        random.Random(seed).shuffle(shuffled)
        assert snapshot(evaluate(shuffled)) == expected


# --------------------------------------------------------------------------
# 2. Contracts: written down before the code, and still in agreement with it
# --------------------------------------------------------------------------

def test_every_rule_has_a_contract_that_agrees_with_the_code():
    from app.detections.rules import CONFIDENCES, RULES, SEVERITIES

    contracts = _contracts()
    assert sorted(contracts) == sorted(RULES) == RULE_IDS
    for rule_id, rule in RULES.items():
        c = contracts[rule_id]
        assert (c["id"], c["version"], c["title"], c["severity"], c["confidence"]) == (
            rule.id, rule.version, rule.title, rule.severity, rule.confidence), rule_id
        assert c["parameters"] == dict(rule.parameters), rule_id
        assert c["attack"]["techniques"] == list(rule.attack), rule_id
        assert (c["attack"]["status"] == "unmapped") == (not rule.attack), rule_id
        assert rule.severity in SEVERITIES and rule.confidence in CONFIDENCES


def test_contracts_only_name_fields_the_event_contract_has():
    from app.events.contract import ATTRIBUTE_TYPES

    allowed = {"source_event_id", "occurred_at", "action", "source_action", "outcome", "src_ip",
               "actor.id", "actor.type", "target.id", "target.type"} | {f"attributes.{k}" for k in ATTRIBUTE_TYPES}
    for rule_id, contract in _contracts().items():
        assert set(contract["logic"]["required_fields"]) <= allowed, rule_id


def test_test_vectors_name_real_scenarios_of_the_rules_own_family():
    manifests = {name: json.loads((FIXTURES / name / "MANIFEST.json").read_text(encoding="utf-8"))
                 for name in ("identity-access-v1", "identity-access-boundary-v1")}
    total = 0
    for rule_id, contract in _contracts().items():
        for vector in contract["test_vectors"]:
            scenarios = {s["id"]: s for s in manifests[vector["fixture"]]["scenarios"]}
            assert vector["scenario"] in scenarios, (rule_id, vector)
            assert scenarios[vector["scenario"]]["family"] == contract["fixture_family"], (rule_id, vector)
            total += 1
    assert total == 33


def test_boundary_fixture_generator_reproduces_the_frozen_files():
    module = _load_module(SCRIPTS / "build_boundary_fixture.py")
    folder = FIXTURES / "identity-access-boundary-v1"
    built = module.build()
    assert sorted(built) == sorted(p.name for p in folder.iterdir() if p.name != "README.md")
    for name, content in built.items():
        assert content == (folder / name).read_bytes(), name
    manifest = json.loads(built["MANIFEST.json"])
    for name, info in manifest["files"].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == info["sha256"], name


def test_boundary_labels_cover_both_sources_and_never_enter_the_events():
    folder = FIXTURES / "identity-access-boundary-v1"
    events = [json.loads(line) for name in ("events.jsonl", "events-hr.jsonl")
              for line in (folder / name).read_text(encoding="utf-8").splitlines()]
    labels = _labels("identity-access-boundary-v1")
    assert {e["source_event_id"] for e in events} == set(labels)
    assert not any({"label", "scenario_id", "part"} & set(e) for e in events)


# --------------------------------------------------------------------------
# 3. The engine and the alert store
# --------------------------------------------------------------------------

@pytest.fixture
async def db():
    from app.database.session import AsyncSessionLocal, engine

    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def sources(sync_engine):
    """Factory for throwaway source ids. Afterwards removes their alerts, runs,
    events and ingestion records, in an order the foreign keys allow."""
    from app.models import (DetectionAlert, DetectionAlertEvent, DetectionRun, EventIngestBatch,
                            EventIngestReject, SecurityEvent)

    made: list[str] = []

    def make() -> str:
        made.append(f"t-{uuid.uuid4().hex[:16]}")
        return made[-1]

    yield make

    with Session(sync_engine) as session:
        for source_id in made:
            alert_ids = select(DetectionAlert.alert_id).where(DetectionAlert.source_id == source_id)
            session.execute(delete(DetectionAlertEvent).where(DetectionAlertEvent.alert_id.in_(alert_ids)))
            session.execute(delete(DetectionAlert).where(DetectionAlert.source_id == source_id))
            session.execute(delete(DetectionRun).where(DetectionRun.source_id == source_id))
            batch_ids = select(EventIngestBatch.id).where(EventIngestBatch.source_id == source_id)
            session.execute(delete(SecurityEvent).where(SecurityEvent.source_id == source_id))
            session.execute(delete(EventIngestReject).where(EventIngestReject.batch_id.in_(batch_ids)))
            session.execute(delete(EventIngestBatch).where(EventIngestBatch.source_id == source_id))
        session.commit()


def nrec(n, minutes, action, outcome="success", *, actor=None, target=None, target_type="principal", **attributes):
    """One source record in the native wire format."""
    record = {"source_event_id": f"g3-{n:04d}", "occurred_at": (T0 + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "action": action, "outcome": outcome}
    if actor:
        record["actor"] = {"type": "user", "id": actor}
    if target:
        record["target"] = {"type": target_type, "id": target}
    if attributes:
        record["attributes"] = attributes
    return record


def burst_records(actor="lab-x"):
    """Five failed sign-ins (minutes 50-54), then a success at 56: one IA-003 alert, nothing else."""
    quiet = {"privileged": False, "mfa_used": True}
    return [nrec(i, 50 + i, "auth.login", "failure", actor=actor, **quiet) for i in range(5)] + [
        nrec(5, 56, "auth.login", actor=actor, **quiet)]


async def _ingest(db, source_id, records):
    from app.events.store import ingest

    return await ingest(db, source_type=NATIVE, source_id=source_id, records=records, origin="test")


async def _detect(db, source_id, **kwargs):
    from app.detections.engine import run_detections

    return await run_detections(db, source_type=NATIVE, source_id=source_id, origin="test", **kwargs)


async def _alerts(db, source_id):
    from app.models import DetectionAlert

    stmt = (select(DetectionAlert).where(DetectionAlert.source_id == source_id)
            .order_by(DetectionAlert.trigger_at, DetectionAlert.alert_id).execution_options(populate_existing=True))
    return list((await db.execute(stmt)).scalars().all())


async def _runs(db, source_id):
    from app.models import DetectionRun

    stmt = select(DetectionRun).where(DetectionRun.source_id == source_id).execution_options(populate_existing=True)
    return list((await db.execute(stmt)).scalars().all())


async def test_a_run_stores_alerts_and_a_second_run_stores_nothing(db, sources):
    source_id = sources()
    await _ingest(db, source_id, burst_records())
    first = await _detect(db, source_id)
    assert (first.status, first.events_considered, first.alerts_created, first.alerts_existing) == ("completed", 6, 1, 0)

    second = await _detect(db, source_id)
    assert (second.alerts_created, second.alerts_existing, second.alerts_no_longer_raised) == (0, 1, 0)
    alerts = await _alerts(db, source_id)
    assert [(a.rule_id, a.rule_version, a.run_id) for a in alerts] == [("IA-003", 1, first.run_id)]
    assert [r.status for r in await _runs(db, source_id)] == ["completed", "completed"]


async def test_reingesting_the_same_events_and_rerunning_adds_no_alerts(db, sources):
    source_id = sources()
    await _ingest(db, source_id, burst_records())
    await _detect(db, source_id)
    replay = await _ingest(db, source_id, burst_records())
    rerun = await _detect(db, source_id)
    assert (replay.inserted, rerun.alerts_created, rerun.alerts_existing) == (0, 0, 1)


async def test_the_alert_id_is_derived_from_rule_version_and_trigger_event(db, sources):
    from app.events.contract import event_id_for

    source_id = sources()
    await _ingest(db, source_id, burst_records())
    await _detect(db, source_id)
    trigger = event_id_for(NATIVE, source_id, "g3-0005")
    expected = hashlib.sha256("\x1f".join(("IA-003", "1", trigger)).encode("utf-8")).hexdigest()
    assert [a.alert_id for a in await _alerts(db, source_id)] == [expected]


async def test_an_alert_cites_its_trigger_and_then_its_context_oldest_first(db, sources):
    from app.events.contract import event_id_for
    from app.models import DetectionAlertEvent

    source_id = sources()
    await _ingest(db, source_id, burst_records())
    await _detect(db, source_id)
    alert = (await _alerts(db, source_id))[0]
    links = (await db.execute(select(DetectionAlertEvent).where(DetectionAlertEvent.alert_id == alert.alert_id)
                              .order_by(DetectionAlertEvent.ordinal))).scalars().all()
    expected = [("trigger", "g3-0005")] + [("context", f"g3-{i:04d}") for i in range(5)]
    assert [(link.role, link.event_id) for link in links] == [
        (role, event_id_for(NATIVE, source_id, sid)) for role, sid in expected]


async def test_a_new_rule_version_adds_alerts_and_leaves_the_old_ones(db, sources):
    from app.detections.rules import RULES

    source_id = sources()
    await _ingest(db, source_id, burst_records())
    await _detect(db, source_id)
    report = await _detect(db, source_id, rules={"IA-003": dataclasses.replace(RULES["IA-003"], version=2)})
    assert report.alerts_created == 1
    assert sorted(a.rule_version for a in await _alerts(db, source_id)) == [1, 2]


async def test_an_alert_the_rule_would_no_longer_raise_is_kept_and_counted(db, sources):
    """A late, approved reset now explains the failures. The stored alert is
    not rewritten or deleted; the run says it would not raise it today."""
    source_id = sources()
    await _ingest(db, source_id, burst_records())
    await _detect(db, source_id)
    await _ingest(db, source_id, [nrec(99, 55, "credential.change", actor="lab-helpdesk", target="lab-x", approval_ref="INC-9")])
    report = await _detect(db, source_id)
    assert (report.alerts_created, report.alerts_existing, report.alerts_no_longer_raised) == (0, 0, 1)
    assert len(await _alerts(db, source_id)) == 1


async def test_a_run_over_too_many_events_is_refused_before_anything_is_written(db, sources, monkeypatch):
    from app.detections import engine

    monkeypatch.setattr(engine, "MAX_EVENTS_PER_RUN", 3)
    source_id = sources()
    await _ingest(db, source_id, burst_records())
    with pytest.raises(engine.RunTooLarge):
        await _detect(db, source_id)
    assert await _runs(db, source_id) == []


async def test_a_failing_rule_marks_the_run_failed_and_stores_no_alerts(db, sources):
    from app.detections.rules import RULES

    def broken(events):
        raise RuntimeError("rule bug")

    source_id = sources()
    await _ingest(db, source_id, burst_records())
    with pytest.raises(RuntimeError):
        await _detect(db, source_id, rules={"IA-003": dataclasses.replace(RULES["IA-003"], detect=broken)})
    assert [r.status for r in await _runs(db, source_id)] == ["failed"]
    assert await _alerts(db, source_id) == []


@pytest.mark.parametrize("bad", [{"source_type": "made.up"}, {"source_id": "bad id!"}])
async def test_an_unknown_source_type_or_malformed_source_id_is_refused(db, bad):
    from app.detections.engine import run_detections

    with pytest.raises(ValueError):
        await run_detections(db, **{"source_type": NATIVE, "source_id": "x", "origin": "test", **bad})


async def test_stored_alerts_and_their_links_cannot_be_modified(db, sources):
    from app.models import DetectionAlert, DetectionAlertEvent

    source_id = sources()
    await _ingest(db, source_id, burst_records())
    await _detect(db, source_id)
    alert_id = (await _alerts(db, source_id))[0].alert_id
    for statement in (update(DetectionAlert).where(DetectionAlert.alert_id == alert_id).values(severity="low"),
                      update(DetectionAlertEvent).where(DetectionAlertEvent.alert_id == alert_id).values(role="context")):
        with pytest.raises(DBAPIError):
            await db.execute(statement)
            await db.commit()
        await db.rollback()
    assert (await _alerts(db, source_id))[0].severity == "high"


async def _ingest_fixture(db, fixture: str, make_source) -> dict[str, str]:
    """Ingest each of a fixture's event files as its own throwaway source."""
    from app.events.store import read_jsonl

    folder = FIXTURES / fixture
    manifest = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))
    mapping = {}
    for name in manifest.get("sources", {"events.jsonl": fixture}):
        mapping[name] = make_source()
        await _ingest(db, mapping[name], read_jsonl(folder / name))
    return mapping


@pytest.mark.parametrize("fixture", ["identity-access-v1", "identity-access-boundary-v1"])
async def test_every_pre_registered_test_vector_holds(db, sources, fixture):
    from app.detections.engine import export_alerts

    mapping = await _ingest_fixture(db, fixture, sources)
    for source_id in mapping.values():
        await _detect(db, source_id)
    labels = _labels(fixture)
    observed: Counter = Counter()
    for source_id in mapping.values():
        for alert in await export_alerts(db, source_id=source_id):
            trigger = [e for e in alert["events"] if e["role"] == "trigger"]
            assert len(trigger) == 1
            observed[(alert["rule_id"], labels[trigger[0]["source_event_id"]]["scenario_id"])] += 1

    mismatches = [
        f"{rule_id} {v['scenario']}: expected {v['expected_alerts']}, got {observed[(rule_id, v['scenario'])]}"
        for rule_id, contract in _contracts().items()
        for v in contract["test_vectors"]
        if v["fixture"] == fixture and observed[(rule_id, v["scenario"])] != v["expected_alerts"]
    ]
    assert mismatches == []


async def test_main_fixture_alerts_cite_exactly_the_labelled_triggers_and_replay_cleanly(db, sources):
    from app.detections.engine import export_alerts
    from app.events.store import read_jsonl

    source_id = (await _ingest_fixture(db, "identity-access-v1", sources))["events.jsonl"]
    report = await _detect(db, source_id)
    assert report.alerts_created == 7
    assert report.not_evaluable == {rule_id: 0 for rule_id in RULE_IDS}

    alerts = await export_alerts(db, source_id=source_id)
    assert Counter(a["rule_id"] for a in alerts) == {"IA-001": 2, "IA-002": 1, "IA-003": 1, "IA-004": 2, "IA-005": 1}
    cited = sorted(e["source_event_id"] for a in alerts for e in a["events"] if e["role"] == "trigger")
    labels = _labels("identity-access-v1")
    assert cited == sorted(sid for sid, label in labels.items() if label["part"] == "trigger")

    await _ingest(db, source_id, read_jsonl(FIXTURES / "identity-access-v1" / "events.jsonl"))
    rerun = await _detect(db, source_id)
    assert (rerun.alerts_created, rerun.alerts_existing, rerun.alerts_no_longer_raised) == (0, 7, 0)


async def test_boundary_fixture_alerts_and_counts_what_it_cannot_judge(db, sources):
    mapping = await _ingest_fixture(db, "identity-access-boundary-v1", sources)
    main = await _detect(db, mapping["events.jsonl"])
    hr = await _detect(db, mapping["events-hr.jsonl"])
    assert (main.alerts_created, hr.alerts_created) == (5, 0)
    assert main.not_evaluable == {"IA-001": 1, "IA-002": 1, "IA-003": 0, "IA-004": 0, "IA-005": 0}


def test_command_line_runs_and_exports(sources):
    """The CLI against the configured (scratch) database, as an operator would use it."""
    import asyncio

    from app.database.session import AsyncSessionLocal, engine

    source_id = sources()

    async def seed():
        async with AsyncSessionLocal() as session:
            await _ingest(session, source_id, burst_records())
        await engine.dispose()

    asyncio.run(seed())

    def cli(*args) -> str:
        done = subprocess.run([sys.executable, "-m", "app.detections", *args], cwd=BACKEND_ROOT, env=os.environ.copy(),
                              capture_output=True, text=True, timeout=120)
        assert done.returncode == 0, done.stderr[-2000:]
        return done.stdout

    report = json.loads(cli("run", "--source-type", NATIVE, "--source-id", source_id))
    assert (report["status"], report["alerts_created"]) == ("completed", 1)
    lines = [json.loads(line) for line in cli("export", "--source-id", source_id).splitlines() if line.strip()]
    assert [(a["rule_id"], [e["role"] for e in a["events"]]) for a in lines] == [("IA-003", ["trigger"] + ["context"] * 5)]


def test_detection_tables_are_not_reachable_through_the_ai_query_engine():
    from app.api.v1.resources import readable_tables
    from app.models.enums import UserRole
    from app.services.grc_engine.schema_graph import TABLES

    for table in ("detection_runs", "detection_alerts", "detection_alert_events"):
        assert table not in TABLES and table not in readable_tables(UserRole.ADMIN)


# --------------------------------------------------------------------------
# 4. API: who may do what, and traceability from alert to source record
# --------------------------------------------------------------------------

def _run_body(source_id: str) -> dict:
    return {"source_type": NATIVE, "source_id": source_id}


@pytest.mark.parametrize("role,expected", [
    ("admin", 200), ("compliance", 200), ("security", 200), ("auditor", 200), ("employee", 403),
])
async def test_the_rule_catalogue_is_for_all_staff(unauth_client, role, expected):
    response = await unauth_client.get(f"{API}/detections/rules", headers=await _as(unauth_client, role))
    assert response.status_code == expected


@pytest.mark.parametrize("role,expected", [
    ("admin", 200), ("compliance", 200), ("security", 200), ("auditor", 403), ("employee", 403),
])
async def test_alerts_are_for_internal_staff_only(unauth_client, role, expected):
    response = await unauth_client.get(f"{API}/detections/alerts", headers=await _as(unauth_client, role))
    assert response.status_code == expected


@pytest.mark.parametrize("role,expected", [
    ("admin", 200), ("security", 200), ("compliance", 403), ("auditor", 403), ("employee", 403),
])
async def test_only_admin_and_security_analyst_can_start_a_run(unauth_client, sources, role, expected):
    response = await unauth_client.post(f"{API}/detections/runs", json=_run_body(sources()),
                                        headers=await _as(unauth_client, role))
    assert response.status_code == expected


async def test_the_catalogue_shows_parameters_and_the_written_contract(unauth_client):
    response = await unauth_client.get(f"{API}/detections/rules", headers=await _as(unauth_client, "auditor"))
    rules = {rule["id"]: rule for rule in response.json()["data"]}
    assert sorted(rules) == RULE_IDS
    assert rules["IA-003"]["parameters"] == {"min_failures": 5, "window_minutes": 30}
    assert (rules["IA-003"]["attack"], rules["IA-002"]["attack"]) == (["T1110.001"], [])
    contract = rules["IA-004"]["contract"]
    assert contract["limitations"] and contract["logic"]["fires_when"] and contract["attack"]["rationale"]
    assert "test_vectors" not in contract


async def test_an_alert_traces_back_to_its_source_records(unauth_client, sources):
    from app.events.contract import canonical_json, sha256_hex

    source_id, admin = sources(), await _as(unauth_client, "admin")
    ingested = await unauth_client.post(f"{API}/security-events/ingest", headers=admin,
                                        json={"source_type": NATIVE, "source_id": source_id, "records": burst_records()})
    assert ingested.json()["data"]["inserted"] == 6
    run = (await unauth_client.post(f"{API}/detections/runs", json=_run_body(source_id),
                                    headers=await _as(unauth_client, "security"))).json()["data"]
    assert run["alerts_created"] == 1

    stored_run = (await unauth_client.get(f"{API}/detections/runs/{run['run_id']}", headers=admin)).json()["data"]
    assert (stored_run["triggered_by"], stored_run["origin"], stored_run["status"]) == ("security@sentinel.ai", "api", "completed")

    listing = (await unauth_client.get(f"{API}/detections/alerts?source_id={source_id}", headers=admin)).json()
    assert listing["meta"]["count"] == 1
    detail = (await unauth_client.get(f"{API}/detections/alerts/{listing['data'][0]['alert_id']}", headers=admin)).json()["data"]
    assert (detail["rule_id"], detail["severity"], detail["confidence"]) == ("IA-003", "high", "medium")
    assert [e["role"] for e in detail["events"]] == ["trigger"] + ["context"] * 5
    for cited in detail["events"]:
        event = (await unauth_client.get(f"{API}/security-events/{cited['event_id']}", headers=admin)).json()["data"]
        assert sha256_hex(canonical_json(event["raw"])) == event["raw_sha256"] == cited["raw_sha256"]


async def test_alert_paging_returns_each_alert_once_in_trigger_time_order(unauth_client, sources):
    source_id, admin = sources(), await _as(unauth_client, "admin")
    records = [nrec(i, i, "auth.login", actor=f"lab-adm-{i}", privileged=True, mfa_used=False) for i in range(5)]
    await unauth_client.post(f"{API}/security-events/ingest", headers=admin,
                             json={"source_type": NATIVE, "source_id": source_id, "records": records})
    await unauth_client.post(f"{API}/detections/runs", json=_run_body(source_id), headers=admin)

    seen, cursor = [], None
    while True:
        url = f"{API}/detections/alerts?source_id={source_id}&order=asc&limit=2" + (f"&cursor={cursor}" if cursor else "")
        page = (await unauth_client.get(url, headers=admin)).json()
        seen += [(a["trigger_at"], a["alert_id"]) for a in page["data"]]
        cursor = page["meta"]["next_cursor"]
        if cursor is None:
            break
    assert len(seen) == 5 == len(set(seen)) and seen == sorted(seen)


@pytest.mark.parametrize("body", [
    {"source_type": "made.up", "source_id": "x"},
    {"source_type": NATIVE, "source_id": "bad id!"},
    {"source_type": NATIVE, "source_id": "x", "extra": 1},
    {"source_type": NATIVE},
])
async def test_bad_run_requests_are_refused(unauth_client, body):
    response = await unauth_client.post(f"{API}/detections/runs", json=body, headers=await _as(unauth_client, "admin"))
    assert response.status_code == 422


async def test_a_run_over_too_many_events_is_refused_over_http(unauth_client, sources, monkeypatch):
    from app.detections import engine

    source_id, admin = sources(), await _as(unauth_client, "admin")
    await unauth_client.post(f"{API}/security-events/ingest", headers=admin,
                             json={"source_type": NATIVE, "source_id": source_id, "records": burst_records()})
    monkeypatch.setattr(engine, "MAX_EVENTS_PER_RUN", 2)
    response = await unauth_client.post(f"{API}/detections/runs", json=_run_body(source_id), headers=admin)
    assert response.status_code == 422 and "limited" in response.json()["error"]["message"]


@pytest.mark.parametrize("query", ["cursor=garbage", "limit=0", "limit=1000", "order=sideways"])
async def test_bad_alert_list_parameters_are_refused(unauth_client, query):
    response = await unauth_client.get(f"{API}/detections/alerts?{query}", headers=await _as(unauth_client, "admin"))
    assert response.status_code == 422


async def test_unknown_alert_and_run_ids_are_404(unauth_client):
    admin = await _as(unauth_client, "admin")
    assert (await unauth_client.get(f"{API}/detections/alerts/{'0' * 64}", headers=admin)).status_code == 404
    assert (await unauth_client.get(f"{API}/detections/runs/{uuid.uuid4()}", headers=admin)).status_code == 404


async def test_monitoring_does_not_claim_to_be_live(unauth_client):
    """Finding F8: the monitoring endpoints filter stored, historical audit logs."""
    data = (await unauth_client.get(f"{API}/intelligence/monitoring/metrics",
                                    headers=await _as(unauth_client, "admin"))).json()["data"]
    assert "monitoring_status" not in data
    assert data["mode"] == "retrospective"


# --------------------------------------------------------------------------
# 5. Evaluation
# --------------------------------------------------------------------------

def _tiny_fixture(tmp_path: Path) -> Path:
    """Two families with one suspicious scenario each, one benign scenario, background."""
    def record(sid, action, outcome="success", actor="u", **attributes):
        return {"source_event_id": sid, "occurred_at": "2026-10-01T08:00:00Z", "action": action, "outcome": outcome,
                "actor": {"type": "user", "id": actor}, "attributes": attributes}

    events = [record("a1", "privilege.grant", privileged=True), record("a2", "privilege.grant", approval_ref="CHG-1"),
              record("b1", "auth.login", "failure", actor="u2"), record("b2", "auth.login", actor="u2"),
              record("n1", "resource.read", actor="u3")]
    labels = [("a1", "X-P", "suspicious", "trigger"), ("a2", "X-B", "benign", "decoy"),
              ("b1", "Y-P", "suspicious", "context"), ("b2", "Y-P", "suspicious", "trigger"), ("n1", "N", "benign", "background")]
    manifest = {"fixture": "tiny", "scenarios": [{"id": "X-P", "family": "fx"}, {"id": "X-B", "family": "fx"},
                                                 {"id": "Y-P", "family": "fy"}, {"id": "N", "family": "background"}]}
    folder = tmp_path / "tiny"
    folder.mkdir()
    (folder / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    (folder / "labels.jsonl").write_text("\n".join(json.dumps(dict(zip(
        ("source_event_id", "scenario_id", "label", "part"), row))) for row in labels) + "\n", encoding="utf-8")
    (folder / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


TINY_CONTRACTS = {
    "R-X": {"fixture_family": "fx", "test_vectors": [{"fixture": "tiny", "scenario": "X-P", "expected_alerts": 1},
                                                    {"fixture": "tiny", "scenario": "X-B", "expected_alerts": 0}]},
    "R-Y": {"fixture_family": "fy", "test_vectors": [{"fixture": "tiny", "scenario": "Y-P", "expected_alerts": 1}]},
}


def _alert(rule_id: str, source_event_id: str) -> dict:
    return {"rule_id": rule_id, "events": [{"source_event_id": source_event_id, "role": "trigger"}]}


@pytest.fixture
def tiny_result(tmp_path):
    evaluator = _load_module(SCRIPTS / "evaluate_detections.py")
    alerts = [_alert("R-X", "a1"), _alert("R-X", "a2"), _alert("R-X", "b2")]
    return evaluator.evaluate_fixture(_tiny_fixture(tmp_path), alerts, TINY_CONTRACTS, {"R-X": 0, "R-Y": 2})


def test_evaluator_counts_hits_misses_and_false_alarms_by_kind(tiny_result):
    rx, ry = tiny_result["rules"]["R-X"], tiny_result["rules"]["R-Y"]
    assert (rx["alerts"], rx["tp"], rx["fp"], rx["fn"]) == (3, 1, 2, 0)
    assert rx["fp_by_kind"] == {"decoy": 1, "other_family_trigger": 1}
    assert rx["precision"] == pytest.approx(1 / 3) and rx["recall"] == 1.0
    assert (ry["alerts"], ry["tp"], ry["fp"], ry["fn"], ry["precision"], ry["recall"]) == (0, 0, 0, 1, None, 0.0)
    assert (ry["not_evaluable"], ry["missed"]) == (2, ["Y-P"])


def test_evaluator_compares_observed_alerts_with_every_test_vector(tiny_result):
    conformance = {(c["rule"], c["scenario"]): c for c in tiny_result["conformance"]}
    assert conformance[("R-X", "X-P")]["as_pre_registered"] is True
    assert (conformance[("R-X", "X-B")]["observed_alerts"], conformance[("R-X", "X-B")]["as_pre_registered"]) == (1, False)
    assert conformance[("R-Y", "Y-P")]["as_pre_registered"] is False


def test_evaluator_scores_sentinels_previous_failure_only_monitoring(tiny_result):
    legacy = tiny_result["comparisons"]["legacy_failure_only"]
    assert (legacy["flagged"], legacy["trigger_events_flagged"], legacy["triggers_total"]) == (1, 0, 2)
    assert legacy["flagged_by_kind"] == {"context": 1}


def _run_benchmark(out: Path, untouchable_db: Path) -> dict:
    url = untouchable_db.as_posix()
    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{url}", "DATABASE_URL_SYNC": f"sqlite:///{url}"}
    done = subprocess.run([sys.executable, str(SCRIPTS / "run_detection_benchmark.py"), "--out", str(out)],
                          cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads((out / "metrics.json").read_text(encoding="utf-8"))


def test_the_benchmark_is_one_repeatable_command_that_leaves_the_configured_database_alone(tmp_path):
    untouchable = tmp_path / "configured-database-must-not-be-created.db"
    first = _run_benchmark(tmp_path / "one", untouchable)
    second = _run_benchmark(tmp_path / "two", untouchable)

    assert not untouchable.exists()
    without_metadata = lambda metrics: {k: v for k, v in metrics.items() if k != "metadata"}  # noqa: E731
    assert without_metadata(first) == without_metadata(second)
    assert first["summary"]["conformance"] == {"vectors": 33, "as_pre_registered": 33}
    assert first["replay"] == {"events_inserted_on_reingest": 0, "alerts_created_on_rerun": 0}
    assert first["fixtures"]["identity-access-v1"]["comparisons"]["legacy_failure_only"]["trigger_events_flagged"] == 0
    assert {"generated_at", "python", "platform", "git"} <= set(first["metadata"])
    assert "known miss" in (tmp_path / "one" / "report.md").read_text(encoding="utf-8")
