import { AlertTriangle, CircleCheck, CircleHelp, CloudOff, ExternalLink, Info, Loader2, Lock, WifiOff } from 'lucide-react';
import { useState } from 'react';
import { useSearchParams } from 'react-router';
import { toast } from 'sonner';
import { isApiError } from '@/api/errors';
import type { OptionReviewStatus, OptionView } from '@/api/types';
import { useAuth } from '@/app/providers/AuthProvider';
import { ReviewHistory } from '@/features/evidence/FindingReviewForm';
import { EvidenceChip } from '@/components/domain/evidence';
import { CodeChip, MoreButton, StatusPill } from '@/components/domain/primitives';
import { Callout, DesktopOnly, EmptyState, ErrorState, LoadingRows } from '@/components/domain/states';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioRow } from '@/components/ui/controls';
import { Label, Textarea } from '@/components/ui/input';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/menu';
import { useEvidence } from '@/hooks/useEvidence';
import { useConnected } from '@/hooks/useSessionStream';
import { useSessionScope } from '@/hooks/useSessionScope';
import { STATUS } from '@/lib/status';
import { formatOffset } from '@/lib/time';
import { cn } from '@/lib/utils';
import { useOptions, useReviewOption } from './queries';

type Decision = Exclude<OptionReviewStatus, 'UNREVIEWED'>;
const DECISIONS: { value: Decision; label: string }[] = [
  { value: 'RELEVANT', label: 'Relevant' },
  { value: 'NOT_RELEVANT', label: 'Not relevant' },
  { value: 'UNSUPPORTED', label: 'Unsupported by evidence' },
  { value: 'UNRESOLVED', label: 'Cannot be determined yet' },
];

