import { AlarmClock, AlertTriangle, CheckCircle2, ChevronRight, Clock3, Info, ListChecks, Play, type LucideIcon } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router';
import type { EntityInfo, FindingView, OpenLoop } from '@/api/types';
import { Card, HatchedBar, MoreButton, StatusPill } from '@/components/domain/primitives';
import { EmptyState, ErrorState, LoadingRows } from '@/components/domain/states';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from '@/components/ui/menu';
import { PillTabsList, PillTabsTrigger, Tabs, TabsContent } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useEvidence } from '@/hooks/useEvidence';
import { LOOP_KIND_LABEL, STATUS } from '@/lib/status';
import { formatClock } from '@/lib/time';
import { cn } from '@/lib/utils';

const PRIORITY_STYLE: Record<FindingView['finding']['priority'], { bg: string; tile: string; icon: LucideIcon }> = {
  ATTENTION: { bg: 'bg-discrepancy-tint/80 hover:bg-discrepancy-tint', tile: 'bg-[#f9d9e7] text-discrepancy', icon: AlarmClock },
  NOTICE: { bg: 'bg-notice-tint/80 hover:bg-notice-tint', tile: 'bg-[#fbe6bd] text-notice', icon: AlertTriangle },
  INFO: { bg: 'bg-sunken hover:bg-track/70', tile: 'bg-track text-ink-2', icon: Info },
};

/**
 * Clicking a card selects its object and highlights its evidence range on the timeline;
 * it never moves the as-of. "Review" opens the finding in Review (full-session lens).
 */
