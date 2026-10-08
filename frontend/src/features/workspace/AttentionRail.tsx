import { AlarmClock, AlertTriangle, CheckCircle2, ChevronRight, Clock3, Info, ListChecks, Play, type LucideIcon } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router';
import type { EntityInfo, FindingView, OpenLoop } from '@/api/types';
import { Card, HatchedBar, MoreButton, StatusPill } from '@/components/domain/primitives';
import { EmptyState, ErrorState, LoadingRows } from '@/components/domain/states';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from '@/components/ui/menu';
import { PillTabsList, PillTabsTrigger, Tabs, TabsContent } from '@/components/ui/tabs';
import { useEvidence } from '@/hooks/useEvidence';
import { LOOP_KIND_LABEL, STATUS } from '@/lib/status';
import { formatClock } from '@/lib/time';
import { cn } from '@/lib/utils';

const PRIORITY_STYLE: Record<FindingView['finding']['priority'], { bg: string; tile: string; icon: LucideIcon }> = {
  ATTENTION: { bg: 'bg-discrepancy-tint/80 hover:bg-discrepancy-tint', tile: 'bg-[#f9d9e7] text-discrepancy', icon: AlarmClock },
  NOTICE: { bg: 'bg-notice-tint/80 hover:bg-notice-tint', tile: 'bg-[#fbe6bd] text-notice', icon: AlertTriangle },
  INFO: { bg: 'bg-sunken hover:bg-track/70', tile: 'bg-track text-ink-2', icon: Info },
};

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
        <div className="min-w-0 flex-1 pr-5">
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
            {reviewed && <StatusPill size="sm" meta={STATUS.findingStatus[f.finding.status]} />}
            {f.finding.stale && <StatusPill size="sm" meta={{ label: 'Stale', tone: 'notice', icon: Clock3 }} />}
          </div>
        </div>
      </div>
      <Link to={reviewHref} aria-label={`Review ${f.label} ${f.title}`} className="absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-r-[20px] text-ink-2 transition-colors hover:text-ink">
        <ChevronRight aria-hidden className="size-[18px]" />
      </Link>
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
        <h2 id="attention-title" className="text-[23px] font-semibold tracking-[-0.025em] text-ink">
          Needs attention
        </h2>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <MoreButton label="Filter findings" />
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
      <Tabs value={tab} onValueChange={setTab} className="mt-4 flex min-h-0 flex-1 flex-col">
        <PillTabsList className="bg-transparent p-0 [&>button]:h-10 [&>button]:text-[15px] [&>button[data-state=active]]:bg-data-tint [&>button[data-state=active]]:text-data-strong [&>button[data-state=active]]:shadow-none">
          <PillTabsTrigger value="findings">
            Findings <span className="tabular opacity-80">{findings?.length ?? '–'}</span>
          </PillTabsTrigger>
          <PillTabsTrigger value="loops">
            Open loops <span className="tabular opacity-80">{openLoops.length}</span>
          </PillTabsTrigger>
        </PillTabsList>
        <TabsContent value="findings" className="mt-4 flex-1">
          {loading && !findings ? (
            <LoadingRows rows={3} />
          ) : error ? (
            <ErrorState compact error={error} onRetry={onRetry} />
          ) : list.length === 0 ? (
            <EmptyState icon={CheckCircle2} title="Nothing available yet" className="py-8">
              No findings are available at {formatClock(asOf)} in this view. This does not mean the situation is safe or complete.
            </EmptyState>
          ) : (
            <ul className="space-y-3">
              {list.map((f) => (
                <FindingCard key={f.finding.id} f={f} reviewHref={reviewBase(`review/findings?finding=${f.finding.id}`)} onFocusRange={onFocusRange} />
              ))}
            </ul>
          )}
        </TabsContent>
        <TabsContent value="loops" className="mt-4 flex-1">
          {openLoops.length === 0 ? (
            <EmptyState icon={ListChecks} title="No open loops at this as-of" className="py-8">
              Loops close only with evidence; unknown coverage keeps them open.
            </EmptyState>
          ) : (
            <ul className="space-y-3">
              {openLoops.map((l) => (
                <LoopRow key={l.id} loop={l} entities={entities} asOf={asOf} label={label} />
              ))}
            </ul>
          )}
        </TabsContent>
      </Tabs>
      <Link to={reviewBase('review/findings')} className="mt-4 flex h-12 items-center gap-3 rounded-[14px] border border-hairline px-4 text-[15px] font-medium text-ink transition-colors hover:bg-sunken">
        <ListChecks aria-hidden className="size-[18px] text-ink-2" />
        <span className="flex-1">Review all</span>
        <ChevronRight aria-hidden className="size-[18px] text-ink-2" />
      </Link>
    </Card>
  );
}
