import { ExternalLink, Sparkles } from 'lucide-react';
import { Drawer } from '../ui/Drawer';
import { Button } from '../ui/Button';
import { Badge, RiskBadge } from '../ui/Badge';
import { ProgressBar } from '../ui/Progress';
import { InvestigationChain } from '../cyber/InvestigationChain';
import { ConfidenceMeter, RiskStatusBadge } from '../common/StatusPills';
import { formatRelative } from '../../utils/format';
import { cn } from '../../utils/cn';
import type { RiskItem } from '../../types/domain';
import { getRiskIntelligence } from '../../services/api';
import { useApiResource } from '../../hooks/useApiResource';

/**
 * The investigation workspace. Opens from any risk row, top-risk card or
 * finding and shows the full POLICY â†’ ... â†’ RECOMMENDATION chain.
 */
export function InvestigationDrawer({
  risk,
  onClose



}: {risk: RiskItem | null;onClose: () => void;}) {

  const aiState = useApiResource(
    () => risk ? getRiskIntelligence(risk.id).catch(e => null) : Promise.resolve(null),
    [risk?.id]
  );
  
  let riskAi = aiState.data;
  let displayRisk = risk;

  if (risk?.id === 'demo-risk-1') {
    riskAi = {
      risk_id: 'demo-risk-1',
      ai_insight: 'Sentinel AI has determined that the main branch protection was disabled by an administrator 3 minutes ago. This violates the SOC 2 code change policy. Immediate remediation is recommended to restore require pull request reviews before merging.',
      llm_used: true
    } as any;
    
    displayRisk = {
      ...risk,
      chain: {
        policy: 'SOC 2 CC8.1: Code Change Management',
        control: 'Require Pull Request Reviews',
        finding: 'Branch protection disabled on `main`',
        asset: 'github.com/company/core-backend',
        evidence: 'GitHub Audit Log: `branch_protection_rule.destroy` by `admin@company.com`',
        impact: 'Direct commits to production branch bypass peer review and CI checks.',
        recommendation: 'Auto-remediate to enforce branch protection and require 1 reviewer.'
      }
    };
  }

  return (
    <Drawer
      open={Boolean(risk)}
      onClose={onClose}
      width="xl"
      title={displayRisk?.title ?? ''}
      subtitle={displayRisk ? `${displayRisk.id} · ${displayRisk.assetType} · updated ${formatRelative(displayRisk.updatedAt)}` : undefined}
      eyebrow={
      displayRisk ?
      <div className="flex flex-wrap items-center gap-2">
            <RiskBadge level={displayRisk.severity} />
            <RiskStatusBadge status={displayRisk.status} />
            <Badge tone="neutral">{displayRisk.framework}</Badge>
            <Badge tone="primary">{displayRisk.control}</Badge>
          </div> :
      undefined
      }
      footer={
      <>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
          <Button variant="outline" iconLeft={<ExternalLink className="h-4 w-4" />}>
            Open in graph
          </Button>
          <Button 
            variant="ai" 
            iconLeft={<Sparkles className="h-4 w-4" />}
            onClick={() => {
              if (displayRisk?.id === 'demo-risk-1') {
                window.dispatchEvent(new CustomEvent('remediate_demo_risk'));
              }
              onClose();
            }}
          >
            Auto-remediate
          </Button>
        </>
      }>
      
      {displayRisk &&
      <div className="space-y-6">
          {/* Score header */}
          <div className="relative overflow-hidden rounded-xl border border-border bg-surface-2/50 p-5">
            <div className="absolute inset-0 cyber-grid-fine opacity-40" aria-hidden />
            <div className="relative flex flex-wrap items-end justify-between gap-5">
              <div>
                <p className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                  Risk score
                </p>
                <p
                className={cn(
                  'mt-1 font-mono text-5xl font-semibold leading-none tracking-tight',
                  displayRisk.score >= 90 ?
                  'text-risk-critical' :
                  displayRisk.score >= 75 ?
                  'text-risk-high' :
                  'text-risk-medium'
                )}>
                
                  {displayRisk.score}
                  <span className="text-lg font-normal text-muted-foreground"> / 100</span>
                </p>
                <p className="mt-2 text-2xs font-semibold uppercase tracking-label text-risk-critical">
                  {displayRisk.severity}
                </p>
              </div>
              <dl className="grid grid-cols-2 gap-x-8 gap-y-2 text-[13px]">
                <div>
                  <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                    Owner
                  </dt>
                  <dd className="mt-0.5 font-medium">{displayRisk.owner}</dd>
                </div>
                <div>
                  <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                    Department
                  </dt>
                  <dd className="mt-0.5 font-medium">{displayRisk.department}</dd>
                </div>
                <div>
                  <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                    Asset
                  </dt>
                  <dd className="mt-0.5 truncate font-mono text-xs">{displayRisk.asset}</dd>
                </div>
                <div>
                  <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                    Sentinel confidence
                  </dt>
                  <dd className="mt-1">
                    <ConfidenceMeter value={displayRisk.aiConfidence ?? 0} />
                  </dd>
                </div>
              </dl>
            </div>
            <div className="relative mt-5 grid gap-3 sm:grid-cols-2">
              <ProgressBar
              label="Likelihood"
              value={displayRisk.likelihood * 20}
              tone="warning"
              showValue />
            
              <ProgressBar label="Impact" value={displayRisk.impact * 20} tone="danger" showValue />
            </div>
          </div>
          {/* AI Risk Intelligence */}
          {riskAi && riskAi.ai_insight && (
            <div className="relative overflow-hidden rounded-xl border border-primary/20 bg-primary/5 p-5">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="h-4 w-4 text-primary" />
                <h4 className="text-sm font-semibold">Sentinel AI Insight</h4>
                {riskAi.llm_used && <Badge tone="info" className="ml-auto">LLM Generated</Badge>}
              </div>
              <p className="text-[13px] text-slate-700 dark:text-slate-300">
                {riskAi.ai_insight}
              </p>
            </div>
          )}

          {/* Investigation chain */}
          <div>
            <p className="mb-3 flex items-center gap-2 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
              Investigation chain
              <span className="h-px flex-1 bg-border" aria-hidden />
            </p>
            <InvestigationChain chain={displayRisk.chain} />
          </div>
        </div>
      }
    </Drawer>);

}