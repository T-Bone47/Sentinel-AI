"""
Builds the synthetic fixture `identity-access-v1`.

    python research/scripts/build_identity_access_fixture.py           # (re)write the fixture files
    python research/scripts/build_identity_access_fixture.py --check   # verify the files on disk are what this script produces

Everything in this fixture is invented by this script. There are no real
people, accounts, hosts or addresses in it: identifiers use a `lab-` prefix
and IP addresses come from the ranges reserved for documentation
(RFC 5737 and RFC 3849).

The fixture is a set of constructed test vectors, not a sample of real
activity. Each suspicious scenario has at least one benign twin that differs
in exactly the fact that should decide the outcome. Detection results on it
show whether a rule does what its definition says; they say nothing about how
often such activity occurs or how a rule performs on real data.

Deterministic: fixed seed, standard library only, no clock, no environment.
The same script version always produces byte-identical files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

FIXTURE = "identity-access-v1"
SEED = 20261117
GENERATOR_VERSION = 1
ADAPTER = "sentinel.native"
OUT_DIR = Path(__file__).resolve().parents[1] / "fixtures" / FIXTURE

DAY_ONE = datetime(2026, 9, 1, tzinfo=timezone.utc)
INDIA = timezone(timedelta(hours=5, minutes=30))
MAX_RECORD_BYTES = 64 * 1024   # mirrors app/events/contract.py: the oversize record must exceed it


def at(day: int, hour: int, minute: int, second: int = 0) -> datetime:
    return DAY_ONE + timedelta(days=day - 1, hours=hour, minutes=minute, seconds=second)


def user(n: int) -> dict[str, str]:
    return {"type": "user", "id": f"lab-user-{n:03d}"}


def admin(n: int) -> dict[str, str]:
    return {"type": "user", "id": f"lab-admin-{n:02d}"}


def principal(actor: dict[str, str]) -> dict[str, str]:
    return {"type": "principal", "id": actor["id"]}


def resource(name: str) -> dict[str, str]:
    return {"type": "resource", "id": f"lab-res-{name}"}


HR_SYNC = {"type": "service", "id": "lab-svc-hr-sync"}
BACKUP = {"type": "service", "id": "lab-svc-backup"}
IDP = {"type": "application", "id": "lab-idp"}
CRM = {"type": "application", "id": "lab-app-crm"}


def dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


class Fixture:
    """Collects events and, separately, the ground truth about them. The two
    never share a record: a label is keyed by event id and lives only in
    labels.jsonl, which is never ingested."""

    def __init__(self) -> None:
        self.rng = random.Random(SEED)
        self.events: list[dict[str, Any]] = []
        self.labels: list[dict[str, str]] = []
        self.scenarios: list[dict[str, Any]] = []
        self._ids: set[str] = set()

    def scenario(self, scenario_id: str, family: str, label: str, summary: str) -> None:
        self.scenarios.append({"id": scenario_id, "family": family, "label": label, "events": 0, "summary": summary})

    def _new_id(self) -> str:
        # Random-looking ids, so an event's id says nothing about which
        # scenario it belongs to or when it happened.
        while True:
            event_id = f"ia1-{self.rng.getrandbits(48):012x}"
            if event_id not in self._ids:
                self._ids.add(event_id)
                return event_id

    def event(self, when: datetime, action: str, outcome: str, part: str, *, actor: dict | None = None,
              target: dict | None = None, src_ip: str | None = None, source_action: str | None = None,
              attrs: dict[str, Any] | None = None, local_time: bool = False) -> dict[str, Any]:
        """`part` is the event's place in its scenario: "trigger" (where a
        detection should fire), "decoy" (where a careless rule would wrongly
        fire), "context" (supporting events) or "background"."""
        scenario = self.scenarios[-1]
        stamp = when.astimezone(INDIA).isoformat() if local_time else when.strftime("%Y-%m-%dT%H:%M:%SZ")
        record: dict[str, Any] = {"source_event_id": self._new_id(), "occurred_at": stamp}
        if actor:
            record["actor"] = actor
        if target:
            record["target"] = target
        record["action"] = action
        if source_action:
            record["source_action"] = source_action
        record["outcome"] = outcome
        if src_ip:
            record["src_ip"] = src_ip
        if attrs:
            record["attributes"] = attrs
        self.events.append(record)
        self.labels.append({"source_event_id": record["source_event_id"], "scenario_id": scenario["id"],
                            "label": scenario["label"], "part": part})
        scenario["events"] += 1
        return record

    def login(self, when: datetime, who: dict, ip: str, part: str, *, ok: bool = True, mfa: bool,
              privileged: bool, reason: str | None = None, local_time: bool = False) -> dict[str, Any]:
        attrs: dict[str, Any] = {"mfa_used": mfa, "privileged": privileged, "auth_method": "password"}
        if reason:
            attrs["failure_reason"] = reason
        return self.event(when, "auth.login", "success" if ok else "failure", part, actor=who, target=IDP,
                          src_ip=ip, source_action="idp.signin", attrs=attrs, local_time=local_time)

    def failed_logins(self, who: dict, ip: str, times: list[datetime]) -> None:
        for when in times:
            self.login(when, who, ip, "context", ok=False, mfa=False, privileged=True, reason="invalid_password")


def scenarios(fx: Fixture) -> None:
    grant = "privilege_grant_without_approval"
    fx.scenario("S01-P1", grant, "suspicious", "An administrator grants a privileged role with no approval reference.")
    fx.event(at(2, 10, 14, 9), "privilege.grant", "success", "trigger", actor=admin(2), target=principal(user(7)),
             src_ip="198.51.100.21", attrs={"role": "payroll-admin", "privileged": True})
    fx.scenario("S01-P2", grant, "suspicious", "A non-administrator grants a privileged role to their own account.")
    fx.event(at(4, 22, 41, 37), "privilege.grant", "success", "trigger", actor=user(5), target=principal(user(5)),
             src_ip="203.0.113.18", attrs={"role": "crm-admin", "privileged": True})
    fx.scenario("S01-B1", grant, "benign", "The same privileged grant as S01-P1, with an approval reference.")
    fx.event(at(3, 11, 2, 44), "privilege.grant", "success", "decoy", actor=admin(1), target=principal(user(3)),
             src_ip="198.51.100.20", attrs={"role": "payroll-admin", "privileged": True, "approval_ref": "CHG-1041"},
             local_time=True)
    fx.scenario("S01-B2", grant, "benign", "Onboarding automation grants a non-privileged role with no approval reference.")
    fx.event(at(5, 6, 0, 3), "privilege.grant", "success", "decoy", actor=HR_SYNC, target=principal(user(9)),
             src_ip="192.0.2.20", attrs={"role": "employee-basic", "privileged": False})

    no_mfa = "privileged_login_without_mfa"
    fx.scenario("S02-P1", no_mfa, "suspicious", "A privileged account signs in successfully without a second factor.")
    fx.login(at(6, 9, 12, 30), admin(3), "203.0.113.61", "trigger", mfa=False, privileged=True)
    fx.scenario("S02-B1", no_mfa, "benign", "A privileged account signs in with a second factor.")
    fx.login(at(6, 9, 30, 5), admin(1), "198.51.100.20", "decoy", mfa=True, privileged=True)
    fx.scenario("S02-B2", no_mfa, "benign", "A non-privileged account signs in without a second factor.")
    fx.login(at(6, 9, 45, 51), user(2), "198.51.100.31", "decoy", mfa=False, privileged=False)
    fx.scenario("S02-B3", no_mfa, "benign", "A privileged sign-in without a second factor that failed: no access was gained.")
    fx.login(at(6, 10, 5, 12), admin(3), "203.0.113.61", "decoy", ok=False, mfa=False, privileged=True,
             reason="invalid_password")

    guessing = "failed_privileged_logins_then_success"
    fx.scenario("S03-P1", guessing, "suspicious",
                "Six failed sign-ins to a privileged account within three minutes, then a success from the same address.")
    fx.failed_logins(admin(2), "203.0.113.50", [at(8, 2, 10, 5), at(8, 2, 10, 41), at(8, 2, 11, 17),
                                                 at(8, 2, 11, 52), at(8, 2, 12, 30), at(8, 2, 13, 2)])
    fx.login(at(8, 2, 14, 10), admin(2), "203.0.113.50", "trigger", mfa=True, privileged=True)
    fx.scenario("S03-B1", guessing, "benign", "Two failed sign-ins then a success: ordinary mistyping.")
    fx.failed_logins(admin(1), "198.51.100.20", [at(8, 8, 30, 10), at(8, 8, 30, 40)])
    fx.login(at(8, 8, 31, 15), admin(1), "198.51.100.20", "decoy", mfa=True, privileged=True)
    fx.scenario("S03-B2", guessing, "benign",
                "Six failed sign-ins, then an approved credential reset by the helpdesk, then a success.")
    fx.failed_logins(admin(3), "198.51.100.22", [at(9, 14, 0, 5), at(9, 14, 0, 39), at(9, 14, 1, 12),
                                                  at(9, 14, 1, 50), at(9, 14, 2, 25), at(9, 14, 3, 0)])
    fx.event(at(9, 14, 20, 11), "credential.change", "success", "context", actor=admin(1), target=principal(admin(3)),
             src_ip="198.51.100.20", source_action="idp.password_reset", attrs={"approval_ref": "INC-2207"})
    fx.login(at(9, 14, 25, 40), admin(3), "198.51.100.22", "decoy", mfa=True, privileged=True)
    fx.scenario("S03-B3", guessing, "benign", "Six failed sign-ins spread over nine hours, then a success.")
    fx.failed_logins(admin(1), "198.51.100.20", [at(10, 7, 5, 13), at(10, 8, 40, 2), at(10, 10, 15, 47),
                                                  at(10, 12, 30, 20), at(10, 14, 10, 9), at(10, 15, 55, 31)])
    fx.login(at(10, 16, 20, 5), admin(1), "198.51.100.20", "decoy", mfa=True, privileged=True)

    disabled = "activity_by_disabled_account"
    fx.scenario("S04-P1", disabled, "suspicious",
                "An account is disabled, and two days later signs in and reads confidential data.")
    fx.event(at(3, 17, 0, 2), "account.disable", "success", "context", actor=HR_SYNC, target=principal(user(11)),
             src_ip="192.0.2.20", attrs={"approval_ref": "HR-OFFBOARD-311"})
    fx.login(at(5, 23, 18, 40), user(11), "203.0.113.77", "trigger", mfa=False, privileged=False)
    fx.event(at(5, 23, 21, 5), "resource.read", "success", "trigger", actor=user(11), target=resource("customer-db"),
             src_ip="203.0.113.77", attrs={"sensitivity": "confidential"})
    fx.scenario("S04-B1", disabled, "benign", "An account is disabled, re-enabled with approval, and then signs in.")
    fx.event(at(3, 17, 5, 10), "account.disable", "success", "context", actor=HR_SYNC, target=principal(user(10)),
             src_ip="192.0.2.20", attrs={"approval_ref": "HR-LEAVE-310"})
    fx.event(at(4, 9, 0, 30), "account.enable", "success", "context", actor=admin(1), target=principal(user(10)),
             src_ip="198.51.100.20", attrs={"approval_ref": "CHG-1055"})
    fx.login(at(5, 9, 10, 44), user(10), "198.51.100.33", "decoy", mfa=True, privileged=False)
    fx.scenario("S04-B2", disabled, "benign", "A disabled account attempts to sign in and is refused: the control worked.")
    fx.event(at(3, 17, 10, 8), "account.disable", "success", "context", actor=HR_SYNC, target=principal(user(12)),
             src_ip="192.0.2.20", attrs={"approval_ref": "HR-OFFBOARD-312"})
    fx.login(at(4, 8, 2, 19), user(12), "198.51.100.34", "decoy", ok=False, mfa=False, privileged=False,
             reason="account_disabled")

    then_access = "permission_change_then_sensitive_access"
    fx.scenario("S05-P1", then_access, "suspicious",
                "An unapproved permission grant, and ten minutes later the grantee exports restricted data.")
    fx.event(at(11, 13, 0, 12), "privilege.grant", "success", "context", actor=admin(2), target=principal(user(6)),
             src_ip="198.51.100.21", attrs={"role": "payroll-reader", "privileged": False})
    fx.event(at(11, 13, 9, 48), "resource.export", "success", "trigger", actor=user(6), target=resource("payroll-export"),
             src_ip="198.51.100.36", attrs={"sensitivity": "restricted"})
    fx.scenario("S05-B1", then_access, "benign", "The same grant and export as S05-P1, but the grant was approved.")
    fx.event(at(11, 15, 0, 7), "privilege.grant", "success", "context", actor=admin(1), target=principal(user(4)),
             src_ip="198.51.100.20", attrs={"role": "payroll-reader", "privileged": False, "approval_ref": "CHG-1102"})
    fx.event(at(11, 15, 8, 30), "resource.export", "success", "decoy", actor=user(4), target=resource("payroll-export"),
             src_ip="198.51.100.34", attrs={"sensitivity": "restricted"})
    fx.scenario("S05-B2", then_access, "benign", "An unapproved grant followed by access to non-sensitive data.")
    fx.event(at(12, 10, 0, 55), "privilege.grant", "success", "context", actor=admin(2), target=principal(user(8)),
             src_ip="198.51.100.21", attrs={"role": "wiki-editor", "privileged": False})
    fx.event(at(12, 10, 7, 21), "resource.read", "success", "decoy", actor=user(8), target=resource("wiki-page"),
             src_ip="198.51.100.38", attrs={"sensitivity": "internal"})


def background(fx: Fixture) -> None:
    """Routine activity around the scenarios. Built so that it cannot form any
    of the suspicious patterns by accident: accounts 010-012 (the disabled
    ones) never appear, administrators always use a second factor and never
    fail, nobody fails more than once in a row, and nobody is granted
    anything or touches restricted data."""
    fx.scenario("N00", "background", "benign", "Routine sign-ins, reads, backups and health checks.")
    rng = fx.rng
    office = [f"198.51.100.{n}" for n in range(40, 70)]

    for day in range(1, 14):
        for person in rng.sample([user(n) for n in range(1, 10)], 5):
            hour, minute, second = rng.randint(7, 10), rng.randint(0, 59), rng.randint(0, 59)
            ip = "2001:db8::17" if rng.random() < 0.05 else rng.choice(office)
            local = rng.random() < 0.2          # some sources report local time with an offset
            if rng.random() < 0.15:             # one mistyped password before the successful sign-in
                fx.login(at(day, hour, minute, second) - timedelta(seconds=40), person, ip, "background", ok=False,
                         mfa=False, privileged=False, reason="invalid_password", local_time=local)
            fx.login(at(day, hour, minute, second), person, ip, "background", mfa=True, privileged=False,
                     local_time=local)
            if rng.random() < 0.6:
                fx.event(at(day, hour + rng.randint(1, 6), rng.randint(0, 59), rng.randint(0, 59)), "resource.read",
                         "success", "background", actor=person, target=resource("wiki-page"), src_ip=ip,
                         attrs={"sensitivity": "internal"}, local_time=local)

        fx.event(at(day, 1, 0, rng.randint(0, 59)), "resource.read", "success", "background", actor=BACKUP,
                 target=resource("customer-db"), src_ip="192.0.2.10", source_action="backup.snapshot",
                 attrs={"sensitivity": "confidential"})
        if day not in (6, 8, 9, 10):            # days on which administrators appear in scenarios
            fx.login(at(day, 8, rng.randint(0, 59), rng.randint(0, 59)), admin(1 + day % 3), rng.choice(office),
                     "background", mfa=True, privileged=True)

    fx.event(at(2, 15, 20, 18), "config.change", "success", "background", actor=admin(1), target=CRM,
             src_ip="198.51.100.20", attrs={"approval_ref": "CHG-1012"})
    fx.event(at(4, 11, 45, 2), "credential.change", "success", "background", actor=user(1), target=principal(user(1)),
             src_ip="198.51.100.41", source_action="idp.password_change")
    fx.event(at(7, 13, 8, 27), "resource.write", "unknown", "background", actor=user(3), target=resource("wiki-page"),
             src_ip="198.51.100.44", attrs={"sensitivity": "internal"})
    fx.event(at(9, 10, 30, 0), "resource.read", "success", "background", actor=user(1), target=resource("customer-db"),
             src_ip="198.51.100.41", attrs={"sensitivity": "confidential"})
    for day in (1, 5, 9):                       # emitted by the system itself: no actor
        fx.event(at(day, 0, 5, 0), "other", "success", "background", target=IDP, source_action="idp.health_check")
    fx.event(at(13, 0, 5, 0), "other", "success", "background", source_action="idp.health_check")   # no actor, no target


def malformed_file() -> tuple[bytes, dict[str, Any]]:
    """Records that must be refused, each for a different reason, with two
    valid records among them to show that one bad record does not affect its
    neighbours."""
    def valid(suffix: str, **changes: Any) -> dict[str, Any]:
        record = {"source_event_id": f"ia1-malformed-{suffix}", "occurred_at": "2026-09-02T10:00:00Z",
                  "actor": user(1), "target": IDP, "action": "auth.login", "outcome": "success",
                  "src_ip": "198.51.100.41", "attributes": {"mfa_used": True, "privileged": False}}
        record.update(changes)
        return record

    without_time = valid("no-time")
    del without_time["occurred_at"]
    cases: list[tuple[str, str | None]] = [
        (dumps(valid("ok-1")), None),
        ('{"source_event_id":"ia1-malformed-truncated","occurred_at":"2026-09-02T10:01:00Z","action":"auth.login"', "invalid_json"),
        ('["not","an","object"]', "not_an_object"),
        (dumps(without_time), "invalid_record"),
        (dumps(valid("naive-time", occurred_at="2026-09-02T10:03:00")), "invalid_record"),
        (dumps(valid("unknown-action", action="auth.teleport")), "invalid_record"),
        (dumps(valid("wrong-type", attributes={"mfa_used": "yes"})), "invalid_record"),
        (dumps(valid("unknown-attribute", attributes={"shoe_size": 9})), "invalid_record"),
        (dumps({**valid("extra-field"), "label": "suspicious"}), "invalid_record"),
        (dumps(valid("far-future", occurred_at="2099-01-01T00:00:00Z")), "timestamp_in_future"),
        (dumps(valid("empty-actor", actor={"type": "user", "id": ""})), "invalid_record"),
        (dumps(valid("bad-ip", src_ip="999.1.1.1")), "invalid_record"),
        ("", None),                                                    # blank line: skipped, not counted
        (dumps(valid("oversize", attributes={"role": "x" * (MAX_RECORD_BYTES + 1)})), "record_too_large"),
        (dumps(valid("ok-2", occurred_at="2026-09-02T10:20:00Z")), None),
        ('"just a string"', "not_an_object"),
    ]
    counted = [(line, reason) for line, reason in cases if line]
    reasons: dict[str, int] = {}
    for _, reason in counted:
        if reason:
            reasons[reason] = reasons.get(reason, 0) + 1
    rejected = sum(reasons.values())
    expected = {"received": len(counted), "inserted": len(counted) - rejected, "duplicates": 0, "conflicts": 0,
                "rejected": rejected, "reject_reasons": dict(sorted(reasons.items()))}
    return ("\n".join(line for line, _ in cases) + "\n").encode("utf-8"), expected


def build() -> dict[str, bytes]:
    """Every generated file, by name. Pure: writes nothing."""
    fx = Fixture()
    scenarios(fx)
    background(fx)

    lines = [dumps(event) for event in fx.events]
    arrival = lines[:]
    fx.rng.shuffle(arrival)                     # arrival order is unrelated to event time
    # Three re-sends of records already in the file. Two are byte-identical;
    # the third has the same content with different key order and spacing,
    # which must still be recognised as the same record.
    resent = fx.rng.sample(range(len(fx.events)), 3)
    for position, copy in zip(
        sorted(fx.rng.sample(range(len(arrival)), 3)),
        (lines[resent[0]], lines[resent[1]], json.dumps(fx.events[resent[2]], sort_keys=True, ensure_ascii=False)),
    ):
        arrival.insert(position, copy)
    events_file = ("\n".join(arrival) + "\n").encode("utf-8")

    labels_file = ("\n".join(dumps(label) for label in fx.labels) + "\n").encode("utf-8")

    # The same id as an event already in events.jsonl, with different content.
    original = next(e for e in fx.events if e["action"] == "auth.login" and e["outcome"] == "success"
                    and e.get("src_ip", "").startswith("198.51.100."))
    conflict_file = (dumps({**original, "src_ip": "203.0.113.200"}) + "\n").encode("utf-8")

    malformed, malformed_expected = malformed_file()

    files = {"events.jsonl": events_file, "labels.jsonl": labels_file,
             "replay-conflict.jsonl": conflict_file, "malformed.jsonl": malformed}
    unique, received = len(fx.events), len(arrival)
    nothing = {"conflicts": 0, "rejected": 0, "reject_reasons": {}}
    times = sorted(datetime.fromisoformat(e["occurred_at"]) for e in fx.events)
    counts: dict[str, int] = {}
    for label in fx.labels:
        counts[label["label"]] = counts.get(label["label"], 0) + 1
    manifest = {
        "fixture": FIXTURE,
        "synthetic": True,
        "description": "Constructed identity-and-access test vectors. Not a sample of real activity.",
        "generator": {"script": "research/scripts/build_identity_access_fixture.py", "version": GENERATOR_VERSION, "seed": SEED},
        "adapter": ADAPTER,
        "event_time_range": {"first": times[0].astimezone(timezone.utc).isoformat(),
                             "last": times[-1].astimezone(timezone.utc).isoformat()},
        "files": {name: {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
                         "lines": content.count(b"\n")} for name, content in files.items()},
        "expected": {
            "events.jsonl": {"received": received, "inserted": unique, "duplicates": received - unique, **nothing},
            "events.jsonl (replayed)": {"received": received, "inserted": 0, "duplicates": received, **nothing},
            "replay-conflict.jsonl": {"received": 1, "inserted": 0, "duplicates": 0, "conflicts": 1, "rejected": 0,
                                      "reject_reasons": {"conflicting_duplicate": 1}},
            "malformed.jsonl": malformed_expected,
        },
        "label_counts": dict(sorted(counts.items())),
        "scenarios": fx.scenarios,
    }
    files["MANIFEST.json"] = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="verify the files on disk instead of writing them")
    args = parser.parse_args()

    files = build()
    if args.check:
        stale = [name for name, content in files.items()
                 if not (OUT_DIR / name).is_file() or (OUT_DIR / name).read_bytes() != content]
        print("fixture is up to date" if not stale else f"out of date: {', '.join(stale)}")
        return 1 if stale else 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (OUT_DIR / name).write_bytes(content)      # bytes, so line endings are LF on every platform
        print(f"wrote {name:<24}{len(content):>8} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
