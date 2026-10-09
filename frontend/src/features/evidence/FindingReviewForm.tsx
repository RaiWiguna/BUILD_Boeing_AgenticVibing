import { ArrowRight, CheckCircle2, History, Info, Loader2, RefreshCw, WifiOff } from 'lucide-react';
import { useEffect, useEffectEvent, useRef, useState } from 'react';
import { hasCode, isApiError } from '@/api/errors';
import type { FindingView, Review } from '@/api/types';
import { useAuth } from '@/app/providers/AuthProvider';
import { StatusPill } from '@/components/domain/primitives';
import { Callout } from '@/components/domain/states';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioRow } from '@/components/ui/controls';
import { Kbd, Label, Textarea } from '@/components/ui/input';
import { DraftGuard } from '@/hooks/useDraftGuard';
import { useConnected } from '@/hooks/useSessionStream';
import { useSessionScope } from '@/hooks/useSessionScope';
import { STATUS } from '@/lib/status';
import { formatDateTimeUtc } from '@/lib/time';
import { cn } from '@/lib/utils';
import { useReviewFinding } from './queries';

type Decision = 'CONFIRMED' | 'DISMISSED' | 'UNRESOLVED';
const MAX = 500;

const ADVANCE_KEY = 'flowlens.advanceAfterSave';
function readAdvance() {
  try {
    return localStorage.getItem(ADVANCE_KEY) === '1';
  } catch {
    return false;
  }
}

/** Typing in a field must never trigger single-key shortcuts. */
export function isTyping(target: EventTarget | null) {
  const el = target as HTMLElement | null;
  return !!el && (el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName) || !!el.closest('[role="dialog"],[role="menu"],[role="listbox"]'));
}

const DECISIONS: { value: Decision; label: string }[] = [
  { value: 'CONFIRMED', label: 'Confirm finding' },
  { value: 'DISMISSED', label: 'Dismiss' },
  { value: 'UNRESOLVED', label: 'Cannot be determined yet' },
];

