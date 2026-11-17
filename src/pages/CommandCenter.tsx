import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  FileBarChart,
  Network,
  RadioTower,
  ScanLine,
  Sparkles } from
'lucide-react';
import { PageHeader, MetaStat } from '../components/layout/PageHeader';
import { SectionCard } from '../components/common/SectionCard';
import { MetricCard } from '../components/common/MetricCard';
import { TrustScore } from '../components/cyber/TrustScore';
import { TrustPosture } from '../components/cyber/TrustPosture';
import { ThreatStream } from '../components/cyber/ThreatStream';
import { FlowChain } from '../components/cyber/FlowChain';
import { InvestigationDrawer } from '../components/risk/InvestigationDrawer';
import { Button } from '../components/ui/Button';
import { Badge, RiskBadge } from '../components/ui/Badge';
import { MonitoringStatus } from '../components/layout/Header';
import { RiskScore, RiskStatusBadge } from '../components/common/StatusPills';
import { formatRelative } from '../utils/format';
import { cn } from '../utils/cn';
import type { RiskItem } from '../types/domain';
import { getDashboard, getRisks, getOrchestratorSummary, getTrustIntelligence } from '../services/api';
import { useApiResource } from '../hooks/useApiResource';
import { AsyncSection } from '../components/common/AsyncSection';
import { buildCommandCenterView } from './commandCenterView';

