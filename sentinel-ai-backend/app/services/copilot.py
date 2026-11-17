"""
Compliance Copilot — Phase 2B, Priority 3.

    question -> intent -> intelligence service -> structured answer

Every answer is composed from live database aggregates via the existing
intelligence services — intent matching, entity-id extraction and every
number in `supporting_data` / `related_entities` / `recommendations` /
`sources` are still 100% deterministic and traceable to a row, LLM or not.

An optional LLM explanation layer (`app.services.llm_service.LLMService`)
may rewrite only the prose `answer` field afterwards, grounded strictly in
that same deterministic result — it cannot see raw database rows and cannot
change the structured fields. `answer()` reports which happened:

    engine="llm_grounded_v1"          llm_used=True   LLM call succeeded
    engine="deterministic_fallback_v1" llm_used=False  matched intent, no
                                                         LLM (unconfigured,
                                                         timed out, errored,
                                                         or returned nothing)
    engine="deterministic_intent_v1"   llm_used=False  no intent matched
                                                         (the LLM is never
                                                         invoked for this
                                                         case — see below)

## Why intent routing and not a chatbot

The brief asks for an enterprise GRC copilot, not a ChatGPT clone. A fixed
intent set means every supported question has a known data path and a known
failure mode: if nothing matches, the Copilot says so and lists what it can
answer, rather than improvising — and skips the LLM call entirely, since
there is no verified context to ground it in. Unmatched questions return
`intent: "unknown"` with `confidence: "none"` — never a plausible-sounding
guess.

## Service reuse

Nothing here recomputes Trust, Risk, Evidence or Policy logic. It calls:

    TrustIntelligenceService     trust explanation, audit readiness
    RiskIntelligenceService      top risks, single-risk explanation
    EvidenceIntelligenceService  coverage, gaps, control provability
    DashboardService             vendor / privacy / IAM / finding aggregates
    LLMService                   optional prose rewrite of `answer` only

`_match_intent` is still a keyword matcher, not a classifier — the LLM layer
sits strictly after it, so a question that matches no intent never reaches
the LLM and never becomes a fabricated answer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Control, Evidence, Finding, Risk, Vendor
from app.services.dashboard import DashboardService
from app.services.evidence_intelligence import EvidenceIntelligenceService
from app.services.llm_service import LLMService
from app.services.risk_intelligence import RiskIntelligenceService
from app.services.trust_intelligence import TrustIntelligenceService

OPEN_FINDING_STATUSES = ("Open", "In Progress")

_ID_TOKEN_RE = re.compile(
    r"\b(?:RISK-\d+|CTRL-\d+|EVD-\d+|FND-\d+|POL-[A-Z0-9\-]+)\b",
    re.IGNORECASE,
)


def _ids_in_text(text: str) -> set[str]:
    return {m.group(0).upper() for m in _ID_TOKEN_RE.finditer(text or "")}


@dataclass(frozen=True)
class Intent:
    name: str
    label: str
    keywords: tuple[tuple[str, ...], ...]  # inner tuple = AND, outer = OR
    example: str


# Ordered: the first match wins, so narrow intents come before broad ones.
# This matters — `top_risks` has a bare ("risk",) fallback that would
# otherwise swallow "which VENDOR is highest risk", so vendor, privacy and
# policy intents are all declared above it.
INTENTS: tuple[Intent, ...] = (
    Intent(
        "audit_readiness",
        "Audit readiness",
        (("audit", "ready"), ("audit-ready",), ("ready", "audit")),
        "Are we audit ready?",
    ),
    Intent(
        "trust_explanation",
        "Trust Score explanation",
        (("trust", "score"), ("trust",), ("why", "score")),
        "Why is our Trust Score what it is?",
    ),
    Intent(
        "evidence_gaps",
        "Evidence gaps",
        (("evidence", "gap"), ("lack", "evidence"), ("without", "evidence"),
         ("missing", "evidence"), ("no", "evidence"), ("evidence", "critical")),
        "Which evidence gaps are critical?",
    ),
    Intent(
        "controls_failing",
        "Failing controls",
        (("control", "fail"), ("failing", "control"), ("control", "broken")),
        "Which controls are failing?",
    ),
    Intent(
        "risk_detail",
        "Single risk explanation",
        (("why", "risk"), ("risk", "critical"), ("explain", "risk")),
        "Why is RISK-12345 critical?",
    ),
    Intent(
        "evidence_for_risk",
        "Evidence supporting a risk",
        (("evidence", "risk"), ("evidence", "support")),
        "What evidence supports this risk?",
    ),
    Intent(
        "vendor_risk",
        "Vendor risk",
        (("vendor",), ("third", "party"), ("supplier",)),
        "Which vendor is highest risk?",
    ),
    Intent(
        "privacy_concerns",
        "DPDP / privacy posture",
        (("dpdp",), ("privacy",), ("personal", "data"), ("consent",)),
        "What are our biggest DPDP concerns?",
    ),
    Intent(
        "policy_gaps",
        "Unsatisfied policy requirements",
        (("policy", "requirement"), ("requirement", "satisf"), ("policy", "gap"),
         ("policy", "not")),
        "What policy requirements are not satisfied?",
    ),
    Intent(
        "critical_findings",
        "Critical findings",
        (("critical", "finding"), ("finding",), ("open", "issue")),
        "Show me critical findings.",
    ),
    Intent(
        "top_risks",
        "Top risks",
        (("top", "risk"), ("biggest", "risk"), ("worst", "risk"), ("critical", "risk"),
         ("highest", "risk"), ("risk",)),
        "What are our top risks?",
    ),
    Intent(
        "priority_actions",
        "What to fix first",
        (("fix", "first"), ("prioriti",), ("what", "should", "do"), ("next", "step"),
         ("remediat",)),
        "What should we fix first?",
    ),
)

SUGGESTED_QUESTIONS = [
    "Are we audit ready?",
    "Why is our Trust Score what it is?",
    "What are our top risks?",
    "Which controls are failing?",
    "Which controls lack evidence?",
    "Which evidence gaps are critical?",
    "Which vendor is highest risk?",
    "What are our biggest DPDP concerns?",
    "What should we fix first?",
    "Show me critical findings.",
]

ID_PATTERNS = {
    "risk": re.compile(r"\bRISK-\d+\b", re.IGNORECASE),
    "control": re.compile(r"\bCTRL-\d+\b", re.IGNORECASE),
    "evidence": re.compile(r"\bEVD-\d+\b", re.IGNORECASE),
    "finding": re.compile(r"\bFND-\d+\b", re.IGNORECASE),
    "policy": re.compile(r"\bPOL-[A-Z0-9\-]+\b", re.IGNORECASE),
}


def _extract_ids(question: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for kind, pattern in ID_PATTERNS.items():
        match = pattern.search(question)
        if match:
            found[kind] = match.group(0).upper()
    return found


class CopilotService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------

    def _match_intent(self, question: str) -> tuple[Intent | None, str]:
        lowered = question.lower()
        ids = _extract_ids(question)

        # An explicit entity id is the strongest signal available.
        if "risk" in ids:
            if "evidence" in lowered:
                return next(i for i in INTENTS if i.name == "evidence_for_risk"), "high"
            return next(i for i in INTENTS if i.name == "risk_detail"), "high"

        for intent in INTENTS:
            for group in intent.keywords:
                if all(token in lowered for token in group):
                    return intent, "high" if len(group) > 1 else "medium"
        return None, "none"

    async def answer(self, question: str) -> dict[str, Any]:
        intent, confidence = self._match_intent(question)
        ids = _extract_ids(question)

        if intent is None:
            return {
                "question": question,
                "intent": "unknown",
                "intent_label": "Not understood",
                "answer": (
                    "I can't answer that from the compliance data I have. I answer "
                    "questions about trust, risks, findings, controls, evidence, "
                    "vendors, privacy and remediation priorities — see the suggestions "
                    "below."
                ),
                "supporting_data": [],
                "related_entities": [],
                "recommendations": [],
                "sources": [],
                "confidence": "none",
                "engine": "deterministic_intent_v1",
                "llm_used": False,
                "suggested_questions": SUGGESTED_QUESTIONS,
            }

        handler = getattr(self, f"_answer_{intent.name}")
        result = await handler(question, ids)

        # ---- LLM explanation layer ----
        # The deterministic handler has already produced verified structured
        # data.  We now attempt to have the LLM rewrite the prose "answer"
        # field only — supporting_data, related_entities, recommendations
        # and sources always come from the deterministic path.
        engine = "deterministic_fallback_v1"
        llm_used = False

        llm = LLMService()
        if llm.is_configured:
            deterministic_for_context = {
                "answer": result.get("answer", ""),
                "supporting_data": result.get("supporting_data", []),
                "related_entities": result.get("related_entities", []),
                "recommendations": result.get("recommendations", []),
                "intent_label": intent.label,
            }
            llm_answer = await llm.explain(deterministic_for_context, question)
            # Source/ID validation: the LLM may only cite identifiers that
            # actually appeared in the verified deterministic result.  If it
            # invents one, discard the LLM text and keep the deterministic
            # answer instead of shipping an unverifiable claim.
            if llm_answer is not None:
                allowed_ids = _ids_in_text(
                    result.get("answer", "")
                    + " " + " ".join(
                        f"{e.get('id','')} {e.get('label','')}" for e in result.get("related_entities", [])
                    )
                    + " " + " ".join(str(r) for r in result.get("recommendations", []))
                    + " " + " ".join(
                        f"{d.get('label','')} {d.get('value','')}" for d in result.get("supporting_data", [])
                    )
                )
                if _ids_in_text(llm_answer) - allowed_ids:
                    llm_answer = None
            if llm_answer is not None:
                result["answer"] = llm_answer
                engine = "llm_grounded_v1"
                llm_used = True

        return {
            "question": question,
            "intent": intent.name,
            "intent_label": intent.label,
            "confidence": result.pop("confidence", confidence),
            "engine": engine,
            "llm_used": llm_used,
            "suggested_questions": SUGGESTED_QUESTIONS,
            **result,
        }

    # ------------------------------------------------------------------
    # handlers — each returns answer / supporting_data / related_entities /
    # recommendations / sources
    # ------------------------------------------------------------------

    async def _answer_audit_readiness(self, question: str, ids: dict) -> dict[str, Any]:
        dashboard = await DashboardService(self.db).build()
        evidence = await EvidenceIntelligenceService(self.db).summary(gap_limit=5)
        readiness = dashboard["audit_readiness"]

        value = readiness.get("value")
        verdict = (
            "not yet" if value is None or value < 70
            else "close" if value < 85
            else "yes"
        )
        answer = (
            f"Audit readiness is {value}/100 — {verdict}. "
            f"{evidence['covered_controls']} of {evidence['total_controls']} controls "
            f"({evidence['coverage_percentage']}%) have verified evidence, "
            f"{evidence['critical_gaps']} gaps are critical, and "
            f"{dashboard['findings']['severe_open']} critical/high findings are still open."
        )
        return {
            "answer": answer,
            "supporting_data": [
                {"label": "Audit readiness", "value": value, "unit": "/100"},
                {"label": "Evidence coverage", "value": evidence["coverage_percentage"], "unit": "%"},
                {"label": "Controls with verified evidence", "value": evidence["covered_controls"]},
                {"label": "Controls without", "value": evidence["uncovered_controls"]},
                {"label": "Critical evidence gaps", "value": evidence["critical_gaps"]},
                {"label": "Open critical/high findings", "value": dashboard["findings"]["severe_open"]},
            ],
            "related_entities": [
                {"type": "control", "id": g["control_id"], "label": g["control_name"],
                 "detail": g["gap_severity"] + " evidence gap"}
                for g in evidence["top_gaps"][:5]
            ],
            "recommendations": [
                f"Close the {evidence['critical_gaps']} critical evidence gaps first — "
                "those controls have no evidence and already have open findings.",
                f"Verify the evidence on {evidence['controls_with_unverified_evidence_only']} "
                "controls that have artefacts collected but none verified.",
                f"Remediate {dashboard['findings']['severe_open']} open critical/high findings.",
            ],
            "sources": [
                {"endpoint": "/api/v1/dashboard", "field": "audit_readiness"},
                {"endpoint": "/api/v1/intelligence/evidence", "field": "coverage_percentage"},
            ],
        }

    async def _answer_trust_explanation(self, question: str, ids: dict) -> dict[str, Any]:
        trust = await TrustIntelligenceService(self.db).build()
        score = trust.get("trust_score")
        contributors = trust.get("negative_contributors") or trust.get("detractors") or []
        positives = trust.get("positive_contributors") or trust.get("contributors") or []

        parts = [f"The Trust Score is {score}."]
        if trust.get("trust_level"):
            parts.append(f"That band is '{trust['trust_level']}'.")
        if contributors:
            names = ", ".join(c.get("label", c.get("domain", "?")) for c in contributors[:3])
            parts.append(f"It is held down mainly by {names}.")
        if positives:
            names = ", ".join(c.get("label", c.get("domain", "?")) for c in positives[:2])
            parts.append(f"{names} are the strongest domains.")
        parts.append(
            "The score is deterministic: a fixed weighted sum of live row-count ratios, "
            "not a model output."
        )

        return {
            "answer": " ".join(parts),
            "supporting_data": [
                {"label": c.get("label", c.get("domain", "?")),
                 "value": c.get("score", c.get("ratio")),
                 "unit": c.get("unit", "")}
                for c in (positives + contributors)[:8]
            ],
            "related_entities": [
                {"type": "risk", "id": r.get("risk_id"), "label": r.get("risk_name"),
                 "detail": r.get("severity")}
                for r in (trust.get("top_risk_drivers") or [])[:5]
            ],
            # TrustIntelligenceService._recommend() returns structured dicts
            # ({priority, action, basis, generated_by}) for its own audit
            # trail — every other handler in this file already emits plain
            # strings here (the frontend contract is `recommendations:
            # string[]`), so format rather than pass the dict through raw.
            "recommendations": [
                f"{a['priority']}: {a['action']}" if isinstance(a, dict) and "action" in a
                else str(a)
                for a in trust.get("recommended_actions", [])
            ],
            "sources": [{"endpoint": "/api/v1/intelligence/trust", "field": "trust_score"}],
        }

    async def _answer_evidence_gaps(self, question: str, ids: dict) -> dict[str, Any]:
        evidence = await EvidenceIntelligenceService(self.db).summary(gap_limit=10)
        critical = [g for g in evidence["top_gaps"] if g["gap_severity"] == "Critical"]
        shown = critical or evidence["top_gaps"]

        answer = (
            f"{evidence['uncovered_controls']} of {evidence['total_controls']} controls "
            f"cannot be proven with verified evidence. "
            f"{evidence['controls_with_no_evidence']} have nothing at all and "
            f"{evidence['controls_with_unverified_evidence_only']} have artefacts that were "
            f"never verified. {evidence['critical_gaps']} gaps are critical — evidence is "
            "required, absent, and the control already has open findings."
        )
        return {
            "answer": answer,
            "supporting_data": [
                {"label": "Evidence coverage", "value": evidence["coverage_percentage"], "unit": "%"},
                {"label": "Controls with no evidence", "value": evidence["controls_with_no_evidence"]},
                {"label": "Unverified evidence only", "value": evidence["controls_with_unverified_evidence_only"]},
                {"label": "Critical gaps", "value": evidence["critical_gaps"]},
                {"label": "High gaps", "value": evidence["high_gaps"]},
            ],
            "related_entities": [
                {"type": "control", "id": g["control_id"], "label": g["control_name"],
                 "detail": f"{g['gap_severity']} · {g['open_findings']} open finding(s)"}
                for g in shown[:8]
            ],
            "recommendations": [
                f"{g['control_id']} ({g['control_name']}): {g['why']}" for g in shown[:5]
            ],
            "sources": [{"endpoint": "/api/v1/intelligence/evidence/coverage", "field": "evidence_gaps"}],
        }

    async def _answer_controls_failing(self, question: str, ids: dict) -> dict[str, Any]:
        db = self.db
        findings = list(
            (
                await db.execute(select(Finding).where(Finding.status.in_(OPEN_FINDING_STATUSES)))
            ).scalars().all()
        )
        by_control: dict[str, list[Finding]] = {}
        for finding in findings:
            by_control.setdefault(finding.control_id, []).append(finding)

        controls = list(
            (
                await db.execute(select(Control).where(Control.control_id.in_(list(by_control))))
            ).scalars().all()
        )
        control_by_id = {c.control_id: c for c in controls}

        ranked = sorted(
            by_control.items(),
            key=lambda kv: (
                sum(1 for f in kv[1] if f.severity == "Critical"),
                sum(1 for f in kv[1] if f.severity == "High"),
                len(kv[1]),
            ),
            reverse=True,
        )

        return {
            "answer": (
                f"{len(by_control)} controls are failing — each has at least one finding "
                f"in status Open or In Progress, across {len(findings)} open findings in total."
            ),
            "supporting_data": [
                {"label": "Failing controls", "value": len(by_control)},
                {"label": "Open findings", "value": len(findings)},
                {"label": "Critical open findings",
                 "value": sum(1 for f in findings if f.severity == "Critical")},
                {"label": "High open findings",
                 "value": sum(1 for f in findings if f.severity == "High")},
            ],
            "related_entities": [
                {
                    "type": "control",
                    "id": control_id,
                    "label": control_by_id[control_id].control_name
                    if control_id in control_by_id
                    else control_id,
                    "detail": f"{len(group)} open finding(s)",
                }
                for control_id, group in ranked[:8]
            ],
            "recommendations": [
                f"{control_id}: remediate {len(group)} open finding(s) "
                f"({', '.join(sorted({f.severity for f in group}))})"
                for control_id, group in ranked[:5]
            ],
            "sources": [{"endpoint": "/api/v1/findings", "field": "status"}],
        }

    async def _answer_top_risks(self, question: str, ids: dict) -> dict[str, Any]:
        risks = await RiskIntelligenceService(self.db).top_risks(limit=8)
        if not risks:
            return self._empty("No open risks are recorded in the risk register.")

        top = risks[0]
        return {
            "answer": (
                f"{len(risks)} open risks ranked by severity x likelihood. The highest is "
                f"{top['risk_id']} — {top.get('risk_name')} "
                f"({top.get('severity')}, score {top.get('risk_score')})."
            ),
            "supporting_data": [
                {"label": r["risk_id"], "value": r.get("risk_score"),
                 "unit": f"· {r.get('severity')}"}
                for r in risks
            ],
            "related_entities": [
                {"type": "risk", "id": r["risk_id"], "label": r.get("risk_name"),
                 "detail": f"{r.get('severity')} · {r.get('current_status')}"}
                for r in risks
            ],
            "recommendations": [
                r.get("recommendation") for r in risks[:5] if r.get("recommendation")
            ],
            "sources": [{"endpoint": "/api/v1/intelligence/risks", "field": "risk_score"}],
        }

    async def _answer_risk_detail(self, question: str, ids: dict) -> dict[str, Any]:
        risk_id = ids.get("risk")
        if not risk_id:
            return await self._answer_top_risks(question, ids)

        explained = await RiskIntelligenceService(self.db).explain(risk_id)
        if explained is None:
            return self._empty(f"No risk with id {risk_id} exists in the register.")

        return {
            "answer": (
                f"{risk_id} — {explained.get('risk_name')} is rated "
                f"{explained.get('severity')} with likelihood {explained.get('likelihood')}, "
                f"giving a score of {explained.get('risk_score')} "
                f"({explained.get('priority')} priority). "
                f"{explained.get('why_it_matters', '')}"
            ).strip(),
            "supporting_data": [
                {"label": "Severity", "value": explained.get("severity")},
                {"label": "Likelihood", "value": explained.get("likelihood")},
                {"label": "Risk score", "value": explained.get("risk_score")},
                {"label": "Status", "value": explained.get("current_status")},
                {"label": "Owner", "value": explained.get("owner_department")},
            ],
            "related_entities": self._risk_entities(explained),
            "recommendations": [explained["recommendation"]]
            if explained.get("recommendation")
            else [],
            "sources": [{"endpoint": f"/api/v1/intelligence/risks/{risk_id}", "field": "risk_score"}],
        }

    async def _answer_evidence_for_risk(self, question: str, ids: dict) -> dict[str, Any]:
        risk_id = ids.get("risk")
        if not risk_id:
            return await self._answer_evidence_gaps(question, ids)

        db = self.db
        risk = (
            await db.execute(select(Risk).where(Risk.risk_id == risk_id))
        ).scalar_one_or_none()
        if risk is None:
            return self._empty(f"No risk with id {risk_id} exists in the register.")
        if not risk.mapped_control_id:
            return self._empty(
                f"{risk_id} is not mapped to a control, so no evidence chain exists for it. "
                "Map it to a control to make it provable."
            )

        control = await EvidenceIntelligenceService(db).control_evidence(risk.mapped_control_id)
        return {
            "answer": (
                f"{risk_id} is mapped to control {control['control_id']} "
                f"({control['control_name']}). {control['can_we_prove_it_works']}"
            ),
            "supporting_data": [
                {"label": "Evidence items", "value": control["evidence_count"]},
                {"label": "Verified", "value": control["verified_evidence_count"]},
                {"label": "Open findings", "value": len(control["open_findings"])},
            ],
            "related_entities": [
                {"type": "evidence", "id": e["evidence_id"], "label": e["evidence_type"],
                 "detail": ("verified" if e["verified"] else "unverified") + f" · {e['collected_date']}"}
                for e in control["evidence"][:8]
            ],
            "recommendations": (
                ["Collect and verify evidence for this control — nothing currently proves it works."]
                if not control["verified_evidence_count"]
                else ["Keep this evidence current; it is what proves the mapped control works."]
            ),
            "sources": [
                {"endpoint": f"/api/v1/intelligence/controls/{control['control_id']}/evidence",
                 "field": "evidence"}
            ],
        }

    async def _answer_critical_findings(self, question: str, ids: dict) -> dict[str, Any]:
        findings = list(
            (
                await self.db.execute(
                    select(Finding).where(
                        Finding.status.in_(OPEN_FINDING_STATUSES),
                        Finding.severity.in_(("Critical", "High")),
                    )
                )
            ).scalars().all()
        )
        critical = [f for f in findings if f.severity == "Critical"]
        return {
            "answer": (
                f"{len(critical)} critical and {len(findings) - len(critical)} high findings "
                "are currently open."
            ),
            "supporting_data": [
                {"label": "Critical open", "value": len(critical)},
                {"label": "High open", "value": len(findings) - len(critical)},
            ],
            "related_entities": [
                {"type": "finding", "id": f.finding_id, "label": f.description[:90],
                 "detail": f"{f.severity} · {f.status} · {f.control_id}"}
                for f in (critical + findings)[:8]
            ],
            "recommendations": [f.recommendation for f in critical[:5] if f.recommendation],
            "sources": [{"endpoint": "/api/v1/findings", "field": "severity"}],
        }

    async def _answer_vendor_risk(self, question: str, ids: dict) -> dict[str, Any]:
        vendors = list((await self.db.execute(select(Vendor))).scalars().all())
        rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}

        def score(v: Vendor) -> tuple[int, int]:
            certs = sum([v.iso27001_certified, v.soc2_certified, v.dpdp_compliant])
            return rank.get(v.risk_rating, 0), -certs

        ranked = sorted(vendors, key=score, reverse=True)
        worst = ranked[0]
        uncertified = [v for v in vendors if not v.iso27001_certified and not v.soc2_certified]

        return {
            "answer": (
                f"{worst.vendor_name} ({worst.vendor_id}) carries the highest rating: "
                f"{worst.risk_rating}, "
                f"{'no ISO 27001 or SOC 2 certification' if not (worst.iso27001_certified or worst.soc2_certified) else 'certified'}, "
                f"{'DPDP compliant' if worst.dpdp_compliant else 'not DPDP compliant'}. "
                f"{len(uncertified)} of {len(vendors)} vendors hold neither ISO 27001 nor SOC 2. "
                "Note: the dataset has no verified link from vendors to risks or controls, "
                "so this ranking uses vendor attributes only."
            ),
            "supporting_data": [
                {"label": "Total vendors", "value": len(vendors)},
                {"label": "Rated Critical",
                 "value": sum(1 for v in vendors if v.risk_rating == "Critical")},
                {"label": "No ISO/SOC certification", "value": len(uncertified)},
                {"label": "Not DPDP compliant",
                 "value": sum(1 for v in vendors if not v.dpdp_compliant)},
            ],
            "related_entities": [
                {"type": "vendor", "id": v.vendor_id, "label": v.vendor_name,
                 "detail": f"{v.risk_rating} · {v.service_category}"}
                for v in ranked[:8]
            ],
            "recommendations": [
                f"Request current certification evidence from {v.vendor_name} ({v.vendor_id})."
                for v in ranked[:4]
            ],
            "sources": [{"endpoint": "/api/v1/vendors", "field": "risk_rating"}],
        }

    async def _answer_privacy_concerns(self, question: str, ids: dict) -> dict[str, Any]:
        dashboard = await DashboardService(self.db).build()
        privacy = dashboard["privacy_statistics"]
        exposed = privacy["third_party_sharing"]
        unencrypted = privacy["personal_data_records"] - privacy["encrypted"]

        return {
            "answer": (
                f"{privacy['personal_data_records']} personal-data elements are catalogued. "
                f"{exposed} are shared with third parties and {unencrypted} are not encrypted. "
                f"Of {privacy['consent_records']} consent records, {privacy['consent_revoked']} "
                f"are revoked and {privacy['consent_expired']} have expired. "
                "The dataset has no verified link between personal-data records and consent "
                "records, so those two are reported separately rather than joined."
            ),
            "supporting_data": [
                {"label": "Personal data elements", "value": privacy["personal_data_records"]},
                {"label": "Shared with third parties", "value": exposed},
                {"label": "Not encrypted", "value": unencrypted},
                {"label": "Consent required", "value": privacy["consent_required"]},
                {"label": "Consents revoked", "value": privacy["consent_revoked"]},
                {"label": "Consents expired", "value": privacy["consent_expired"]},
            ],
            "related_entities": [],
            "recommendations": [
                f"Encrypt the {unencrypted} personal-data elements currently unencrypted.",
                f"Review third-party transfers for {exposed} shared elements.",
                f"Re-obtain consent for {privacy['consent_expired']} expired records.",
            ],
            "sources": [{"endpoint": "/api/v1/dashboard", "field": "privacy_statistics"}],
        }

    async def _answer_policy_gaps(self, question: str, ids: dict) -> dict[str, Any]:
        evidence = await EvidenceIntelligenceService(self.db).summary(gap_limit=8)
        mandatory_gaps = [g for g in evidence["top_gaps"] if g.get("mandatory_policy")]

        return {
            "answer": (
                f"{evidence['uncovered_controls']} control requirements cannot currently be "
                f"demonstrated. {len(mandatory_gaps)} of the top gaps sit under policies marked "
                "mandatory. A requirement counts as satisfied only when its control has "
                "verified evidence and no open findings."
            ),
            "supporting_data": [
                {"label": "Requirements not demonstrable", "value": evidence["uncovered_controls"]},
                {"label": "Critical gaps", "value": evidence["critical_gaps"]},
                {"label": "Under mandatory policies", "value": len(mandatory_gaps)},
            ],
            "related_entities": [
                {"type": "control", "id": g["control_id"], "label": g["control_name"],
                 "detail": f"{g.get('policy_name') or g['policy_id']} · {g['gap_severity']}"}
                for g in (mandatory_gaps or evidence["top_gaps"])[:8]
            ],
            "recommendations": [
                f"{g['control_id']} under {g.get('policy_name') or g['policy_id']}: {g['why']}"
                for g in (mandatory_gaps or evidence["top_gaps"])[:5]
            ],
            "sources": [
                {"endpoint": "/api/v1/intelligence/evidence/coverage", "field": "evidence_gaps"},
                {"endpoint": "/api/v1/intelligence/policies/{policy_id}", "field": "requirements"},
            ],
        }

    async def _answer_priority_actions(self, question: str, ids: dict) -> dict[str, Any]:
        evidence = await EvidenceIntelligenceService(self.db).summary(gap_limit=5)
        risks = await RiskIntelligenceService(self.db).top_risks(limit=3)
        dashboard = await DashboardService(self.db).build()

        actions: list[str] = []
        if evidence["critical_gaps"]:
            actions.append(
                f"1. Close {evidence['critical_gaps']} critical evidence gaps — controls that "
                "require evidence, have none, and already have open findings."
            )
        if risks:
            actions.append(
                f"2. Address {risks[0]['risk_id']} ({risks[0].get('risk_name')}), the "
                f"highest-scoring open risk."
            )
        if dashboard["iam_statistics"]["privileged_without_mfa"]:
            actions.append(
                f"3. Enable MFA on {dashboard['iam_statistics']['privileged_without_mfa']} "
                "privileged accounts that currently have none."
            )
        if dashboard["asset_statistics"]["cloud_assets"]["public_access"]:
            actions.append(
                f"4. Review {dashboard['asset_statistics']['cloud_assets']['public_access']} "
                "publicly accessible cloud assets."
            )
        if evidence["controls_with_unverified_evidence_only"]:
            actions.append(
                f"5. Verify evidence on {evidence['controls_with_unverified_evidence_only']} "
                "controls where artefacts exist but none are verified — the cheapest coverage win."
            )

        return {
            "answer": (
                "Ranked by what most improves provable compliance: critical evidence gaps "
                "first (they block audit readiness and already have failures), then the "
                "highest-scoring open risk, then identity and cloud exposure."
            ),
            "supporting_data": [
                {"label": "Critical evidence gaps", "value": evidence["critical_gaps"]},
                {"label": "Open critical/high findings", "value": dashboard["findings"]["severe_open"]},
                {"label": "Privileged accounts without MFA",
                 "value": dashboard["iam_statistics"]["privileged_without_mfa"]},
                {"label": "Public cloud assets",
                 "value": dashboard["asset_statistics"]["cloud_assets"]["public_access"]},
            ],
            "related_entities": [
                {"type": "control", "id": g["control_id"], "label": g["control_name"],
                 "detail": g["gap_severity"]}
                for g in evidence["top_gaps"][:5]
            ],
            "recommendations": actions,
            "sources": [
                {"endpoint": "/api/v1/intelligence/evidence", "field": "critical_gaps"},
                {"endpoint": "/api/v1/intelligence/risks", "field": "risk_score"},
                {"endpoint": "/api/v1/dashboard", "field": "iam_statistics"},
            ],
        }

    # ------------------------------------------------------------------

    @staticmethod
    def _risk_entities(explained: dict[str, Any]) -> list[dict[str, Any]]:
        entities: list[dict[str, Any]] = []
        control = explained.get("mapped_control") or explained.get("control")
        if isinstance(control, dict) and control.get("control_id"):
            entities.append(
                {"type": "control", "id": control["control_id"],
                 "label": control.get("control_name"), "detail": control.get("severity")}
            )
        for finding in explained.get("related_findings", [])[:5]:
            entities.append(
                {"type": "finding", "id": finding.get("finding_id"),
                 "label": finding.get("description", "")[:90],
                 "detail": f"{finding.get('severity')} · {finding.get('status')}"}
            )
        for item in explained.get("related_evidence", [])[:5]:
            entities.append(
                {"type": "evidence", "id": item.get("evidence_id"),
                 "label": item.get("evidence_type"),
                 "detail": "verified" if item.get("verified") else "unverified"}
            )
        return entities

    @staticmethod
    def _empty(message: str) -> dict[str, Any]:
        return {
            "answer": message,
            "supporting_data": [],
            "related_entities": [],
            "recommendations": [],
            "sources": [],
            "confidence": "high",
        }
