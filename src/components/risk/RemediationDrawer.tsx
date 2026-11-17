import { ExternalLink, Sparkles, CheckCircle2 } from 'lucide-react';
import { Drawer } from '../ui/Drawer';
import { Button } from '../ui/Button';
import { Badge, RiskBadge } from '../ui/Badge';
import { FindingStatusBadge } from '../common/StatusPills';
import { formatRelative } from '../../utils/format';
import type { Finding } from '../../types/domain';
import { getRemediationIntelligence } from '../../services/api';
import { useApiResource } from '../../hooks/useApiResource';

export function RemediationDrawer({
  finding,
  onClose
}: {
  finding: Finding | null;
  onClose: () => void;
}) {
  const aiState = useApiResource(
    () => finding ? getRemediationIntelligence(finding.id).catch(e => null) : Promise.resolve(null),
    [finding?.id]
  );
  
  const remediationAi = aiState.data;

  return (
    <Drawer
      open={Boolean(finding)}
      onClose={onClose}
      width="xl"
      title={finding?.title ?? ''}
      subtitle={finding ? `${finding.id} · ${finding.asset} · updated ${formatRelative(finding.detectedAt)}` : undefined}
      eyebrow={
        finding ? (
          <div className="flex flex-wrap items-center gap-2">
            <RiskBadge level={finding.severity} />
            <FindingStatusBadge status={finding.status} />
            <Badge tone="primary">{finding.control}</Badge>
          </div>
        ) : undefined
      }
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
          <Button variant="outline" iconLeft={<ExternalLink className="h-4 w-4" />}>
            Open in graph
          </Button>
          <Button variant="ai" iconLeft={<Sparkles className="h-4 w-4" />}>
            Auto-remediate
          </Button>
        </>
      }
    >
      {finding && (
        <div className="space-y-6">
          {/* Finding details */}
          <div className="rounded-xl border border-border bg-surface-2/50 p-5">
             <dl className="grid grid-cols-2 gap-x-8 gap-y-4 text-[13px]">
                <div className="col-span-2">
                  <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                    Description
                  </dt>
                  <dd className="mt-1 font-medium">{remediationAi?.description || finding.title}</dd>
                </div>
                <div>
                  <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                    Owner
                  </dt>
                  <dd className="mt-0.5 font-medium">{finding.owner}</dd>
                </div>
                <div>
                  <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                    Source
                  </dt>
                  <dd className="mt-0.5 font-medium">{finding.source}</dd>
                </div>
              </dl>
          </div>

          {/* AI Remediation Plan */}
          {remediationAi && remediationAi.remediation_plan && (
            <div className="relative overflow-hidden rounded-xl border border-primary/20 bg-primary/5 p-5">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="h-4 w-4 text-primary" />
                <h4 className="text-sm font-semibold">Remediation Plan</h4>
                {remediationAi.remediation_plan.generated_by === "deterministic_rules_v1" ? 
                  <Badge tone="neutral" className="ml-auto">Deterministic</Badge> : 
                  <Badge tone="info" className="ml-auto">LLM Generated</Badge>
                }
              </div>
              
              <ul className="space-y-3">
                {remediationAi.remediation_plan.steps.map((step: string, index: number) => (
                  <li key={index} className="flex gap-3 text-[13px] text-slate-700 dark:text-slate-300">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-muted-foreground mt-0.5" />
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Related Context */}
          {remediationAi && (remediationAi.control_context?.control_name || (remediationAi.related_risks && remediationAi.related_risks.length > 0)) && (
            <div>
              <p className="mb-3 flex items-center gap-2 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                Related Context
                <span className="h-px flex-1 bg-border" aria-hidden />
              </p>
              
              <div className="space-y-4 rounded-xl border border-border p-4 bg-card">
                 {remediationAi.control_context?.control_name && (
                    <div>
                        <p className="text-xs text-muted-foreground mb-1">Failing Control</p>
                        <Badge tone="primary">{remediationAi.control_context.control_name}</Badge>
                    </div>
                 )}
                 
                 {remediationAi.related_risks && remediationAi.related_risks.length > 0 && (
                    <div>
                        <p className="text-xs text-muted-foreground mb-2">Exacerbated Risks</p>
                        <ul className="space-y-2">
                           {remediationAi.related_risks.map((r: any) => (
                              <li key={r.risk_id} className="flex items-center gap-2 text-[13px]">
                                 <RiskBadge level={r.severity} />
                                 <span className="font-medium">{r.risk_name}</span>
                                 <span className="text-muted-foreground ml-auto font-mono text-2xs">{r.risk_id}</span>
                              </li>
                           ))}
                        </ul>
                    </div>
                 )}
              </div>
            </div>
          )}
        </div>
      )}
    </Drawer>
  );
}
