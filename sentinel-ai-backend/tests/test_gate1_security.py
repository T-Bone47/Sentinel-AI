"""
Gate 1 — authentication, authorization and session isolation.

Negative tests first: every case here describes something a caller must NOT
be able to do. Expectations are written out by hand rather than derived from
the permission matrix, so a wrong matrix entry fails a test instead of
silently agreeing with itself.

Scope note: Sentinel is single-tenant. These tests prove role and per-user
boundaries on the enumerated cases below; they do not claim tenant isolation.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from sqlalchemy import inspect, select, text

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models import Device, IAMRecord, User
from app.models.enums import UserRole
from tests.conftest import DEMO_PASSWORD

API = "/api/v1"
ROLE_EMAIL = {
    "admin": "admin@sentinel.ai",
    "compliance": "compliance@sentinel.ai",
    "security": "security@sentinel.ai",
    "auditor": "auditor@sentinel.ai",
    "employee": "employee@sentinel.ai",
}
POST_BODIES = {
    "/copilot/query": {"question": "Are we audit ready?"},
    "/ai/query": {"question": "Are we audit ready?"},
    "/intelligence/policy/analyze": {
        "text": "All privileged accounts must use multi-factor authentication."
    },
}

# Routes that are deliberately reachable without a permission check.
PUBLIC = {f"{API}/health", f"{API}/auth/login", f"{API}/auth/refresh"}
AUTHENTICATED_ONLY = {f"{API}/auth/me", f"{API}/auth/logout"}


async def _login(client, email: str, password: str = DEMO_PASSWORD) -> dict:
    response = await client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


_TOKENS: dict[str, str] = {}


async def _as(client, role: str) -> dict[str, str]:
    """Headers for a seeded role. Cached: these sessions are never logged out."""
    if role not in _TOKENS:
        _TOKENS[role] = (await _login(client, ROLE_EMAIL[role]))["access_token"]
    return _bearer(_TOKENS[role])


async def _call(client, role: str, method: str, path: str):
    headers = await _as(client, role)
    if method == "POST":
        return await client.post(f"{API}{path}", json=POST_BODIES[path], headers=headers)
    return await client.get(f"{API}{path}", headers=headers)


@pytest.fixture(autouse=True)
def _reset_login_throttle():
    """Failed-login counters are process-wide; never let one test lock another out."""
    from app.core import login_throttle as lt

    counters = [t for t in (lt.throttle, getattr(lt, "address_throttle", None)) if t is not None]
    for counter in counters:
        counter.reset()
    yield
    for counter in counters:
        counter.reset()


@pytest.fixture
def temp_user(sync_engine):
    """Factory for throwaway accounts, removed (with their sessions) afterwards."""
    from sqlalchemy.orm import Session

    created: list[str] = []
    password = "Temp-" + uuid.uuid4().hex

    def make(role: UserRole = UserRole.EMPLOYEE, employee_id: str | None = None) -> tuple[str, str]:
        email = f"gate1-{uuid.uuid4().hex[:12]}@example.com"
        with Session(sync_engine) as session:
            session.add(
                User(
                    email=email,
                    full_name="Gate 1 temp user",
                    role=role,
                    hashed_password=hash_password(password),
                    is_active=True,
                    employee_id=employee_id,
                )
            )
            session.commit()
        created.append(email)
        return email, password

    yield make

    with Session(sync_engine) as session:
        for email in created:
            user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if user is None:
                continue
            if inspect(sync_engine).has_table("auth_sessions"):
                session.execute(text("DELETE FROM auth_sessions WHERE user_id = :uid"), {"uid": user.id})
            session.delete(user)
        session.commit()


# --------------------------------------------------------------------------
# 1. Every route is guarded (default deny)
# --------------------------------------------------------------------------

def _operations() -> list[tuple[str, str]]:
    """Every (METHOD, path) the app really serves, read from its OpenAPI schema.

    Deliberately not `app.routes`: this FastAPI version keeps included routers
    as nested wrappers there, so walking it silently finds almost nothing.
    """
    return [
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith(API)
        for method in operations
    ]


def _concrete(path: str) -> str:
    return path.replace("{", "").replace("}", "")


def test_route_inventory_is_not_vacuous():
    paths = {path for _, path in _operations()}
    assert len(paths) >= 40
    assert {f"{API}/risks", f"{API}/ai/query", f"{API}/organization/graph"} <= paths


async def test_every_route_is_denied_when_the_matrix_grants_nothing(unauth_client, monkeypatch):
    """Default deny, proven behaviourally: with an empty matrix even an admin
    gets 403 everywhere. A route added without a permission guard would
    answer 200/404/422 here and fail this test."""
    from app.core import permissions

    headers = await _as(unauth_client, "admin")
    monkeypatch.setattr(permissions, "MATRIX", {})
    not_denied = []
    for method, path in _operations():
        if path in PUBLIC | AUTHENTICATED_ONLY:
            continue
        response = await unauth_client.request(method, _concrete(path), json={}, headers=headers)
        if response.status_code != 403:
            not_denied.append(f"{method} {path} -> {response.status_code}")
    assert not_denied == []


def test_unknown_role_resource_action_combinations_are_denied():
    from app.core.permissions import is_allowed

    assert is_allowed(UserRole.ADMIN, "risks", "read") is True
    assert is_allowed(UserRole.ADMIN, "risks", "delete") is False          # action never granted
    assert is_allowed(UserRole.ADMIN, "no-such-resource", "read") is False  # resource not in matrix
    assert is_allowed(UserRole.EMPLOYEE, "risks", "read") is False


async def test_anonymous_requests_get_401_on_every_guarded_route(unauth_client):
    leaked = []
    for method, path in _operations():
        if path in PUBLIC:
            continue
        response = await unauth_client.request(method, _concrete(path), json={})
        if response.status_code != 401:
            leaked.append(f"{method} {path} -> {response.status_code}")
    assert leaked == []


# --------------------------------------------------------------------------
# 2. Role matrix — hand-written expectations
# --------------------------------------------------------------------------

MATRIX_CASES = [
    # employee: self-service only, everything else denied
    *[("employee", "GET", p, 403) for p in (
        "/risks", "/controls", "/findings", "/evidence", "/reports", "/vendors",
        "/cloud-assets", "/applications", "/audit-logs", "/dpdp/personal-data",
        "/dashboard", "/frameworks", "/frameworks/ISO 27001", "/organization/graph",
        "/intelligence/trust", "/intelligence/risks", "/intelligence/evidence",
        "/intelligence/monitoring/anomalies", "/intelligence/orchestrator/summary",
        "/copilot/suggestions", "/risks/RISK-0001", "/policies/POL-0001",
        "/applications/APP-0001", "/audit-logs/LOG-0001",
    )],
    *[("employee", "POST", p, 403) for p in POST_BODIES],
    *[("employee", "GET", p, 200) for p in ("/policies", "/employees", "/devices", "/iam", "/dpdp/consents")],
    # auditor (external): governance, risk and asset inventory — no per-person records
    *[("auditor", "GET", p, 403) for p in (
        "/employees", "/employees/EMP0001", "/devices", "/iam", "/audit-logs", "/dpdp/consents",
        "/intelligence/monitoring/anomalies", "/intelligence/monitoring/metrics",
        "/intelligence/orchestrator/summary",
        "/organization/graph", "/organization/graph?scope=org",
        "/organization/graph?scope=governance&include_activity=true",
    )],
    *[("auditor", "GET", p, 200) for p in (
        "/risks", "/controls", "/evidence", "/findings", "/policies", "/reports", "/vendors",
        "/cloud-assets", "/applications", "/dpdp/personal-data", "/dashboard", "/frameworks",
        "/intelligence/trust", "/intelligence/risks", "/intelligence/evidence",
        "/organization/graph?scope=governance", "/organization/graph?aggregated=true",
        "/copilot/suggestions",
    )],
    ("auditor", "POST", "/copilot/query", 200),
    # security analyst: everything operational, but not row-level consent records
    *[("security", "GET", p, 403) for p in (
        "/dpdp/consents", "/organization/graph?include_activity=true",
    )],
    *[("security", "GET", p, 200) for p in (
        "/employees", "/employees/EMP0001", "/devices", "/iam", "/audit-logs", "/risks",
        "/organization/graph", "/intelligence/monitoring/anomalies", "/dpdp/personal-data",
    )],
    # compliance officer and admin: full read
    *[(role, "GET", p, 200) for role in ("compliance", "admin") for p in (
        "/employees", "/iam", "/audit-logs", "/dpdp/consents", "/risks",
        "/organization/graph?include_activity=true&include_privacy=true&include_vendors=true",
        "/intelligence/monitoring/anomalies",
    )],
]


@pytest.mark.parametrize("role,method,path,expected", MATRIX_CASES)
async def test_role_matrix(unauth_client, role, method, path, expected):
    response = await _call(unauth_client, role, method, path)
    assert response.status_code == expected, f"{role} {method} {path}: {response.text[:200]}"


async def test_forbidden_response_does_not_leak_data(unauth_client):
    response = await _call(unauth_client, "employee", "GET", "/risks")
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "http_403"


async def test_me_reports_the_resources_the_role_can_read(unauth_client):
    headers = await _as(unauth_client, "employee")
    permissions = (await unauth_client.get(f"{API}/auth/me", headers=headers)).json()["data"]["permissions"]
    assert "policies" in permissions
    assert "risks" not in permissions


# --------------------------------------------------------------------------
# 3. Object-level scoping — an employee sees only their own records
# --------------------------------------------------------------------------

@pytest.fixture
def own_employee_id(db_session) -> str:
    user = db_session.execute(select(User).where(User.email == ROLE_EMAIL["employee"])).scalar_one()
    assert user.employee_id, "seed_users.py must link the employee account to an Employee row"
    return user.employee_id


@pytest.mark.parametrize("path", ["/employees", "/devices", "/iam", "/dpdp/consents"])
async def test_employee_lists_contain_only_own_rows(unauth_client, own_employee_id, path):
    headers = await _as(unauth_client, "employee")
    body = (await unauth_client.get(f"{API}{path}?page_size=200", headers=headers)).json()
    assert body["meta"]["total"] == len(body["data"])
    assert all(row["employee_id"] == own_employee_id for row in body["data"])


@pytest.mark.parametrize("query", [
    "employee_id=EMP0002", "manager_id=EMP0231", "department=Engineering", "search=a",
    "employee_id=EMP0002&employee_id=EMP0003",
])
@pytest.mark.parametrize("path", ["/employees", "/iam", "/devices", "/dpdp/consents"])
async def test_employee_cannot_widen_scope_with_filters(unauth_client, own_employee_id, path, query):
    headers = await _as(unauth_client, "employee")
    body = (await unauth_client.get(f"{API}{path}?{query}&page_size=200", headers=headers)).json()
    assert all(row["employee_id"] == own_employee_id for row in body["data"])


async def test_employee_can_read_own_profile_but_not_a_colleagues(unauth_client, own_employee_id):
    headers = await _as(unauth_client, "employee")
    own = await unauth_client.get(f"{API}/employees/{own_employee_id}", headers=headers)
    assert own.status_code == 200
    assert own.json()["data"]["employee_id"] == own_employee_id
    # A direct-report list would expose other people's records.
    assert own.json()["data"]["direct_reports"] == []

    other = await unauth_client.get(f"{API}/employees/EMP0002", headers=headers)
    assert other.status_code == 404  # 404, not 403: do not confirm the record exists


async def test_employee_cannot_read_another_persons_device_or_iam_record(
    unauth_client, db_session, own_employee_id
):
    headers = await _as(unauth_client, "employee")
    device = db_session.execute(
        select(Device.device_id).where(Device.employee_id != own_employee_id).limit(1)
    ).scalar_one()
    iam = db_session.execute(
        select(IAMRecord.iam_user_id).where(IAMRecord.employee_id != own_employee_id).limit(1)
    ).scalar_one()
    assert (await unauth_client.get(f"{API}/devices/{device}", headers=headers)).status_code == 404
    assert (await unauth_client.get(f"{API}/iam/{iam}", headers=headers)).status_code == 404


async def test_employee_account_without_a_linked_record_sees_nothing(unauth_client, temp_user):
    email, password = temp_user(UserRole.EMPLOYEE, employee_id=None)
    headers = _bearer((await _login(unauth_client, email, password))["access_token"])
    for path in ("/employees", "/devices", "/iam", "/dpdp/consents"):
        body = (await unauth_client.get(f"{API}{path}", headers=headers)).json()
        assert body["data"] == [] and body["meta"]["total"] == 0, path
    assert (await unauth_client.get(f"{API}/employees/EMP0001", headers=headers)).status_code == 404


# --------------------------------------------------------------------------
# 4. Field-level withholding on compound endpoints
# --------------------------------------------------------------------------

async def _an_application_with_consents(client) -> str:
    headers = await _as(client, "admin")
    row = (await client.get(f"{API}/dpdp/consents?page_size=1", headers=headers)).json()["data"][0]
    return row["application_id"]


async def test_application_detail_withholds_consent_records_from_security_analyst(unauth_client):
    app_id = await _an_application_with_consents(unauth_client)

    full = (await _call(unauth_client, "admin", "GET", f"/applications/{app_id}")).json()["data"]
    assert full["consent_records"], "fixture application should have consent rows"
    assert full["withheld"] == []

    limited = (await _call(unauth_client, "security", "GET", f"/applications/{app_id}")).json()["data"]
    assert limited["consent_records"] == []
    assert limited["withheld"] == ["consent_records"]
    assert limited["recent_activity"] == full["recent_activity"]  # still permitted


async def test_application_detail_withholds_activity_and_consents_from_auditor(unauth_client):
    app_id = await _an_application_with_consents(unauth_client)
    data = (await _call(unauth_client, "auditor", "GET", f"/applications/{app_id}")).json()["data"]
    assert data["consent_records"] == [] and data["recent_activity"] == []
    assert sorted(data["withheld"]) == ["consent_records", "recent_activity"]


async def test_dashboard_withholds_per_person_audit_rows_from_auditor(unauth_client):
    admin = (await _call(unauth_client, "admin", "GET", "/dashboard")).json()["data"]
    assert admin["recent_audit_activity"]["recent"], "admin should see recent audit rows"

    auditor = (await _call(unauth_client, "auditor", "GET", "/dashboard")).json()["data"]
    assert auditor["recent_audit_activity"]["recent"] == []
    # Aggregates are not personal data and stay visible.
    assert auditor["recent_audit_activity"]["total_failures"] == admin["recent_audit_activity"]["total_failures"]


# --------------------------------------------------------------------------
# 5. AI query engine honours the same matrix
# --------------------------------------------------------------------------

@pytest.fixture
async def db():
    from app.database.session import AsyncSessionLocal, engine

    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()


async def test_general_engine_refuses_row_query_on_a_table_the_caller_cannot_read(db):
    from app.services.grc_engine import reasoning_service
    from app.services.grc_engine.query_dsl import QueryPlan, ReasoningPlan

    plan = ReasoningPlan(question_type="list", row_query=QueryPlan(base_table="consent_records", limit=5))
    readable = frozenset({"risks", "controls"})
    result = await reasoning_service._run_general_engine(db, "List consents", plan, readable_tables=readable)
    assert result.engine == "access_denied_v1"
    assert result.evidence == []
    assert result.llm_used is False


async def test_general_engine_refuses_join_through_a_table_the_caller_cannot_read(db):
    from app.services.grc_engine import reasoning_service
    from app.services.grc_engine.query_dsl import JoinStep, QueryPlan, ReasoningPlan

    plan = ReasoningPlan(
        question_type="list",
        row_query=QueryPlan(
            base_table="applications",
            joins=[JoinStep(from_table="applications", from_column="application_id",
                            to_table="consent_records", to_column="application_id")],
            limit=5,
        ),
    )
    readable = frozenset({"applications"})
    result = await reasoning_service._run_general_engine(db, "Apps with consents", plan, readable_tables=readable)
    assert result.engine == "access_denied_v1"
    assert result.evidence == []


async def test_general_engine_drops_metric_namespaces_built_from_unreadable_rows(db):
    from app.services.grc_engine import reasoning_service
    from app.services.grc_engine.query_dsl import ReasoningPlan

    plan = ReasoningPlan(question_type="analytical", metrics_needed=["recent_audit_activity", "vendor_risk"])
    readable = frozenset({"vendors"})
    result = await reasoning_service._run_general_engine(db, "Activity?", plan, readable_tables=readable)
    assert "recent_audit_activity" not in result.metrics
    assert "vendor_risk" in result.metrics


async def test_ai_query_passes_the_callers_readable_tables_to_the_engine(unauth_client, monkeypatch):
    from app.services.grc_engine import reasoning_service

    seen: dict[str, frozenset] = {}

    async def spy(db, question, **kwargs):
        seen[question] = kwargs["readable_tables"]
        return reasoning_service.GeneralAnswer(question=question, question_type="factual", answer="ok")

    monkeypatch.setattr(reasoning_service, "answer", spy)
    for role in ("security", "auditor", "admin"):
        response = await unauth_client.post(
            f"{API}/ai/query", json={"question": role}, headers=await _as(unauth_client, role)
        )
        assert response.status_code == 200

    assert "consent_records" not in seen["security"] and "audit_logs" in seen["security"]
    assert not {"employees", "iam_records", "audit_logs", "consent_records"} & seen["auditor"]
    assert {"consent_records", "audit_logs", "employees"} <= seen["admin"]


# --------------------------------------------------------------------------
# 6. Sessions — short-lived, rotating, revocable
# --------------------------------------------------------------------------

def _forge(claims: dict, key: str | None = None) -> str:
    return jwt.encode(claims, key or settings.secret_key, algorithm=settings.algorithm)


async def test_access_token_is_short_lived(unauth_client, temp_user):
    email, password = temp_user()
    token = (await _login(unauth_client, email, password))["access_token"]
    lifetime = jwt.get_unverified_claims(token)["exp"] - time.time()
    assert lifetime <= 15 * 60 + 5


async def test_logout_revokes_the_access_token_immediately(unauth_client, temp_user):
    email, password = temp_user()
    tokens = await _login(unauth_client, email, password)
    headers = _bearer(tokens["access_token"])
    assert (await unauth_client.get(f"{API}/auth/me", headers=headers)).status_code == 200

    assert (await unauth_client.post(f"{API}/auth/logout", headers=headers)).status_code == 200
    assert (await unauth_client.get(f"{API}/auth/me", headers=headers)).status_code == 401


async def test_logout_revokes_the_refresh_token(unauth_client, temp_user):
    email, password = temp_user()
    tokens = await _login(unauth_client, email, password)
    await unauth_client.post(f"{API}/auth/logout", headers=_bearer(tokens["access_token"]))
    response = await unauth_client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 401


async def test_logout_of_one_session_leaves_the_users_other_session_alive(unauth_client, temp_user):
    email, password = temp_user()
    first = await _login(unauth_client, email, password)
    second = await _login(unauth_client, email, password)
    await unauth_client.post(f"{API}/auth/logout", headers=_bearer(first["access_token"]))
    assert (await unauth_client.get(f"{API}/auth/me", headers=_bearer(second["access_token"]))).status_code == 200


async def test_refresh_rotates_the_refresh_token(unauth_client, temp_user):
    email, password = temp_user()
    tokens = await _login(unauth_client, email, password)
    rotated = (
        await unauth_client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    ).json()["data"]
    assert rotated["refresh_token"] != tokens["refresh_token"]
    assert (await unauth_client.get(f"{API}/auth/me", headers=_bearer(rotated["access_token"]))).status_code == 200
    again = await unauth_client.post(f"{API}/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
    assert again.status_code == 200


async def test_replayed_refresh_token_is_rejected_and_kills_the_session(unauth_client, temp_user):
    email, password = temp_user()
    tokens = await _login(unauth_client, email, password)
    rotated = (
        await unauth_client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    ).json()["data"]

    replay = await unauth_client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    # Reuse of a rotated token means it was stolen: the whole session dies.
    assert (await unauth_client.get(f"{API}/auth/me", headers=_bearer(rotated["access_token"]))).status_code == 401
    latest = await unauth_client.post(f"{API}/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
    assert latest.status_code == 401


async def test_expired_access_token_is_rejected(unauth_client, temp_user):
    email, password = temp_user()
    claims = jwt.get_unverified_claims((await _login(unauth_client, email, password))["access_token"])
    claims["exp"] = int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())
    assert (await unauth_client.get(f"{API}/auth/me", headers=_bearer(_forge(claims)))).status_code == 401


async def test_token_signed_with_another_key_is_rejected(unauth_client, temp_user):
    email, password = temp_user()
    claims = jwt.get_unverified_claims((await _login(unauth_client, email, password))["access_token"])
    forged = _forge({**claims, "role": "admin"}, key="attacker-controlled-key")
    assert (await unauth_client.get(f"{API}/auth/me", headers=_bearer(forged))).status_code == 401


async def test_validly_signed_token_without_a_live_session_is_rejected(unauth_client):
    """Knowing the signing key alone must not be enough: a session row has to exist."""
    exp = int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
    base = {"sub": ROLE_EMAIL["admin"], "role": "admin", "type": "access", "exp": exp}
    for claims in (base, {**base, "sid": str(uuid.uuid4())}):
        response = await unauth_client.get(f"{API}/risks", headers=_bearer(_forge(claims)))
        assert response.status_code == 401, claims


async def test_role_claim_in_the_token_is_not_trusted(unauth_client, temp_user):
    """Authorization reads the role from the database, not from the token."""
    email, password = temp_user(UserRole.EMPLOYEE)
    claims = jwt.get_unverified_claims((await _login(unauth_client, email, password))["access_token"])
    escalated = _forge({**claims, "role": "admin"})
    assert (await unauth_client.get(f"{API}/risks", headers=_bearer(escalated))).status_code == 403


async def test_disabling_a_user_invalidates_their_tokens_immediately(unauth_client, temp_user, sync_engine):
    from sqlalchemy.orm import Session

    email, password = temp_user()
    tokens = await _login(unauth_client, email, password)
    with Session(sync_engine) as session:
        session.execute(select(User).where(User.email == email)).scalar_one().is_active = False
        session.commit()

    assert (await unauth_client.get(f"{API}/auth/me", headers=_bearer(tokens["access_token"]))).status_code == 401
    refresh = await unauth_client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401


# --------------------------------------------------------------------------
# 7. Brute-force control
# --------------------------------------------------------------------------

async def _bad_login(client, email: str):
    return await client.post(f"{API}/auth/login", json={"email": email, "password": "wrong-password"})


async def test_a_disabled_account_answers_like_a_wrong_password(unauth_client, temp_user, sync_engine):
    """R8: a different answer after the right password would confirm the password."""
    from sqlalchemy.orm import Session

    email, password = temp_user()
    with Session(sync_engine) as session:
        session.execute(select(User).where(User.email == email)).scalar_one().is_active = False
        session.commit()
    right = await unauth_client.post(f"{API}/auth/login", json={"email": email, "password": password})
    wrong = await _bad_login(unauth_client, email)
    assert right.status_code == wrong.status_code == 401
    assert right.json() == wrong.json()


async def test_failures_from_one_address_lock_that_address(unauth_client, temp_user):
    """R6: guessing spread across many accounts from one address is throttled too."""
    from app.core.login_throttle import MAX_ADDRESS_FAILURES

    email, password = temp_user()
    for i in range(MAX_ADDRESS_FAILURES):
        assert (await _bad_login(unauth_client, f"nobody-{i}@example.com")).status_code == 401
    blocked = await unauth_client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert blocked.status_code == 429


def test_one_user_cannot_push_out_another_users_conversations():
    """R10: each user has their own cap inside the shared bound."""
    from app.services.conversation_store import ConversationStore

    store = ConversationStore(max_entries=500, max_per_user=20)
    store.put("victim", "c-1", "kept")
    for i in range(600):
        store.put("noisy", f"c-{i}", "x")
    assert store.get("victim", "c-1") == "kept"
    assert sum(store.get("noisy", f"c-{i}") is not None for i in range(600)) == 20


def test_api_docs_are_not_served_outside_development(monkeypatch):
    """R7: the schema maps every route; publish it only where developers need it."""
    from app.core.config import settings
    from app.main import create_app

    monkeypatch.setattr(settings, "environment", "production")
    app = create_app()
    assert (app.openapi_url, app.docs_url, app.redoc_url) == (None, None, None)


async def test_repeated_failed_logins_lock_the_account_even_for_the_right_password(unauth_client, temp_user):
    email, password = temp_user()
    for _ in range(5):
        assert (await _bad_login(unauth_client, email)).status_code == 401

    locked = await unauth_client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0


async def test_lockout_behaves_the_same_for_unknown_accounts(unauth_client):
    """Otherwise the lockout itself reveals which email addresses exist."""
    email = f"nobody-{uuid.uuid4().hex[:8]}@example.com"
    statuses = [(await _bad_login(unauth_client, email)).status_code for _ in range(6)]
    assert statuses == [401] * 5 + [429]


async def test_lockout_is_per_account(unauth_client, temp_user):
    victim, _ = temp_user()
    other, other_password = temp_user()
    for _ in range(6):
        await _bad_login(unauth_client, victim)
    assert (await _login(unauth_client, other, other_password))["access_token"]


async def test_successful_login_resets_the_failure_count(unauth_client, temp_user):
    email, password = temp_user()
    for _ in range(2):
        for _ in range(4):
            await _bad_login(unauth_client, email)
        assert (await _login(unauth_client, email, password))["access_token"]


# --------------------------------------------------------------------------
# 8. Startup configuration validation
# --------------------------------------------------------------------------

STRONG_SECRET = "x9" * 24
SAFE_DB = "postgresql+asyncpg://svc_sentinel:a-real-password@db.internal:5432/sentinel"


def _settings(**overrides):
    from app.core.config import Settings

    base = dict(
        environment="production", secret_key=STRONG_SECRET, debug=False,
        database_url=SAFE_DB, database_url_sync=SAFE_DB.replace("+asyncpg", "+psycopg"),
    )
    return Settings(_env_file=None, **{**base, **overrides})


def test_production_starts_with_safe_configuration():
    assert _settings().environment == "production"


@pytest.mark.parametrize("overrides", [
    {"secret_key": "dev-only-secret-change-me"},
    {"secret_key": "short"},
    {"debug": True},
    {"database_url": "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel_ai"},
    {"database_url_sync": "postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel_ai"},
    {"environment": "staging", "secret_key": "dev-only-secret-change-me"},
    {"environment": "prod-eu", "secret_key": "dev-only-secret-change-me"},  # unknown name is not "dev"
])
def test_unsafe_configuration_refuses_to_start_outside_development(overrides):
    with pytest.raises(ValueError):
        _settings(**overrides)


def test_environment_defaults_to_production_so_forgetting_it_fails_closed(monkeypatch):
    from app.core.config import Settings

    for name in ("ENVIRONMENT", "SECRET_KEY", "DEBUG"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_development_keeps_working_with_local_defaults():
    from app.core.config import Settings

    dev = Settings(_env_file=None, environment="development", secret_key="dev-only-secret-change-me")
    assert "http://localhost:5173" in dev.allowed_origins


def test_localhost_origins_are_not_allowed_in_production():
    prod = _settings(frontend_url="https://sentinel.example.com")
    assert prod.allowed_origins == ["https://sentinel.example.com"]


def test_seed_script_refuses_the_public_demo_password_outside_development(monkeypatch):
    import sys

    from scripts import seed_users

    monkeypatch.setattr(seed_users.settings, "environment", "production")
    monkeypatch.setattr(sys, "argv", ["seed_users.py"])
    assert seed_users.main() != 0


# --------------------------------------------------------------------------
# 9. AI conversation memory is private, expiring and deletable
# --------------------------------------------------------------------------

def test_conversation_store_scopes_by_user_and_expires():
    from app.services.conversation_store import ConversationStore

    now = [1000.0]
    store = ConversationStore(ttl_seconds=60, max_entries=2, clock=lambda: now[0])
    store.put("user-a", "c1", "a's context")

    assert store.get("user-a", "c1") == "a's context"
    assert store.get("user-b", "c1") is None            # same id, different user
    assert store.delete("user-b", "c1") is False        # cannot delete someone else's
    assert store.get("user-a", "c1") == "a's context"

    now[0] += 61
    assert store.get("user-a", "c1") is None            # expired

    store.put("user-a", "c1", "1")
    store.put("user-a", "c2", "2")
    store.put("user-a", "c3", "3")
    assert store.get("user-a", "c1") is None            # bounded: oldest evicted
    assert store.delete("user-a", "c3") is True
    assert store.get("user-a", "c3") is None


async def test_one_user_cannot_read_anothers_conversation_by_guessing_its_id(unauth_client, monkeypatch):
    from app.services.grc_engine import reasoning_service

    contexts: list[tuple[str, str | None]] = []

    async def spy(db, question, *, conversation_context=None, **kwargs):
        contexts.append((question, conversation_context))
        return reasoning_service.GeneralAnswer(question=question, question_type="factual", answer=f"answer to {question}")

    monkeypatch.setattr(reasoning_service, "answer", spy)
    conversation_id = uuid.uuid4().hex
    admin, security = await _as(unauth_client, "admin"), await _as(unauth_client, "security")

    async def ask(headers, question):
        response = await unauth_client.post(
            f"{API}/ai/query", json={"question": question, "conversation_id": conversation_id}, headers=headers
        )
        assert response.status_code == 200
        return response.json()["data"]

    await ask(admin, "admin secret question")
    await ask(security, "security follow-up")     # same conversation_id, different user
    await ask(admin, "admin follow-up")

    by_question = dict(contexts)
    assert by_question["security follow-up"] is None
    assert "admin secret question" in by_question["admin follow-up"]
    assert "security follow-up" not in by_question["admin follow-up"]   # and no cross-user write


async def test_server_issues_a_conversation_id_and_owner_can_delete_it(unauth_client, monkeypatch):
    from app.services.grc_engine import reasoning_service

    contexts: list[str | None] = []

    async def spy(db, question, *, conversation_context=None, **kwargs):
        contexts.append(conversation_context)
        return reasoning_service.GeneralAnswer(question=question, question_type="factual", answer="ok")

    monkeypatch.setattr(reasoning_service, "answer", spy)
    admin, security = await _as(unauth_client, "admin"), await _as(unauth_client, "security")

    first = (await unauth_client.post(f"{API}/ai/query", json={"question": "q1"}, headers=admin)).json()["data"]
    conversation_id = first["conversation_id"]
    assert len(conversation_id) >= 32

    other = await unauth_client.delete(f"{API}/ai/conversations/{conversation_id}", headers=security)
    assert other.status_code == 404
    mine = await unauth_client.delete(f"{API}/ai/conversations/{conversation_id}", headers=admin)
    assert mine.status_code == 200

    await unauth_client.post(
        f"{API}/ai/query", json={"question": "q2", "conversation_id": conversation_id}, headers=admin
    )
    assert contexts[-1] is None


# --------------------------------------------------------------------------
# 10. Error payloads
# --------------------------------------------------------------------------

async def test_validation_error_does_not_echo_submitted_secrets(unauth_client):
    secret = "Sup3r-Secret-" + uuid.uuid4().hex
    response = await unauth_client.post(f"{API}/auth/login", json={"password": secret})
    assert response.status_code == 422
    assert secret not in response.text


async def test_login_failure_message_is_identical_for_unknown_user_and_wrong_password(unauth_client, temp_user):
    email, _ = temp_user()
    known = await _bad_login(unauth_client, email)
    unknown = await _bad_login(unauth_client, f"nobody-{uuid.uuid4().hex[:8]}@example.com")
    assert known.status_code == unknown.status_code == 401
    assert known.json() == unknown.json()


# --------------------------------------------------------------------------
# 11. Findings from the Opus review of Gates 1-2 (2026-11-17)
# --------------------------------------------------------------------------

async def test_password_check_does_not_stall_other_requests(unauth_client, monkeypatch):
    """bcrypt is deliberately slow. Run on the event loop, every sign-in
    attempt — including ones for unknown emails — freezes the whole API."""
    import asyncio

    from app.api.v1.routers import auth_router

    entered: dict[str, float] = {}

    def slow_verify(password: str, hashed: str) -> bool:
        entered["at"] = time.perf_counter()
        time.sleep(0.6)
        return False

    monkeypatch.setattr(auth_router, "verify_password", slow_verify)
    attempt = asyncio.create_task(_bad_login(unauth_client, f"slow-{uuid.uuid4().hex[:8]}@example.com"))
    while "at" not in entered:
        await asyncio.sleep(0.005)
    health = await unauth_client.get(f"{API}/health")
    answered_after = time.perf_counter() - entered["at"]
    assert (await attempt).status_code == 401
    assert health.status_code == 200
    assert answered_after < 0.3, f"health check waited {answered_after:.2f}s behind a password check"


def test_lockout_survives_a_flood_of_other_failed_logins(monkeypatch):
    """The throttle is bounded. Filling it with throwaway emails must not
    evict a live lock, or the lock is trivially bypassed."""
    from app.core import login_throttle

    monkeypatch.setattr(login_throttle, "MAX_TRACKED", 50)
    throttle_under_test = login_throttle.LoginThrottle(clock=lambda: 1000.0)
    for _ in range(login_throttle.MAX_FAILURES):
        throttle_under_test.record_failure("victim@example.com")
    assert throttle_under_test.retry_after("victim@example.com") > 0

    for n in range(500):
        throttle_under_test.record_failure(f"noise-{n}@example.com")

    assert throttle_under_test.retry_after("victim@example.com") > 0
    assert len(throttle_under_test._entries) <= 50          # still bounded


def _auth_log(caplog) -> str:
    return "\n".join(r.getMessage() for r in caplog.records if r.name == "sentinel.auth")


async def test_refresh_token_reuse_is_logged_without_secrets(unauth_client, temp_user, caplog):
    import logging

    email, password = temp_user()
    tokens = await _login(unauth_client, email, password)
    await unauth_client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    with caplog.at_level(logging.WARNING, logger="sentinel.auth"):
        replay = await unauth_client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert replay.status_code == 401
    log = _auth_log(caplog)
    assert "refresh token reuse" in log
    assert email not in log and tokens["refresh_token"] not in log and tokens["access_token"] not in log


async def test_account_lockout_is_logged_without_the_email(unauth_client, caplog):
    import logging

    email = f"nobody-{uuid.uuid4().hex[:8]}@example.com"
    with caplog.at_level(logging.WARNING, logger="sentinel.auth"):
        for _ in range(5):
            await _bad_login(unauth_client, email)

    log = _auth_log(caplog)
    assert "locked" in log
    assert email not in log and email.split("@")[0] not in log
