/**
 * Backend Copilot answer -> the existing Copilot UI shape.
 *
 * The page already renders a headline, a body, "primary contributors" and a
 * recommendation panel. The backend returns `answer`, `supporting_data`,
 * `related_entities`, `recommendations`, `sources` and a *textual* confidence.
 * This maps one onto the other so the page keeps its design.
 *
 * Two honesty notes that drove the mapping:
 *
 * 1. **Confidence stays textual.** The UI's `ConfidenceMeter` wants a number,
 *    but the backend reports "high" / "medium" / "low" / "none". Converting
 *    "high" into "92%" would invent precision that no part of the system
 *    computed, so `confidence` is left undefined and the label is rendered as
 *    text instead.
 *
 * 2. **`delta` is not a trend.** The contributor row shows a signed number
 *    styled red/green. Backend `supporting_data` values are current counts,
 *    not changes, so `delta` carries the raw value and the sign styling is
 *    neutralised by always passing a non-negative number where the value is a
 *    count. Nothing here implies movement over time — the system stores no
 *    history for these figures.
 */

import type { CopilotAnswer } from './api';
import type { ChatMessage } from '../data/ai';

const SEVERITY_HINT = /critical|high|fail|gap|revoked|expired|without|no /i;

function splitAnswer(answer: string): { headline: string; body: string } {
  const match = answer.match(/^(.*?[.!?])\s+(.*)$/s);
  if (!match || match[1].length > 160) {
    return { headline: answer, body: '' };
  }
  return { headline: match[1].trim(), body: match[2].trim() };
}

export function toChatMessage(result: CopilotAnswer): ChatMessage {
  const { headline, body } = splitAnswer(result.answer);

  const contributors = result.supporting_data
    .filter((item) => item.value !== null && item.value !== undefined)
    .slice(0, 6)
    .map((item) => {
      const numeric = typeof item.value === 'number' ? item.value : Number(item.value);
      return {
        label: item.label,
        // Counts, not deltas — see the note at the top of this file.
        delta: Number.isFinite(numeric) ? numeric : 0,
        detail: Number.isFinite(numeric)
          ? `${item.unit ?? ''}`.trim() || 'current count'
          : String(item.value)
      };
    });

  const context = {
    controls: result.related_entities
      .filter((e) => e.type === 'control')
      .slice(0, 6)
      .map((e) => ({ id: e.id, name: e.label, status: e.detail ?? '' })),
    evidence: result.related_entities
      .filter((e) => e.type === 'evidence')
      .slice(0, 6)
      .map((e) => ({ id: e.id, name: e.label })),
    assets: result.related_entities
      .filter((e) => !['control', 'evidence'].includes(e.type))
      .slice(0, 6)
      .map((e) => ({
        id: e.id,
        name: e.label,
        severity: (SEVERITY_HINT.test(e.detail ?? '') ? 'high' : 'low') as 'high' | 'low'
      })),
    recommendation:
      result.recommendations[0] ??
      (result.intent === 'unknown'
        ? 'Try one of the suggested questions — those map to data Sentinel actually holds.'
        : 'No specific action is derivable from the current data.')
  };

  return {
    id: `a-${Date.now()}`,
    role: 'assistant',
    headline,
    content: body || headline,
    contributors: contributors.length ? contributors : undefined,
    // Deliberately no numeric confidence — see note 1.
    context
  };
}

/**
 * Per-answer LLM status. The backend already distinguishes
 * `engine: "llm_grounded_v1"` from `"deterministic_fallback_v1"` /
 * `"deterministic_intent_v1"` via `llm_used` — this just gives the UI a
 * single place to render that honestly. Never say "AI powered" here when
 * `llm_used` is false; "Verified fallback" is the deterministic path, not a
 * degraded one — every figure in it is still real.
 */
export function engineStatus(
  result: CopilotAnswer
): { label: string; shortLabel: string; tone: 'ai' | 'neutral' } {
  if (result.llm_used) {
    return { label: 'Sentinel AI · LLM grounded', shortLabel: 'LLM grounded', tone: 'ai' };
  }
  return {
    label: 'Sentinel AI · Verified fallback',
    shortLabel: 'Verified fallback · no LLM',
    tone: 'neutral'
  };
}

export function confidenceLabel(result: CopilotAnswer): string {
  switch (result.confidence) {
    case 'high':
      return 'High confidence · exact match on stored data';
    case 'medium':
      return 'Medium confidence · matched on a single keyword';
    case 'low':
      return 'Low confidence';
    default:
      return 'No answer — question outside the available data';
  }
}
