"""
Shared test fixtures.

These are integration smoke tests, not unit tests: they run against the
real Postgres database with the real ingested datasets, because the thing
under test IS "real data reaches the API". A mocked repository would pass
while the demo was broken.

Requires: Postgres up, `alembic upgrade head` applied, and
`python -m app.ingestion.run` completed at least once.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Tests must never depend on a live NVIDIA key or make real provider calls.
# Keep the LLM disabled for the whole test session unless a test explicitly
# opts in by patching settings.
os.environ.setdefault("NVIDIA_API_KEY", "")
os.environ.setdefault("COPILOT_LLM_ENABLED", "false")
# The app fails closed (ENVIRONMENT defaults to production and rejects demo
# secrets). The test suite runs against a disposable local database.
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402

DATASETS_DIR = ROOT / "datasets"

# Expected row counts, taken from the real CSVs (line count minus header).
EXPECTED_COUNTS = {
    "employees": 500,
    "devices": 500,
    "cloud_assets": 300,
    "applications": 100,
    "vendors": 100,
    "policies": 100,
    "controls": 300,
    "risks": 300,
    "evidence": 500,
    "findings": 300,
    "reports": 100,
    "personal_data_inventory": 300,
    "consent_records": 500,
    "iam_records": 500,
    "audit_logs": 10000,
}

DEMO_PASSWORD = os.environ.get("SENTINEL_DEMO_PASSWORD", "Sentinel@123")


@pytest.fixture(scope="session")
def sync_engine():
    return create_engine(settings.database_url_sync, future=True)


@pytest.fixture
def db_session(sync_engine):
    with Session(sync_engine) as session:
        yield session


@pytest.fixture
async def unauth_client():
    from httpx import ASGITransport, AsyncClient
    from app.database.session import engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await engine.dispose()


@pytest.fixture
async def client(unauth_client):
    """
    httpx client bound directly to the ASGI app, automatically authenticated.
    """
    response = await unauth_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sentinel.ai", "password": DEMO_PASSWORD},
    )
    if response.status_code == 200:
        token = response.json()["data"]["access_token"]
        unauth_client.headers["Authorization"] = f"Bearer {token}"
    yield unauth_client


@pytest.fixture
async def auth_headers(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sentinel.ai", "password": DEMO_PASSWORD},
    )
    if response.status_code != 200:
        pytest.skip("demo users not seeded — run scripts/seed_users.py")
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
