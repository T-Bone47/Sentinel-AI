import { motion } from 'framer-motion';
import {
  ArrowUp,
  Boxes,
  FileBadge,
  Loader2,
  MessageSquare,
  ShieldCheck,
  Sparkles,
  Lightbulb } from
'lucide-react';
import { PageHeader, MetaStat } from '../components/layout/PageHeader';
import { Button } from '../components/ui/Button';
import { Badge, RiskBadge } from '../components/ui/Badge';
import { ConfidenceMeter } from '../components/common/StatusPills';
import { EmptyState, ErrorState } from '../components/ui/States';
import { type ChatMessage } from '../data/ai';
import { askCopilot, getCopilotSuggestions, type CopilotAnswer } from '../services/api';
import { confidenceLabel, engineStatus, toChatMessage } from '../services/copilotAdapter';
import { useApiResource } from '../hooks/useApiResource';
import React, { useState, useMemo } from 'react';
import { cn } from '../utils/cn';

// Sequential status text for the single round-trip to POST /copilot/query.
// There is no streaming/WebSocket backend behind this, so these stages are
// a client-side progression shown while that one request is in flight — see
// `send()` below. The cycle stops the instant the real response (or error)
// arrives, however far through it got, so it never claims a stage finished
// before it did.
const PROGRESS_STAGES = [
'Understanding your request...',
'Checking GRC intelligence...',
'Analyzing verified data...',
'Generating Sentinel response...'];