export function CommandCenter() {
  const [activeRisk, setActiveRisk] = useState<RiskItem | null>(null);

  // Two live calls: the aggregate dashboard, and the top critical risks the
  // reviewer will click into. Both hit Postgres — nothing here is seeded.
  const state = useApiResource(
    () =>
      Promise.all([
        getDashboard(),
        getRisks({ severity: 'Critical', page_size: 6, sort: 'risk_id' }),
        getOrchestratorSummary().catch(() => null),
        getTrustIntelligence().catch(() => null)
      ]).then(([dashboard, risks, orchestrator, trustAi]) => ({ dashboard, risks: risks.data, orchestrator, trustAi })),
    []
  );

  if (state.status !== 'success' || !state.data) {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  const { dashboard, risks, orchestrator, trustAi } = state.data;
  const view = buildCommandCenterView(dashboard);
  let {
    trustScore,
    trustDomains,
    executiveKpis,
    threatStream,
    topologyNodes,
    frameworkScores,
    headline
  } = view;

  const finalTrustScore = trustAi ? trustAi.trust_score : trustScore.value;
  let topRisks = risks.slice(0, 4);
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow={
        <>
            <MonitoringStatus />
            <Badge tone="ai">
              <Sparkles className="h-3 w-3" aria-hidden />
              Sentinel analysing continuously
            </Badge>
          </>
        }
        title="Command Center"
        subtitle="Continuous trust across people, identity, devices, applications, cloud, vendors, policies, controls and evidence."
        meta={
        <>
            <MetaStat
            label="Aggregated"
            value={formatRelative(trustScore.updatedAt)}
            icon={<ScanLine className="h-3.5 w-3.5" aria-hidden />} />
          
            <MetaStat
            label="Records evaluated"
            value={trustScore.signalsEvaluated.toLocaleString()}
            icon={<RadioTower className="h-3.5 w-3.5" aria-hidden />} />
          
            <MetaStat label="Datasets" value="15" />
          </>
        }
        actions={
        <>
            <Button variant="outline" iconLeft={<FileBarChart className="h-4 w-4" />}>
              Generate report
            </Button>
            <Button variant="primary" iconLeft={<ScanLine className="h-4 w-4" />}>
              Run assessment
            </Button>
          </>
        } />
      

      {/* ---------------------------------------------------------------- HERO */}
      <div className="grid gap-4 xl:grid-cols-12">
        <motion.section
          aria-label="Organization trust score"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          className="scanlines relative overflow-hidden rounded-xl border border-border bg-card xl:col-span-8">
          
          <div className="absolute inset-0 cyber-grid mask-fade opacity-70" aria-hidden />
          <div
            className="pointer-events-none absolute inset-y-0 -left-1/3 w-1/3 bg-gradient-to-r from-transparent via-primary/[0.07] to-transparent motion-safe:animate-sweep"
            aria-hidden />
          
          <div className="flex flex-col items-center justify-center pt-10 pb-12 relative z-10">
            {orchestrator && orchestrator.executive_summary && (
              <div className="max-w-3xl text-center mb-10 px-6">
                <Badge tone="info" className="mb-4">
                  <Sparkles className="h-3.5 w-3.5 mr-1.5 inline-block" /> 
                  {orchestrator.llm_used ? 'Sentinel AI Executive Summary' : 'System Summary'}
                </Badge>
                <p className="text-lg text-foreground/90 font-medium leading-relaxed">
                  {orchestrator.executive_summary}
                </p>
              </div>
            )}
            
            <TrustScore 
              score={finalTrustScore}
              max={trustScore.max}
              band={trustAi ? trustAi.trust_level : trustScore.band}
              domains={trustDomains}
              signals={trustScore.signalsEvaluated}
            />
          </div>
          <div className="relative border-t border-border/70 px-4 py-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                What the score is made of
              </p>
              <p
                className="font-mono text-2xs text-muted-foreground"
                title={`${trustScore.formula} · ${trustScore.note}`}>
                {trustScore.engine} · {trustScore.formula}
              </p>
            </div>
            {/* Real contributors, straight from the backend's published
                weights and components. Hovering the engine label shows the
                formula so the number is auditable, not asserted. */}
            <ul className="space-y-2">
              {trustScore.components.map((component) =>
              <li key={component.id}>
                  <div className="flex items-baseline justify-between gap-3 text-xs">
                    <span className="truncate text-muted-foreground">{component.label}</span>
                    <span className="shrink-0 font-mono text-foreground">
                      {Math.round(component.ratio * 100)}%
                      <span className="ml-1.5 text-muted-foreground">
                        × {component.weight} = {component.points} pts
                      </span>
                    </span>
                  </div>
                  <div className="mt-1 h-1 overflow-hidden rounded-full bg-surface-3">
                    <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.round(component.ratio * 100)}%` }}
                    transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                    className={cn(
                      'h-full rounded-full',
                      component.ratio >= 0.8 ?
                      'bg-success' :
                      component.ratio >= 0.6 ?
                      'bg-warning' :
                      'bg-risk-critical'
                    )} />
                  
                  </div>
                </li>
              )}
            </ul>
          </div>
        </motion.section>

        {/* Live stream */}
        <SectionCard
          title="Live risk stream"
          description="Signals as they arrive from connected sources"
          className="xl:col-span-4"
          delay={0.08}
          bodyClassName="pt-0"
          actions={<MonitoringStatus compact />}>
          
          <div className="max-h-[420px] overflow-y-auto pr-1">
            <ThreatStream events={threatStream} />
          </div>
        </SectionCard>
      </div>

      {/* ------------------------------------------------- EXECUTIVE METRICS */}
      <section aria-label="Executive metrics" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {executiveKpis.map((kpi, i) =>
        <MetricCard key={kpi.id} kpi={kpi} index={i} />
        )}
      </section>

      {/* ----------------------------------------------- POSTURE + TOP RISKS */}
      <div className="grid gap-4 xl:grid-cols-12">
        <SectionCard
          title="Trust posture"
          description="Score, trend and status by domain"
          className="xl:col-span-5"
          delay={0.05}>
          
          <TrustPosture domains={trustDomains} />
        </SectionCard>

        <SectionCard
          title="Top risks"
          description="Highest-scoring open exposures across the estate"
          className="xl:col-span-7"
          delay={0.1}
          bodyClassName="px-0 pb-0"
          actions={
          <Link
            to="/risk"
            className="flex items-center gap-1 text-xs font-medium text-primary hover:underline">
            
              Risk Center
              <ArrowRight className="h-3.5 w-3.5" aria-hidden />
            </Link>
          }>
          
          <ul className="divide-y divide-border border-t border-border">
            {topRisks.map((risk) =>
            <li key={risk.id}>
                <button
                type="button"
                onClick={() => setActiveRisk(risk)}
                className="group flex w-full items-center gap-4 px-5 py-3 text-left transition-colors duration-150 hover:bg-primary/[0.05]">
                
                  <span className="w-[86px] shrink-0">
                    <RiskBadge level={risk.severity} withDot={false} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13px] font-medium">
                      {risk.title}
                    </span>
                    <span className="mt-0.5 flex items-center gap-2 truncate font-mono text-2xs text-muted-foreground">
                      {risk.id}
                      <span className="text-border-strong">”¢</span>
                      {risk.asset}
                      <span className="text-border-strong">”¢</span>
                      {risk.owner}
                    </span>
                  </span>
                  <span className="hidden shrink-0 md:block">
                    <RiskStatusBadge status={risk.status} />
                  </span>
                  <span className="shrink-0 text-right">
                    <RiskScore score={risk.score} />
                    <span className="block text-[10px] uppercase tracking-label text-muted-foreground">
                      risk
                    </span>
                  </span>
                  <ArrowRight
                  className="h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-180 group-hover:translate-x-0.5 group-hover:text-primary"
                  aria-hidden />
                
                </button>
              </li>
            )}
          </ul>
        </SectionCard>
      </div>

      {/* -------------------------------------------- COMPLIANCE + TOPOLOGY */}
      <div className="grid gap-4 xl:grid-cols-12">
        <SectionCard
          title="Framework coverage"
          description="Control coverage against each adopted framework"
          className="xl:col-span-5"
          delay={0.05}
          actions={
          <Link
            to="/frameworks"
            className="text-xs font-medium text-primary hover:underline">
            
              Frameworks
            </Link>
          }>
          
          <ul className="space-y-4">
            {frameworkScores.map((framework) =>
            <li key={framework.id}>
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-[13px] font-medium">{framework.name}</span>
                  <span
                  className={cn(
                    'font-mono text-[15px] font-semibold',
                    framework.coverage >= 90 ?
                    'text-success' :
                    framework.coverage >= 80 ?
                    'text-warning' :
                    'text-risk-critical'
                  )}>
                  
                    {framework.coverage}%
                  </span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-3">
                  <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${framework.coverage}%` }}
                  transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                  className={cn(
                    'h-full rounded-full',
                    framework.coverage >= 90 ?
                    'bg-success' :
                    framework.coverage >= 80 ?
                    'bg-warning' :
                    'bg-risk-critical'
                  )} />
                
                </div>
                <p className="mt-1.5 font-mono text-2xs text-muted-foreground">
                  {framework.passed} passed · {framework.failed} failed ·{' '}
                  {framework.evidence} evidence
                </p>
              </li>
            )}
          </ul>
        </SectionCard>

        <SectionCard
          title="System topology"
          description="How trust propagates from people to evidence"
          className="xl:col-span-7"
          delay={0.1}
          actions={
          <Link
            to="/graph"
            className="flex items-center gap-1 text-xs font-medium text-primary hover:underline">
            
              <Network className="h-3.5 w-3.5" aria-hidden />
              Explore graph
            </Link>
          }>
          
          <div className="relative overflow-hidden rounded-lg border border-border/70 bg-surface-2/40 p-4">
            <div className="absolute inset-0 cyber-dots opacity-40" aria-hidden />
            <FlowChain nodes={topologyNodes} className="relative" />
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-ai-border/50 bg-ai-surface/30 px-3.5 py-2.5">
            <p className="flex items-start gap-2 text-xs leading-relaxed text-muted-foreground">
              <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ai" aria-hidden />
              <span>
                <span className="font-medium text-foreground">Sentinel:</span>{' '}
                {headline}
              </span>
            </p>
            <Link to="/copilot">
              <Button
                variant="ghost"
                size="xs"
                className="text-ai hover:bg-ai/10 hover:text-ai"
                iconRight={<ArrowRight className="h-3.5 w-3.5" />}>
                
                Ask why
              </Button>
            </Link>
          </div>
        </SectionCard>
      </div>

      <InvestigationDrawer risk={activeRisk} onClose={() => setActiveRisk(null)} />
    </div>);

}