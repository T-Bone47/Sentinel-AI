import { AlertTriangle, Check, X } from 'lucide-react';
import { cn } from '../../utils/cn';
import { Badge, type BadgeTone } from '../ui/Badge';
import type {
  CheckState,
  ComplianceStatus,
  Control,
  EvidenceItem,
  Finding,
  PolicyStatus,
  RiskItem,
  Vendor } from
'../../types/domain';

/* ------------------------------------------------ quick âœ“ / âš  / âœ• indicators */

export function CheckPill({
  state,
  label,
  className




}: {state: CheckState;label?: string;className?: string;}) {
  const config = {
    pass: { icon: Check, tone: 'text-success border-success/35 bg-success/10' },
    warn: { icon: AlertTriangle, tone: 'text-warning border-warning/35 bg-warning/10' },
    fail: { icon: X, tone: 'text-risk-critical border-risk-critical/35 bg-risk-critical/10' }
  }[state];
  const Icon = config.icon;

  return (
    <span
      className={cn('inline-flex items-center gap-1.5', className)}
      title={label ?? state}>
      
      <span
        className={cn(
          'flex h-5 w-5 items-center justify-center rounded-md border',
          config.tone
        )}>
        
        <Icon className="h-3 w-3" strokeWidth={3} aria-hidden />
      </span>
      {label && <span className="text-[13px] text-muted-foreground">{label}</span>}
      <span className="sr-only">{state}</span>
    </span>);

}

/* --------------------------------------------------------------- status maps */

const complianceCopy: Record<ComplianceStatus, {label: string;tone: BadgeTone;}> = {
  compliant: { label: 'Compliant', tone: 'success' },
  'at-risk': { label: 'At risk', tone: 'warning' },
  'non-compliant': { label: 'Non-compliant', tone: 'danger' },
  'not-assessed': { label: 'Not assessed', tone: 'neutral' }
};

export function ComplianceStatusBadge({ status }: {status: ComplianceStatus;}) {
  const { label, tone } = complianceCopy[status];
  return (
    <Badge tone={tone} dot>
      {label}
    </Badge>);

}

const policyCopy: Record<PolicyStatus, {label: string;tone: BadgeTone;}> = {
  published: { label: 'Published', tone: 'success' },
  'in-review': { label: 'In review', tone: 'primary' },
  draft: { label: 'Draft', tone: 'neutral' },
  archived: { label: 'Archived', tone: 'neutral' }
};

export function PolicyStatusBadge({ status }: {status: PolicyStatus;}) {
  const { label, tone } = policyCopy[status];
  return (
    <Badge tone={tone} dot>
      {label}
    </Badge>);

}

const controlCopy: Record<Control['status'], {label: string;tone: BadgeTone;}> = {
  passing: { label: 'Passing', tone: 'success' },
  failing: { label: 'Failing', tone: 'danger' },
  partial: { label: 'Partial', tone: 'warning' },
  'not-tested': { label: 'Not tested', tone: 'neutral' }
};

export function ControlStatusBadge({ status }: {status: Control['status'];}) {
  const { label, tone } = controlCopy[status];
  return (
    <Badge tone={tone} dot>
      {label}
    </Badge>);

}

const riskStatusCopy: Record<RiskItem['status'], {label: string;tone: BadgeTone;}> = {
  open: { label: 'Open', tone: 'danger' },
  investigating: { label: 'Investigating', tone: 'primary' },
  mitigating: { label: 'Mitigating', tone: 'warning' },
  accepted: { label: 'Accepted', tone: 'neutral' },
  closed: { label: 'Closed', tone: 'success' }
};

export function RiskStatusBadge({ status }: {status: RiskItem['status'];}) {
  const { label, tone } = riskStatusCopy[status];
  return <Badge tone={tone}>{label}</Badge>;
}

const findingCopy: Record<Finding['status'], {label: string;tone: BadgeTone;}> = {
  open: { label: 'Open', tone: 'danger' },
  'in-progress': { label: 'In progress', tone: 'primary' },
  resolved: { label: 'Resolved', tone: 'success' },
  suppressed: { label: 'Suppressed', tone: 'neutral' }
};

export function FindingStatusBadge({ status }: {status: Finding['status'];}) {
  const { label, tone } = findingCopy[status];
  return <Badge tone={tone}>{label}</Badge>;
}

const evidenceCopy: Record<EvidenceItem['status'], {label: string;tone: BadgeTone;}> = {
  verified: { label: 'Verified', tone: 'success' },
  pending: { label: 'Pending', tone: 'primary' },
  expiring: { label: 'Expiring', tone: 'warning' },
  expired: { label: 'Expired', tone: 'danger' }
};

export function EvidenceStatusBadge({ status }: {status: EvidenceItem['status'];}) {
  const { label, tone } = evidenceCopy[status];
  return (
    <Badge tone={tone} dot>
      {label}
    </Badge>);

}

const vendorCopy: Record<Vendor['certificationStatus'], {label: string;tone: BadgeTone;}> = {
  compliant: { label: 'Compliant', tone: 'success' },
  expiring: { label: 'Expiring', tone: 'warning' },
  expired: { label: 'Expired', tone: 'danger' },
  'high-risk': { label: 'High risk', tone: 'danger' }
};

export function VendorStatusBadge({
  status


}: {status: Vendor['certificationStatus'];}) {
  const { label, tone } = vendorCopy[status];
  return (
    <Badge tone={tone} dot>
      {label}
    </Badge>);

}

/* ------------------------------------------------------------------ AI meter */

export function ConfidenceMeter({
  value,
  className



}: {value: number;className?: string;}) {
  return (
    <span
      className={cn('inline-flex items-center gap-2', className)}
      title={`Sentinel confidence ${value}%`}>
      
      <span className="h-1.5 w-14 overflow-hidden rounded-full bg-ai/15">
        <span
          className="block h-full rounded-full bg-ai"
          style={{ width: `${Math.min(100, value)}%` }} />
        
      </span>
      <span className="font-mono text-2xs text-ai">{value}%</span>
    </span>);

}

/** Numeric risk score with severity-tinted emphasis. */
export function RiskScore({ score, className }: {score: number;className?: string;}) {
  const tone =
  score >= 90 ?
  'text-risk-critical' :
  score >= 75 ?
  'text-risk-high' :
  score >= 50 ?
  'text-risk-medium' :
  'text-muted-foreground';
  return (
    <span className={cn('font-mono text-sm font-semibold tabular-nums', tone, className)}>
      {score}
    </span>);

}