from __future__ import annotations

import pytest

from app.database.session import AsyncSessionLocal, engine
from app.services.grc_engine import metrics_catalog


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()


async def test_fetch_returns_only_requested_namespaces(db):
    result = await metrics_catalog.fetch(db, ["vendor_risk"])
    assert list(result.keys()) == ["vendor_risk"]


async def test_fetch_silently_drops_unknown_namespaces(db):
    result = await metrics_catalog.fetch(db, ["vendor_risk", "not_a_real_namespace"])
    assert list(result.keys()) == ["vendor_risk"]


async def test_fetch_empty_list_returns_empty_dict(db):
    assert await metrics_catalog.fetch(db, []) == {}


async def test_fetch_deduplicates_repeated_namespaces(db):
    result = await metrics_catalog.fetch(db, ["risks", "risks", "risks"])
    assert list(result.keys()) == ["risks"]


async def test_trust_score_namespace_has_real_score(db):
    result = await metrics_catalog.fetch(db, ["trust_score"])
    assert 0 <= result["trust_score"]["trust_score"] <= 100


async def test_vendor_risk_namespace_carries_the_island_note(db):
    """The honesty note about vendors having no verified FK must survive
    the wrapper unchanged — this is the exact fact the reasoning layer
    depends on to avoid fabricating a vendor<->risk link."""
    result = await metrics_catalog.fetch(db, ["vendor_risk"])
    assert "island" in result["vendor_risk"]["note"].lower()


async def test_iam_statistics_has_privileged_without_mfa():
    assert "iam_statistics" in metrics_catalog.NAMESPACE_DESCRIPTIONS


def test_every_namespace_has_a_description():
    from app.services.grc_engine.schema_graph import METRIC_NAMESPACES

    for namespace in METRIC_NAMESPACES:
        assert namespace in metrics_catalog.NAMESPACE_DESCRIPTIONS, namespace


def test_describe_for_llm_is_nonempty_and_lists_all_namespaces():
    desc = metrics_catalog.describe_for_llm()
    for namespace in metrics_catalog.NAMESPACE_DESCRIPTIONS:
        assert namespace in desc
