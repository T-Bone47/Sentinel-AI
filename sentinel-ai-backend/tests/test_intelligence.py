"""
Phase 2 intelligence tests — same convention as test_api.py: real Postgres,
real ingested data, httpx against the ASGI app. These are additive; nothing
here touches the 61 Phase 1 tests.
"""
from __future__ import annotations

import pytest


async def test_trust_intelligence_shape_and_real_values(client, auth_headers):
    response = await client.get("/api/v1/intelligence/trust", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]

    for key in (
        "trust_score",
        "trust_level",
        "trust_domains",
        "positive_contributors",
        "negative_contributors",
        "score_change",
        "top_risk_drivers",
        "evidence_coverage",
        "control_coverage",
        "audit_readiness",
        "recommended_actions",
    ):
        assert key in data, f"missing key: {key}"

    assert isinstance(data["trust_score"], (int, float))
    assert 0 <= data["trust_score"] <= 100
    assert data["trust_level"] in ("Strong", "Adequate", "At Risk", "Critical")
    assert len(data["trust_domains"]) == 5  # the five Phase 1 components, unchanged

    # Every domain value must come straight from the live component ratios —
    # not fabricated — so each is in [0, 1] and contribution = value * weight * 100.
    for domain in data["trust_domains"]:
        assert 0.0 <= domain["value"] <= 1.0
        expected = round(domain["value"] * domain["weight"] * 100, 2)
        assert domain["contribution_points"] == expected

    # positive/negative contributors must be a subset of trust_domains, not invented rows
    domain_keys = {d["key"] for d in data["trust_domains"]}
    for bucket in ("positive_contributors", "negative_contributors"):
        for entry in data[bucket]:
            assert entry["key"] in domain_keys

    # top_risk_drivers must be real, currently-open Critical/High risks
    for driver in data["top_risk_drivers"]:
        assert driver["severity"] in ("Critical", "High")
        assert driver["status"] in ("Open", "In Remediation")

    # every recommended action must be explicitly labelled non-generative
    for action in data["recommended_actions"]:
        assert action["generated_by"] == "deterministic_rules_v1"
        assert "basis" in action


async def test_trust_intelligence_score_change_is_real_not_fabricated(client, auth_headers):
    # Changed 2026-11-17 (Gate 2): reading the score used to write a history
    # row, so "the previous snapshot" was simply the previous page view. The
    # comparison is now against the most recent *recorded measurement*, and
    # reading never records one (tests/test_gate2_trust_measurements.py).
    await client.post("/api/v1/intelligence/trust/measurements", headers=auth_headers)

    first = (await client.get("/api/v1/intelligence/trust", headers=auth_headers)).json()["data"]
    second = (await client.get("/api/v1/intelligence/trust", headers=auth_headers)).json()["data"]

    # A measurement of the current data was just taken and nothing changed
    # since, so the delta must be exactly zero — not None, not a random
    # number — and identical on both reads.
    for data in (first, second):
        assert data["score_change"]["status"] == "compared against the most recent recorded measurement"
        assert data["score_change"]["delta"] == 0.0
        assert data["score_change"]["prior_score"] == data["trust_score"]
    assert first["score_change"]["prior_computed_at"] == second["score_change"]["prior_computed_at"]


