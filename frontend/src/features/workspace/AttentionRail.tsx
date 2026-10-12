import { AlarmClock, AlertTriangle, CheckCircle2, ChevronRight, CircleHelp, Clock3, Flag, Info, ListChecks, Loader2, MessageSquareText, MinusCircle, Play, Plane, type LucideIcon } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router';
import type { FindingView, LiveFact, ReminderView, SlotComparisonRow } from '@/api/types';
import { Card, MoreButton, StatusPill } from '@/components/domain/primitives';
import { EmptyState, ErrorState, LoadingRows } from '@/components/domain/states';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from '@/components/ui/menu';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useEvidence } from '@/hooks/useEvidence';
import { STATUS } from '@/lib/status';
import { formatClock, formatUtcAt } from '@/lib/time';
import { cn } from '@/lib/utils';

const PRIORITY_STYLE: Record<FindingView['finding']['priority'], { bg: string; tile: string; icon: LucideIcon }> = {
  ATTENTION: { bg: 'bg-discrepancy-tint/80 hover:bg-discrepancy-tint', tile: 'bg-[#f9d9e7] text-discrepancy', icon: AlarmClock },
  NOTICE: { bg: 'bg-notice-tint/80 hover:bg-notice-tint', tile: 'bg-[#fbe6bd] text-notice', icon: AlertTriangle },
  INFO: { bg: 'bg-sunken hover:bg-track/70', tile: 'bg-track text-ink-2', icon: Info },
};

const SLOT_LABEL: Record<SlotComparisonRow['slot'], string> = { CALLSIGN: 'Callsign', RUNWAY: 'Runway', ACTION: 'Instruction', CONDITION: 'Condition', NEGATION: 'Negation' };
const SLOT_STATE: Record<SlotComparisonRow['status'], { label: string; icon: LucideIcon; tone: string }> = {
  MATCHED: { label: 'Match', icon: CheckCircle2, tone: 'text-ready' },
  MISMATCH: { label: 'Differs', icon: AlertTriangle, tone: 'text-discrepancy' },
  MISSING: { label: 'Not heard', icon: MinusCircle, tone: 'text-ink-3' },
  AMBIGUOUS: { label: 'Unclear', icon: CircleHelp, tone: 'text-notice' },
};