function OptionDetail({ o }: { o: OptionView }) {
  const { run } = useSessionScope();
  const ids = Object.keys(o.evidence_labels);
  return (
    <div>
      <h2 className="text-[26px] font-semibold leading-tight tracking-[-0.03em] text-ink">{o.title}</h2>
      <section className="mt-5">
        <h3 className="text-[15px] font-semibold text-ink">Evaluation question</h3>
        <p className="mt-1 text-[16px] leading-relaxed text-ink-2">{o.evaluation_question}</p>
      </section>
      <div className="my-4 h-px bg-hairline" />
      <section>
        <h3 className="text-[15px] font-semibold text-ink">Rationale</h3>
        <p className="mt-1 text-[16px] leading-relaxed text-ink-2">{o.option.rationale}</p>
        <p className="mt-2 text-[14px] text-ink-2">
          <span className="font-medium text-ink">Statement · </span>
          {o.option.statement}
        </p>
      </section>
      <div className="my-4 h-px bg-hairline" />
      <section>
        <h3 className="text-[15px] font-semibold text-ink">Evidence references</h3>
        <div className="mt-2.5 flex flex-wrap gap-2">
          {ids.map((id) => (
            <EvidenceChip key={id} id={id} label={o.evidence_labels[id]!} />
          ))}
        </div>
      </section>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="rounded-[18px] border border-hairline-soft p-4">
          <h3 className="text-[15px] font-semibold text-ink">Preconditions</h3>
          <ul className="mt-2.5 space-y-2">
            {o.option.preconditions.map((p) => (
              <li key={p} className="flex items-center gap-2.5 text-[14.5px] text-ink-2">
                <CircleCheck aria-hidden className="size-[18px] shrink-0 text-ready" /> {p}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-[18px] bg-notice-tint p-4">
          <h3 className="flex items-center gap-2 text-[15px] font-semibold text-notice">
            <AlertTriangle aria-hidden className="size-[18px]" /> Still unknown
          </h3>
          <ul className="mt-2.5 space-y-2">
            {o.option.unknowns.map((u) => (
              <li key={u} className="flex items-center gap-2.5 text-[14.5px] text-ink">
                <CircleHelp aria-hidden className="size-[18px] shrink-0 text-notice" /> {u}
              </li>
            ))}
          </ul>
        </div>
      </div>
      <section className="mt-5">
        <h3 className="text-[15px] font-semibold text-ink">Trade-offs · Hypothesis</h3>
        <ul className="mt-1 space-y-1 text-[14.5px] text-ink-2">
          {o.option.consequences.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </section>
      <div className="my-4 h-px bg-hairline" />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-2 text-[15px] text-ink-2">
          Applicability: <CodeChip tone="discrepancy">{o.option.applicability}</CodeChip>
        </p>
        <p className="text-[12.5px] text-ink-3">
          Prompt {o.option.prompt_version} · Model {o.option.model_version} · Run {run?.label} · as of {formatOffset(o.option.as_of_ms)}
        </p>
      </div>
    </div>
  );
}

function OptionReviewForm({ o }: { o: OptionView }) {
  const { can } = useAuth();
  const { archived } = useSessionScope();
  const { open } = useEvidence();
  const connected = useConnected();
  const [decision, setDecision] = useState<Decision | ''>('');
  const [reason, setReason] = useState('');
  const mutation = useReviewOption(o.option.id);
  const writable = can('review.write') && o.review_allowed && !archived;
  const ready = !!decision && !!reason.trim() && connected && !mutation.isPending;
  const firstEvidence = Object.keys(o.evidence_labels)[0];

  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-[22px] font-semibold tracking-[-0.025em] text-ink">Evaluator rating</h2>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <MoreButton label="Rating options" />
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-[240px]">
            <DropdownMenuItem onSelect={() => firstEvidence && open(firstEvidence)}>
              <ExternalLink /> Open evidence
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      {!writable ? (
        <Callout className="mt-4" tone="muted" icon={Lock} title="Rating is read-only">
          {archived ? 'Archived sessions cannot be rated.' : 'Your role can read options but not rate them.'}
        </Callout>
      ) : (
        <form
          className="mt-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (!decision || !reason.trim()) return;
            mutation.mutate(
              { decision, reason: reason.trim() },
              {
                onSuccess: () => {
                  toast.success(`Rating saved for ${o.label}`, { description: 'Append-only — earlier ratings stay in history.' });
                  setDecision('');
                  setReason('');
                },
              },
            );
          }}
        >
          <RadioGroup value={decision} onValueChange={(v) => setDecision(v as Decision)} aria-label="Rating" className="gap-0 divide-y divide-hairline-soft" disabled={!connected}>
            {DECISIONS.map((d) => (
              <RadioRow key={d.value} value={d.value} label={d.label} className="rounded-none py-3 first:rounded-t-[12px] last:rounded-b-[12px]" />
            ))}
          </RadioGroup>
          <Label htmlFor={`opt-reason-${o.option.id}`} className="mt-5 block text-[15px] font-semibold">
            Rating reason <span className="font-normal text-ink-2">(required)</span>
          </Label>
          <Textarea id={`opt-reason-${o.option.id}`} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} placeholder="Write an evidence-based reason" className="mt-2 min-h-[110px]" />
          <p className="mt-1.5 flex justify-between gap-2 text-[12.5px] text-ink-3">
            <span>Choose a rating and add a reason before saving.</span>
            <span className="tabular">{reason.length}/500</span>
          </p>
          {mutation.error && (
            <p role="alert" className="mt-3 rounded-[12px] bg-discrepancy-tint px-3.5 py-2.5 text-[13.5px] text-discrepancy">
              {isApiError(mutation.error) ? `${mutation.error.message} ${mutation.error.recovery ?? ''}` : 'Saving failed. Your draft is kept.'}
            </p>
          )}
          {!connected && (
            <p role="status" className="mt-3 flex items-center gap-2 rounded-[12px] bg-notice-tint px-3.5 py-2.5 text-[13.5px] text-notice">
              <WifiOff aria-hidden className="size-4" /> Saving is paused while disconnected.
            </p>
          )}
          <Button type="submit" size="lg" variant={ready ? 'primary' : 'tonal'} className="mt-4 w-full" disabled={mutation.isPending || !connected}>
            {mutation.isPending && <Loader2 className="animate-spin" />} Save rating
          </Button>
        </form>
      )}
      {firstEvidence && (
        <Button variant="tonal" size="lg" className="mt-3 w-full" onClick={() => open(firstEvidence)}>
          <ExternalLink /> Open evidence
        </Button>
      )}
      <p className="mt-3 flex items-start gap-1.5 text-[12.5px] text-ink-2">
        <Info aria-hidden className="mt-0.5 size-3.5 shrink-0" /> Options are hypotheses for evaluation. They are not instructions and cannot be executed or sent.
      </p>
      <ReviewHistory reviews={o.reviews} className="mt-4" />
    </div>
  );
}

