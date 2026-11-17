"""
Sentinel Orchestrator — Phase 2, Priority 8.

The "State of the Union" service. Aggregates data from Trust, Risk,
Continuous Monitoring, Evidence, and Remediation engines into a single
executive summary. Optionally uses the LLM to narrate the results.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.trust_intelligence import TrustIntelligenceService
from app.services.risk_intelligence import RiskIntelligenceService
from app.services.evidence_intelligence import EvidenceIntelligenceService
from app.services.remediation_intelligence import RemediationIntelligenceService
from app.services.monitoring_intelligence import ContinuousMonitoringService
from app.services.llm_service import LLMService


class SentinelOrchestratorService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = LLMService()

    async def generate_executive_summary(self) -> dict[str, Any]:
        """
        Gathers the most critical data from all intelligence services
        and returns a unified state of the union payload.
        """
        # Gather deterministic intelligence
        trust_data = await TrustIntelligenceService(self.db).build()
        risk_data = await RiskIntelligenceService(self.db).top_risks(limit=3)
        monitoring_metrics = await ContinuousMonitoringService(self.db).get_metrics()
        monitoring_anomalies = await ContinuousMonitoringService(self.db).get_anomalies(limit=3)
        remediation_data = await RemediationIntelligenceService(self.db).top_remediations(limit=3)
        evidence_data = await EvidenceIntelligenceService(self.db).summary(gap_limit=3)

        payload = {
            "trust_posture": {
                "score": trust_data["trust_score"],
                "level": trust_data["trust_level"],
                "change": trust_data["score_change"]
            },
            "top_risks": risk_data,
            "active_threats": {
                "metrics": monitoring_metrics,
                "recent_anomalies": monitoring_anomalies
            },
            "immediate_remediations": remediation_data,
            "evidence_gaps": evidence_data["top_gaps"]
        }

        # Attempt to narrate the summary with the LLM
        narrative = self._fallback_narrative(payload)
        llm_used = False

        if self.llm.is_configured:
            system_prompt = (
                "You are the Sentinel AI executive orchestrator. Read the following JSON payload "
                "containing the current GRC state of the organization. Write a 2-3 sentence executive summary "
                "highlighting the most critical insights (trust score, top risks, and immediate threats). "
                "Do not use markdown formatting. Be concise, objective, and action-oriented."
            )
            # We use complete_structured to pass a raw text system prompt and get a raw string back
            llm_response = await self.llm.complete_structured(
                system_prompt=system_prompt,
                user_message=json.dumps(payload, default=str),
                max_tokens=600
            )
            if llm_response:
                narrative = llm_response.strip()
                llm_used = True

        return {
            "executive_summary": narrative,
            "llm_used": llm_used,
            "posture": payload
        }

    @staticmethod
    def _fallback_narrative(payload: dict[str, Any]) -> str:
        score = payload["trust_posture"]["score"]
        level = payload["trust_posture"]["level"]
        anomalies_count = payload["active_threats"]["metrics"]["total_anomalies"]
        risks_count = len(payload["top_risks"])
        remediations_count = len(payload["immediate_remediations"])
        
        return (
            f"The organization is currently at a {level} trust level with a score of {score}. "
            f"There are {anomalies_count} active anomalies requiring investigation, and "
            f"{risks_count} critical risks identified. "
            f"Prioritize the {remediations_count} immediate remediation actions to improve compliance posture."
        )
