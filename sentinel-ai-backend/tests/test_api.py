"""
API smoke tests — one per Review-1 success criterion.

Deliberately shallow and broad: the goal is "every screen the frontend has
can get real data", not exhaustive contract testing.
"""
from __future__ import annotations

import pytest

from tests.conftest import DEMO_PASSWORD, EXPECTED_COUNTS

LIST_ENDPOINTS = [
    ("/api/v1/employees", EXPECTED_COUNTS["employees"]),
    ("/api/v1/devices", EXPECTED_COUNTS["devices"]),
    ("/api/v1/cloud-assets", EXPECTED_COUNTS["cloud_assets"]),
    ("/api/v1/applications", EXPECTED_COUNTS["applications"]),
    ("/api/v1/vendors", EXPECTED_COUNTS["vendors"]),
    ("/api/v1/policies", EXPECTED_COUNTS["policies"]),
    ("/api/v1/controls", EXPECTED_COUNTS["controls"]),
    ("/api/v1/risks", EXPECTED_COUNTS["risks"]),
    ("/api/v1/findings", EXPECTED_COUNTS["findings"]),
    ("/api/v1/evidence", EXPECTED_COUNTS["evidence"]),
    ("/api/v1/reports", EXPECTED_COUNTS["reports"]),
    ("/api/v1/iam", EXPECTED_COUNTS["iam_records"]),
    ("/api/v1/audit-logs", EXPECTED_COUNTS["audit_logs"]),
    ("/api/v1/dpdp/personal-data", EXPECTED_COUNTS["personal_data_inventory"]),
    ("/api/v1/dpdp/consents", EXPECTED_COUNTS["consent_records"]),
]


async def test_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