export function OptionsPage() {
  const options = useOptions();
  const [params, setParams] = useSearchParams();
  const { mode, setMode, asOf } = useSessionScope();
  const data = options.data;
  const list = data?.options ?? [];
  const selectedId = params.get('option') ?? list[0]?.option.id ?? null;
  const selected = list.find((o) => o.option.id === selectedId) ?? null;

  if (options.isError && !data)
    return (
      <div className="card p-6">
        <ErrorState error={options.error} onRetry={() => options.refetch()} />
      </div>
    );
  if (!data)
    return (
      <div className="card p-6">
        <LoadingRows rows={5} />
      </div>
    );

  return (
    <div className="space-y-5">
      {!data.provider_available && (
        <Callout tone="notice" icon={CloudOff} title="Analysis provider unavailable">
          Stored options remain readable. New options cannot be generated until the provider is reachable; nothing is fabricated in the meantime.
        </Callout>
      )}
      {list.length === 0 ? (
        <div className="card p-6">
          <EmptyState title="No option candidates in this view">
            {mode === 'AS_KNOWN' ? (
              <>
                None are available at {formatOffset(asOf)}.{' '}
                <button type="button" className="font-medium text-data hover:underline" onClick={() => setMode('DEBRIEF')}>
                  Switch to Debrief
                </button>
              </>
            ) : (
              'This run produced no options.'
            )}
          </EmptyState>
        </div>
      ) : (
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[minmax(220px,270px)_minmax(0,1fr)] xl:grid-cols-[minmax(220px,250px)_minmax(0,1fr)_minmax(290px,330px)] 2xl:grid-cols-[270px_minmax(0,1fr)_360px]">
          <nav aria-label="Option candidates" className="card p-3">
            <ul className="space-y-1">
              {list.map((o) => {
                const active = o.option.id === selectedId;
                return (
                  <li key={o.option.id}>
                    <button
                      type="button"
                      aria-current={active ? 'true' : undefined}
                      onClick={() =>
                        setParams(
                          (p) => {
                            const n = new URLSearchParams(p);
                            n.set('option', o.option.id);
                            return n;
                          },
                          { replace: true },
                        )
                      }
                      className={cn('group flex w-full items-center gap-3 rounded-[16px] px-4 py-3.5 text-left transition-colors', active ? 'bg-data-tint/80 shadow-[inset_3px_0_0_0_#2563eb]' : 'hover:bg-sunken')}
                    >
                      <span className="min-w-0 flex-1">
                        <span className={cn('block text-[13.5px]', active ? 'text-data-strong' : 'text-ink-2')}>{o.label}</span>
                        <span className="mt-0.5 block text-[16.5px] font-medium leading-snug tracking-[-0.01em] text-ink">{o.title}</span>
                        {o.option.review_status !== 'UNREVIEWED' && <StatusPill size="sm" className="mt-2" meta={STATUS.optionReview[o.option.review_status]} />}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>
          {selected && (
            <>
              <section aria-label="Option detail" className="card p-6">
                <OptionDetail o={selected} />
              </section>
              <section aria-label="Evaluator rating" className="card p-6 lg:col-span-2 xl:col-span-1">
                <DesktopOnly what="Rating options">
                  <OptionReviewForm key={selected.option.id} o={selected} />
                </DesktopOnly>
              </section>
            </>
          )}
        </div>
      )}
      {data.insufficient.map((i) => (
        <section key={i.entity_id} aria-label={`Insufficient context for ${i.entity_label}`} className="card flex items-start gap-4 p-5">
          <span aria-hidden className="inline-flex size-12 shrink-0 items-center justify-center rounded-full bg-notice-tint text-notice">
            <AlertTriangle className="size-[22px]" />
          </span>
          <div>
            <h2 className="text-[18px] font-semibold text-ink">Insufficient context</h2>
            <p className="mt-0.5 text-[15px] text-ink-2">
              {i.entity_label} · {i.reason}
            </p>
            <p className="text-[15px] text-ink-2">Needed: {i.needed.join(' and ').toLowerCase()}.</p>
          </div>
        </section>
      ))}
    </div>
  );
}