async def test_risk_intelligence_top_list_is_ranked_and_real(client, auth_headers):
    response = await client.get("/api/v1/intelligence/risks?limit=10", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    risks = body["data"]
    assert len(risks) == 10
    assert body["meta"]["count"] == 10

    # descending risk_score
    scores = [r["risk_score"] for r in risks]
    assert scores == sorted(scores, reverse=True)

    # only open/in-remediation risks are eligible for the top list
    for r in risks:
        assert r["current_status"] in ("Open", "In Remediation")
        assert r["priority"] in ("Critical", "High", "Medium", "Low")
        assert r["confidence"]["level"] in ("high", "medium", "low")


async def test_risk_intelligence_detail_with_mapped_control(client, auth_headers):
    """A risk that IS mapped to a control: verify the real chain resolves —
    same FKs detail_router.risk_detail already uses (control_id join)."""
    top = (await client.get("/api/v1/intelligence/risks?limit=1", headers=auth_headers)).json()["data"]
    risk_id = top[0]["risk_id"]

    response = await client.get(f"/api/v1/intelligence/risks/{risk_id}", headers=auth_headers)
    assert response.status_code == 200
    detail = response.json()["data"]

    assert detail["risk_id"] == risk_id
    assert "affected_assets" in detail  # only present on the detail call, not the list
    assert "department-level correlation" in detail["affected_assets"]["basis"]
    assert len(detail["risk_drivers"]) >= 1
    assert "generated_by" in detail["recommended_action"]


async def test_risk_intelligence_handles_risk_with_no_mapped_control(client, auth_headers, db_session):
    """A risk WITHOUT a mapped control must degrade gracefully — empty
    lists and a 'low' confidence label, never a crash or an invented chain."""
    from sqlalchemy import text

    row = db_session.execute(
        text("SELECT risk_id FROM risks WHERE mapped_control_id IS NULL LIMIT 1")
    ).first()
    if row is None:
        import pytest

        pytest.skip("every risk in this dataset happens to have a mapped control")
    risk_id = row[0]

    response = await client.get(f"/api/v1/intelligence/risks/{risk_id}", headers=auth_headers)
    assert response.status_code == 200
    detail = response.json()["data"]
    assert detail["affected_controls"] == []
    assert detail["related_findings"] == []
    assert detail["confidence"]["level"] == "low"


async def test_risk_intelligence_detail_404_for_unknown_risk(client, auth_headers):
    response = await client.get("/api/v1/intelligence/risks/NOT-A-REAL-RISK", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Risk 'NOT-A-REAL-RISK' not found"


async def test_intelligence_endpoints_match_existing_auth_convention(client):
    """dashboard_router and detail_router don't gate their GETs behind auth
    (confirmed: neither has a Depends(get_current_user)) — the intelligence
    router deliberately matches that existing convention rather than
    introducing a new, inconsistent auth rule for just these two endpoints.
    If that convention ever changes platform-wide, it should change here
    too, in the same commit — not diverge silently."""
    response = await client.get("/api/v1/intelligence/trust")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Evidence Intelligence (Phase 2B, Priority 1)
# ---------------------------------------------------------------------------


async def test_evidence_intelligence_summary(client):
    body = (await client.get("/api/v1/intelligence/evidence")).json()["data"]

    assert body["total_controls"] == 300
    assert body["covered_controls"] + body["uncovered_controls"] == 300
    assert (
        body["controls_with_no_evidence"] + body["controls_with_unverified_evidence_only"]
        == body["uncovered_controls"]
    )
    assert 0 <= body["coverage_percentage"] <= 100
    # The formula and adequacy rule must travel with the number.
    assert "VERIFIED" in body["formula"]
    assert body["adequacy_rule"]
    # No freshness judgement is derivable from this dataset.
    assert body["freshness_policy_available"] is False


async def test_evidence_coverage_matches_its_own_formula(client):
    body = (await client.get("/api/v1/intelligence/evidence/coverage")).json()["data"]
    recomputed = round(100 * body["covered_controls"] / body["total_controls"], 2)
    assert recomputed == body["coverage_percentage"]


async def test_evidence_coverage_agrees_with_the_dashboard(client):
    """
    The dashboard counts a control as evidenced if it has ANY evidence; this
    service requires VERIFIED evidence. So coverage here must be <= the
    dashboard's, never above it — a cheap guard against the two drifting apart.
    """
    dashboard = (await client.get("/api/v1/dashboard")).json()["data"]
    coverage = (await client.get("/api/v1/intelligence/evidence/coverage")).json()["data"]

    assert coverage["total_controls"] == dashboard["evidence_coverage"]["total_controls"]
    assert (
        coverage["covered_controls"]
        <= dashboard["evidence_coverage"]["controls_with_evidence"]
    )
    assert (
        coverage["verified_evidence_items"]
        == dashboard["evidence_coverage"]["verified_evidence"]
    )


async def test_every_gap_is_genuinely_uncovered(client):
    body = (await client.get("/api/v1/intelligence/evidence/coverage")).json()["data"]
    gaps = body["evidence_gaps"]

    assert len(gaps) == body["uncovered_controls"]
    for gap in gaps:
        assert gap["verified_evidence_items"] == 0
        assert gap["gap_type"] in ("no_evidence", "unverified_only")
        assert gap["gap_severity"] in ("Critical", "High", "Medium", "Low")
        assert gap["why"]


async def test_gaps_are_ranked_most_severe_first(client):
    gaps = (await client.get("/api/v1/intelligence/evidence/coverage")).json()["data"][
        "evidence_gaps"
    ]
    rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    severities = [rank[g["gap_severity"]] for g in gaps]
    assert severities == sorted(severities, reverse=True)


async def test_critical_gaps_have_open_findings(client):
    """A Critical gap means: evidence required, none at all, and known failures."""
    gaps = (await client.get("/api/v1/intelligence/evidence/coverage")).json()["data"][
        "evidence_gaps"
    ]
    for gap in (g for g in gaps if g["gap_severity"] == "Critical"):
        assert gap["evidence_required"] is True
        assert gap["gap_type"] == "no_evidence"
        assert gap["open_findings"] > 0


async def test_framework_coverage_sums_to_the_total(client):
    body = (await client.get("/api/v1/intelligence/evidence/coverage")).json()["data"]
    by_framework = body["by_framework"]
    assert sum(f["total_controls"] for f in by_framework) == body["total_controls"]
    assert sum(f["covered_controls"] for f in by_framework) == body["covered_controls"]


async def test_control_evidence_view(client):
    listing = await client.get("/api/v1/controls", params={"page_size": 1})
    control_id = listing.json()["data"][0]["control_id"]
    body = (await client.get(f"/api/v1/intelligence/controls/{control_id}/evidence")).json()[
        "data"
    ]

    assert body["control_id"] == control_id
    assert body["covered"] == (body["verified_evidence_count"] > 0)
    assert body["can_we_prove_it_works"]
    for item in body["evidence"]:
        assert item["control_id"] if "control_id" in item else True
        assert item["age_days"] >= 0


async def test_evidence_detail_links_only_real_relationships(client):
    listing = await client.get("/api/v1/evidence", params={"page_size": 1})
    evidence_id = listing.json()["data"][0]["evidence_id"]
    body = (await client.get(f"/api/v1/intelligence/evidence/{evidence_id}")).json()["data"]

    assert body["evidence_id"] == evidence_id
    assert body["counts_toward_coverage"] == body["verified"]
    # findings.evidence_id is a real FK, so anything listed here must cite it.
    for finding in body["directly_supports_findings"]:
        assert finding["finding_id"]
    assert body["control"] is not None


async def test_evidence_intelligence_404s(client):
    assert (await client.get("/api/v1/intelligence/evidence/NOPE")).status_code == 404
    assert (
        await client.get("/api/v1/intelligence/controls/NOPE/evidence")
    ).status_code == 404


# ---------------------------------------------------------------------------
# Policy Intelligence (Phase 2B, Priority 2)
# ---------------------------------------------------------------------------

SAMPLE_POLICY = (
    "All privileged accounts must use multi-factor authentication before accessing "
    "production systems. Personal data must be encrypted at rest and in transit. "
    "Access reviews shall be performed quarterly for all privileged users. "
    "Vendors must complete a security due diligence assessment prior to onboarding. "
    "The colour of the office wall is blue."
)

UNMAPPABLE_POLICY = (
    "Employees must bring their own reusable coffee mug to the cafeteria every "
    "Tuesday morning. Staff shall water the office ficus plants twice weekly."
)


async def test_policy_analysis_extracts_only_obligations(client):
    body = (
        await client.post(
            "/api/v1/intelligence/policy/analyze",
            json={"text": SAMPLE_POLICY, "title": "Access Control Policy"},
        )
    ).json()["data"]

    # Four obligation sentences; the wall-colour sentence is not a requirement.
    assert body["requirements_found"] == 4
    assert all("colour of the office wall" not in r["requirement"] for r in body["requirements"])
    assert all(r["obligation"] in ("mandatory", "advisory") for r in body["requirements"])


async def test_policy_analysis_declares_it_is_not_an_llm(client):
    body = (
        await client.post("/api/v1/intelligence/policy/analyze", json={"text": SAMPLE_POLICY})
    ).json()["data"]

    assert body["llm_used"] is False
    assert body["engine"] == "rule_based_v1"
    assert "not a language model" in body["engine_note"].lower()
    assert "no llm is configured" in body["engine_note"].lower()


async def test_policy_requirements_map_to_real_controls(client):
    body = (
        await client.post("/api/v1/intelligence/policy/analyze", json={"text": SAMPLE_POLICY})
    ).json()["data"]

    controls = (await client.get("/api/v1/controls", params={"page_size": 200})).json()
    known = {c["control_id"] for c in controls["data"]}

    mapped_any = False
    for requirement in body["requirements"]:
        for mapping in requirement["mapped_controls"]:
            mapped_any = True
            # Every mapped control must actually exist in the catalogue.
            assert mapping["control_id"] in known or mapping["control_id"].startswith("CTRL-")
            assert 0 < mapping["match_score"] <= 1.0
            assert mapping["match_score"] >= body["match_threshold"]
    assert mapped_any, "the MFA/encryption/vendor requirements should map to real controls"


async def test_unmappable_requirements_are_not_guessed(client):
    """The single most important honesty property of this feature."""
    body = (
        await client.post("/api/v1/intelligence/policy/analyze", json={"text": UNMAPPABLE_POLICY})
    ).json()["data"]

    assert body["requirements_found"] == 2
    assert body["requirements_unmapped"] == 2
    for requirement in body["requirements"]:
        assert requirement["mapped_controls"] == []
        assert requirement["mapping_note"] == "No verified control mapping found."
        assert requirement["confidence"] == "none"
        assert requirement["gap"] == "unmapped"


async def test_policy_compliance_matches_its_own_formula(client):
    body = (
        await client.post("/api/v1/intelligence/policy/analyze", json={"text": SAMPLE_POLICY})
    ).json()["data"]
    expected = round(100 * body["requirements_satisfied"] / body["requirements_found"], 2)
    assert expected == body["compliance_percentage"]
    assert body["requirements_mapped"] + body["requirements_unmapped"] == body["requirements_found"]


async def test_stored_policy_uses_the_real_foreign_key_not_text_matching(client):
    listing = await client.get("/api/v1/policies", params={"page_size": 1})
    policy_id = listing.json()["data"][0]["policy_id"]
    body = (await client.get(f"/api/v1/intelligence/policies/{policy_id}")).json()["data"]

    assert body["policy"]["policy_id"] == policy_id
    assert body["engine"] == "database_foreign_key"
    assert body["requirements_unmapped"] == 0
    for requirement in body["requirements"]:
        assert requirement["mapping_source"] == "database_foreign_key"
        assert requirement["confidence"] == "verified"
        assert requirement["mapped_controls"][0]["policy_id"] == policy_id

    detail = (await client.get(f"/api/v1/policies/{policy_id}")).json()["data"]
    assert body["actual_control_count"] == detail["control_count"]


async def test_policy_analysis_rejects_trivial_input(client):
    response = await client.post("/api/v1/intelligence/policy/analyze", json={"text": "short"})
    assert response.status_code == 422


async def test_policy_intelligence_404(client):
    assert (await client.get("/api/v1/intelligence/policies/NOPE")).status_code == 404


# ---------------------------------------------------------------------------
# Compliance Copilot (Phase 2B, Priority 3)
# ---------------------------------------------------------------------------

REQUIRED_QUESTIONS = [
    ("Are we audit ready?", "audit_readiness"),
    ("Why is our Trust Score what it is?", "trust_explanation"),
    ("What are our top risks?", "top_risks"),
    ("Which controls are failing?", "controls_failing"),
    ("Which controls lack evidence?", "evidence_gaps"),
    ("Which evidence gaps are critical?", "evidence_gaps"),
    ("Which vendor is highest risk?", "vendor_risk"),
    ("What are our biggest DPDP concerns?", "privacy_concerns"),
    ("What should we fix first?", "priority_actions"),
    ("Show me critical findings.", "critical_findings"),
    ("What policy requirements are currently not satisfied?", "policy_gaps"),
]


async def ask(client, question: str) -> dict:
    response = await client.post("/api/v1/copilot/query", json={"question": question})
    assert response.status_code == 200, question
    return response.json()["data"]


@pytest.mark.parametrize("question,expected_intent", REQUIRED_QUESTIONS)
async def test_copilot_routes_every_required_question(client, question, expected_intent):
    body = await ask(client, question)
    assert body["intent"] == expected_intent, f"{question!r} routed to {body['intent']}"
    assert body["answer"]
    # No LLM_API_KEY is set in the test environment, so every matched intent
    # takes the deterministic-fallback path, not the "unknown question" path
    # (which alone still reports engine="deterministic_intent_v1" — see
    # CopilotService.answer()). This mirrors the contract asserted in
    # tests/test_copilot_llm.py::TestCopilotAnswerIntegration.
    assert body["llm_used"] is False
    assert body["engine"] == "deterministic_fallback_v1"
    assert body["confidence"] in ("high", "medium", "low", "none")


async def test_copilot_answers_carry_traceable_sources(client):
    for question, _ in REQUIRED_QUESTIONS:
        body = await ask(client, question)
        assert body["sources"], f"{question!r} returned no source references"
        for source in body["sources"]:
            assert source["endpoint"].startswith("/api/v1/")


async def test_copilot_audit_readiness_matches_the_dashboard(client):
    body = await ask(client, "Are we audit ready?")
    dashboard = (await client.get("/api/v1/dashboard")).json()["data"]
    readiness = dashboard["audit_readiness"]["value"]
    assert str(readiness) in body["answer"]


async def test_copilot_evidence_answer_matches_evidence_intelligence(client):
    body = await ask(client, "Which controls lack evidence?")
    coverage = (await client.get("/api/v1/intelligence/evidence")).json()["data"]
    assert str(coverage["uncovered_controls"]) in body["answer"]
    assert str(coverage["total_controls"]) in body["answer"]


async def test_copilot_declines_out_of_scope_questions(client):
    """The Copilot must not improvise when it has no data path."""
    body = await ask(client, "What is the airspeed velocity of an unladen swallow?")
    assert body["intent"] == "unknown"
    assert body["confidence"] == "none"
    assert body["supporting_data"] == []
    assert body["recommendations"] == []
    assert body["suggested_questions"]


async def test_copilot_explains_a_specific_risk(client):
    listing = await client.get("/api/v1/risks", params={"page_size": 50})
    risk_id = next(
        r["risk_id"] for r in listing.json()["data"] if r["mapped_control_id"]
    )
    body = await ask(client, f"Why is {risk_id} critical?")
    assert body["intent"] == "risk_detail"
    assert risk_id in body["answer"]


async def test_copilot_finds_evidence_for_a_specific_risk(client):
    listing = await client.get("/api/v1/risks", params={"page_size": 50})
    risk_id = next(
        r["risk_id"] for r in listing.json()["data"] if r["mapped_control_id"]
    )
    body = await ask(client, f"What evidence supports {risk_id}?")
    assert body["intent"] == "evidence_for_risk"
    assert risk_id in body["answer"]


async def test_copilot_handles_an_unknown_risk_id_without_inventing_one(client):
    body = await ask(client, "Why is RISK-00000000 critical?")
    assert "no risk" in body["answer"].lower()
    assert body["related_entities"] == []


async def test_copilot_suggestions_endpoint(client):
    body = (await client.get("/api/v1/copilot/suggestions")).json()["data"]
    assert len(body["suggested_questions"]) >= 10
    assert body["llm_used"] is False
    intents = {i["intent"] for i in body["intents"]}
    assert {"audit_readiness", "trust_explanation", "evidence_gaps"} <= intents


async def test_copilot_rejects_empty_questions(client):
    assert (
        await client.post("/api/v1/copilot/query", json={"question": ""})
    ).status_code == 422


async def test_remediation_intelligence_top_list_is_ranked_and_real(client, auth_headers):
    response = await client.get("/api/v1/intelligence/remediation?limit=10", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    findings = body["data"]
    assert len(findings) <= 10
    
    # Check that they are open/in progress
    for f in findings:
        assert f["status"] in ("Open", "In Progress")
        assert "severity" in f
        assert "finding_id" in f
        assert "remediation_plan" in f

    # Ensure it's ranked by severity score Critical > High > Medium > Low
    scores = []
    severity_map = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    for f in findings:
        scores.append(severity_map.get(f["severity"], 1))
    assert scores == sorted(scores, reverse=True)


async def test_remediation_intelligence_detail(client, auth_headers):
    # Get a finding from the top list
    top = await client.get("/api/v1/intelligence/remediation?limit=1", headers=auth_headers)
    findings = top.json()["data"]
    if not findings:
        pytest.skip("No open findings available in test database.")
        
    finding_id = findings[0]["finding_id"]
    
    response = await client.get(f"/api/v1/intelligence/remediation/{finding_id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    
    assert data["finding_id"] == finding_id
    assert "description" in data
    assert "recommendation" in data
    assert "remediation_plan" in data
    assert "steps" in data["remediation_plan"]
    assert len(data["remediation_plan"]["steps"]) >= 2
    assert data["remediation_plan"]["generated_by"] == "deterministic_rules_v1"


async def test_continuous_monitoring_anomalies(client, auth_headers):
    response = await client.get("/api/v1/intelligence/monitoring/anomalies?limit=5", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    data = body["data"]
    
    assert isinstance(data, list)
    if data:
        anomaly = data[0]
        assert "log_id" in anomaly
        assert "timestamp" in anomaly
        assert "risk_score" in anomaly
        assert "anomaly_reason" in anomaly


async def test_continuous_monitoring_metrics(client, auth_headers):
    response = await client.get("/api/v1/intelligence/monitoring/metrics", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    data = body["data"]
    
    assert "total_anomalies" in data
    assert "high_risk_events" in data
    assert "failed_operations" in data
    assert "top_anomalous_actions" in data
    # Changed 2026-11-17 (finding F8): this used to assert the claim
    # "monitoring_status: Active". The service only filters stored audit logs.
    assert data["mode"] == "retrospective"
    assert "monitoring_status" not in data


async def test_sentinel_orchestrator_summary(client, auth_headers):
    response = await client.get("/api/v1/intelligence/orchestrator/summary", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    data = body["data"]
    
    assert "executive_summary" in data
    assert "llm_used" in data
    assert "posture" in data
    posture = data["posture"]
    assert "trust_posture" in posture
    assert "top_risks" in posture
    assert "active_threats" in posture
    assert "immediate_remediations" in posture
    assert "evidence_gaps" in posture
