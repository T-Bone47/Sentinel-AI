"""
Source adapters: one function per source format, each turning one source
record into a `NormalizedEvent` or raising `ContractError`.

An adapter only reads what the record says. It does not look anything up,
enrich, or guess. Fields it does not map are not lost: the whole source
record is stored next to the normalized event.

Adapters are versioned. The version is stored on every event
(`normalizer`, e.g. "aws.cloudtrail@1"), so a later change to a mapping can
never silently reinterpret events that were read under the old one.
"""
from __future__ import annotations

import ipaddress
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.events.contract import MAX_ATTRIBUTE_CHARS, ContractError, NormalizedEvent, normalized


@dataclass(frozen=True)
class Adapter:
    name: str
    version: int
    normalize: Callable[[dict[str, Any]], NormalizedEvent]

    @property
    def normalizer(self) -> str:
        return f"{self.name}@{self.version}"


# --- sentinel.native --------------------------------------------------------
# The contract itself as JSON. Used by the synthetic fixtures and by any
# producer that can emit the contract directly.

def _native(record: dict[str, Any]) -> NormalizedEvent:
    return normalized(record)


# --- aws.cloudtrail -----------------------------------------------------------
# One element of a CloudTrail log file's "Records" array (management events).
# Written from the published record structure. Run on 266 real records
# (Splunk attack_data: console sign-in failures, IAM DeletePolicy and
# DeleteGroup); the grant, revoke, account, credential and successful sign-in
# mappings have still seen hand-written records only. See
# docs/EVENT_CONTRACT.md, "Adapters".

_CT_ACTOR_TYPES = {
    "IAMUser": "user", "Root": "user", "FederatedUser": "user", "SAMLUser": "user",
    "WebIdentityUser": "user", "IdentityCenterUser": "user",
    "AssumedRole": "role", "Role": "role",
    "AWSService": "service",
}
_CT_ACTIONS: dict[str, str] = {
    "signin:ConsoleLogin": "auth.login",
    "iam:CreateUser": "account.create",
    "iam:DeleteUser": "account.delete",
    **dict.fromkeys(
        ("iam:AttachUserPolicy", "iam:AttachRolePolicy", "iam:AttachGroupPolicy", "iam:PutUserPolicy",
         "iam:PutRolePolicy", "iam:PutGroupPolicy", "iam:AddUserToGroup"),
        "privilege.grant",
    ),
    **dict.fromkeys(
        ("iam:DetachUserPolicy", "iam:DetachRolePolicy", "iam:DetachGroupPolicy", "iam:DeleteUserPolicy",
         "iam:DeleteRolePolicy", "iam:DeleteGroupPolicy", "iam:RemoveUserFromGroup"),
        "privilege.revoke",
    ),
    **dict.fromkeys(
        ("iam:CreateLoginProfile", "iam:UpdateLoginProfile", "iam:DeleteLoginProfile", "iam:ChangePassword",
         "iam:CreateAccessKey", "iam:UpdateAccessKey", "iam:DeleteAccessKey",
         "iam:EnableMFADevice", "iam:DeactivateMFADevice", "iam:CreateVirtualMFADevice",
         "iam:DeleteVirtualMFADevice"),
        "credential.change",
    ),
}
# Actions whose request names the principal being changed.
_CT_PRINCIPAL_ACTIONS = {"account.create", "account.delete", "privilege.grant", "privilege.revoke", "credential.change"}


def _short_text(value: Any) -> str | None:
    return value if isinstance(value, str) and 0 < len(value) <= MAX_ATTRIBUTE_CHARS else None


def _ip_or_none(value: Any) -> Any:
    """The value if it parses as an IP address, else None."""
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return None
    return value


def _cloudtrail(record: dict[str, Any]) -> NormalizedEvent:
    identity = record.get("userIdentity")
    if identity is not None and not isinstance(identity, dict):
        raise ContractError("userIdentity: must be an object")
    identity = identity or {}
    event_source, event_name = record.get("eventSource"), record.get("eventName")
    if not isinstance(event_source, str) or not isinstance(event_name, str):
        raise ContractError("eventSource, eventName: must be strings")

    source_action = f"{event_source.split('.', 1)[0]}:{event_name}"
    action = _CT_ACTIONS.get(source_action, "other")
    params = record.get("requestParameters") if isinstance(record.get("requestParameters"), dict) else {}
    attributes: dict[str, Any] = {}

    actor_id = next((identity[k] for k in ("arn", "principalId", "userName", "invokedBy") if _short_text(identity.get(k))), None)
    actor = {"type": _CT_ACTOR_TYPES.get(identity.get("type"), "unknown"), "id": actor_id} if actor_id else None
    if identity.get("type") == "Root":
        attributes["privileged"] = True

    target = None
    if action in _CT_PRINCIPAL_ACTIONS:
        principal = next((params[k] for k in ("userName", "roleName", "groupName") if _short_text(params.get(k))), None)
        if principal:
            target = {"type": "principal", "id": principal}
    if action in ("privilege.grant", "privilege.revoke"):
        in_group_change = event_name in ("AddUserToGroup", "RemoveUserFromGroup")
        role = _short_text(params.get("policyArn")) or _short_text(params.get("policyName")) \
            or (_short_text(params.get("groupName")) if in_group_change else None)
        if role:
            attributes["role"] = role

    # A record without an errorCode is a call that succeeded — except console
    # sign-in, which reports its result in responseElements instead.
    error_code = _short_text(record.get("errorCode"))
    if error_code:
        outcome = "failure"
        attributes["failure_reason"] = error_code
    elif source_action == "signin:ConsoleLogin":
        response = record.get("responseElements") if isinstance(record.get("responseElements"), dict) else {}
        outcome = {"Success": "success", "Failure": "failure"}.get(response.get("ConsoleLogin"), "unknown")
    else:
        outcome = "success"

    if source_action == "signin:ConsoleLogin":
        extra = record.get("additionalEventData") if isinstance(record.get("additionalEventData"), dict) else {}
        if extra.get("MFAUsed") in ("Yes", "No"):
            attributes["mfa_used"] = extra["MFAUsed"] == "Yes"

    # sourceIPAddress (below) is an address for calls from people and tools,
    # and a service host name (e.g. "cloudformation.amazonaws.com") for AWS itself.
    return normalized({
        "source_event_id": record.get("eventID"),
        "occurred_at": record.get("eventTime"),
        "actor": actor,
        "target": target,
        "action": action,
        "source_action": source_action,
        "outcome": outcome,
        "src_ip": _ip_or_none(record.get("sourceIPAddress")),
        "attributes": attributes,
    })


