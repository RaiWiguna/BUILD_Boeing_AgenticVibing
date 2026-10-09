import { AlertTriangle, Brain, CheckCircle2, ChevronRight, Clock3, FileText, Flag, MoreHorizontal, RadioTower } from 'lucide-react';
import { useEffect, useEffectEvent, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import type { FindingView } from '@/api/types';
import { EvidencePanel } from '@/features/evidence/EvidencePanel';
import { isTyping } from '@/features/evidence/FindingReviewForm';
import { useTranscript } from './queries';
import { useFindings } from '@/features/workspace/queries';
import { CodeChip, MoreButton, StatusPill } from '@/components/domain/primitives';
import { EmptyState, ErrorState, LoadingRows } from '@/components/domain/states';
import { Select } from '@/components/ui/controls';
import { Kbd } from '@/components/ui/input';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/menu';
import { useEvidence } from '@/hooks/useEvidence';
import { useSessionScope } from '@/hooks/useSessionScope';
import { CATEGORY_LABEL, STATUS } from '@/lib/status';
import { formatDate, formatOffset } from '@/lib/time';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

const STATUS_FILTER = [
  { value: 'NEEDS_REVIEW', label: 'Needs review' },
  { value: 'ALL', label: 'All statuses' },
  { value: 'CONFIRMED', label: 'Confirmed' },
  { value: 'DISMISSED', label: 'Dismissed' },
  { value: 'UNRESOLVED', label: 'Cannot be determined' },
];

/** Open or under review = still needs a reviewer decision. */
export const needsReview = (f: FindingView) => f.finding.status === 'OPEN' || f.finding.status === 'UNDER_REVIEW';
const matches = (status: string) => (f: FindingView) => status === 'ALL' || (status === 'NEEDS_REVIEW' ? needsReview(f) : f.finding.status === status);

function priorityChip(f: FindingView) {
  const p = STATUS.priority[f.finding.priority];
  const s = f.finding.status;
  return (
    <CodeChip tone={p.tone}>
      {p.code}
      {f.finding.priority === 'ATTENTION' && ` · ${s === 'UNRESOLVED' ? 'UNRESOLVED' : s}`}
    </CodeChip>
  );
}

function FindingList({ findings, selected, onSelect }: { findings: FindingView[]; selected: string | null; onSelect: (id: string) => void }) {
  return (
    <ul className="space-y-1" aria-label="Findings in session">
      {findings.map((f) => {
        const active = f.finding.id === selected;
        return (
          <li key={f.finding.id}>
            <button
              type="button"
              aria-current={active ? 'true' : undefined}
              onClick={() => onSelect(f.finding.id)}
              className={cn(
                'group relative flex w-full items-center gap-3 rounded-[16px] px-4 py-3.5 text-left transition-colors duration-[140ms]',
                active ? 'bg-data-tint/80 shadow-[inset_3px_0_0_0_#2563eb]' : 'hover:bg-sunken',
              )}
            >
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-2 text-[13.5px]">
                  <span className="font-medium text-ink">
                    {f.label} · {f.entity_label}
                  </span>
                  <span className="text-ink-2 tabular">{formatOffset(f.finding.event_time_ms)}</span>
                </span>
                <span className="mt-1 block text-[16px] font-medium tracking-[-0.01em] text-ink">{f.title}</span>
                <span className="mt-2 flex flex-wrap items-center gap-1.5">
                  {priorityChip(f)}
                  {f.finding.stale && <StatusPill size="sm" meta={{ label: 'Stale', tone: 'notice', icon: Clock3 }} />}
                  {!needsReview(f) && <StatusPill size="sm" meta={{ label: 'Reviewed', tone: 'ready', icon: CheckCircle2 }} />}
                </span>
              </span>
              <ChevronRight aria-hidden className="size-[18px] shrink-0 text-ink-2 transition-transform group-hover:translate-x-0.5" />
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function FindingDetail({ f }: { f: FindingView }) {
  const { detail, run, href } = useSessionScope();
  const { open } = useEvidence();
  const transcript = useTranscript();
  // Cross-links: the transcript segment behind the first quoted evidence, and the object's memory.
  const evidenceLabels = new Set(f.finding.evidence.map((e) => detail?.labels[e.id]).filter(Boolean));
  const segment = transcript.data?.rows.find((r) => evidenceLabels.has(r.evidence_label));
  const entity = detail?.entities.find((e) => e.callsign === f.entity_label);
  const reviewer = f.reviews.length ? f.reviews[f.reviews.length - 1]!.decision : null;
  return (
    <div>
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-[27px] font-semibold leading-tight tracking-[-0.03em] text-ink">{f.title}</h2>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <MoreButton label="Finding options" />
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-[230px]">
            <DropdownMenuItem onSelect={() => open(f.finding.id)}>
              <Flag /> Open evidence drawer
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link to={`/help#finding-categories`}>
                <MoreHorizontal /> About this category
              </Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <p className="mt-2 text-[16px] leading-relaxed text-ink-2">{f.finding.statement}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {segment && (
          <Link to={href('review/transcript', { segment: segment.original.id })} className="inline-flex h-8 items-center gap-1.5 rounded-full bg-data-tint px-3 text-[13px] font-medium text-data-strong hover:bg-data-soft">
            <FileText aria-hidden className="size-3.5" /> Open in transcript · {segment.label}
          </Link>
        )}
        {entity && (
          <Link to={href(`memory/${entity.id}`)} className="inline-flex h-8 items-center gap-1.5 rounded-full bg-track px-3 text-[13px] font-medium text-ink hover:bg-hairline">
            <Brain aria-hidden className="size-3.5" /> {entity.callsign} memory
          </Link>
        )}
      </div>
      <dl className="mt-5 space-y-3.5 text-[15px]">
        {[
          ['Category', <span className="text-ink">{CATEGORY_LABEL[f.finding.category] ?? f.finding.category}</span>],
          ['Priority', <CodeChip tone={STATUS.priority[f.finding.priority].tone}>{f.finding.priority}</CodeChip>],
          ['Reviewer', <span className="text-ink">{reviewer ? (reviewer === 'UNRESOLVED' ? 'Cannot be determined yet' : STATUS.reviewer[reviewer as 'CONFIRMED' | 'DISMISSED']?.label ?? reviewer) : 'Unreviewed'}</span>],
          ['Movement', <CodeChip tone={f.movement === 'DIVERGENCE_CANDIDATE' ? 'discrepancy' : f.movement === 'CONSISTENT' ? 'data' : 'neutral'}>{f.movement}</CodeChip>],
          ['Quality', <StatusPill size="sm" meta={STATUS.quality[f.finding.quality]} />],
        ].map(([k, v]) => (
          <div key={k as string} className="grid grid-cols-[120px_1fr] items-center gap-3">
            <dt className="text-ink-2">{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
      {f.finding.unknowns.length > 0 && (
        <div className="mt-4 rounded-[14px] bg-notice-tint/70 px-4 py-3">
          <p className="flex items-center gap-2 text-[14px] font-semibold text-notice">
            <AlertTriangle aria-hidden className="size-4" /> Still unknown
          </p>
          <ul className="mt-1 list-disc pl-6 text-[14px] text-ink">
            {f.finding.unknowns.map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="my-5 h-px bg-hairline" />
      <div className={cn('flex items-start gap-3.5 rounded-[16px] p-4', f.source_alert.status === 'PRESENT' ? 'bg-notice-tint' : 'bg-sunken')}>
        <span aria-hidden className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-surface text-notice shadow-control">
          <RadioTower className="size-[18px]" />
        </span>
        <div>
          <p className="text-[15px] font-semibold text-ink">Source alert</p>
          <p className="mt-0.5 text-[14.5px] text-ink-2">{f.source_alert.status === 'PRESENT' ? `Recorded${f.source_alert.severity ? ` · ${f.source_alert.severity}` : ''}` : 'Not available'}</p>
        </div>
      </div>
      <p className="mt-2.5 text-[13px] text-ink-2">AI findings and source alerts are recorded separately. {f.source_alert.note}</p>
      {f.correction_note && <p className="mt-3 rounded-[12px] bg-data-tint px-3.5 py-2.5 text-[13.5px] text-data-strong">{f.correction_note}</p>}
      <div className="my-5 h-px bg-hairline" />
      <h3 className="text-[17px] font-semibold text-ink">Context</h3>
      <dl className="mt-3 space-y-3 text-[15px]">
        <div className="grid grid-cols-[120px_1fr] gap-3">
          <dt className="text-ink-2">Session</dt>
          <dd className="text-ink">{detail?.title}</dd>
        </div>
        <div className="grid grid-cols-[120px_1fr] gap-3">
          <dt className="text-ink-2">Event time</dt>
          <dd className="text-ink tabular">
            {formatOffset(f.finding.event_time_ms)}
            <span className="block text-[13px] text-ink-2">available {f.finding.available_time_ms != null ? formatOffset(f.finding.available_time_ms) : '—'}</span>
          </dd>
        </div>
        <div className="grid grid-cols-[120px_1fr] gap-3">
          <dt className="text-ink-2">Callsign</dt>
          <dd className="text-ink">{f.entity_label}</dd>
        </div>
        <div className="grid grid-cols-[120px_1fr] gap-3">
          <dt className="text-ink-2">Run</dt>
          <dd className="text-ink">{run?.label}</dd>
        </div>
        <div className="grid grid-cols-[120px_1fr] gap-3">
          <dt className="text-ink-2">Date</dt>
          <dd className="text-ink">{detail ? formatDate(detail.recorded_at) : '—'}</dd>
        </div>
        <div className="grid grid-cols-[120px_1fr] gap-3">
          <dt className="text-ink-2">Rules</dt>
          <dd className="text-ink">
            {f.finding.rule_version} · <CodeChip>{f.finding.applicability}</CodeChip>
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function FindingsPage() {
  const findings = useFindings();
  const [params, setParams] = useSearchParams();
  const [status, setStatus] = useState('NEEDS_REVIEW');
  const { mode, setMode, asOf } = useSessionScope();
  const all = findings.data ?? [];
  const list = all.filter(matches(status));
  const reviewed = all.filter((f) => !needsReview(f)).length;
  const selectedId = params.get('finding') ?? list[0]?.finding.id ?? all[0]?.finding.id ?? null;
  const selected = all.find((f) => f.finding.id === selectedId) ?? null;
  // The selected item stays visible even after it leaves the "Needs review" filter (D-3).
  const shown = selected && !list.includes(selected) ? all.filter((f) => list.includes(f) || f === selected) : list;
  const at = all.findIndex((f) => f.finding.id === selectedId);
  // Next = the next item after the current one (session order) that matches the filter, wrapping around.
  const next = [...all.slice(at + 1), ...all.slice(0, Math.max(0, at))].find((f) => f !== selected && matches(status)(f) && (status !== 'NEEDS_REVIEW' || needsReview(f))) ?? null;
  const select = (id: string) =>
    setParams(
      (p) => {
        const n = new URLSearchParams(p);
        n.set('finding', id);
        return n;
      },
      { replace: true },
    );

  // Pin the default selection in the URL so saving never moves the reviewer to another item.
  const pinned = params.get('finding');
  const first = list[0]?.finding.id ?? all[0]?.finding.id;
  useEffect(() => {
    if (!pinned && first) select(first);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pinned, first]);

  // J / K move through the visible queue; ignored while typing.
  const step = useEffectEvent((dir: 1 | -1) => {
    if (!shown.length) return;
    const i = shown.findIndex((f) => f.finding.id === selectedId);
    const target = shown[Math.min(shown.length - 1, Math.max(0, i + dir))];
    if (target) select(target.finding.id);
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(e.target)) return;
      if (e.key === 'j' || e.key === 'J') step(1);
      else if (e.key === 'k' || e.key === 'K') step(-1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  if (findings.isError && !findings.data)
    return (
      <div className="card p-6">
        <ErrorState error={findings.error} onRetry={() => findings.refetch()} />
      </div>
    );

  return (
    <div className="grid flex-1 grid-cols-1 items-start gap-5 fit:min-h-0 fit:grid-rows-[minmax(0,1fr)] fit:items-stretch lg:grid-cols-[minmax(250px,300px)_minmax(0,1fr)] xl:grid-cols-[minmax(260px,290px)_minmax(270px,320px)_minmax(0,1fr)] 2xl:grid-cols-[300px_minmax(300px,370px)_minmax(0,1fr)]">
      <section aria-labelledby="findings-list" className="card p-3 lg:sticky lg:top-6 fit:static fit:flex fit:min-h-0 fit:flex-col">
        <div className="px-2 pb-3 pt-1.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 id="findings-list" className="whitespace-nowrap text-[15.5px] font-semibold text-ink">
              Findings in session
            </h2>
            <Select size="sm" label="Filter by status" value={status} onValueChange={setStatus} options={STATUS_FILTER} className="h-9 pl-3 pr-2.5 text-[13.5px]" />
          </div>
          {findings.data && (
            <div className="mt-3">
              <p className="flex items-center justify-between text-[13px] text-ink-2 tabular">
                <span>
                  <span className="font-semibold text-ink">{reviewed}</span> of {all.length} reviewed
                </span>
                <span>{all.length - reviewed} {all.length - reviewed === 1 ? 'needs' : 'need'} review</span>
              </p>
              <div role="progressbar" aria-label="Review progress" aria-valuemin={0} aria-valuemax={all.length} aria-valuenow={reviewed} className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-track">
                <div className="h-full rounded-full bg-data transition-[width] duration-300" style={{ width: `${all.length ? (reviewed / all.length) * 100 : 0}%` }} />
              </div>
              <p className="mt-2 hidden text-[12px] text-ink-3 xl:block">
                <Kbd>J</Kbd> <Kbd>K</Kbd> next / previous
              </p>
            </div>
          )}
        </div>
        {!findings.data ? (
          <LoadingRows rows={3} className="px-2" />
        ) : shown.length === 0 ? (
          <EmptyState className="py-8" title="No findings in this view">
            {mode === 'AS_KNOWN' ? (
              <>
                Nothing matching is available at {formatOffset(asOf)}.{' '}
                <button type="button" className="font-medium text-data hover:underline" onClick={() => setMode('DEBRIEF')}>
                  Switch to Debrief
                </button>
              </>
            ) : status === 'NEEDS_REVIEW' ? (
              <>
                Every finding has a reviewer decision.{' '}
                <button type="button" className="font-medium text-data hover:underline" onClick={() => setStatus('ALL')}>
                  Show all
                </button>
              </>
            ) : (
              'Try another status filter.'
            )}
          </EmptyState>
        ) : (
          <ScrollArea className="fit:min-h-0 fit:flex-1">
            <FindingList findings={shown} selected={selectedId} onSelect={select} />
          </ScrollArea>
        )}
      </section>

      {selected ? (
        <>
          <section aria-label="Finding detail" className="card fit:flex fit:min-h-0 fit:flex-col fit:overflow-hidden">
            <ScrollArea className="p-6 fit:min-h-0 fit:flex-1">
              <FindingDetail f={selected} />
            </ScrollArea>
          </section>
          <section aria-label="Evidence" className="card p-5 fit:flex fit:min-h-0 fit:flex-col fit:short:block fit:short:overflow-y-auto fit:short:scrollbar-thin lg:col-span-2 xl:col-span-1">
            <EvidencePanel id={selected.finding.id} headingId="findings-evidence-title" className="fit:flex-1" embedded onNext={next ? () => select(next.finding.id) : () => undefined} nextLabel={next?.label ?? null} />
          </section>
        </>
      ) : (
        findings.data && (
          <div className="card p-6">
            <EmptyState title="Select a finding" />
          </div>
        )
      )}
    </div>
  );
}
