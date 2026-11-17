import { ArrowRight, Sparkles } from 'lucide-react';
import { cn } from '../../utils/cn';
import { formatRelative } from '../../utils/format';
import type { AiInsight } from '../../types/domain';
import { Card } from '../ui/Card';
import { Badge, RiskBadge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { ConfidenceMeter } from '../common/StatusPills';

export function AiInsightCard({
  insight,
  index = 0,
  onAction,
  compact = false





}: {insight: AiInsight;index?: number;onAction?: (insight: AiInsight) => void;compact?: boolean;}) {
  return (
    <Card
      tone="ai"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: index * 0.05, ease: [0.22, 1, 0.36, 1] }}
      className={cn('flex flex-col p-5 transition-shadow hover:ai-glow', compact && 'p-4')}>
      
      <div className="flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-md ai-gradient text-white">
          <Sparkles className="h-3.5 w-3.5" aria-hidden />
        </span>
        <Badge tone="ai">{insight.category}</Badge>
        <RiskBadge level={insight.impact} withDot={false} />
        <span className="ml-auto text-2xs text-muted-foreground">
          {formatRelative(insight.createdAt)}
        </span>
      </div>
      <h3 className="mt-3 text-[13px] font-semibold leading-snug text-foreground">
        {insight.title}
      </h3>
      {!compact &&
      <p className="mt-2 flex-1 text-xs leading-relaxed text-muted-foreground">
          {insight.summary}
        </p>
      }
      <div className="mt-4 flex items-center justify-between gap-3">
        <ConfidenceMeter value={insight.confidence} />
        <Button
          variant="ghost"
          size="xs"
          className="text-ai hover:bg-ai/10 hover:text-ai"
          onClick={() => onAction?.(insight)}
          iconRight={<ArrowRight className="h-3.5 w-3.5" />}>
          
          Review
        </Button>
      </div>
    </Card>);

}