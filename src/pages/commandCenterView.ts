/**
 * Command Center view model.
 *
 * Turns the backend's /dashboard aggregate into exactly the shapes the
 * existing Command Center components expect. Every number below traces to a
 * live COUNT or GROUP BY in Postgres — this file does no invention, and
 * where the backend genuinely has no answer (score history, for instance)
 * the field is omitted so the UI can hide it rather than fill it in.
 */

import type { FlowNode } from '../components/cyber/FlowChain';
import type { DashboardView } from '../services/api';
import type { Kpi, StreamEvent, TrustDomain } from '../types/domain';

function posture(ratio: number): TrustDomain['status'] {
  if (ratio >= 0.8) return 'trusted';
  if (ratio >= 0.6) return 'warning';
  return 'critical';
}

function pct(numerator: number, denominator: number): number {
  return denominator ? numerator / denominator : 0;
}

export interface CommandCenterView {
  trustScore: {
    value: number;
    max: number;
    band: string;
    updatedAt: string;
    signalsEvaluated: number;
    engine: string;
    formula: string;
    note: string;
    components: DashboardView['trustScore']['components'];
  };
  auditReadiness: DashboardView['auditReadiness'];
  trustDomains: TrustDomain[];
  executiveKpis: Kpi[];
  threatStream: StreamEvent[];
  topologyNodes: FlowNode[];
  frameworkScores: DashboardView['frameworkScores'];
  headline: string;
}

