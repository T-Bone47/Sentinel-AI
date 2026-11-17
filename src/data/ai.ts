import type { AiInsight, NotificationItem, RiskLevel } from '../types/domain';

export const aiInsights: AiInsight[] = [
{
  id: 'AI-501',
  title: 'Trust Score will fall below 84 within 6 days unless cloud exposure is closed',
  summary:
  'The public claim archive plus the unencrypted payments volume compound: both map to CTL-A.8.12. Sentinel projects a 71% chance the ISO 27001 surveillance audit opens a major non-conformity.',
  confidence: 94,
  impact: 'critical',
  category: 'Prediction',
  createdAt: '2026-08-07T09:12:00Z'
},
{
  id: 'AI-498',
  title: 'Close 14 SOC 2 gaps by reusing ISO 27001 evidence already collected',
  summary:
  'Sentinel mapped 14 SOC 2 controls to existing ISO 27001 artifacts collected this quarter. Accepting the mapping lifts SOC 2 coverage from 88% to 94% with no new evidence work.',
  confidence: 89,
  impact: 'high',
  category: 'Recommendation',
  createdAt: '2026-08-07T08:40:00Z'
},
{
  id: 'AI-494',
  title: 'Privileged identity with no MFA is also on an unmonitored endpoint',
  summary:
  'jonas.meyer@northwind.io holds AWS AdministratorAccess, has no second factor, and their endpoint EDR agent has been silent for 62 hours. Combined likelihood of account takeover is 4.1× baseline.',
  confidence: 92,
  impact: 'critical',
  category: 'Anomaly',
  createdAt: '2026-08-07T08:05:00Z'
},
{
  id: 'AI-489',
  title: 'Draft ready: DPDP retention amendment for claim records',
  summary:
  'A policy amendment aligned to DPDP §8(7) is drafted and mapped to CTL-DPDP-8. Three clauses require privacy officer confirmation before publication.',
  confidence: 91,
  impact: 'medium',
  category: 'Policy Draft',
  createdAt: '2026-08-06T18:22:00Z'
},
{
  id: 'AI-482',
  title: 'Vireo Screening is the highest-risk vendor relationship in the estate',
  summary:
  'Biometric and government ID data flows to an uncertified processor with 48% consent coverage and an expired questionnaire. No compensating control is recorded.',
  confidence: 95,
  impact: 'critical',
  category: 'Recommendation',
  createdAt: '2026-08-06T14:10:00Z'
}];


export const aiSuggestedPrompts = [
'Why did our Trust Score change?',
'Are we audit ready?',
'Show critical risks.',
'Which vendor is highest risk?',
'Show DPDP violations.',
'Find access control gaps.',
'Generate audit summary.'];


export interface ReasoningContributor {
  label: string;
  delta: number;
  detail: string;
}

export interface CopilotContext {
  controls: {id: string;name: string;status: string;}[];
  evidence: {id: string;name: string;}[];
  assets: {id: string;name: string;severity: RiskLevel;}[];
  recommendation: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  /** Structured reasoning shown in the center reasoning pane. */
  headline?: string;
  contributors?: ReasoningContributor[];
  confidence?: number;
  context?: CopilotContext;
}

export const seedConversation: ChatMessage[] = [
{
  id: 'm1',
  role: 'user',
  content: 'Why did our Trust Score drop?'
},
{
  id: 'm2',
  role: 'assistant',
  headline: 'Trust Score decreased from 91 → 87 over the last 9 days.',
  content:
  'Three signals account for the entire delta. All three are concentrated in cloud and identity, and two of them share a single failing control (CTL-A.8.12), so remediating that control recovers most of the loss.',
  contributors: [
  {
    label: 'MFA compliance gap',
    delta: -2,
    detail: '6 privileged identities without a second factor · CTL-A.5.17'
  },
  {
    label: 'Public cloud exposure',
    delta: -3,
    detail: 's3://nw-claims-archive publicly enumerable · CTL-A.8.12'
  },
  {
    label: 'Vendor certification expiry',
    delta: -1,
    detail: 'Lumenpay SOC 2 report expired 2026-07-14 · CTL-CC9.2'
  },
  {
    label: 'Evidence automation gains',
    delta: 2,
    detail: '+38 automated artifacts collected this period'
  }],

  confidence: 94,
  context: {
    controls: [
    { id: 'CTL-A.8.12', name: 'Public cloud storage DLP', status: 'failing' },
    { id: 'CTL-A.5.17', name: 'MFA on privileged accounts', status: 'failing' },
    { id: 'CTL-CC9.2', name: 'Third-party risk assessment', status: 'partial' }],

    evidence: [
    { id: 'EV-8829', name: 'S3 bucket policy snapshot' },
    { id: 'EV-8836', name: 'MFA enrollment report' },
    { id: 'EV-8812', name: 'Lumenpay due diligence questionnaire' }],

    assets: [
    { id: 'CLD-4402', name: 's3://nw-claims-archive', severity: 'critical' },
    { id: 'IAM-2201', name: 'jonas.meyer@northwind.io', severity: 'critical' },
    { id: 'VEN-5501', name: 'Lumenpay', severity: 'high' }],

    recommendation:
    'Block public access on the claim archive and enforce privileged MFA in Okta. Sentinel estimates +4.6 Trust Score within 48 hours and clears the ISO 27001 audit blocker.'
  }
}];