# --- entra.signin -------------------------------------------------------------
# One Microsoft Entra ID sign-in as Azure Monitor exports it: a record of
# category "SignInLogs", the sign-in itself in "properties". Run on one real
# file (30 failed password sign-ins of one user, Splunk attack_data); the
# success and MFA mappings have seen hand-written records only. Sign-in logs
# say nothing about the account's roles, so `privileged` is never set.

_ENTRA_MFA = {"singleFactorAuthentication": False, "multiFactorAuthentication": True}


def _entra_signin(record: dict[str, Any]) -> NormalizedEvent:
    if record.get("category") != "SignInLogs":
        raise ContractError("category: only 'SignInLogs' records are read")
    props = record.get("properties")
    if not isinstance(props, dict):
        raise ContractError("properties: must be an object")
    status = props.get("status")
    error_code = status.get("errorCode") if isinstance(status, dict) else None
    if type(error_code) is not int:
        raise ContractError("properties.status.errorCode: must be an integer")

    attributes: dict[str, Any] = {}
    if error_code:
        outcome = "failure"
        attributes["failure_reason"] = str(error_code)
    else:
        outcome = "success"
        # The strongest factor the sign-in needed. Only a success shows it was met.
        requirement = props.get("authenticationRequirement")
        if isinstance(requirement, str) and requirement in _ENTRA_MFA:
            attributes["mfa_used"] = _ENTRA_MFA[requirement]

    user = _short_text(props.get("userPrincipalName")) or _short_text(props.get("userId"))
    app = _short_text(props.get("appId"))
    return normalized({
        "source_event_id": props.get("id"),
        "occurred_at": props.get("createdDateTime"),
        "actor": {"type": "user", "id": user} if user else None,
        "target": {"type": "application", "id": app} if app else None,
        "action": "auth.login",
        "source_action": "SignInLogs",
        "outcome": outcome,
        "src_ip": _ip_or_none(props.get("ipAddress")),
        "attributes": attributes,
    })


# --- lanl.auth ----------------------------------------------------------------
# One line of LANL's auth.txt ("Comprehensive, Multi-Source Cyber-Security
# Events", 2015), mapped as research/M2_PREREGISTRATION.md §5 registers it. The
# record is {"line": <its number in auth.txt, from 1>, "text": <the line>}:
# lines carry no id of their own, and identical lines are separate events.

_LANL_ORIGIN = datetime(1970, 1, 1, tzinfo=timezone.utc)   # LANL's real start is undisclosed
_LANL_USER = re.compile(r"U\d+@")


def _lanl_auth(record: dict[str, Any]) -> NormalizedEvent:
    line, text = record.get("line"), record.get("text")
    if type(line) is not int or line < 1 or not isinstance(text, str):
        raise ContractError("line, text: must be a positive whole number and a string")
    fields = text.split(",")
    if len(fields) != 9 or not (fields[0].isascii() and fields[0].isdigit()):
        raise ContractError("text: must be 9 comma-separated fields, the first a whole number of seconds")
    seconds, src_user, _dst_user, _src_computer, dst_computer, _auth_type, _logon_type, orientation, result = fields
    return normalized({
        "source_event_id": str(line),
        "occurred_at": (_LANL_ORIGIN + timedelta(seconds=int(seconds))).isoformat(),
        "actor": {"type": "user" if _LANL_USER.match(src_user) else "unknown", "id": src_user},
        "target": {"type": "resource", "id": dst_computer},
        "action": "auth.login" if orientation == "LogOn" else "other",
        "source_action": orientation,
        "outcome": {"Success": "success", "Fail": "failure"}.get(result, "unknown"),
    })


ADAPTERS: dict[str, Adapter] = {
    adapter.name: adapter
    for adapter in (Adapter("sentinel.native", 1, _native), Adapter("aws.cloudtrail", 1, _cloudtrail),
                    Adapter("entra.signin", 1, _entra_signin), Adapter("lanl.auth", 1, _lanl_auth))
}
