"""
The rule catalogue for GET /detections/rules: what the code runs, plus the
human-readable contract from research/rules/ when that folder is present.

The contracts live outside the backend package on purpose: they are research
artifacts, pre-registered before the code. A deployment that ships only the
backend still serves the catalogue, with "contract": null.
"""
from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.detections.rules import RULES, Rule

CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "research" / "rules"


@lru_cache(maxsize=None)
def load_contract(rule_id: str) -> dict[str, Any] | None:
    """Rule ids come from the code registry only, never from a request."""
    path = CONTRACTS_DIR / f"{rule_id}.toml"
    if not path.is_file():
        return None
    with path.open("rb") as handle:
        contract = tomllib.load(handle)
    contract.pop("test_vectors", None)        # the evaluation reports these
    return contract


def rule_out(rule: Rule) -> dict[str, Any]:
    return {"id": rule.id, "version": rule.version, "title": rule.title, "severity": rule.severity,
            "confidence": rule.confidence, "attack": list(rule.attack), "parameters": dict(rule.parameters),
            "logic": rule.logic, "contract": load_contract(rule.id)}


def catalogue() -> list[dict[str, Any]]:
    return [rule_out(rule) for rule in RULES.values()]