/** Canned responses so the copilot answers the suggested questions convincingly. */
export const copilotResponses: Record<string, ChatMessage> = {
  'are we audit ready': {
    id: 'r-audit',
    role: 'assistant',
    headline: 'Audit readiness is 91% — ISO 27001 is ready, SOC 2 is not.',
    content:
    'ISO 27001 (95% readiness) and DPDP (92%) would pass today. SOC 2 sits at 89% because 20 controls fail evidence review, and 2 of those are blocked by the open cloud exposure. Internal Controls trails at 84% with one control never tested.',
    contributors: [
    { label: 'ISO 27001', delta: 95, detail: '176 passed · 11 failed · audit Sep 29' },
    { label: 'SOC 2', delta: 89, detail: '148 passed · 20 failed · audit Oct 14' },
    { label: 'DPDP', delta: 92, detail: '82 passed · 8 failed · audit Nov 5' },
    { label: 'Internal Controls', delta: 84, detail: 'CTL-INT-14 never tested' }],

    confidence: 91,
    context: {
      controls: [
      { id: 'CTL-INT-14', name: 'Change management approval', status: 'not tested' },
      { id: 'CTL-A.8.12', name: 'Public cloud storage DLP', status: 'failing' }],

      evidence: [{ id: 'EV-8804', name: 'IR tabletop minutes (expired)' }],
      assets: [{ id: 'CLD-4402', name: 's3://nw-claims-archive', severity: 'critical' }],
      recommendation:
      'Test CTL-INT-14 and refresh the two expired artifacts. That moves overall readiness to 95% before the SOC 2 window opens.'
    }
  },
  'show critical risks': {
    id: 'r-critical',
    role: 'assistant',
    headline: '4 critical risks are open — 2 share the same failing control.',
    content:
    'RSK-2291 (public storage exposure, score 94) and RSK-2258 (biometric data with an uncertified vendor, score 91) are the two highest. RSK-2284 and RSK-2288 are high but escalate to critical if left past their SLA on Aug 10.',
    contributors: [
    { label: 'RSK-2291', delta: 94, detail: 'Public storage exposure · Kenji Tanaka' },
    { label: 'RSK-2258', delta: 91, detail: 'Biometric data with uncertified vendor · Aisha Bello' },
    { label: 'RSK-2288', delta: 87, detail: 'MFA coverage gap · Dana Okafor' },
    { label: 'RSK-2284', delta: 84, detail: 'Unencrypted payments volume · Rohan Bhatt' }],

    confidence: 96,
    context: {
      controls: [
      { id: 'CTL-A.8.12', name: 'Public cloud storage DLP', status: 'failing' },
      { id: 'CTL-CC9.2', name: 'Third-party risk assessment', status: 'partial' }],

      evidence: [{ id: 'EV-8829', name: 'S3 bucket policy snapshot' }],
      assets: [
      { id: 'CLD-4402', name: 's3://nw-claims-archive', severity: 'critical' },
      { id: 'VEN-5430', name: 'Vireo Screening', severity: 'critical' }],

      recommendation:
      'Open an investigation on RSK-2291 first — it is the only critical risk that also blocks an audit milestone.'
    }
  },
  'which vendor is highest risk': {
    id: 'r-vendor',
    role: 'assistant',
    headline: 'Vireo Screening — risk score 91, no certification, biometric data.',
    content:
    'Vireo processes government ID and biometric data for 1,842 data principals from an Indian region, holds no ISO 27001 or SOC 2 certification, and its security questionnaire expired on 2026-07-11. Consent coverage for the purpose is 48%.',
    contributors: [
    { label: 'Vireo Screening', delta: 91, detail: 'Uncertified · biometric · consent 48%' },
    { label: 'Lumenpay', delta: 82, detail: 'SOC 2 expired · cardholder data' },
    { label: 'Helix Analytics', delta: 78, detail: 'No certification · US transfer' },
    { label: 'Corvex Cloud', delta: 64, detail: 'ISO 27001 expiring Sep 2' }],

    confidence: 95,
    context: {
      controls: [{ id: 'CTL-CC9.2', name: 'Third-party risk assessment', status: 'partial' }],
      evidence: [{ id: 'EV-8760', name: 'Vireo security questionnaire (expired)' }],
      assets: [{ id: 'VEN-5430', name: 'Vireo Screening', severity: 'critical' }],
      recommendation:
      'Suspend new submissions to Vireo, execute a DPA with audit rights, and complete a DPIA before processing resumes.'
    }
  },
  'show dpdp violations': {
    id: 'r-dpdp',
    role: 'assistant',
    headline: '2 consent violations and 3 retention risks across 42 personal data assets.',
    content:
    'Product analytics (Helix) and background verification (Vireo) both process personal data without valid consent for a material share of principals. Separately, 1,204 claim records are past their retention window.',
    contributors: [
    { label: 'Product analytics', delta: -61, detail: 'Helix Analytics · consent 61% · 2.1M events' },
    { label: 'Background verification', delta: -48, detail: 'Vireo Screening · consent 48% · biometric' },
    { label: 'Retention breach', delta: -3, detail: '1,204 claim records overdue · CTL-DPDP-8' }],

    confidence: 93,
    context: {
      controls: [
      { id: 'CTL-DPDP-6', name: 'Valid consent per purpose', status: 'partial' },
      { id: 'CTL-DPDP-8', name: 'Retention limits enforced', status: 'failing' }],

      evidence: [{ id: 'EV-8820', name: 'Consent ledger extract' }],
      assets: [
      { id: 'PD-7065', name: 'Behavioral analytics events', severity: 'high' },
      { id: 'PD-7101', name: 'Government ID (Aadhaar / PAN)', severity: 'critical' }],

      recommendation:
      'Suppress ingestion for non-consented principals, then re-run the retention task with the corrected predicate.'
    }
  },
  'find access control gaps': {
    id: 'r-access',
    role: 'assistant',
    headline: '6 access control gaps — all traceable to two controls.',
    content:
    'Six privileged identities lack MFA, two service accounts hold wildcard permissions, and one dormant contractor retains warehouse access. Together they represent the largest single recoverable Trust Score component.',
    contributors: [
    { label: 'Privileged MFA gaps', delta: -2, detail: '6 identities · CTL-A.5.17 failing' },
    { label: 'Wildcard service permissions', delta: -1, detail: 'svc-payments-deploy · s3:*' },
    { label: 'Dormant standing access', delta: -0.5, detail: 'contractor.jsmith · 71 days idle' }],

    confidence: 90,
    context: {
      controls: [
      { id: 'CTL-A.5.17', name: 'MFA on privileged accounts', status: 'failing' },
      { id: 'CTL-CC6.1', name: 'Access provisioning / deprovisioning', status: 'passing' }],

      evidence: [{ id: 'EV-8841', name: 'Privileged access review Q3 2026' }],
      assets: [
      { id: 'IAM-2201', name: 'jonas.meyer@northwind.io', severity: 'critical' },
      { id: 'IAM-2188', name: 'svc-payments-deploy', severity: 'high' }],

      recommendation:
      'Enforce privileged MFA, scope the deploy role to specific buckets, and convert contractor access to just-in-time.'
    }
  },
  'generate audit summary': {
    id: 'r-summary',
    role: 'assistant',
    headline: 'Audit summary drafted — Trust 87, readiness 91%, 4 critical risks.',
    content:
    'Sentinel assembled an executive narrative citing 418 evidence artifacts across 4 frameworks. Two claims require human confirmation before the report can be issued to auditors.',
    contributors: [
    { label: 'Trust Score', delta: 87, detail: 'GOOD · +4.2% this week' },
    { label: 'Audit readiness', delta: 91, detail: 'ISO 27001 ready · SOC 2 at risk' },
    { label: 'Evidence coverage', delta: 86, detail: '418 of 486 controls' }],

    confidence: 92,
    context: {
      controls: [{ id: 'CTL-A.8.12', name: 'Public cloud storage DLP', status: 'failing' }],
      evidence: [{ id: 'EV-8841', name: 'Privileged access review Q3 2026' }],
      assets: [{ id: 'CLD-4402', name: 's3://nw-claims-archive', severity: 'critical' }],
      recommendation: 'Review the 2 flagged claims, then export the report from the Reports workspace.'
    }
  }
};

export const notifications: NotificationItem[] = [
{
  id: 'n1',
  title: 'Critical exposure detected',
  body: 'Public access enabled on s3://nw-claims-archive — 128,402 claim records.',
  kind: 'risk',
  read: false,
  createdAt: '2026-08-07T09:42:00Z'
},
{
  id: 'n2',
  title: 'Sentinel drafted a remediation plan',
  body: 'RSK-2291 mitigation plan ready with evidence pre-attached.',
  kind: 'ai',
  read: false,
  createdAt: '2026-08-07T09:14:00Z'
},
{
  id: 'n3',
  title: 'MFA coverage dropped',
  body: 'Privileged MFA coverage fell to 94% — 6 identities affected.',
  kind: 'compliance',
  read: false,
  createdAt: '2026-08-07T09:38:00Z'
},
{
  id: 'n4',
  title: 'Evidence sync completed',
  body: '486 controls refreshed from 9 connected systems.',
  kind: 'system',
  read: true,
  createdAt: '2026-08-07T04:00:00Z'
}];