export function buildCommandCenterView(dashboard: DashboardView): CommandCenterView {
  const d = dashboard.raw;
  const assets = d.asset_statistics;
  const employees = assets.employees;
  const devices = assets.devices;
  const cloud = assets.cloud_assets;
  const apps = assets.applications;
  const iam = d.iam_statistics;
  const vendors = d.vendor_risk;
  const privacy = d.privacy_statistics;

  /* ------------------------------------------------------- trust domains */
  // Each domain is a real ratio over real counts, with the underlying numbers
  // spelled out in `detail` so nothing is a black box.
  const identityRatio = pct(iam.mfa_enabled, iam.total);
  const peopleRatio = pct(employees.mfa_enabled, employees.total);
  const deviceRatio = pct(devices.compliant, devices.total);
  const appRatio = pct(apps.encrypted, apps.total);
  const cloudRatio = pct(cloud.total - cloud.public_access, cloud.total);
  const vendorRatio = pct(vendors.iso27001_certified, vendors.total);
  const policyRatio = pct(
    d.compliance_coverage.controls_with_evidence,
    d.compliance_coverage.total_controls
  );

  const trustDomains: TrustDomain[] = [
    {
      id: 'identity',
      label: 'Identity',
      score: Math.round(identityRatio * 100),
      delta: 0,
      status: posture(identityRatio),
      detail: `${iam.mfa_enabled}/${iam.total} with MFA · ${iam.privileged_without_mfa} privileged gaps`
    },
    {
      id: 'people',
      label: 'People',
      score: Math.round(peopleRatio * 100),
      delta: 0,
      status: posture(peopleRatio),
      detail: `${employees.total} employees · ${employees.active} active`
    },
    {
      id: 'devices',
      label: 'Devices',
      score: Math.round(deviceRatio * 100),
      delta: 0,
      status: posture(deviceRatio),
      detail: `${devices.compliant}/${devices.total} compliant · ${devices.encrypted} encrypted`
    },
    {
      id: 'applications',
      label: 'Applications',
      score: Math.round(appRatio * 100),
      delta: 0,
      status: posture(appRatio),
      detail: `${apps.total} apps · ${apps.internet_facing} internet-facing`
    },
    {
      id: 'cloud',
      label: 'Cloud',
      score: Math.round(cloudRatio * 100),
      delta: 0,
      status: posture(cloudRatio),
      detail: `${cloud.public_access} public · ${cloud.logging_enabled}/${cloud.total} logging`
    },
    {
      id: 'vendors',
      label: 'Vendors',
      score: Math.round(vendorRatio * 100),
      delta: 0,
      status: posture(vendorRatio),
      detail: `${vendors.total} vendors · ${vendors.contracts_expiring_90d} expiring in 90d`
    },
    {
      id: 'policies',
      label: 'Governance',
      score: Math.round(policyRatio * 100),
      delta: 0,
      status: posture(policyRatio),
      detail: `${d.compliance_coverage.controls_with_evidence}/${d.compliance_coverage.total_controls} controls evidenced`
    }
  ];

  /* --------------------------------------------------------------- KPIs */
  // `delta` is 0 and `spark` is flat throughout: Phase 1 stores a single
  // snapshot, so there is no prior period to compare against. Showing an
  // invented trend on the hero metrics would be the exact dishonesty this
  // integration is meant to remove.
  const flat = [0, 0, 0, 0, 0, 0, 0];
  const executiveKpis: Kpi[] = [
    {
      id: 'critical-risks',
      label: 'Critical risks',
      value: d.risks.critical,
      delta: 0,
      direction: 'flat',
      positiveIsGood: false,
      caption: `${d.risks.open} open of ${d.risks.total} registered`,
      status: d.risks.critical > 0 ? 'critical' : 'trusted',
      spark: flat
    },
    {
      id: 'open-findings',
      label: 'Open findings',
      value: d.findings.open,
      delta: 0,
      direction: 'flat',
      positiveIsGood: false,
      caption: `${d.findings.critical_open} critical · ${d.findings.high_open} high`,
      status: d.findings.severe_open > 0 ? 'warning' : 'trusted',
      spark: flat
    },
    {
      id: 'evidence-coverage',
      label: 'Evidence coverage',
      value: d.evidence_coverage.coverage_pct,
      suffix: '%',
      delta: 0,
      direction: 'flat',
      positiveIsGood: true,
      caption: `${d.evidence_coverage.controls_with_evidence}/${d.evidence_coverage.total_controls} controls evidenced`,
      status: posture(d.evidence_coverage.coverage_pct / 100),
      spark: flat
    },
    {
      id: 'audit-readiness',
      label: 'Audit readiness',
      value: dashboard.auditReadiness.value ?? 0,
      suffix: '%',
      delta: 0,
      direction: 'flat',
      positiveIsGood: true,
      caption: `${d.evidence_coverage.verified_pct}% of evidence verified`,
      status: posture((dashboard.auditReadiness.value ?? 0) / 100),
      spark: flat
    }
  ];

  /* ------------------------------------------------------- live activity */
  const threatStream: StreamEvent[] = (d.recent_audit_activity.recent ?? []).map((event) => ({
    id: event.log_id,
    time: event.timestamp,
    severity:
      event.risk_score >= 80
        ? 'critical'
        : event.risk_score >= 60
          ? 'high'
          : event.risk_score >= 40
            ? 'medium'
            : 'low',
    title: `${event.action} — ${event.result} (risk ${event.risk_score})`,
    source: event.geo_location || 'Audit log'
  }));

  /* ----------------------------------------------------------- topology */
  // The real governance chain, with real counts at each hop.
  const topologyNodes: FlowNode[] = [
    {
      id: 'policy',
      label: 'Policies',
      value: String(d.totals.policies),
      status: 'trusted'
    },
    {
      id: 'control',
      label: 'Controls',
      value: String(d.totals.controls),
      status: d.compliance_coverage.failed_controls > 0 ? 'warning' : 'trusted'
    },
    {
      id: 'finding',
      label: 'Findings',
      value: String(d.findings.open),
      status: d.findings.severe_open > 0 ? 'critical' : 'warning'
    },
    {
      id: 'evidence',
      label: 'Evidence',
      value: String(d.totals.evidence),
      status: d.evidence_coverage.coverage_pct >= 80 ? 'trusted' : 'warning'
    },
    {
      id: 'risk',
      label: 'Risks',
      value: String(d.risks.open),
      status: d.risks.critical > 0 ? 'critical' : 'warning'
    }
  ];

  /* ----------------------------------------------------------- headline */
  // A factual sentence assembled from the largest real signals. Deliberately
  // not framed as an AI insight — Phase 1 has no model.
  const headline = buildHeadline(d);

  return {
    trustScore: {
      value: dashboard.trustScore.value ?? 0,
      max: 100,
      band: dashboard.trustScore.band,
      updatedAt: d.generated_at,
      signalsEvaluated: Object.values(d.totals).reduce((sum, n) => sum + n, 0),
      engine: dashboard.trustScore.engine,
      formula: dashboard.trustScore.formula,
      note: dashboard.trustScore.note,
      components: dashboard.trustScore.components
    },
    auditReadiness: dashboard.auditReadiness,
    trustDomains,
    executiveKpis,
    threatStream,
    topologyNodes,
    frameworkScores: dashboard.frameworkScores,
    headline
  };
}

function buildHeadline(d: DashboardView['raw']): string {
  const parts: string[] = [];
  if (d.findings.severe_open > 0) {
    parts.push(
      `${d.findings.severe_open} critical/high findings are open across ${d.compliance_coverage.failed_controls} failing controls`
    );
  }
  if (d.iam_statistics.privileged_without_mfa > 0) {
    parts.push(
      `${d.iam_statistics.privileged_without_mfa} privileged identities have no MFA`
    );
  }
  if (d.asset_statistics.cloud_assets.public_access > 0) {
    parts.push(
      `${d.asset_statistics.cloud_assets.public_access} cloud assets are publicly accessible`
    );
  }
  if (!parts.length) {
    return `No critical exposures open across ${d.totals.controls} controls.`;
  }
  return `${parts.slice(0, 2).join('; ')}. Evidence covers ${d.evidence_coverage.coverage_pct}% of controls.`;
}
