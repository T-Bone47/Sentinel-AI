"""
The security-event contract, version 1.

Every source adapter must turn one source record into a `NormalizedEvent`,
or refuse it with a `ContractError`. Nothing reaches the event store any
other way. The prose specification is docs/EVENT_CONTRACT.md; this module is
the executable form and the two must agree.

Design rules that the code below enforces:
  * Strict, not forgiving. Unknown fields, unknown vocabulary and wrong types
    are errors. A detector must be able to rely on `mfa_used` being a bool.
  * Timestamps must say which timezone they are in. A naive timestamp is
    refused, never assumed to be UTC.
  * Error messages name the field and the rule. They never repeat the value
    that was submitted, because a refused record may contain anything.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

SCHEMA_VERSION = 1

# --- limits ---------------------------------------------------------------
MAX_RECORD_BYTES = 64 * 1024            # one source record, canonical form
MAX_BATCH_RECORDS = 500                 # records per API request
MAX_BODY_BYTES = 1024 * 1024            # API request body
MAX_FUTURE_SKEW_SECONDS = 24 * 3600     # events dated further ahead are refused
MAX_ID_CHARS = 512                      # actor / target identifiers (cloud ARNs are long)
MAX_SOURCE_EVENT_ID_CHARS = 200
MAX_ATTRIBUTE_CHARS = 500
MAX_DETAIL_CHARS = 300

SOURCE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$"

# --- vocabularies ---------------------------------------------------------
# Deliberately short. An action a source reports that has no entry here is
# stored as "other" with its native name kept in `source_action`.
Action = Literal[
    "auth.login",
    "account.create", "account.disable", "account.enable", "account.delete",
    "privilege.grant", "privilege.revoke",
    "credential.change",
    "resource.read", "resource.write", "resource.delete", "resource.export",
    "config.change",
    "other",
]
Outcome = Literal["success", "failure", "unknown"]
ActorType = Literal["user", "service", "role", "unknown"]
TargetType = Literal["principal", "application", "resource"]

# The only attributes an event may carry, and their types. Everything here is
# something the *source* asserted; nothing is inferred or enriched at ingest.
ATTRIBUTE_TYPES: dict[str, type] = {
    "mfa_used": bool,        # this authentication satisfied a second factor
    "privileged": bool,      # the session, account or granted role is administrative
    "auth_method": str,      # e.g. "password", "sso", "api_key"
    "approval_ref": str,     # change/approval ticket the source attached to the action
    "role": str,             # role, policy or group granted or revoked
    "sensitivity": str,      # classification of the target, from ATTRIBUTE_CHOICES
    "failure_reason": str,   # the source's reason code for a failed outcome
}
ATTRIBUTE_CHOICES: dict[str, frozenset[str]] = {
    "sensitivity": frozenset({"public", "internal", "confidential", "restricted"}),
}

# Refused in every text field: C0 and C1 control characters, and the invisible
# formatting characters (zero-width spaces and joiners, directional marks,
# embeddings, overrides and isolates, the byte-order mark) that can make an
# identifier display as something other than what it is.
_PRINTABLE = re.compile(r"^[^\x00-\x1f\x7f-\x9f؜​-‏‪-‮⁠-⁩﻿]+$")
_SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,39}$")


class ContractError(ValueError):
    """A record that cannot become an event. `reason` is a stable code;
    `detail` is safe to store and show (field names and rules only)."""

    def __init__(self, detail: str, reason: str = "invalid_record") -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail[:MAX_DETAIL_CHARS]


def _text(value: Any, limit: int) -> str:
    if not isinstance(value, str) or not value or len(value) > limit or not _PRINTABLE.match(value):
        raise ValueError(f"must be 1 to {limit} printable characters")
    return value


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Principal(_Strict):
    type: ActorType
    id: str

    @field_validator("id", mode="before")
    @classmethod
    def _id(cls, value: Any) -> str:
        return _text(value, MAX_ID_CHARS)


class Target(_Strict):
    type: TargetType
    id: str

    @field_validator("id", mode="before")
    @classmethod
    def _id(cls, value: Any) -> str:
        return _text(value, MAX_ID_CHARS)


class NormalizedEvent(_Strict):
    """One event, in the shape every adapter must produce. This is also the
    wire format of the `sentinel.native` adapter."""

    source_event_id: str            # the source's own id for this record
    occurred_at: datetime           # when it happened, per the source; stored as UTC
    actor: Principal | None = None  # who did it; absent when the source does not say
    target: Target | None = None    # what it was done to
    action: Action
    source_action: str              # the source's own name for the action; defaults to `action`
    outcome: Outcome
    src_ip: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _default_source_action(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("source_action") is None and isinstance(data.get("action"), str):
            return {**data, "source_action": data["action"]}
        return data

    @field_validator("source_event_id", mode="before")
    @classmethod
    def _source_event_id(cls, value: Any) -> str:
        return _text(value, MAX_SOURCE_EVENT_ID_CHARS)

    @field_validator("source_action", mode="before")
    @classmethod
    def _source_action(cls, value: Any) -> str:
        return _text(value, 200)

    @field_validator("occurred_at", mode="before")
    @classmethod
    def _occurred_at(cls, value: Any) -> datetime:
        try:
            parsed = datetime.fromisoformat(value) if isinstance(value, str) else None
        except ValueError:
            parsed = None
        if parsed is None:
            raise ValueError("must be an RFC 3339 timestamp string")
        if parsed.tzinfo is None:
            raise ValueError("must include a UTC offset (for example a trailing 'Z')")
        return parsed.astimezone(timezone.utc)

    @field_validator("src_ip", mode="before")
    @classmethod
    def _src_ip(cls, value: Any) -> str | None:
        if value is None:
            return None
        try:
            return str(ipaddress.ip_address(value)) if isinstance(value, str) else _not_an_ip()
        except ValueError:
            raise ValueError("must be an IPv4 or IPv6 address") from None

    @field_validator("attributes", mode="before")
    @classmethod
    def _attributes(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("must be an object")
        problems = []
        for key, item in value.items():
            expected = ATTRIBUTE_TYPES.get(key)
            if expected is None:
                shown = f"'{key}'" if isinstance(key, str) and _SAFE_NAME.match(key) else "an entry"
                problems.append(f"{shown} is not a known attribute")
            elif type(item) is not expected:      # exact: a bool is not accepted where an int is, or vice versa
                problems.append(f"'{key}' must be of type {expected.__name__}")
            elif expected is str and (not item or len(item) > MAX_ATTRIBUTE_CHARS or not _PRINTABLE.match(item)):
                problems.append(f"'{key}' must be 1 to {MAX_ATTRIBUTE_CHARS} printable characters")
            elif key in ATTRIBUTE_CHOICES and item not in ATTRIBUTE_CHOICES[key]:
                problems.append(f"'{key}' must be one of: {', '.join(sorted(ATTRIBUTE_CHOICES[key]))}")
        if problems:
            raise ValueError("; ".join(problems))
        return dict(value)


def _not_an_ip() -> str:
    raise ValueError("not an address")


def _describe(exc: ValidationError) -> str:
    """Field path and rule for every problem — never the offending input."""
    parts = []
    for error in exc.errors():
        path = ".".join(
            str(p) if isinstance(p, int) or _SAFE_NAME.match(str(p)) else "<field>" for p in error["loc"]
        )
        parts.append(f"{path or 'record'}: {error['msg']}")
    return "; ".join(parts)


def normalized(data: dict[str, Any]) -> NormalizedEvent:
    """Validate a dict in contract shape. The single gate every adapter uses."""
    try:
        return NormalizedEvent.model_validate(data)
    except ValidationError as exc:
        raise ContractError(_describe(exc)) from None


# --- identity and integrity -------------------------------------------------

def event_id_for(source_type: str, source_id: str, source_event_id: str) -> str:
    """The event's permanent id: SHA-256 over the three values that identify
    a record at its source, joined by a separator (0x1F) that none of them is
    allowed to contain. An identifier, not an integrity check."""
    return hashlib.sha256("\x1f".join((source_type, source_id, source_event_id)).encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    """One fixed text form for a JSON value: keys sorted, no insignificant
    whitespace, non-ASCII characters written literally. Two records that
    differ only in key order or spacing have the same canonical form.

    (This is our own definition, close to but not claimed to be RFC 8785.)
    """
    try:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        text.encode("utf-8")
    except (ValueError, TypeError, RecursionError):
        raise ContractError("record cannot be written as canonical UTF-8 JSON", reason="invalid_json") from None
    return text


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
