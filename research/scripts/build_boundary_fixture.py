"""
Builds the synthetic boundary fixture `identity-access-boundary-v1`.

    python research/scripts/build_boundary_fixture.py           # (re)write the fixture files
    python research/scripts/build_boundary_fixture.py --check   # verify the files on disk are what this script produces

Fifteen small, hand-placed cases at the edges of the five detection rules:
thresholds, window limits, events at the same instant, arrival order, and three
situations the rules are known to miss. The expected outcome of every case was
written into the rule contracts (research/rules/*.toml), and their hashes were
recorded in docs/PROGRESS.md, before this script or any rule code existed.

Synthetic, like identity-access-v1: `lab-` identifiers, documentation-range
addresses (RFC 5737), a fixed seed, standard library only. Events are written
in the order they are created below — deliberately not shuffled — so that case
B-10 can put a sign-in earlier in the file than the disable it follows.

Two sources: `events.jsonl` is the identity provider, `events-hr.jsonl` is a
separate HR system. Case B-12 needs both.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))   # also works under `python -I`

from build_identity_access_fixture import (  # noqa: E402
    HR_SYNC, IDP, Fixture, admin, at, dumps, principal, resource, user,
)

FIXTURE = "identity-access-boundary-v1"
SEED = 20261118
GENERATOR_VERSION = 1
ADAPTER = "sentinel.native"
OUT_DIR = Path(__file__).resolve().parents[1] / "fixtures" / FIXTURE
SOURCES = {"events.jsonl": FIXTURE, "events-hr.jsonl": f"{FIXTURE}-hr"}

GUESSING = "failed_privileged_logins_then_success"
THEN_ACCESS = "permission_change_then_sensitive_access"
DISABLED = "activity_by_disabled_account"
GRANT = "privilege_grant_without_approval"
NO_MFA = "privileged_login_without_mfa"

MINUTE = timedelta(minutes=1)
SECOND = timedelta(seconds=1)
OFFICE_IP = "198.51.100.110"


class BoundaryFixture(Fixture):
    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random(SEED)
        self.hr_events: list[dict[str, Any]] = []   # recorded by the separate HR source

    def _new_id(self) -> str:
        while True:
            event_id = f"iab1-{self.rng.getrandbits(48):012x}"
            if event_id not in self._ids:
                self._ids.add(event_id)
                return event_id

    def grant(self, when, grantee, part, role, *, privileged: bool | None = False) -> None:
        attrs: dict[str, Any] = {"role": role}
        if privileged is not None:
            attrs["privileged"] = privileged
        self.event(when, "privilege.grant", "success", part, actor=admin(12), target=principal(grantee),
                   src_ip="198.51.100.120", attrs=attrs)

    def export(self, when, who, part) -> None:
        self.event(when, "resource.export", "success", part, actor=who, target=resource("finance-export"),
                   src_ip="198.51.100.130", attrs={"sensitivity": "restricted"})

    def disable(self, when, account) -> None:
        self.event(when, "account.disable", "success", "context", actor=HR_SYNC, target=principal(account),
                   src_ip="192.0.2.20", attrs={"approval_ref": "HR-OFFBOARD-901"})

    def sign_in(self, when, who, part) -> None:
        self.login(when, who, OFFICE_IP, part, mfa=True, privileged=False)


def cases(fx: BoundaryFixture) -> None:
    fx.scenario("B-01", GUESSING, "benign", "Four failed sign-ins, then a success: one short of the threshold.")
    fx.failed_logins(user(101), OFFICE_IP, [at(20, 8, m) for m in range(4)])
    fx.sign_in(at(20, 8, 5), user(101), "decoy")

    fx.scenario("B-02", GUESSING, "suspicious", "Five failed sign-ins, the first exactly 30 minutes before the success.")
    t = at(20, 10, 0)
    fx.failed_logins(user(102), OFFICE_IP, [t - 30 * MINUTE, t - 20 * MINUTE, t - 10 * MINUTE, t - 5 * MINUTE, t - MINUTE])
    fx.sign_in(t, user(102), "trigger")

    fx.scenario("B-03", GUESSING, "benign", "As B-02, but the first failure is 30 minutes and 1 second before the success.")
    t = at(20, 12, 0)
    fx.failed_logins(user(103), OFFICE_IP,
                     [t - 30 * MINUTE - SECOND, t - 20 * MINUTE, t - 10 * MINUTE, t - 5 * MINUTE, t - MINUTE])
    fx.sign_in(t, user(103), "decoy")

    fx.scenario("B-04", GUESSING, "suspicious", "Five failed sign-ins from five different addresses, then a success.")
    for n in range(5):
        fx.failed_logins(user(104), f"203.0.113.{141 + n}", [at(20, 14, n)])
    fx.login(at(20, 14, 5), user(104), "203.0.113.146", "trigger", mfa=True, privileged=False)

    fx.scenario("B-05", GUESSING, "benign", "Five failed sign-ins by one account, then a success by a different account.")
    fx.failed_logins(user(105), OFFICE_IP, [at(20, 16, m) for m in range(5)])
    fx.sign_in(at(20, 16, 5), user(106), "decoy")

    fx.scenario("B-06", THEN_ACCESS, "suspicious", "An unapproved grant, then a restricted export exactly 60 minutes later.")
    fx.grant(at(21, 9, 0), user(107), "context", "finance-reader")
    fx.export(at(21, 10, 0), user(107), "trigger")

    fx.scenario("B-07", THEN_ACCESS, "benign", "As B-06, but the export is 60 minutes and 1 second after the grant.")
    fx.grant(at(21, 11, 0), user(108), "context", "finance-reader")
    fx.export(at(21, 12, 0, 1), user(108), "decoy")

    fx.scenario("B-08", THEN_ACCESS, "benign", "An unapproved grant to one principal, then a restricted export by another.")
    fx.grant(at(21, 13, 0), user(109), "context", "finance-reader")
    fx.export(at(21, 13, 10), user(110), "decoy")

    fx.scenario("B-09", DISABLED, "benign", "A sign-in at the same instant as the disable: not after it.")
    fx.disable(at(22, 9, 0), user(111))
    fx.sign_in(at(22, 9, 0), user(111), "decoy")

    fx.scenario("B-10", DISABLED, "suspicious",
                "A sign-in two hours after the disable, written earlier in the file than the disable.")
    fx.sign_in(at(22, 13, 0), user(112), "trigger")
    fx.disable(at(22, 11, 0), user(112))

    fx.scenario("B-11", DISABLED, "benign", "Disabled, re-enabled without an approval reference, then a sign-in.")
    fx.disable(at(22, 15, 0), user(113))
    fx.event(at(22, 16, 0), "account.enable", "success", "context", actor=admin(11), target=principal(user(113)),
             src_ip="198.51.100.111")
    fx.sign_in(at(22, 17, 0), user(113), "decoy")

    fx.scenario("B-12", DISABLED, "suspicious",
                "The disable is recorded by a separate HR source; the sign-in three hours later by the identity provider.")
    fx.disable(at(23, 9, 0), user(114))
    fx.hr_events.append(fx.events.pop())
    fx.sign_in(at(23, 12, 0), user(114), "trigger")

    fx.scenario("B-13", GRANT, "suspicious",
                "An administrative role granted without approval, where the source omits the privileged flag.")
    fx.grant(at(23, 14, 0), user(115), "trigger", "db-admin", privileged=None)

    fx.scenario("B-14", NO_MFA, "suspicious",
                "A privileged sign-in where the source omits whether a second factor was used.")
    fx.event(at(24, 9, 0), "auth.login", "success", "trigger", actor=admin(13), target=IDP, src_ip="198.51.100.113",
             source_action="idp.signin", attrs={"privileged": True, "auth_method": "password"})

    fx.scenario("B-15", GUESSING, "suspicious", "Five failed sign-ins, then two successes a minute apart.")
    fx.failed_logins(user(116), OFFICE_IP, [at(24, 11, m) for m in range(5)])
    fx.sign_in(at(24, 11, 5), user(116), "trigger")
    fx.sign_in(at(24, 11, 6), user(116), "decoy")


def _lines(items: list[dict[str, Any]]) -> bytes:
    return ("\n".join(dumps(item) for item in items) + "\n").encode("utf-8")


def build() -> dict[str, bytes]:
    """Every generated file, by name. Pure: writes nothing."""
    fx = BoundaryFixture()
    cases(fx)
    files = {"events.jsonl": _lines(fx.events), "events-hr.jsonl": _lines(fx.hr_events), "labels.jsonl": _lines(fx.labels)}

    def stored_once(count: int) -> dict[str, Any]:
        return {"received": count, "inserted": count, "duplicates": 0, "conflicts": 0, "rejected": 0, "reject_reasons": {}}

    counts: dict[str, int] = {}
    for label in fx.labels:
        counts[label["label"]] = counts.get(label["label"], 0) + 1
    manifest = {
        "fixture": FIXTURE,
        "synthetic": True,
        "description": "Hand-placed edge cases for the five detection rules, including three known misses. "
                       "Not a sample of real activity.",
        "generator": {"script": "research/scripts/build_boundary_fixture.py", "version": GENERATOR_VERSION, "seed": SEED},
        "adapter": ADAPTER,
        "sources": SOURCES,
        "files": {name: {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
                         "lines": content.count(b"\n")} for name, content in files.items()},
        "expected": {"events.jsonl": stored_once(len(fx.events)), "events-hr.jsonl": stored_once(len(fx.hr_events))},
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
