import { History, Info, Loader2, RefreshCw, WifiOff } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { hasCode, isApiError } from '@/api/errors';
import type { FindingView, Review } from '@/api/types';
import { useAuth } from '@/app/providers/AuthProvider';
import { StatusPill } from '@/components/domain/primitives';
import { Callout } from '@/components/domain/states';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioRow } from '@/components/ui/controls';
import { Label, Textarea } from '@/components/ui/input';
import { useConnected } from '@/hooks/useSessionStream';
import { useSessionScope } from '@/hooks/useSessionScope';
import { STATUS } from '@/lib/status';
import { formatDateTimeUtc } from '@/lib/time';
import { cn } from '@/lib/utils';
import { useReviewFinding } from './queries';

type Decision = 'CONFIRMED' | 'DISMISSED' | 'UNRESOLVED';
const MAX = 500;

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
 */
export function FindingReviewForm({ finding }: { finding: FindingView }) {
  const { archived } = useSessionScope();
  const connected = useConnected();
  const [decision, setDecision] = useState<Decision | ''>('');
  const [reason, setReason] = useState('');
  const [touched, setTouched] = useState(false);
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
          toast.success(`Review saved for ${finding.label}`, { description: `Revision ${revision + 1} · append-only` });
          setDecision('');
          setReason('');
          setTouched(false);
        },
      },
    );
  };

  return (
    <section aria-labelledby={`review-${finding.finding.id}`}>
      <h3 id={`review-${finding.finding.id}`} className="text-[19px] font-semibold tracking-[-0.02em] text-ink">
        Reviewer decision
      </h3>
      <form
        className="mt-3 space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <RadioGroup value={decision} onValueChange={(v) => setDecision(v as Decision)} aria-label="Decision" className="flex flex-wrap gap-x-1 gap-y-0.5" disabled={disabled}>
          {DECISIONS.map((d) => (
            <RadioRow key={d.value} value={d.value} label={d.label} className="px-2.5 py-2 [&_span.block]:whitespace-nowrap [&_span.block]:text-[14.5px]" />
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
              onChange={(e) => setReason(e.target.value)}
              onBlur={() => setTouched(true)}
              placeholder="Write an evidence-based reason"
              aria-invalid={!!reasonError}
              aria-describedby={`reason-help-${finding.finding.id}`}
              disabled={disabled}
              className="min-h-[84px] pb-7"
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

        <Button type="submit" size="lg" variant={canSave ? 'primary' : 'tonal'} className="w-full" disabled={mutation.isPending || disabled} aria-disabled={!canSave}>
          {mutation.isPending && <Loader2 className="animate-spin" />}
          {mutation.isPending ? 'Saving review…' : 'Save review'}
        </Button>
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