async def test_openapi_schema_is_served(client):
    response = await client.get("/api/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/dashboard" in paths
    assert "/api/v1/organization/graph" in paths


@pytest.mark.parametrize("path,expected_total", LIST_ENDPOINTS)
async def test_list_endpoints_return_real_totals(client, path: str, expected_total: int):
    response = await client.get(path, params={"page": 1, "page_size": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["meta"]["total"] == expected_total
    assert len(body["data"]) == min(5, expected_total)


async def test_pagination_advances(client):
    first = (await client.get("/api/v1/employees", params={"page": 1, "page_size": 10})).json()
    second = (await client.get("/api/v1/employees", params={"page": 2, "page_size": 10})).json()
    assert first["meta"]["total_pages"] == 50
    assert {e["employee_id"] for e in first["data"]}.isdisjoint(
        {e["employee_id"] for e in second["data"]}
    )


async def test_filtering_and_search(client):
    filtered = await client.get("/api/v1/risks", params={"severity": "Critical", "page_size": 5})
    assert filtered.status_code == 200
    assert all(r["severity"] == "Critical" for r in filtered.json()["data"])

    searched = await client.get("/api/v1/employees", params={"search": "arora", "page_size": 5})
    assert searched.status_code == 200
    assert searched.json()["meta"]["total"] > 0


async def test_sorting(client):
    response = await client.get("/api/v1/audit-logs", params={"sort": "-risk_score", "page_size": 5})
    scores = [row["risk_score"] for row in response.json()["data"]]
    assert scores == sorted(scores, reverse=True)


async def test_audit_log_date_range_filter(client):
    response = await client.get(
        "/api/v1/audit-logs",
        params={"date_from": "2026-07-01", "date_to": "2026-07-31", "page_size": 5},
    )
    assert response.status_code == 200
    for row in response.json()["data"]:
        assert row["timestamp"][:7] == "2026-07"


async def test_unknown_id_returns_404_in_envelope(client):
    response = await client.get("/api/v1/risks/DOES-NOT-EXIST")
    assert response.status_code == 404
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "http_404"


# ---------------------------------------------------------------------------
# Investigation chain
# ---------------------------------------------------------------------------

async def test_risk_detail_walks_the_control_chain(client):
    listing = await client.get(
        "/api/v1/risks", params={"page_size": 50, "sort": "risk_id"}
    )
    risk_id = next(
        r["risk_id"] for r in listing.json()["data"] if r["mapped_control_id"]
    )
    detail = (await client.get(f"/api/v1/risks/{risk_id}")).json()["data"]

    assert detail["control"] is not None
    assert detail["control"]["control_id"] == detail["mapped_control_id"]
    assert detail["policy"]["policy_id"] == detail["control"]["policy_id"]
    for finding in detail["findings"]:
        assert finding["control_id"] == detail["mapped_control_id"]
    for evidence in detail["evidence"]:
        assert evidence["control_id"] == detail["mapped_control_id"]


async def test_finding_detail_includes_control_policy_and_evidence(client):
    listing = await client.get("/api/v1/findings", params={"page_size": 50})
    finding_id = next(f["finding_id"] for f in listing.json()["data"] if f["evidence_id"])
    detail = (await client.get(f"/api/v1/findings/{finding_id}")).json()["data"]

    assert detail["control"]["control_id"] == detail["control_id"]
    assert detail["policy"] is not None
    assert detail["evidence"]["evidence_id"] == detail["evidence_id"]


async def test_evidence_detail_links_back_to_control(client):
    listing = await client.get("/api/v1/evidence", params={"page_size": 5})
    evidence_id = listing.json()["data"][0]["evidence_id"]
    detail = (await client.get(f"/api/v1/evidence/{evidence_id}")).json()["data"]

    assert detail["control"]["control_id"] == detail["control_id"]
    assert detail["policy"] is not None


async def test_employee_360_view(client):
    listing = await client.get("/api/v1/employees", params={"page_size": 1})
    employee_id = listing.json()["data"][0]["employee_id"]
    detail = (await client.get(f"/api/v1/employees/{employee_id}")).json()["data"]

    assert detail["employee_id"] == employee_id
    assert detail["device"] is not None
    assert detail["iam_record"] is not None
    assert isinstance(detail["recent_activity"], list)


# ---------------------------------------------------------------------------
# Dashboard / frameworks / graph
# ---------------------------------------------------------------------------

async def test_dashboard_aggregates_real_data(client):
    body = (await client.get("/api/v1/dashboard")).json()["data"]

    assert body["totals"] == {
        "employees": 500, "devices": 500, "cloud_assets": 300, "applications": 100,
        "vendors": 100, "policies": 100, "controls": 300, "risks": 300,
        "evidence": 500, "findings": 300, "reports": 100,
        "personal_data_records": 300, "consent_records": 500,
        "iam_records": 500, "audit_logs": 10000,
    }
    for section in (
        "risks", "findings", "evidence_coverage", "compliance_coverage",
        "framework_status", "recent_audit_activity", "asset_statistics",
        "vendor_risk", "privacy_statistics", "iam_statistics",
    ):
        assert section in body, f"dashboard is missing '{section}'"

    assert body["risks"]["critical"] + body["risks"]["high"] <= body["risks"]["total"]
    assert body["evidence_coverage"]["controls_with_evidence"] <= 300


async def test_trust_score_is_transparent_and_recomputable(client):
    body = (await client.get("/api/v1/dashboard")).json()["data"]
    score = body["trust_score"]

    assert score["engine"] == "deterministic_phase1"
    recomputed = round(
        100 * sum(score["components"][k] * w for k, w in score["weights"].items()), 1
    )
    assert recomputed == score["value"], "trust score does not match its own published formula"
    assert 0 <= score["value"] <= 100


async def test_scores_can_be_switched_off(client):
    body = (await client.get("/api/v1/dashboard", params={"scores": "off"})).json()["data"]
    assert body["trust_score"]["value"] is None
    assert "Phase 2" in body["trust_score"]["status"]


async def test_framework_rollup(client):
    body = (await client.get("/api/v1/frameworks")).json()
    frameworks = {f["framework"] for f in body["data"]}
    assert frameworks == {"CIS Controls", "DPDP", "ISO 27001", "NIST", "SOC2"}
    assert sum(f["total_controls"] for f in body["data"]) == 300

    detail = await client.get("/api/v1/frameworks/ISO 27001")
    assert detail.status_code == 200
    assert detail.json()["data"]["framework"] == "ISO 27001"


async def test_organization_graph_edges_reference_real_nodes(client):
    body = (await client.get(
        "/api/v1/organization/graph", params={"scope": "full", "limit_employees": 25}
    )).json()["data"]

    node_ids = {n["id"] for n in body["nodes"]}
    assert len(node_ids) == len(body["nodes"]), "duplicate node ids"
    for edge in body["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids
    assert body["meta"]["node_count"] > 0
    assert "MITIGATES" in body["meta"]["edge_types"]


async def test_graph_vendors_are_unconnected(client):
    """Vendors have no FK in the source data — they must stay unconnected."""
    body = (await client.get(
        "/api/v1/organization/graph",
        params={"scope": "governance", "include_vendors": "true"},
    )).json()["data"]

    vendor_ids = {n["id"] for n in body["nodes"] if n["type"] == "vendor"}
    assert vendor_ids
    for edge in body["edges"]:
        assert edge["source"] not in vendor_ids
        assert edge["target"] not in vendor_ids


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

async def test_login_and_me(client, auth_headers):
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "admin"


async def test_login_rejects_bad_password(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sentinel.ai", "password": "definitely-wrong"},
    )
    assert response.status_code == 401


async def test_me_requires_a_token(unauth_client):
    assert (await unauth_client.get("/api/v1/auth/me")).status_code == 401


async def test_refresh_issues_a_new_access_token(client):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "auditor@sentinel.ai", "password": DEMO_PASSWORD},
    )
    refresh_token = login.json()["data"]["refresh_token"]
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]


async def test_access_token_is_not_accepted_as_a_refresh_token(client, auth_headers):
    token = auth_headers["Authorization"].removeprefix("Bearer ")
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert response.status_code == 401