export function Copilot() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [answers, setAnswers] = useState<CopilotAnswer[]>([]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [progressIndex, setProgressIndex] = useState(0);
  const [failure, setFailure] = useState<string | null>(null);
  const [lastFailedQuestion, setLastFailedQuestion] = useState<string | null>(null);

  // Suggested questions come from the backend, so the list can never drift
  // from the intents the Copilot actually supports.
  const suggestions = useApiResource(() => getCopilotSuggestions(), []);
  const aiSuggestedPrompts = suggestions.data?.suggested_questions ?? [];

  const latestAssistantMessage = useMemo(
    () => [...messages].reverse().find((m) => m.role === 'assistant'),
    [messages]
  );
  // A failed request must immediately hide any stale successful answer, or
  // the reasoning panel and evidence sidebar keep showing the *previous*
  // answer's controls/evidence/assets as though still current while the
  // center panel separately reports the backend unreachable — a real,
  // pre-existing gap: `failure` was checked only after `latest`, so it was
  // unreachable once any answer had ever succeeded in the session.
  const latest = failure ? undefined : latestAssistantMessage;
  const latestAnswer = failure ? null : answers.length ? answers[answers.length - 1] : null;

  const threads = useMemo(
    () =>
      messages.
      filter((m) => m.role === 'user').
      slice(-6).
      reverse().
      map((m, i) => ({ id: m.id, title: m.content, time: i === 0 ? 'Now' : '', active: i === 0 })),
    [messages]
  );

  const send = async (text: string) => {
    const value = text.trim();
    if (!value || thinking) return;
    setMessages((current) => [
    ...current,
    { id: `u-${Date.now()}`, role: 'user', content: value }]
    );
    setInput('');
    setThinking(true);
    setProgressIndex(0);
    setFailure(null);
    setLastFailedQuestion(null);

    const progressTimer = window.setInterval(() => {
      setProgressIndex((i) => Math.min(i + 1, PROGRESS_STAGES.length - 1));
    }, 850);

    try {
      const result = await askCopilot(value);
      setAnswers((current) => [...current, result]);
      setMessages((current) => [...current, toChatMessage(result)]);
    } catch (error) {
      // No canned fallback: if the backend is unreachable the user is told,
      // rather than being shown a scripted answer that looks real.
      setFailure(
        error instanceof Error ?
        error.message :
        'The Copilot backend is unreachable.'
      );
      setLastFailedQuestion(value);
    } finally {
      window.clearInterval(progressTimer);
      setThinking(false);
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow={
        <>
            <Badge tone="ai">
              <Sparkles className="h-3 w-3" aria-hidden />
              Sentinel Analyst · grounded in your estate
            </Badge>
            <Badge tone="success" dot>
              Answers cite their sources
            </Badge>
          </>
        }
        title="AI Copilot"
        subtitle="Answers composed from live control, risk, evidence and identity data. Intent matching is always deterministic — an LLM may narrate the answer when configured, grounded only in that verified data — and every answer lists the endpoints it was built from."
        meta={
        <>
            <MetaStat
            label="Engine"
            value={latestAnswer ? engineStatus(latestAnswer).shortLabel : 'Deterministic + optional LLM'} />
          
            <MetaStat
            label="Answers from"
            value={`${suggestions.data?.intents.length ?? 0} data-backed intents`} />
          
            <MetaStat label="Grounding" value="Live PostgreSQL records" />
          </>
        } />
      

      <div className="grid gap-4 xl:grid-cols-12">
        {/* LEFT — conversation */}
        <section
          aria-label="Conversation"
          className="flex h-[640px] flex-col overflow-hidden rounded-xl border border-border bg-card xl:col-span-4">
          
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <p className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
              <MessageSquare className="h-3.5 w-3.5" aria-hidden />
              Conversation
            </p>
            <Button variant="ghost" size="xs">
              New
            </Button>
          </div>

          <ul className="border-b border-border px-2 py-2">
            {threads.map((thread) =>
            <li key={thread.id}>
                <button
                type="button"
                className={cn(
                  'flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left transition-colors duration-150',
                  thread.active ? 'bg-ai/[0.10] text-foreground' : 'hover:bg-accent/60'
                )}>
                
                  <span
                  className={cn(
                    'h-1.5 w-1.5 shrink-0 rounded-full',
                    thread.active ? 'bg-ai' : 'bg-border-strong'
                  )}
                  aria-hidden />
                
                  <span className="min-w-0 flex-1 truncate text-[13px] font-medium">
                    {thread.title}
                  </span>
                  <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
                    {thread.time}
                  </span>
                </button>
              </li>
            )}
          </ul>

          <div
            className="flex-1 space-y-3 overflow-y-auto px-4 py-4"
            role="log"
            aria-live="polite">
            
            {messages.map((message) =>
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22 }}
              className={cn(
                'flex',
                message.role === 'user' ? 'justify-end' : 'justify-start'
              )}>
              
                <div
                className={cn(
                  'max-w-[88%] rounded-lg px-3 py-2 text-[13px] leading-relaxed',
                  message.role === 'user' ?
                  'bg-primary/15 text-foreground' :
                  'border border-ai-border/50 bg-ai-surface/25'
                )}>
                
                  {message.role === 'assistant' &&
                <p className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-label text-ai">
                      <Sparkles className="h-3 w-3" aria-hidden />
                      Sentinel
                    </p>
                }
                  <p>{message.headline ?? message.content}</p>
                </div>
              </motion.div>
            )}
            {thinking &&
            <p className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-ai" aria-hidden />
                {PROGRESS_STAGES[progressIndex]}
              </p>
            }
          </div>

          <div className="border-t border-border px-4 py-4 bg-surface-1/50 backdrop-blur-md">
            <div className="scrollbar-none mb-3 flex gap-2 overflow-x-auto pb-1">
              {aiSuggestedPrompts.map((prompt) =>
              <button
                key={prompt}
                type="button"
                onClick={() => send(prompt)}
                className="shrink-0 rounded-full border border-ai/20 bg-card/60 px-3 py-1.5 text-2xs font-medium text-muted-foreground shadow-sm transition-all duration-300 hover:border-ai/50 hover:text-ai hover:shadow-[0_0_10px_oklch(var(--ai)/0.2)]">
                
                  {prompt}
                </button>
              )}
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                send(input);
              }}
              className="group relative flex items-center gap-3 rounded-full border border-border-strong bg-card/80 p-1.5 pr-2.5 shadow-lg backdrop-blur-xl transition-all focus-within:border-ai/50 focus-within:ring-2 focus-within:ring-ai/20">
              
              <div className="relative ml-2 flex h-6 w-6 shrink-0 items-center justify-center">
                <motion.div
                  className="absolute inset-0 rounded-full bg-ai"
                  animate={{
                    scale: thinking ? [1, 1.4, 1] : [1, 1.1, 1],
                    opacity: thinking ? [0.6, 1, 0.6] : [0.3, 0.6, 0.3],
                  }}
                  transition={{
                    duration: thinking ? 0.8 : 3,
                    repeat: Infinity,
                    ease: "easeInOut"
                  }}
                  style={{ filter: thinking ? 'blur(6px)' : 'blur(4px)' }}
                />
                <motion.div
                  className="relative h-2.5 w-2.5 rounded-full bg-white shadow-[0_0_8px_oklch(var(--ai))]"
                  animate={{ scale: thinking ? [1, 0.8, 1] : 1 }}
                  transition={{ duration: 0.8, repeat: Infinity }}
                />
              </div>

              <label htmlFor="copilot-input" className="sr-only">
                Ask Sentinel
              </label>
              <input
                id="copilot-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask Sentinel to analyze..."
                className="h-10 flex-1 bg-transparent px-2 text-[14px] outline-none placeholder:text-muted-foreground/60 text-foreground" 
              />
              
              <Button
                type="submit"
                variant="ai"
                size="icon-sm"
                className="h-8 w-8 rounded-full shadow-md"
                disabled={!input.trim() || thinking}
                aria-label="Send">
                
                <ArrowUp className="h-4 w-4" />
              </Button>
            </form>
          </div>
        </section>

        {/* CENTER — reasoning */}
        <section
          aria-label="Sentinel reasoning"
          className="relative flex h-[640px] flex-col overflow-hidden rounded-xl border border-ai-border/50 bg-card xl:col-span-5">
          
          <div className="absolute inset-0 cyber-grid-fine opacity-25" aria-hidden />
          <div className="relative flex items-center justify-between border-b border-ai-border/40 px-4 py-3">
            <p className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-label text-ai">
              <span className="relative flex h-4 w-4 items-center justify-center">
                <span className="absolute h-4 w-4 rounded-full bg-ai/25 motion-safe:animate-signal-ping" />
                <Sparkles className="relative h-3 w-3" aria-hidden />
              </span>
              Reasoning
            </p>
            {latest?.confidence && <ConfidenceMeter value={latest.confidence} />}
          </div>

          <div className="relative flex-1 overflow-y-auto px-5 py-5">
            {thinking ?
            <div className="space-y-3">
                {PROGRESS_STAGES.slice(0, progressIndex + 1).map(
                (step, i) => {
                  const isCurrent = i === progressIndex;
                  return (
                    <motion.p
                    key={step}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: isCurrent ? [0.35, 1, 0.35] : 0.6, y: 0 }}
                    transition={
                    isCurrent ?
                    { duration: 1.1, repeat: Infinity } :
                    { duration: 0.18 }
                    }
                    className="flex items-center gap-2 font-mono text-xs text-ai">
                    
                        <span
                      className={cn('h-1 w-1 rounded-full', isCurrent ? 'bg-ai' : 'bg-ai/50')}
                      aria-hidden />
                    
                        {step}
                      </motion.p>);

                }
              )}
              </div> :

            failure ?
            <ErrorState
              title={failure === 'Cannot reach the Sentinel AI backend. Check that the API is running.' ? 'Copilot backend unreachable' : 'Copilot error'}
              description={failure === 'Cannot reach the Sentinel AI backend. Check that the API is running.' 
                ? `${failure} Start the API with \`uvicorn app.main:app --reload\` — this Copilot answers only from live data and has no offline fallback.`
                : failure
              }
              onRetry={lastFailedQuestion ? () => send(lastFailedQuestion) : undefined} /> :

            latest ?
            <div className="space-y-5">
                <h2 className="text-base font-semibold leading-snug">{latest.headline}</h2>
                <p className="text-[13px] leading-relaxed text-muted-foreground">
                  {latest.content}
                </p>

                {latest.contributors &&
              <div>
                    <p className="mb-2.5 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                      Primary contributors
                    </p>
                    <ul className="space-y-2">
                      {latest.contributors.map((contributor, i) => {
                    const negative = contributor.delta < 0;
                    return (
                      <motion.li
                        key={contributor.label}
                        initial={{ opacity: 0, x: -6 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.24, delay: i * 0.06 }}
                        className="flex items-center gap-3 rounded-lg border border-border bg-surface-2/60 px-3.5 py-2.5">
                        
                            <span
                          className={cn(
                            'w-11 shrink-0 text-center font-mono text-sm font-semibold',
                            negative ? 'text-risk-critical' : 'text-success'
                          )}>
                          
                              {negative ? '' : '+'}
                              {contributor.delta}
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="block truncate text-[13px] font-medium">
                                {contributor.label}
                              </span>
                              <span className="block truncate font-mono text-2xs text-muted-foreground">
                                {contributor.detail}
                              </span>
                            </span>
                          </motion.li>);

                  })}
                    </ul>
                  </div>
              }

                {latest.context &&
              <div className="rounded-lg border border-ai-border/60 bg-ai-surface/30 p-4">
                    <p className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-label text-ai">
                      <Lightbulb className="h-3.5 w-3.5" aria-hidden />
                      Recommended action
                    </p>
                    <p className="mt-2 text-[13px] leading-relaxed">
                      {latest.context.recommendation}
                    </p>
                    <div className="mt-3.5 flex flex-wrap gap-2">
                      <Button variant="ai" size="sm" iconLeft={<Sparkles className="h-3.5 w-3.5" />}>
                        Apply with Sentinel
                      </Button>
                      <Button variant="outline" size="sm">
                        Create task
                      </Button>
                    </div>
                  </div>
              }

                {latestAnswer &&
              <div className="space-y-3 rounded-lg border border-border bg-surface-2/40 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={latestAnswer.intent === 'unknown' ? 'warning' : 'success'} dot>
                        {latestAnswer.intent_label}
                      </Badge>
                      {latestAnswer.intent !== 'unknown' &&
                  <Badge tone={engineStatus(latestAnswer).tone} dot>
                          {engineStatus(latestAnswer).label}
                        </Badge>
                  }
                      <span className="font-mono text-2xs text-muted-foreground">
                        {confidenceLabel(latestAnswer)}
                      </span>
                    </div>

                    {latestAnswer.recommendations.length > 1 &&
                <div>
                        <p className="mb-1.5 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                          Recommended actions
                        </p>
                        <ul className="space-y-1.5">
                          {latestAnswer.recommendations.slice(0, 5).map((rec, i) => {
                    // Defensive: the contract is string[], but never let a
                    // shape mismatch anywhere on the backend take the whole
                    // page down via the error boundary over one bullet.
                    const text =
                    typeof rec === 'string' ?
                    rec :
                    JSON.stringify(rec);
                    return (
                      <li key={text || i} className="flex gap-2 text-[13px] leading-relaxed">
                              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-ai" aria-hidden />
                              <span className="min-w-0">{text}</span>
                            </li>);

                  })}
                        </ul>
                      </div>
                }

                    {/* Source references make every figure above checkable —
                        the whole point of a GRC copilot over a chatbot. */}
                    {latestAnswer.sources.length > 0 &&
                <div>
                        <p className="mb-1.5 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                          Derived from
                        </p>
                        <ul className="flex flex-wrap gap-1.5">
                          {latestAnswer.sources.map((source) =>
                    <li
                      key={`${source.endpoint}-${source.field}`}
                      className="rounded border border-border bg-surface-3/60 px-2 py-1 font-mono text-2xs text-muted-foreground">
                      
                              {source.endpoint}
                              <span className="text-foreground/70"> · {source.field}</span>
                            </li>
                    )}
                        </ul>
                      </div>
                }
                  </div>
              }
              </div> :

            <EmptyState
              tone="ai"
              icon={<Sparkles className="h-6 w-6" />}
              title="Ask Sentinel anything about your posture"
              description="Every answer is composed from live database records and lists the endpoints it came from." />

            }
          </div>
        </section>

        {/* RIGHT — evidence + context */}
        <section
          aria-label="Evidence and context"
          className="flex h-[640px] flex-col gap-4 overflow-y-auto xl:col-span-3">
          
          <ContextPanel
            title="Related controls"
            icon={<ShieldCheck className="h-3.5 w-3.5" aria-hidden />}
            empty="No controls cited yet">
            
            {latest?.context?.controls.map((control) =>
            <li
              key={control.id}
              className="rounded-md border border-border bg-surface-2/50 px-3 py-2">
              
                <p className="font-mono text-2xs text-primary">{control.id}</p>
                <p className="mt-0.5 truncate text-[13px]">{control.name}</p>
                <p
                className={cn(
                  'mt-1 text-2xs font-semibold uppercase tracking-label',
                  control.status.includes('fail') ?
                  'text-risk-critical' :
                  control.status.includes('partial') ?
                  'text-warning' :
                  'text-muted-foreground'
                )}>
                
                  {control.status}
                </p>
              </li>
            )}
          </ContextPanel>

          <ContextPanel
            title="Evidence"
            icon={<FileBadge className="h-3.5 w-3.5" aria-hidden />}
            empty="No evidence cited yet">
            
            {latest?.context?.evidence.map((item) =>
            <li
              key={item.id}
              className="flex items-center gap-2 rounded-md border border-border bg-surface-2/50 px-3 py-2">
              
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-success" aria-hidden />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px]">{item.name}</span>
                  <span className="block font-mono text-2xs text-muted-foreground">
                    {item.id}
                  </span>
                </span>
              </li>
            )}
          </ContextPanel>

          <ContextPanel
            title="Affected assets"
            icon={<Boxes className="h-3.5 w-3.5" aria-hidden />}
            empty="No assets cited yet">
            
            {latest?.context?.assets.map((asset) =>
            <li
              key={asset.id}
              className="rounded-md border border-border bg-surface-2/50 px-3 py-2">
              
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-mono text-2xs text-muted-foreground">
                    {asset.id}
                  </span>
                  <RiskBadge level={asset.severity} withDot={false} />
                </div>
                <p className="mt-1 truncate text-[13px]">{asset.name}</p>
              </li>
            )}
          </ContextPanel>
        </section>
      </div>
    </div>);

}

function ContextPanel({
  title,
  icon,
  children,
  empty





}: {title: string;icon: React.ReactNode;children?: React.ReactNode;empty: string;}) {
  const hasChildren = React.Children.count(children) > 0;
  return (
    <div className="rounded-xl border border-border bg-card">
      <p className="flex items-center gap-2 border-b border-border px-4 py-2.5 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
        {icon}
        {title}
      </p>
      {hasChildren ?
      <ul className="space-y-2 p-3">{children}</ul> :

      <p className="px-4 py-6 text-center text-xs text-muted-foreground">{empty}</p>
      }
    </div>);

}
