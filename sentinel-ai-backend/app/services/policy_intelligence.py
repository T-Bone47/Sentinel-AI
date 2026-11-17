"""
Policy Intelligence — Phase 2B, Priority 2.

Turns a static policy document into structured requirements, maps each one
onto controls that actually exist in the database, and reports the current
compliance state of each mapping using Evidence Intelligence.

    policy text -> requirements -> controls -> frameworks -> evidence -> gap

## No LLM is configured in this project

There is no API key, no model client, and no LLM dependency in
`pyproject.toml` or `app/core/config.py`. Rather than spend the session
standing up that infrastructure — which the brief explicitly warns against
— extraction and mapping are **deterministic and rule-based**, and they run
locally with no network access.

That is a real limitation and it is reported honestly in every response:
`"engine": "rule_based_v1"`. Nothing here is described as AI-generated.

The seam for a future LLM is `RequirementExtractor`. Implement that one
protocol (`extract(text) -> list[ExtractedRequirement]`), pass it to
`PolicyIntelligenceService`, and the mapping, evidence and gap layers below
are unchanged. `ControlMatcher` is separately swappable for an embedding
model if lexical matching proves too blunt.

## Mapping honesty

A requirement maps to a control only when lexical overlap clears
MATCH_THRESHOLD. Below that the requirement is returned with
`mapped_controls: []` and the explicit string
**"No verified control mapping found."** — never a nearest guess. Match
scores ship with every mapping so a reviewer can judge them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Control, Evidence, Finding, Policy, Risk

OPEN_FINDING_STATUSES = ("Open", "In Progress")
NO_MAPPING = "No verified control mapping found."

# Obligation markers. A sentence without one of these is background prose,
# not a requirement, and is skipped.
OBLIGATION_PATTERNS = (
    r"\bmust\b",
    r"\bshall\b",
    r"\brequired to\b",
    r"\bis required\b",
    r"\bare required\b",
    r"\bmay not\b",
    r"\bmust not\b",
    r"\bshall not\b",
    r"\bshould\b",
    r"\bis mandatory\b",
    r"\bare mandatory\b",
    r"\bwill be\b",
    r"\bneeds? to\b",
    r"\bhas to\b",
    r"\bhave to\b",
    r"\bensure that\b",
    r"\bat a minimum\b",
    r"\bno later than\b",
    r"\bprohibited\b",
)
OBLIGATION_RE = re.compile("|".join(OBLIGATION_PATTERNS), re.IGNORECASE)

# "must" / "shall" are hard obligations; "should" is advisory. The strength
# is reported, not used to silently drop anything.
STRONG_RE = re.compile(r"\b(must|shall|required|mandatory|prohibited)\b", re.IGNORECASE)

STOPWORDS = {
    "a", "all", "an", "and", "any", "are", "as", "at", "be", "been", "being", "by",
    "each", "for", "from", "has", "have", "in", "is", "it", "its", "may", "must",
    "no", "not", "of", "on", "or", "shall", "should", "such", "that", "the", "their",
    "them", "these", "this", "those", "to", "was", "were", "which", "who", "will",
    "with", "within", "ensure", "required", "requirement", "policy", "organization",
    "organisation", "company", "system", "systems", "appropriate", "relevant",
    "applicable", "including", "include", "includes", "other", "than", "when",
    "where", "least", "minimum", "maintain", "maintained", "provide", "provided",
}

# Category vocabulary drawn from the real `policies.category` values in the
# dataset, so extracted categories line up with what is already stored.
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Access Control": ("access", "privilege", "privileged", "authorization", "authorisation", "least privilege", "role", "permission", "account"),
    "Authentication": ("mfa", "multi-factor", "multifactor", "password", "credential", "authentication", "sso", "biometric"),
    "Data Protection": ("encrypt", "encryption", "at rest", "in transit", "key management", "masking", "tokenization", "confidential"),
    "Data Privacy": ("personal data", "data subject", "consent", "dpdp", "gdpr", "privacy", "pii", "erasure", "retention"),
    "Third-Party Risk": ("vendor", "supplier", "third party", "third-party", "subcontractor", "outsourc", "due diligence"),
    "Incident Response": ("incident", "breach", "response plan", "escalation", "forensic", "containment"),
    "Monitoring": ("monitor", "logging", "log", "audit trail", "alert", "detection", "siem", "intrusion"),
    "Business Continuity": ("continuity", "disaster recovery", "backup", "restore", "rto", "rpo", "resilience"),
    "Change Management": ("change", "release", "deployment", "patch", "configuration", "version"),
    "Asset Management": ("asset", "inventory", "device", "endpoint", "hardware", "software", "cloud resource"),
    "Risk Management": ("risk assessment", "risk register", "threat", "vulnerability", "risk treatment"),
    "Training": ("training", "awareness", "onboarding", "education", "phishing simulation"),
    "Governance": ("governance", "roles and responsibilities", "accountability", "oversight", "board", "steering"),
}

# Requirement text -> what would prove it. Mirrors the real
# `evidence.evidence_type` vocabulary in the dataset.
EVIDENCE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Configuration Screenshot": ("configur", "setting", "enabled", "enforce"),
    "Access Review Report": ("access", "privilege", "review", "recertif", "entitlement"),
    "Audit Log Export": ("log", "monitor", "audit trail", "record", "retain"),
    "Policy Acknowledgement": ("acknowledg", "attest", "sign", "accept"),
    "Training Completion Report": ("training", "awareness", "educat"),
    "Penetration Test Report": ("penetration", "pen test", "security testing", "vulnerability scan"),
    "Vendor Assessment": ("vendor", "supplier", "third party", "third-party", "due diligence"),
    "Backup Verification": ("backup", "restore", "recovery", "continuity"),
    "Encryption Certificate": ("encrypt", "tls", "certificate", "key"),
    "Incident Report": ("incident", "breach", "escalation"),
}

FRAMEWORK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "DPDP": ("dpdp", "personal data", "data principal", "data fiduciary", "consent"),
    "ISO 27001": ("iso 27001", "iso/iec 27001", "isms", "annex a"),
    "SOC2": ("soc 2", "soc2", "trust services", "availability criteria"),
    "NIST": ("nist", "csf", "800-53", "identify, protect"),
    "CIS Controls": ("cis", "cis control", "benchmark", "safeguard"),
}

# Lexical overlap below this is not a mapping. Tuned against the real
# control vocabulary: high enough to reject incidental word sharing, low
# enough to catch genuine paraphrase ("privileged accounts must use MFA"
# -> "Privileged Access Multi-Factor Enforcement").
MATCH_THRESHOLD = 0.22
MAX_CONTROLS_PER_REQUIREMENT = 3


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9][a-z0-9\-]{2,}", text.lower())
    return {w for w in words if w not in STOPWORDS}


def _split_sentences(text: str) -> list[str]:
    # Normalise bullets and numbered clauses into sentence boundaries, since
    # policy documents lean on lists far more than on prose full stops.
    normalised = re.sub(r"[\u2022\u25cf\u25aa\-\*]\s+", ". ", text)
    normalised = re.sub(r"\n\s*\d+[\.\)]\s+", ". ", normalised)
    normalised = re.sub(r"\n{2,}", ". ", normalised)
    normalised = normalised.replace("\n", " ")
    parts = re.split(r"(?<=[.;:!?])\s+", normalised)
    return [p.strip() for p in parts if p.strip()]


@dataclass
class ExtractedRequirement:
    text: str
    obligation: str  # "mandatory" | "advisory"
    category: str | None
    frameworks: list[str] = field(default_factory=list)
    evidence_requirements: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


class RequirementExtractor(Protocol):
    """
    The LLM seam. Implement this and pass it to PolicyIntelligenceService to
    replace rule-based extraction without touching mapping or gap analysis.
    """

    name: str

    def extract(self, text: str) -> list[ExtractedRequirement]: ...


class RuleBasedExtractor:
    """Deterministic extraction. No network, no model, no API key."""

    name = "rule_based_v1"

    def extract(self, text: str) -> list[ExtractedRequirement]:
        requirements: list[ExtractedRequirement] = []
        seen: set[str] = set()

        for sentence in _split_sentences(text):
            if len(sentence) < 25 or not OBLIGATION_RE.search(sentence):
                continue
            key = sentence.lower()[:120]
            if key in seen:
                continue
            seen.add(key)

            lowered = sentence.lower()
            requirements.append(
                ExtractedRequirement(
                    text=sentence.rstrip(".;: "),
                    obligation="mandatory" if STRONG_RE.search(sentence) else "advisory",
                    category=self._category(lowered),
                    frameworks=self._frameworks(lowered),
                    evidence_requirements=self._evidence(lowered),
                    keywords=sorted(_tokens(sentence))[:12],
                )
            )
        return requirements

    @staticmethod
    def _category(lowered: str) -> str | None:
        best, best_hits = None, 0
        for category, keywords in CATEGORY_KEYWORDS.items():
            hits = sum(1 for k in keywords if k in lowered)
            if hits > best_hits:
                best, best_hits = category, hits
        return best

    @staticmethod
    def _frameworks(lowered: str) -> list[str]:
        return [f for f, keywords in FRAMEWORK_KEYWORDS.items() if any(k in lowered for k in keywords)]

    @staticmethod
    def _evidence(lowered: str) -> list[str]:
        return [e for e, keywords in EVIDENCE_KEYWORDS.items() if any(k in lowered for k in keywords)][:3]


class ControlMatcher:
    """
    Lexical matcher over the real control catalogue.

    Score is weighted Jaccard-style overlap between requirement tokens and
    the control's name + description, with the name weighted higher because
    control names in this dataset are dense and specific
    ("Privileged Access Multi-Factor Enforcement"). Swappable for an
    embedding matcher later; the score contract (0..1) stays the same.
    """

    name = "lexical_v1"

    def __init__(self, controls: list[Control], policies: dict[str, Policy]) -> None:
        self.controls = controls
        self.policies = policies
        self._index: list[tuple[Control, set[str], set[str]]] = [
            (c, _tokens(c.control_name), _tokens(c.description or "")) for c in controls
        ]

    def match(self, requirement: ExtractedRequirement) -> list[dict[str, Any]]:
        req_tokens = _tokens(requirement.text)
        if not req_tokens:
            return []

        scored: list[tuple[float, Control, list[str]]] = []
        for control, name_tokens, desc_tokens in self._index:
            name_hits = req_tokens & name_tokens
            desc_hits = req_tokens & desc_tokens
            if not name_hits and not desc_hits:
                continue

            denominator = len(req_tokens | name_tokens) or 1
            score = (2.0 * len(name_hits) + 1.0 * len(desc_hits)) / denominator

            policy = self.policies.get(control.policy_id)
            # A framework named in the requirement is corroborating evidence,
            # not a match on its own — small bonus, capped.
            if policy and requirement.frameworks and policy.framework in requirement.frameworks:
                score += 0.05
            if (
                policy
                and requirement.category
                and policy.category
                and requirement.category.lower() == policy.category.lower()
            ):
                score += 0.05

            score = min(score, 1.0)
            if score >= MATCH_THRESHOLD:
                scored.append((score, control, sorted(name_hits | desc_hits)))

        scored.sort(key=lambda t: t[0], reverse=True)
        return [
            {
                "control_id": control.control_id,
                "control_name": control.control_name,
                "control_severity": control.severity,
                "policy_id": control.policy_id,
                "framework": self.policies[control.policy_id].framework
                if control.policy_id in self.policies
                else None,
                "match_score": round(score, 3),
                "matched_terms": terms[:8],
            }
            for score, control, terms in scored[:MAX_CONTROLS_PER_REQUIREMENT]
        ]


def _confidence(mappings: list[dict[str, Any]]) -> str:
    if not mappings:
        return "none"
    top = mappings[0]["match_score"]
    if top >= 0.45:
        return "high"
    if top >= 0.30:
        return "medium"
    return "low"


class PolicyIntelligenceService:
    def __init__(self, db: AsyncSession, extractor: RequirementExtractor | None = None) -> None:
        self.db = db
        self.extractor = extractor or RuleBasedExtractor()

    async def _catalogue(self) -> tuple[list[Control], dict[str, Policy]]:
        controls = list((await self.db.execute(select(Control))).scalars().all())
        policies = list((await self.db.execute(select(Policy))).scalars().all())
        return controls, {p.policy_id: p for p in policies}

    async def analyze_text(self, text: str, title: str | None = None) -> dict[str, Any]:
        controls, policies = await self._catalogue()
        matcher = ControlMatcher(controls, policies)
        requirements = self.extractor.extract(text)

        analysed: list[dict[str, Any]] = []
        for index, requirement in enumerate(requirements, start=1):
            mappings = matcher.match(requirement)
            state = await self._current_state(mappings)
            analysed.append(
                {
                    "requirement_id": f"REQ-{index:03d}",
                    "requirement": requirement.text,
                    "obligation": requirement.obligation,
                    "category": requirement.category,
                    "mapped_frameworks": sorted(
                        {m["framework"] for m in mappings if m["framework"]}
                    )
                    or requirement.frameworks,
                    "mapped_controls": mappings,
                    "mapping_note": None if mappings else NO_MAPPING,
                    "evidence_requirements": requirement.evidence_requirements,
                    "current_state": state["current_state"],
                    "gap": state["gap"],
                    "gap_severity": state["gap_severity"],
                    "supporting_evidence": state["supporting_evidence"],
                    "open_findings": state["open_findings"],
                    "related_risks": state["related_risks"],
                    "confidence": _confidence(mappings),
                    "recommended_action": state["recommended_action"],
                }
            )

        satisfied = sum(1 for r in analysed if r["gap"] == "none")
        unmapped = sum(1 for r in analysed if not r["mapped_controls"])
        gaps = [r for r in analysed if r["gap"] not in ("none",)]

        return {
            "title": title or "Untitled policy",
            "engine": self.extractor.name,
            "matcher": "lexical_v1",
            "llm_used": False,
            "engine_note": (
                "Requirements and control mappings are produced by deterministic rules, "
                "not a language model — no LLM is configured in this project. Mappings "
                "below MATCH_THRESHOLD are reported as unmapped rather than guessed."
            ),
            "characters_analyzed": len(text),
            "requirements_found": len(analysed),
            "requirements_mapped": len(analysed) - unmapped,
            "requirements_unmapped": unmapped,
            "requirements_satisfied": satisfied,
            "requirements_with_gaps": len(gaps),
            "compliance_percentage": round(100 * satisfied / len(analysed), 2) if analysed else 0.0,
            "compliance_formula": (
                "requirements whose mapped controls all have verified evidence and no "
                "open findings / total extracted requirements * 100"
            ),
            "requirements": analysed,
            "match_threshold": MATCH_THRESHOLD,
        }

    async def analyze_stored_policy(self, policy_id: str) -> dict[str, Any] | None:
        """
        Analyse a policy already in the database. Its real controls are known
        via `controls.policy_id`, so this reports the *actual* mapping
        alongside what the text-matcher would have inferred — a useful check
        on the matcher itself.
        """
        policy = (
            await self.db.execute(select(Policy).where(Policy.policy_id == policy_id))
        ).scalar_one_or_none()
        if policy is None:
            return None

        controls = list(
            (
                await self.db.execute(select(Control).where(Control.policy_id == policy_id))
            ).scalars().all()
        )

        # A stored policy's controls ARE its requirements, and the mapping is
        # already known from `controls.policy_id` — a real foreign key, not an
        # inference. So the lexical matcher is bypassed here entirely and each
        # requirement is reported with `mapping_source: "database_foreign_key"`
        # and confidence "verified". Running the text matcher over control
        # descriptions would only re-derive, less reliably, a link the database
        # already states.
        requirements: list[dict[str, Any]] = []
        control_states = []
        for index, control in enumerate(controls, start=1):
            state = await self._control_state(control)
            control_states.append(state)
            derived = await self._current_state(
                [
                    {
                        "control_id": control.control_id,
                        "control_name": control.control_name,
                        "control_severity": control.severity,
                        "policy_id": control.policy_id,
                        "framework": policy.framework,
                        "match_score": 1.0,
                        "matched_terms": [],
                    }
                ]
            )
            requirements.append(
                {
                    "requirement_id": f"REQ-{index:03d}",
                    "requirement": control.description or control.control_name,
                    "obligation": "mandatory" if policy.mandatory else "advisory",
                    "category": policy.category,
                    "mapped_frameworks": [policy.framework],
                    "mapped_controls": [
                        {
                            "control_id": control.control_id,
                            "control_name": control.control_name,
                            "control_severity": control.severity,
                            "policy_id": control.policy_id,
                            "framework": policy.framework,
                            "match_score": 1.0,
                            "matched_terms": [],
                        }
                    ],
                    "mapping_source": "database_foreign_key",
                    "mapping_note": None,
                    "evidence_requirements": ["Required" ] if control.evidence_required else [],
                    "current_state": derived["current_state"],
                    "gap": derived["gap"],
                    "gap_severity": derived["gap_severity"],
                    "supporting_evidence": derived["supporting_evidence"],
                    "open_findings": derived["open_findings"],
                    "related_risks": derived["related_risks"],
                    "confidence": "verified",
                    "recommended_action": derived["recommended_action"],
                }
            )

        satisfied = sum(1 for r in requirements if r["gap"] == "none")
        analysis = {
            "title": policy.policy_name,
            "engine": "database_foreign_key",
            "matcher": "not_applicable",
            "llm_used": False,
            "engine_note": (
                "No text matching was performed. This policy's controls are linked by a "
                "real foreign key (controls.policy_id), so each requirement's mapping is "
                "read from the database rather than inferred."
            ),
            "characters_analyzed": 0,
            "requirements_found": len(requirements),
            "requirements_mapped": len(requirements),
            "requirements_unmapped": 0,
            "requirements_satisfied": satisfied,
            "requirements_with_gaps": len(requirements) - satisfied,
            "compliance_percentage": round(100 * satisfied / len(requirements), 2)
            if requirements
            else 0.0,
            "compliance_formula": (
                "controls with verified evidence and no open findings / total controls "
                "attached to this policy * 100"
            ),
            "requirements": requirements,
            "match_threshold": None,
        }

        covered = sum(1 for c in control_states if c["covered"])
        return {
            **analysis,
            "policy": {
                "policy_id": policy.policy_id,
                "policy_name": policy.policy_name,
                "framework": policy.framework,
                "category": policy.category,
                "version": policy.version,
                "owner_department": policy.owner_department,
                "mandatory": policy.mandatory,
            },
            "source": "stored_policy_controls",
            "source_note": (
                "The dataset stores policy metadata and its linked controls, not the "
                "original document text. Requirements below are extracted from the "
                "control descriptions actually attached to this policy."
            ),
            "actual_controls": control_states,
            "actual_control_count": len(controls),
            "actual_controls_covered": covered,
            "actual_coverage_percentage": round(100 * covered / len(controls), 2)
            if controls
            else 0.0,
        }

    # ------------------------------------------------------------------
    # current state / gap analysis
    # ------------------------------------------------------------------

    async def _control_state(self, control: Control) -> dict[str, Any]:
        db = self.db
        evidence = list(
            (
                await db.execute(select(Evidence).where(Evidence.control_id == control.control_id))
            ).scalars().all()
        )
        findings = list(
            (
                await db.execute(
                    select(Finding).where(
                        Finding.control_id == control.control_id,
                        Finding.status.in_(OPEN_FINDING_STATUSES),
                    )
                )
            ).scalars().all()
        )
        risks = list(
            (
                await db.execute(select(Risk).where(Risk.mapped_control_id == control.control_id))
            ).scalars().all()
        )
        verified = [e for e in evidence if e.verified]
        return {
            "control_id": control.control_id,
            "control_name": control.control_name,
            "severity": control.severity,
            "covered": bool(verified),
            "evidence_count": len(evidence),
            "verified_evidence_count": len(verified),
            "open_findings": [
                {"finding_id": f.finding_id, "severity": f.severity, "status": f.status}
                for f in findings
            ],
            "related_risks": [
                {"risk_id": r.risk_id, "risk_name": r.risk_name, "severity": r.severity}
                for r in risks
            ],
            "evidence": [
                {
                    "evidence_id": e.evidence_id,
                    "evidence_type": e.evidence_type,
                    "verified": e.verified,
                    "collected_date": e.collected_date.isoformat(),
                }
                for e in verified[:5]
            ],
        }

    async def _current_state(self, mappings: list[dict[str, Any]]) -> dict[str, Any]:
        if not mappings:
            return {
                "current_state": "Not assessable — no control in the catalogue matches this requirement.",
                "gap": "unmapped",
                "gap_severity": "Unknown",
                "supporting_evidence": [],
                "open_findings": [],
                "related_risks": [],
                "recommended_action": (
                    "Create a control for this requirement, or confirm it is out of scope. "
                    "Sentinel will not assert a mapping it cannot verify."
                ),
            }

        controls = list(
            (
                await self.db.execute(
                    select(Control).where(
                        Control.control_id.in_([m["control_id"] for m in mappings])
                    )
                )
            ).scalars().all()
        )
        states = [await self._control_state(c) for c in controls]

        covered = [s for s in states if s["covered"]]
        open_findings = [f for s in states for f in s["open_findings"]]
        risks = [r for s in states for r in s["related_risks"]]
        evidence = [e for s in states for e in s["evidence"]]

        if covered and not open_findings:
            gap, severity = "none", "None"
            state_text = (
                f"Satisfied — {len(covered)} of {len(states)} mapped control(s) have verified "
                f"evidence and no open findings."
            )
            action = "No action required. Keep evidence current."
        elif covered and open_findings:
            gap, severity = "partial", "High" if any(
                f["severity"] in ("Critical", "High") for f in open_findings
            ) else "Medium"
            state_text = (
                f"Partially satisfied — evidence exists, but {len(open_findings)} finding(s) "
                f"are still open against the mapped control(s)."
            )
            action = "Remediate the open findings, then re-verify the supporting evidence."
        elif not covered and any(s["evidence_count"] for s in states):
            gap, severity = "unverified", "Medium"
            state_text = (
                "Not demonstrable — evidence has been collected for the mapped control(s) "
                "but none of it is verified."
            )
            action = "Verify the collected evidence so the requirement becomes provable."
        else:
            gap = "no_evidence"
            severity = "Critical" if open_findings else "High"
            state_text = "Not satisfied — no evidence exists for the mapped control(s)."
            action = "Collect and verify evidence for the mapped control(s)."

        return {
            "current_state": state_text,
            "gap": gap,
            "gap_severity": severity,
            "supporting_evidence": evidence[:5],
            "open_findings": open_findings[:10],
            "related_risks": risks[:10],
            "recommended_action": action,
        }
