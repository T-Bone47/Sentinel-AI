"""
The detection rules.

Each rule is a pure function over the events of one source, in event-time
order. It never reads the clock, the database or another source, so the same
events always give the same findings. Each rule's human-readable contract is
research/rules/<id>.toml, and tests/test_gate3_detections.py fails if the two
disagree (docs/DECISIONS.md, ADR-010).

Conventions every rule follows
  * "After" means strictly later. Events at the same instant are not treated
    as ordered (docs/EVENT_CONTRACT.md §5): a state change never affects an
    action at the same instant, in either direction.
  * When a rule needs an attribute that an event does not carry, the event is
    counted as not evaluable. It is never treated as a negative.
  * A finding has exactly one trigger event — the event at which the rule
    fires — and any number of context events: the evidence that made it fire.
  * Summaries hold identifiers, times, and only the attribute the rule is
    about (the role granted, the data classification). Nothing else from the
    source record is copied into them.
"""
from __future__ import annotations

import bisect
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from itertools import groupby
from typing import Any

SEVERITIES = ("low", "medium", "high", "critical")
CONFIDENCES = ("low", "medium", "high")


@dataclass(frozen=True)
class EventView:
    """The parts of a stored event a rule may look at."""

    event_id: str
    occurred_at: datetime
    action: str
    outcome: str
    actor_id: str | None = None
    target_id: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.outcome == "success"


@dataclass(frozen=True)
class Finding:
    trigger_id: str
    context_ids: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class RuleResult:
    findings: list[Finding]
    not_evaluable: int = 0


@dataclass(frozen=True)
class Rule:
    id: str
    version: int
    title: str
    severity: str
    confidence: str
    attack: tuple[str, ...]           # ATT&CK technique ids; empty means unmapped
    parameters: Mapping[str, Any]     # also written in the contract; a test checks they match
    logic: str                        # one sentence, for the catalogue
    detect: Callable[[Sequence[EventView]], RuleResult]


