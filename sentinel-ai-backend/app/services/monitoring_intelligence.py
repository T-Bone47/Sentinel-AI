"""
Continuous Monitoring Intelligence — Phase 2, Priority 5.

Retrospective analysis of the audit-log records already stored in the
database: high-risk actions and failed sensitive operations, and aggregate
counts. It does not watch events as they happen; nothing here is real-time
(finding F8, corrected 2026-11-17).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Application, Employee


class ContinuousMonitoringService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_anomalies(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Retrieves the most recent anomalous audit logs.
        Anomalies are defined heuristically as logs with a risk_score >= 80,
        or logs where a sensitive action failed.
        """
        stmt = (
            select(AuditLog, Employee, Application)
            .outerjoin(Employee, AuditLog.employee_id == Employee.employee_id)
            .outerjoin(Application, AuditLog.application_id == Application.application_id)
            .where(
                (AuditLog.risk_score >= 80) |
                (AuditLog.result == "Failure")
            )
            .order_by(desc(AuditLog.timestamp))
            .limit(limit)
        )
        
        results = await self.db.execute(stmt)
        
        anomalies = []
        for row in results.all():
            log: AuditLog = row.AuditLog
            emp: Employee | None = row.Employee
            app: Application | None = row.Application
            
            anomalies.append({
                "log_id": log.log_id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "action": log.action,
                "result": log.result,
                "risk_score": log.risk_score,
                "ip_address": log.ip_address,
                "geo_location": log.geo_location,
                "employee": {
                    "employee_id": emp.employee_id,
                    "name": f"{emp.first_name} {emp.last_name}",
                    "department": emp.department,
                } if emp else None,
                "application": {
                    "application_id": app.application_id,
                    "name": app.application_name,
                } if app else None,
                "anomaly_reason": self._determine_anomaly_reason(log)
            })
            
        return anomalies

    async def get_metrics(self) -> dict[str, Any]:
        """
        Aggregates high-level metrics for a continuous monitoring dashboard.
        """
        # Total anomalies (risk_score >= 80 or result == 'Failure')
        anomalies_count_stmt = select(func.count()).select_from(AuditLog).where(
            (AuditLog.risk_score >= 80) | (AuditLog.result == "Failure")
        )
        total_anomalies = await self.db.scalar(anomalies_count_stmt) or 0
        
        # High risk actions specifically
        high_risk_count_stmt = select(func.count()).select_from(AuditLog).where(
            AuditLog.risk_score >= 80
        )
        total_high_risk = await self.db.scalar(high_risk_count_stmt) or 0
        
        # Failed actions specifically
        failed_count_stmt = select(func.count()).select_from(AuditLog).where(
            AuditLog.result == "Failure"
        )
        total_failed = await self.db.scalar(failed_count_stmt) or 0
        
        # Top anomalous actions
        top_actions_stmt = (
            select(AuditLog.action, func.count(AuditLog.log_id).label("count"))
            .where((AuditLog.risk_score >= 80) | (AuditLog.result == "Failure"))
            .group_by(AuditLog.action)
            .order_by(desc("count"))
            .limit(5)
        )
        top_actions_result = await self.db.execute(top_actions_stmt)
        top_actions = [{"action": row.action, "count": row.count} for row in top_actions_result.all()]
        
        return {
            "total_anomalies": total_anomalies,
            "high_risk_events": total_high_risk,
            "failed_operations": total_failed,
            "top_anomalous_actions": top_actions,
            # Finding F8: this filters audit-log rows already in the database.
            # Nothing watches events as they happen, so nothing may say "Active".
            "mode": "retrospective",
            "mode_note": "Computed from audit-log records already stored; nothing here watches events as they happen.",
            "generated_by": "deterministic_monitoring_v1"
        }

    @staticmethod
    def _determine_anomaly_reason(log: AuditLog) -> str:
        reasons = []
        if log.risk_score >= 80:
            reasons.append(f"High risk score ({log.risk_score})")
        if log.result == "Failure":
            reasons.append(f"Failed operation ({log.action})")
        
        return " and ".join(reasons) if reasons else "Unknown anomaly"