function FindingCard({ f, reviewHref, onFocusRange }: { f: FindingView; reviewHref: string; onFocusRange: (f: FindingView) => void }) {
  const { open } = useEvidence();
  const style = PRIORITY_STYLE[f.finding.priority];
  const Icon = style.icon;
  const quote = f.finding.evidence.length > 1 ? f.finding.evidence[f.finding.evidence.length - 1]!.quote : null;
  const reviewed = f.finding.status !== 'OPEN';
  return (
    <li className={cn('group relative rounded-[20px] p-3.5 transition-colors duration-[140ms]', style.bg)} onClick={() => onFocusRange(f)} onFocus={() => onFocusRange(f)}>
      <div className="flex items-start gap-3">
        <span aria-hidden className={cn('mt-0.5 inline-flex size-9 shrink-0 items-center justify-center rounded-full', style.tile)}>
          <Icon className="size-[18px]" strokeWidth={2} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <h3 className="text-[15px] font-semibold leading-snug tracking-[-0.01em] text-ink">
              {f.entity_label} · {f.title}
            </h3>
            <span className="shrink-0 pt-px text-[13px] text-ink-2 tabular">{formatClock(f.finding.event_time_ms)}</span>
          </div>
          <p className="mt-0.5 text-[13.5px] leading-snug text-ink-2">{f.finding.statement}</p>
          {quote && <p className="mt-1 text-[13.5px] text-ink-2 [quotes:'“'_'”']"><q>{quote}</q></p>}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => open(f.finding.id)}
              className="inline-flex h-9 items-center gap-2 rounded-[11px] bg-surface px-3.5 text-[14px] font-medium text-ink shadow-control transition-shadow hover:shadow-pop"
            >
              <Play aria-hidden className="size-3.5 fill-current" /> Listen to evidence
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

function LoopRow({ loop, entities, asOf, label }: { loop: OpenLoop; entities: EntityInfo[]; asOf: number; label: (id: string) => string }) {
  const { open } = useEvidence();
  const ents = loop.entity_ids.map((id) => entities.find((e) => e.id === id)?.callsign ?? 'Unknown').join(', ');
  const elapsed = Math.max(0, asOf - loop.started_ms);
  const window = loop.expected_window_ms;
  const overdue = window != null && elapsed > window;
  const meta = STATUS.loop[loop.status];
  const origin = loop.evidence[0];
  return (
    <li className="rounded-[18px] border border-hairline-soft bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[15px] font-semibold text-ink">
            {ents} · {LOOP_KIND_LABEL[loop.kind] ?? loop.kind}
          </p>
          <p className="mt-0.5 text-[13.5px] text-ink-2 tabular">
            Since {formatClock(loop.started_ms)} · {window != null ? `window ${Math.round(window / 1000)} s` : 'no timer'}
          </p>
        </div>
        <StatusPill size="sm" meta={meta} />
      </div>
      {window != null && loop.status === 'OPEN' && (
        <div className="mt-3">
          <HatchedBar value={Math.min(elapsed, window)} max={window} variant={overdue ? 'notice' : 'data'} height={8} label={`${Math.round(elapsed / 1000)} of ${Math.round(window / 1000)} seconds elapsed`} />
          <p className="mt-1.5 text-[12.5px] text-ink-3 tabular">
            {overdue ? `Expected window passed ${Math.round((elapsed - window) / 1000)} s ago` : `${Math.round((window - elapsed) / 1000)} s left in window`} · {loop.timer_profile_version}
          </p>
        </div>
      )}
      {!loop.coverage_known && <p className="mt-2 text-[13px] text-notice">Coverage unknown — closure may be outside the stored audio.</p>}
      {origin && (
        <button type="button" onClick={() => open(origin.id)} className="mt-3 inline-flex h-8 items-center gap-1.5 rounded-full bg-data-tint px-3 text-[13px] font-semibold text-data-strong hover:bg-data-soft">
          <Play aria-hidden className="size-3 fill-current" /> {label(origin.id)}
        </button>
      )}
    </li>
  );
}

/** "Needs attention" rail (comp 03): findings and open loops at the current as-of. */
export function AttentionRail({
  findings,
  loading,
  error,
  onRetry,
  loops,
  entities,
  asOf,
  reviewBase,
  label,
  onFocusRange,
  className,
}: {
  findings: FindingView[] | undefined;
  loading: boolean;
  error: unknown;
  onRetry: () => void;
  loops: OpenLoop[];
  entities: EntityInfo[];
  asOf: number;
  reviewBase: (path: string) => string;
  label: (id: string) => string;
  onFocusRange: (f: FindingView) => void;
  className?: string;
}) {
  const [tab, setTab] = useState('findings');
  const [priority, setPriority] = useState<'ALL' | 'ATTENTION' | 'NOTICE' | 'INFO'>('ALL');
  const list = (findings ?? []).filter((f) => priority === 'ALL' || f.finding.priority === priority);
  const openLoops = loops.filter((l) => l.status === 'OPEN' || l.status === 'PARTIAL');
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
      <Tabs value={tab} onValueChange={setTab} className="mt-4 flex min-h-0 flex-1 flex-col fit:mt-3">
        <PillTabsList className="bg-transparent p-0 [&>button]:h-10 fit:[&>button]:h-9 [&>button]:text-[15px] [&>button[data-state=active]]:bg-data-tint [&>button[data-state=active]]:text-data-strong [&>button[data-state=active]]:shadow-none">
          <PillTabsTrigger value="findings">
            Findings <span className="tabular opacity-80">{findings?.length ?? '–'}</span>
          </PillTabsTrigger>
          <PillTabsTrigger value="loops">
            Open loops <span className="tabular opacity-80">{openLoops.length}</span>
          </PillTabsTrigger>
        </PillTabsList>
        <TabsContent value="findings" className="mt-4 flex-1 fit:mt-3 fit:flex fit:min-h-0 fit:flex-col">
          {loading && !findings ? (
            <LoadingRows rows={3} />
          ) : error ? (
            <ErrorState compact error={error} onRetry={onRetry} />
          ) : list.length === 0 ? (
            <EmptyState icon={CheckCircle2} title="Nothing available yet" className="py-8">
              No findings are available at {formatClock(asOf)} in this view. This does not mean the situation is safe or complete.
            </EmptyState>
          ) : (
            <ScrollArea as="ul" aria-label="Findings at this as-of" className="-mx-1 space-y-3 px-1 fit:min-h-0 fit:flex-1">
              {list.map((f) => (
                <FindingCard key={f.finding.id} f={f} reviewHref={reviewBase(`review/findings?finding=${f.finding.id}`)} onFocusRange={onFocusRange} />
              ))}
            </ScrollArea>
          )}
        </TabsContent>
        <TabsContent value="loops" className="mt-4 flex-1 fit:mt-3 fit:flex fit:min-h-0 fit:flex-col">
          {openLoops.length === 0 ? (
            <EmptyState icon={ListChecks} title="No open loops at this as-of" className="py-8">
              Loops close only with evidence; unknown coverage keeps them open.
            </EmptyState>
          ) : (
            <ScrollArea as="ul" aria-label="Open loops at this as-of" className="-mx-1 space-y-3 px-1 fit:min-h-0 fit:flex-1">
              {openLoops.map((l) => (
                <LoopRow key={l.id} loop={l} entities={entities} asOf={asOf} label={label} />
              ))}
            </ScrollArea>
          )}
        </TabsContent>
      </Tabs>
    </Card>
  );
}