export function ReviewHistory({ reviews, className }: { reviews: Review[]; className?: string }) {
  const { session } = useAuth();
  if (!reviews.length) return null;
  return (
    <div className={className}>
      <p className="flex items-center gap-2 text-[13px] font-medium text-ink-2">
        <History aria-hidden className="size-4" /> Review history · append-only
      </p>
      <ol className="mt-2 space-y-2">
        {[...reviews].reverse().map((r, i) => (
          <li key={r.id} className={cn('rounded-[14px] border border-hairline-soft px-3.5 py-2.5', i > 0 && 'opacity-75')}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <StatusPill size="sm" meta={r.decision === 'CONFIRMED' ? STATUS.reviewer.CONFIRMED : r.decision === 'DISMISSED' ? STATUS.reviewer.DISMISSED : r.decision === 'UNRESOLVED' ? STATUS.findingStatus.UNRESOLVED : STATUS.reviewer.UNREVIEWED} />
              <span className="text-[12px] text-ink-3 tabular">
                Revision {reviews.length - i} · {r.actor_id === session?.account.id ? 'You' : 'Another reviewer'} · {formatDateTimeUtc(r.recorded_at)}
              </span>
            </div>
            <p className="mt-1.5 text-[13.5px] text-ink">{r.reason}</p>
            {i === 0 && reviews.length > 1 && <p className="mt-1 text-[12px] text-ink-3">Supersedes revision {reviews.length - 1}; earlier revisions stay in the audit trail.</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}

/**
 * Reviewer decision (comp 06). Starts with no selection, requires a reason, writes a new
 * append-only revision, never auto-retries, and keeps the draft on conflicts or connection loss.
 * After saving it stays on the item and offers "Next finding" (decision D-3); keys 1/2/3 pick a
 * decision (never saving) and ⌘/Ctrl+Enter saves when the form is valid.
 */
export function FindingReviewForm({ finding, onNext, nextLabel, className }: { finding: FindingView; onNext?: () => void; nextLabel?: string | null; className?: string }) {
  const { archived } = useSessionScope();
  const connected = useConnected();
  const [decision, setDecision] = useState<Decision | ''>('');
  const [reason, setReason] = useState('');
  const [touched, setTouched] = useState(false);
  const [saved, setSaved] = useState<number | null>(null);
  const [advance, setAdvance] = useState(readAdvance);
  const formRef = useRef<HTMLFormElement>(null);
  const mutation = useReviewFinding(finding.finding.id);
  const revision = finding.reviews.length;
  const reasonError = touched && !reason.trim() ? 'A reason is required. Base it on the evidence above.' : null;
  const conflict = mutation.error && hasCode(mutation.error, 'VERSION_CONFLICT');
  const disabled = archived || !connected || mutation.isPending;
  const canSave = !!decision && !!reason.trim() && !disabled;

  const submit = () => {
    setTouched(true);
    if (!decision || !reason.trim()) return;
    mutation.mutate(
      { decision, reason: reason.trim(), expectedVersion: finding.finding.revision },
      {
        onSuccess: () => {
          setDecision('');
          setReason('');
          setTouched(false);
          setSaved(revision + 1);
          if (advance && onNext) onNext();
        },
      },
    );
  };

  // Keyboard: 1/2/3 choose a decision outside text fields; ⌘/Ctrl+Enter saves from anywhere on the page.
  const onSaveKey = useEffectEvent(() => submit());
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (disabled) return;
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        onSaveKey();
        return;
      }
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(e.target)) return;
      const d = DECISIONS[Number(e.key) - 1];
      if (d) {
        e.preventDefault();
        setDecision(d.value);
        setSaved(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [disabled]);

  const toggleAdvance = (v: boolean) => {
    setAdvance(v);
    try {
      localStorage.setItem(ADVANCE_KEY, v ? '1' : '0');
    } catch {
      /* preference only */
    }
  };

  return (
    <section aria-labelledby={`review-${finding.finding.id}`} className={className}>
      <DraftGuard dirty={!!decision || !!reason.trim()} what="review" />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id={`review-${finding.finding.id}`} className="text-[19px] font-semibold tracking-[-0.02em] text-ink">
          Reviewer decision
        </h3>
        <span className="hidden items-center gap-1 text-[12px] text-ink-3 xl:inline-flex">
          <Kbd>1</Kbd>
          <Kbd>2</Kbd>
          <Kbd>3</Kbd> choose · <Kbd>⌘↵</Kbd> save
        </span>
      </div>
      {saved != null && (
        <div role="status" className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-[14px] bg-ready-tint px-3.5 py-2.5 text-[14px] text-ink">
          <CheckCircle2 aria-hidden className="size-[18px] text-ready" />
          <span className="flex-1">
            Review saved for {finding.label} · revision {saved}, append-only.
          </span>
          {onNext && nextLabel && (
            <Button size="sm" variant="primary" onClick={onNext}>
              Next finding · {nextLabel} <ArrowRight />
            </Button>
          )}
          {onNext && !nextLabel && <span className="text-[13px] text-ink-2">All findings in this queue are reviewed.</span>}
        </div>
      )}
      <form
        ref={formRef}
        className="mt-3 space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <RadioGroup
          value={decision}
          onValueChange={(v) => {
            setDecision(v as Decision);
            setSaved(null);
          }} aria-label="Decision" className="flex flex-wrap gap-x-1 gap-y-0.5" disabled={disabled}>
          {DECISIONS.map((d) => (
            <RadioRow key={d.value} value={d.value} label={d.label} className="px-2.5 py-1.5 [&_span.block]:whitespace-nowrap [&_span.block]:text-[14.5px]" />
          ))}
        </RadioGroup>
        <div className="space-y-1.5">
          <Label htmlFor={`reason-${finding.finding.id}`}>
            Reason <span className="font-normal text-ink-2">(required)</span>
          </Label>
          <div className="relative">
            <Textarea
              id={`reason-${finding.finding.id}`}
              value={reason}
              maxLength={MAX}
              onChange={(e) => {
                setReason(e.target.value);
                setSaved(null);
              }}
              onBlur={() => setTouched(true)}
              placeholder="Write an evidence-based reason"
              aria-invalid={!!reasonError}
              aria-describedby={`reason-help-${finding.finding.id}`}
              disabled={disabled}
              className="min-h-[72px] pb-7"
            />
            <span className="pointer-events-none absolute bottom-2 right-3 text-[12px] text-ink-3 tabular">
              {reason.length}/{MAX}
            </span>
          </div>
          <p id={`reason-help-${finding.finding.id}`} className={cn('text-[12.5px]', reasonError ? 'text-discrepancy' : 'sr-only')}>
            {reasonError ?? 'Reason is required.'}
          </p>
        </div>

        {conflict && (
          <Callout
            tone="notice"
            icon={RefreshCw}
            title="A newer review was saved by someone else"
            action={
              <Button size="sm" variant="secondary" onClick={() => mutation.reset()}>
                <RefreshCw /> I’ve read the latest — keep my draft
              </Button>
            }
          >
            Your draft is kept. Check the latest revision below, then save again if your decision still applies.
          </Callout>
        )}
        {mutation.error && !conflict && (
          <p role="alert" className="rounded-[12px] bg-discrepancy-tint px-3.5 py-2.5 text-[13.5px] text-discrepancy">
            {isApiError(mutation.error) ? `${mutation.error.message} ${mutation.error.recovery ?? ''}` : 'Saving failed. Your draft is kept.'}
          </p>
        )}
        {!connected && (
          <p role="status" className="flex items-center gap-2 rounded-[12px] bg-notice-tint px-3.5 py-2.5 text-[13.5px] text-notice">
            <WifiOff aria-hidden className="size-4" /> Saving is paused while disconnected. Your draft stays here; nothing is queued.
          </p>
        )}
        {archived && <p className="rounded-[12px] bg-sunken px-3.5 py-2.5 text-[13.5px] text-ink-2">Archived session — reviews are read-only.</p>}

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" size="lg" variant={canSave ? 'primary' : 'tonal'} className="min-w-[200px] flex-1" disabled={mutation.isPending || disabled} aria-disabled={!canSave}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            {mutation.isPending ? 'Saving review…' : 'Save review'}
          </Button>
          {onNext && (
            <label className="flex cursor-pointer items-center gap-2 text-[13px] text-ink-2">
              <input type="checkbox" checked={advance} onChange={(e) => toggleAdvance(e.target.checked)} className="size-4 accent-[#2563eb]" />
              Advance after saving
            </label>
          )}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 text-[12.5px] text-ink-2">
          <span className="flex items-center gap-1.5">
            <Info aria-hidden className="size-3.5" /> Acknowledging does not confirm the finding.
          </span>
          <span className="tabular">Revision {revision + 1} · Append-only</span>
        </div>
      </form>
      <ReviewHistory reviews={finding.reviews} className="mt-4" />
    </section>
  );
}