def _at(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _name(identifier: str | None, kind: str = "actor") -> str:
    return identifier or f"an unidentified {kind}"


# --- IA-001 -------------------------------------------------------------------

def _privileged_grant_without_approval(events: Sequence[EventView]) -> RuleResult:
    findings, not_evaluable = [], 0
    for e in events:
        if e.action != "privilege.grant" or not e.succeeded:
            continue
        privileged = e.attributes.get("privileged")
        if privileged is None:
            not_evaluable += 1
        elif privileged and "approval_ref" not in e.attributes:
            role = e.attributes.get("role", "an unnamed role")
            findings.append(Finding(e.event_id, (), (
                f"{_name(e.actor_id)} granted the privileged role '{role}' to {_name(e.target_id, 'principal')} "
                f"at {_at(e.occurred_at)} with no approval reference.")))
    return RuleResult(findings, not_evaluable)


# --- IA-002 -------------------------------------------------------------------

def _privileged_sign_in_without_mfa(events: Sequence[EventView]) -> RuleResult:
    findings, not_evaluable = [], 0
    for e in events:
        if e.action != "auth.login" or not e.succeeded:
            continue
        privileged, mfa_used = e.attributes.get("privileged"), e.attributes.get("mfa_used")
        if privileged is False:
            continue                                   # out of scope, not unknown
        if privileged is None or mfa_used is None:
            not_evaluable += 1
        elif mfa_used is False:
            findings.append(Finding(e.event_id, (), (
                f"{_name(e.actor_id)} opened a privileged session at {_at(e.occurred_at)} without a second factor.")))
    return RuleResult(findings, not_evaluable)


# --- IA-003 -------------------------------------------------------------------

IA003_MIN_FAILURES = 5
IA003_WINDOW_MINUTES = 30


def _failed_sign_ins_then_success(events: Sequence[EventView]) -> RuleResult:
    window = timedelta(minutes=IA003_WINDOW_MINUTES)
    failures: dict[str, list[EventView]] = defaultdict(list)
    successes: dict[str, list[EventView]] = defaultdict(list)
    approved_resets: dict[str, list[datetime]] = defaultdict(list)
    not_evaluable = 0
    for e in events:
        if e.action == "auth.login":
            if e.actor_id is None:
                not_evaluable += 1
            elif e.outcome == "failure":
                failures[e.actor_id].append(e)
            elif e.succeeded:
                successes[e.actor_id].append(e)
        elif e.action == "credential.change" and e.succeeded and e.target_id and "approval_ref" in e.attributes:
            approved_resets[e.target_id].append(e.occurred_at)

    findings = []
    for account, wins in successes.items():
        fails = failures.get(account, [])
        fail_times = [f.occurred_at for f in fails]
        win_times = [w.occurred_at for w in wins]
        resets = approved_resets.get(account, [])
        for win in wins:
            t = win.occurred_at
            # Failures in [t - window, t): the start is inclusive, the success's own instant is not.
            in_window = fails[bisect.bisect_left(fail_times, t - window):bisect.bisect_left(fail_times, t)]
            if len(in_window) < IA003_MIN_FAILURES:
                continue
            last_failure = in_window[-1].occurred_at
            if win_times[bisect.bisect_right(win_times, last_failure)] < t:
                continue                               # an earlier success already followed this burst
            later_reset = bisect.bisect_right(resets, last_failure)
            if later_reset < len(resets) and resets[later_reset] < t:
                continue                               # an approved reset in between explains the failures
            findings.append(Finding(win.event_id, tuple(f.event_id for f in in_window), (
                f"{account} signed in at {_at(t)} after {len(in_window)} failed sign-ins "
                f"in the preceding {IA003_WINDOW_MINUTES} minutes.")))
    return RuleResult(findings, not_evaluable)


# --- IA-004 -------------------------------------------------------------------

def _activity_by_disabled_account(events: Sequence[EventView]) -> RuleResult:
    findings, not_evaluable = [], 0
    disabled: dict[str, EventView] = {}                # account -> the disable that began its disabled period
    for _, same_instant in groupby(events, key=lambda e: e.occurred_at):
        group = list(same_instant)
        for e in group:                                # judged against the state left by strictly earlier events
            started = disabled.get(e.actor_id) if e.actor_id else None
            if started is not None and e.succeeded:
                findings.append(Finding(e.event_id, (started.event_id,), (
                    f"{e.actor_id} performed {e.action} at {_at(e.occurred_at)}, after the account was "
                    f"disabled at {_at(started.occurred_at)}.")))
        # Then this instant's state changes apply, to later events only:
        # disables first, then enables, so the outcome never depends on how
        # simultaneous events happen to sort.
        changes = [e for e in group if e.succeeded and e.action in ("account.disable", "account.enable")]
        not_evaluable += sum(1 for e in changes if e.target_id is None)
        for e in changes:
            if e.action == "account.disable" and e.target_id:
                disabled.setdefault(e.target_id, e)
        for e in changes:
            if e.action == "account.enable" and e.target_id:
                disabled.pop(e.target_id, None)
    return RuleResult(findings, not_evaluable)


# --- IA-005 -------------------------------------------------------------------

IA005_WINDOW_MINUTES = 60
IA005_SENSITIVE_LEVELS = ("confidential", "restricted")


def _unapproved_grant_then_sensitive_access(events: Sequence[EventView]) -> RuleResult:
    window = timedelta(minutes=IA005_WINDOW_MINUTES)
    unapproved: dict[str, list[EventView]] = defaultdict(list)    # grantee -> grants, oldest first
    for e in events:
        if e.action == "privilege.grant" and e.succeeded and e.target_id and "approval_ref" not in e.attributes:
            unapproved[e.target_id].append(e)

    findings, not_evaluable = [], 0
    for e in events:
        if e.action not in ("resource.read", "resource.export") or not e.succeeded or e.actor_id not in unapproved:
            continue
        recent = [g for g in unapproved[e.actor_id] if g.occurred_at < e.occurred_at <= g.occurred_at + window]
        if not recent:
            continue
        sensitivity = e.attributes.get("sensitivity")
        if sensitivity is None:
            not_evaluable += 1
        elif sensitivity in IA005_SENSITIVE_LEVELS:
            minutes = int((e.occurred_at - recent[-1].occurred_at).total_seconds() // 60)
            findings.append(Finding(e.event_id, tuple(g.event_id for g in recent), (
                f"{e.actor_id} performed {e.action} on {sensitivity} resource {_name(e.target_id, 'resource')} "
                f"at {_at(e.occurred_at)}, {minutes} min after an unapproved permission grant.")))
    return RuleResult(findings, not_evaluable)


# --- registry ------------------------------------------------------------------

RULES: dict[str, Rule] = {rule.id: rule for rule in (
    Rule("IA-001", 1, "Privileged access granted without approval", "high", "medium", ("T1098",), {},
         "A privileged role granted with no approval reference.",
         _privileged_grant_without_approval),
    Rule("IA-002", 1, "Privileged sign-in without MFA", "medium", "high", (), {},
         "A privileged session opened without a second factor.",
         _privileged_sign_in_without_mfa),
    Rule("IA-003", 1, "Repeated failed sign-ins, then success", "high", "medium", ("T1110.001",),
         {"min_failures": IA003_MIN_FAILURES, "window_minutes": IA003_WINDOW_MINUTES},
         "The first success after at least 5 failed sign-ins in the preceding 30 minutes, "
         "with no approved credential reset in between.",
         _failed_sign_ins_then_success),
    Rule("IA-004", 1, "Activity by a disabled account", "high", "high", ("T1078",), {},
         "A successful action by an account after it was disabled and before it was enabled again.",
         _activity_by_disabled_account),
    Rule("IA-005", 1, "Unapproved permission change, then sensitive access", "high", "medium", ("T1098",),
         {"window_minutes": IA005_WINDOW_MINUTES, "sensitive_levels": list(IA005_SENSITIVE_LEVELS)},
         "Confidential or restricted data read or exported within 60 minutes of an unapproved grant to the reader.",
         _unapproved_grant_then_sensitive_access),
)}


def evaluate(events: Iterable[EventView], rules: Mapping[str, Rule] | None = None) -> dict[str, RuleResult]:
    """Run each rule over the events, after putting them in event-time order
    (ties broken by event id, which carries no meaning)."""
    ordered = sorted(events, key=lambda e: (e.occurred_at, e.event_id))
    return {rule_id: rule.detect(ordered) for rule_id, rule in (RULES if rules is None else rules).items()}
