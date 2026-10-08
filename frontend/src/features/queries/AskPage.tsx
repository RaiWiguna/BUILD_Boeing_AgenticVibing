import { useMutation } from '@tanstack/react-query';
import { ArrowUp, CircleCheck, CircleHelp, CircleSlash, FlaskConical, Loader2, MessageSquareText, ShieldAlert, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { isApiError } from '@/api/errors';
import type { QueryResultView, QueryStatus } from '@/api/types';
import { ModeToggle, ScopeBanners } from '@/features/workspace/SessionHeader';
import { SessionPageHeader } from '@/features/workspace/SessionPageHeader';
import { CodeChip, StatusPill } from '@/components/domain/primitives';
import { EvidenceChip } from '@/components/domain/evidence';
import { EmptyState } from '@/components/domain/states';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/input';
import { useApi } from '@/hooks/useApi';
import { useConnected } from '@/hooks/useSessionStream';
import { useSessionScope } from '@/hooks/useSessionScope';
import { idemKey, releaseKeys } from '@/lib/idempotency';
import type { StatusMeta } from '@/lib/status';
import { formatClock, formatTimeUtc } from '@/lib/time';

const MAX = 280;

const SUGGESTIONS = ['What was the last instruction to FLN214?', 'What is still open for FLN402?', 'Last instruction related to runway 27?', 'What do we know about VEH03?'];

const STATUS_META: Record<QueryStatus, StatusMeta> = {
  COMPLETE: { label: 'Answered from evidence', tone: 'data', icon: CircleCheck },
  PARTIAL: { label: 'Partial · some context missing', tone: 'notice', icon: CircleHelp },
  INSUFFICIENT_CONTEXT: { label: 'Unknown · not covered', tone: 'muted', icon: CircleSlash },
  UNAVAILABLE: { label: 'Unavailable', tone: 'muted', icon: ShieldAlert },
};

function useAsk() {
  const api = useApi();
  const { scope, mode, asOf, sid } = useSessionScope();
  return useMutation({
    mutationFn: (question: string) => api.ask(scope!, { asOfMs: asOf, mode }, question, { idempotencyKey: idemKey(`ask:${sid}`, { question, asOf, mode }) }),
    onSuccess: () => releaseKeys(`ask:${sid}`),
  });
}

function ResultCard({ r }: { r: QueryResultView }) {
  const unknown = r.status === 'INSUFFICIENT_CONTEXT' || r.status === 'UNAVAILABLE';
  return (
    <article className="card p-5" aria-label={`Answer to: ${r.question}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="flex items-start gap-2.5 text-[16px] font-medium text-ink">
          <span aria-hidden className="mt-0.5 inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-track text-[12px] font-semibold text-ink-2">
            Q
          </span>
          {r.question}
        </p>
        <StatusPill size="sm" meta={STATUS_META[r.status]} />
      </div>
      {r.items.length > 0 && (
        <ul className="mt-4 space-y-2.5 pl-[34px]">
          {r.items.map((it, i) => (
            <li key={i} className="rounded-[14px] border border-hairline-soft px-3.5 py-3">
              <div className="flex items-start justify-between gap-3">
                <p className="text-[15px] leading-snug text-ink">{it.statement}</p>
                <span className="flex shrink-0 gap-1">
                  {it.evidence_ids.map((id, j) => (
                    <EvidenceChip key={id} id={id} label={it.evidence_labels[j] ?? 'E-?'} size="sm" />
                  ))}
                </span>
              </div>
              {it.evidence_ids.length === 0 && <p className="mt-1 text-[12.5px] text-ink-3">No evidence item · derived from current state</p>}
              {it.unknowns.length > 0 && <p className="mt-1 text-[12.5px] text-notice">Unknown: {it.unknowns.join(', ')}</p>}
            </li>
          ))}
        </ul>
      )}
      {r.note && (
        <p className={unknown ? 'mt-4 ml-[34px] rounded-[14px] bg-sunken px-3.5 py-3 text-[14px] text-ink-2' : 'mt-3 ml-[34px] text-[13.5px] text-ink-2'}>
          {r.note}
        </p>
      )}
      <p className="mt-4 ml-[34px] flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-ink-3 tabular">
        <Sparkles aria-hidden className="size-3.5" /> AI interpretation · model {r.model_version} · {r.mode === 'DEBRIEF' ? 'Debrief' : 'As-known'} at {formatClock(r.as_of_ms)} · context {formatClock(r.context_range.start_ms)}–{formatClock(r.context_range.end_ms)} · asked {formatTimeUtc(r.asked_at)}
      </p>
    </article>
  );
}

/** Contextual query (P1). Read-only; answers come only from this session's evidence at the current as-of. */
export function AskPage() {
  const { mode, asOf, archived } = useSessionScope();
  const connected = useConnected();
  const ask = useAsk();
  const [question, setQuestion] = useState('');
  const [history, setHistory] = useState<QueryResultView[]>([]);
  const canAsk = !!question.trim() && connected && !ask.isPending;

  const submit = (q = question) => {
    const text = q.trim();
    if (!text || !connected) return;
    ask.mutate(text, {
      onSuccess: (r) => {
        setHistory((h) => [r, ...h]);
        setQuestion('');
      },
    });
  };

  return (
    <div className="flex min-h-full flex-col">
      <SessionPageHeader
        title="Ask"
        chips={
          <span className="inline-flex h-[30px] items-center gap-1.5 rounded-full bg-[#f3eefe] px-3 text-[13.5px] font-medium text-[#6941c6]">
            <FlaskConical aria-hidden className="size-[15px]" /> P1 · Experimental
          </span>
        }
        actions={<ModeToggle />}
      />
      <ScopeBanners />
      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-5">
          <section aria-labelledby="ask-title" className="card p-5">
            <h2 id="ask-title" className="text-[20px] font-semibold tracking-[-0.02em] text-ink">
              Ask about this session
            </h2>
            <p className="mt-1 text-[14px] text-ink-2">
              Answers use only evidence available {mode === 'DEBRIEF' ? 'in Debrief' : 'As-known'} at <span className="font-medium text-ink tabular">{formatClock(asOf)}</span>. Read-only — nothing is changed or sent.
            </p>
            <form
              className="relative mt-4"
              onSubmit={(e) => {
                e.preventDefault();
                submit();
              }}
            >
              <Textarea
                value={question}
                maxLength={MAX}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    submit();
                  }
                }}
                aria-label="Question"
                placeholder="e.g. What was the last instruction to FLN214?"
                className="min-h-[96px] pr-16 pb-9"
                disabled={!connected}
              />
              <span className="pointer-events-none absolute bottom-3 left-3.5 text-[12px] text-ink-3 tabular">
                {question.length}/{MAX} · Enter to ask
              </span>
              <Button type="submit" variant="primary" size="icon" aria-label="Ask" className="absolute bottom-2.5 right-2.5" disabled={!canAsk}>
                {ask.isPending ? <Loader2 className="animate-spin" /> : <ArrowUp />}
              </Button>
            </form>
            <div className="mt-3 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" onClick={() => submit(s)} disabled={!connected || ask.isPending} className="inline-flex h-8 items-center rounded-full border border-hairline bg-surface px-3 text-[13px] text-ink-2 shadow-control transition-colors hover:bg-sunken hover:text-ink disabled:opacity-50">
                  {s}
                </button>
              ))}
            </div>
            {ask.error && (
              <p role="alert" className="mt-3 rounded-[12px] bg-notice-tint px-3.5 py-2.5 text-[13.5px] text-notice">
                {isApiError(ask.error) ? `${ask.error.message} ${ask.error.recovery ?? ''}` : 'The question could not be answered.'}
              </p>
            )}
            {!connected && <p className="mt-3 text-[13px] text-notice">Asking is paused while disconnected.</p>}
            {archived && <p className="mt-3 text-[13px] text-ink-2">Archived session — questions still read stored evidence only.</p>}
          </section>

          {history.length === 0 ? (
            <div className="card">
              <EmptyState icon={MessageSquareText} title="No questions yet">
                Ask about an object, a runway or what is still open. Unknown answers say so and carry no evidence.
              </EmptyState>
            </div>
          ) : (
            <div aria-live="polite" className="space-y-4">
              {history.map((r) => (
                <ResultCard key={r.id} r={r} />
              ))}
            </div>
          )}
        </div>

        <aside className="card p-5 xl:sticky xl:top-6" aria-labelledby="ask-rules">
          <h2 id="ask-rules" className="text-[17px] font-semibold text-ink">
            How answers work
          </h2>
          <ul className="mt-3 space-y-3 text-[14px] leading-snug text-ink-2">
            <li className="flex gap-2.5">
              <CircleCheck aria-hidden className="mt-0.5 size-4 shrink-0 text-data" /> Each statement links to its evidence. Open a chip to listen or read.
            </li>
            <li className="flex gap-2.5">
              <CircleSlash aria-hidden className="mt-0.5 size-4 shrink-0 text-ink-3" /> If the session does not cover it, the answer is “Unknown” — never a guess.
            </li>
            <li className="flex gap-2.5">
              <ShieldAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-notice" /> No clearances, instructions or general aviation advice. Questions cannot change state.
            </li>
          </ul>
          <div className="mt-4 flex flex-wrap gap-1.5 border-t border-hairline-soft pt-4">
            <CodeChip>{mode === 'DEBRIEF' ? 'DEBRIEF' : 'AS_KNOWN'}</CodeChip>
            <CodeChip tone="muted">MODEL · MOCK</CodeChip>
          </div>
        </aside>
      </div>
    </div>
  );
}