/** Said vs heard per critical slot, compact enough for the rail. */
function SlotRows({ slots }: { slots: SlotComparisonRow[] }) {
  return (
    <table className="mt-2.5 w-full table-fixed overflow-hidden rounded-[12px] bg-surface/70 text-left text-[12.5px] leading-snug">
      <caption className="sr-only">Said and heard per slot</caption>
      <thead className="text-[11px] uppercase tracking-[0.05em] text-ink-3">
        <tr>
          <th scope="col" className="w-[76px] px-2.5 pb-1 pt-2 font-medium">
            <span className="sr-only">Slot</span>
          </th>
          <th scope="col" className="px-1.5 pb-1 pt-2 font-medium">
            Said
          </th>
          <th scope="col" className="px-1.5 pb-1 pt-2 font-medium">
            Heard
          </th>
          <th scope="col" className="w-7 pb-1 pt-2">
            <span className="sr-only">Compare</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {slots.map((r) => {
          const st = SLOT_STATE[r.status];
          const Icon = st.icon;
          return (
            <tr key={r.slot} className={cn('border-t border-hairline-soft align-top', r.status === 'MISMATCH' && 'bg-discrepancy-tint/60')}>
              <th scope="row" className="px-2.5 py-1.5 font-medium text-ink-2">
                {SLOT_LABEL[r.slot]}
              </th>
              <td className={cn('break-words px-1.5 py-1.5', r.said ? 'text-ink' : 'text-ink-3')}>{r.said ?? '—'}</td>
              <td className={cn('break-words px-1.5 py-1.5', r.heard ? (r.status === 'MISMATCH' ? 'font-semibold text-discrepancy' : 'text-ink') : 'text-ink-3')}>{r.heard ?? '—'}</td>
              <td className="py-1.5 pr-2">
                <span role="img" aria-label={st.label} title={st.label} className="inline-flex">
                  <Icon aria-hidden className={cn('size-4', st.tone)} />
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/** Fact rows for highlights that are not a readback comparison (position, traffic, confirmation). */
function FactRows({ facts }: { facts: LiveFact[] }) {
  return (
    <dl className="mt-2.5 grid grid-cols-[96px_minmax(0,1fr)] overflow-hidden rounded-[12px] bg-surface/70 text-[12.5px] leading-snug">
      {facts.map((x, i) => (
        <div key={x.label} className={cn('contents', i > 0 && '[&>*]:border-t [&>*]:border-hairline-soft')}>
          <dt className="px-2.5 py-1.5 font-medium text-ink-2">{x.label}</dt>
          <dd className={cn('break-words px-1.5 py-1.5', x.tone === 'attention' ? 'font-semibold text-discrepancy' : x.tone === 'notice' ? 'text-notice' : 'text-ink')}>{x.value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** How long a resolved highlight or a done reminder stays (dimmed) in the live rail. */
const LINGER_MS = 30_000;

/**
 * Clicking a card selects its object and highlights its evidence range on the timeline;
 * it never moves the as-of. "Review" opens the finding in Review (full-session lens).
 */
function FindingCard({ f, reviewHref, onFocusRange, onListen, isNew, clock, resolved }: { f: FindingView; reviewHref: string; onFocusRange: (f: FindingView) => void; onListen?: (f: FindingView) => void; isNew?: boolean; clock: (ms: number) => string; resolved?: boolean }) {
  const { open } = useEvidence();
  const style = resolved ? PRIORITY_STYLE.INFO : PRIORITY_STYLE[f.finding.priority];
  const Icon = style.icon;
  const reviewed = f.finding.status !== 'OPEN';
  return (
    <li className={cn('group relative rounded-[20px] p-3.5 transition-colors duration-[140ms]', style.bg, resolved && 'opacity-70', isNew && 'animate-in fade-in slide-in-from-top-2 ring-2 ring-data/40 duration-500')} onClick={() => onFocusRange(f)} onFocus={() => onFocusRange(f)}>
      <div className="flex items-start gap-3">
        <span aria-hidden className={cn('mt-0.5 inline-flex size-9 shrink-0 items-center justify-center rounded-full', style.tile)}>
          <Icon className="size-[18px]" strokeWidth={2} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <h3 className="text-[15px] font-semibold leading-snug tracking-[-0.01em] text-ink">
              {f.entity_label} · {f.live.title}
            </h3>
            <span className="flex shrink-0 items-center gap-1.5 pt-px text-[13px] text-ink-2 tabular">
              {clock(f.finding.event_time_ms)}
            </span>
          </div>
          {resolved && f.live.resolved ? (
            <p className="mt-0.5 flex items-start gap-1.5 text-[13.5px] leading-snug text-ink-2">
              <CheckCircle2 aria-hidden className="mt-0.5 size-3.5 shrink-0 text-ready" />
              <span>
                <span className="font-medium text-ink">Resolved</span> · {f.live.resolved}
              </span>
            </p>
          ) : (
            <p className="mt-0.5 text-[13.5px] leading-snug text-ink-2">{f.live.text}</p>
          )}
          {!resolved && f.slots.length > 0 && <SlotRows slots={f.slots} />}
          {!resolved && f.live.facts && f.live.facts.length > 0 && <FactRows facts={f.live.facts} />}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={(e) => {
                if (!onListen) return open(f.finding.id);
                e.stopPropagation();
                onListen(f);
              }}
              className="inline-flex h-9 items-center gap-2 rounded-[11px] bg-surface px-3.5 text-[14px] font-medium text-ink shadow-control transition-shadow hover:shadow-pop"
            >
              <Play aria-hidden className="size-3.5 fill-current" /> {onListen ? 'Listen' : 'View evidence'}
            </button>
            <Link to={reviewHref} onClick={(e) => e.stopPropagation()} className="inline-flex h-9 items-center gap-1.5 rounded-[11px] px-3 text-[14px] font-medium text-ink transition-colors hover:bg-surface/70">
              <ListChecks aria-hidden className="size-4 text-ink-2" /> Review
            </Link>
            {reviewed && <StatusPill size="sm" meta={STATUS.findingStatus[f.finding.status]} />}
            {f.finding.stale && <StatusPill size="sm" meta={{ label: 'Stale', tone: 'notice', icon: Clock3 }} />}
          </div>
        </div>
      </div>
    </li>
  );
}

const REMINDER_ICON: Record<ReminderView['kind'], LucideIcon> = { LIMIT: Flag, TRAFFIC: Plane, INTENT: MessageSquareText };
const SOURCE_LABEL = { ATC: 'ATC', PILOT: 'Pilot' } as const;

/** One standing item: the current clearance limit, traffic advised, or what the pilot said they will do. */
function ReminderRow({ r, clock, onOpen }: { r: ReminderView; clock: (ms: number) => string; onOpen: (r: ReminderView) => void }) {
  const Icon = REMINDER_ICON[r.kind];
  const done = r.state === 'DONE';
  const when = (
    <span className="shrink-0 text-[12.5px] text-ink-3 tabular">
      {r.source ? `${SOURCE_LABEL[r.source]} ` : ''}
      {clock(r.event_time_ms)}
    </span>
  );
  if (done)
    return (
      <li>
        <button type="button" onClick={() => onOpen(r)} title={r.done_text ?? undefined} className="flex w-full items-center gap-2.5 rounded-[12px] px-2.5 py-1 text-left opacity-60 transition-colors hover:bg-sunken">
          <CheckCircle2 aria-hidden className="size-4 shrink-0 text-ink-3" />
          <span className="min-w-0 flex-1 truncate text-[13px] text-ink-2">
            <span className="line-through decoration-ink-3">
              {r.entity_label} · {r.title}
            </span>{' '}
            · Done{r.done_text ? ` · ${r.done_text}` : ''}
          </span>
        </button>
      </li>
    );
  return (
    <li>
      <button type="button" onClick={() => onOpen(r)} className="flex w-full items-start gap-2.5 rounded-[12px] px-2.5 py-1.5 text-left transition-colors hover:bg-sunken">
        <span aria-hidden className="mt-0.5 inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-data-tint text-data">
          <Icon className={cn('size-3.5', r.kind === 'TRAFFIC' && '-rotate-45')} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-baseline justify-between gap-2">
            <span className="min-w-0 text-[14px] font-semibold leading-snug text-ink">
              {r.entity_label} · {r.title}
            </span>
            {when}
          </span>
          <span className="block text-[13px] leading-snug text-ink-2">
            {r.text}
            {r.previous && <span className="text-ink-3"> Was: {r.previous.title}.</span>}
          </span>
        </span>
      </button>
    </li>
  );
}

/** "Needs attention" rail (comp 03): findings available at the current as-of. */
export function AttentionRail({
  findings,
  loading,
  error,
  onRetry,
  asOf,
  reviewBase,
  onFocusRange,
  checking = false,
  recent,
  onListen,
  startUtc,
  reminders,
  live = true,
  className,
}: {
  findings: FindingView[] | undefined;
  loading: boolean;
  error: unknown;
  onRetry: () => void;
  asOf: number;
  reviewBase: (path: string) => string;
  onFocusRange: (f: FindingView) => void;
  /** Live view: the system is checking each transmission as it completes (shown while playing). */
  checking?: boolean;
  /** DEMO live view: finding IDs that just became available. */
  recent?: Set<string>;
  /** DEMO live view: play the evidence range instead of opening the drawer. */
  onListen?: (f: FindingView) => void;
  /** Recording start; times show as UTC wall clock when known. */
  startUtc?: string;
  /** Standing items to keep in mind (clearance limits, traffic advised, stated intentions). */
  reminders?: ReminderView[];
  /** As-known replay: resolved items fade out shortly after they end. */
  live?: boolean;
  className?: string;
}) {
  const { open } = useEvidence();
  const clock = (ms: number) => (startUtc ? formatUtcAt(startUtc, ms) : formatClock(ms));
  const [priority, setPriority] = useState<'ALL' | 'ATTENTION' | 'NOTICE' | 'INFO'>('ALL');
  // Lost or unreadable audio is shown in the transcript and timeline, not as a highlight.
  const highlights = (findings ?? []).filter((f) => f.live.attention !== false);
  const isResolved = (f: FindingView) => f.live.until_ms != null && f.live.until_ms <= asOf;
  const lingering = (until: number | null | undefined) => !live || until == null || asOf - until < LINGER_MS;
  const shown = highlights.filter((f) => !isResolved(f) || lingering(f.live.until_ms));
  const active = highlights.filter((f) => !isResolved(f));
  const filtered = shown.filter((f) => priority === 'ALL' || f.finding.priority === priority);
  const keep = (reminders ?? []).filter((r) => r.state === 'ACTIVE' || lingering(r.done_time_ms));
  // Live view: newest first so a finding that just arrived is in sight.
  const list = onListen ? [...filtered].sort((a, b) => (b.finding.available_time_ms ?? 0) - (a.finding.available_time_ms ?? 0)) : filtered;
  return (
    <Card as="aside" aria-labelledby="attention-title" className={cn('flex flex-col p-5', className)}>
      <div className="flex items-center justify-between gap-3">
        <h2 id="attention-title" className="whitespace-nowrap text-[23px] font-semibold tracking-[-0.025em] text-ink fit:text-[20px]">
          Needs attention
        </h2>
        <div className="flex items-center gap-1">
          <Link to={reviewBase('review/findings')} className="inline-flex h-9 items-center gap-0.5 whitespace-nowrap rounded-[11px] px-2 text-[14px] font-medium text-data hover:bg-data-tint">
            Review all <ChevronRight aria-hidden className="size-4" />
          </Link>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <MoreButton label="Filter findings" className="fit:size-9" />
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-[220px]">
              <DropdownMenuLabel>Priority</DropdownMenuLabel>
              {(['ALL', 'ATTENTION', 'NOTICE', 'INFO'] as const).map((p) => (
                <DropdownMenuItem key={p} onSelect={() => setPriority(p)}>
                  <span className="flex-1">{p === 'ALL' ? 'All priorities' : STATUS.priority[p].label}</span>
                  {priority === p && <CheckCircle2 className="!text-data" />}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between gap-3 text-[14px] text-ink-3">
        <p>
          <span className="tabular">{findings ? active.length : '–'}</span> active · <span className="tabular">{clock(asOf)}</span>
        </p>
        {checking && (
          <span role="status" className="inline-flex items-center gap-1.5 text-[13px] font-medium text-data">
            <Loader2 aria-hidden className="size-3.5 animate-spin" /> Checking
          </span>
        )}
      </div>
      <div className="mt-3 flex min-h-0 flex-1 flex-col">
      {loading && !findings ? (
        <LoadingRows rows={3} />
      ) : error ? (
        <ErrorState compact error={error} onRetry={onRetry} />
      ) : (
        <ScrollArea className="-mx-1 px-1 fit:min-h-0 fit:flex-1">
          {keep.length > 0 && (
            <section aria-labelledby="keep-in-mind" className="mb-3 border-b border-hairline-soft pb-2">
              <h3 id="keep-in-mind" className="px-1 text-[12.5px] font-medium uppercase tracking-[0.06em] text-ink-3">
                Keep in mind
              </h3>
              <ul className="mt-1.5 space-y-0.5">
                {keep.map((r) => (
                  <ReminderRow key={r.id} r={r} clock={clock} onOpen={(x) => x.evidence[0] && open(x.evidence[0])} />
                ))}
              </ul>
            </section>
          )}
          {list.length === 0 ? (
            <EmptyState icon={CheckCircle2} title="Nothing flagged" className="py-8">
              No alerts at {clock(asOf)}. Not a safety confirmation.
            </EmptyState>
          ) : (
            <ul aria-label="Active highlights" className="space-y-3">
              {list.map((f) => (
                <FindingCard key={f.finding.id} f={f} reviewHref={reviewBase(`review/findings?finding=${f.finding.id}`)} onFocusRange={onFocusRange} onListen={onListen} isNew={recent?.has(f.finding.id)} clock={clock} resolved={isResolved(f)} />
              ))}
            </ul>
          )}
        </ScrollArea>
      )}
      </div>
    </Card>
  );
}
