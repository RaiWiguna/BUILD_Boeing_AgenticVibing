import { AlertTriangle, ChevronRight, Clock3, Flag, MoreHorizontal, RadioTower } from 'lucide-react';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import type { FindingView } from '@/api/types';
import { EvidencePanel } from '@/features/evidence/EvidencePanel';
import { useFindings } from '@/features/workspace/queries';
import { CodeChip, MoreButton, StatusPill } from '@/components/domain/primitives';
import { EmptyState, ErrorState, LoadingRows } from '@/components/domain/states';
import { Select } from '@/components/ui/controls';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/menu';
import { useEvidence } from '@/hooks/useEvidence';
import { useSessionScope } from '@/hooks/useSessionScope';
import { CATEGORY_LABEL, STATUS } from '@/lib/status';
import { formatDate, formatOffset } from '@/lib/time';
import { cn } from '@/lib/utils';

const STATUS_FILTER = [
  { value: 'ALL', label: 'All statuses' },
  { value: 'OPEN', label: 'Open' },
  { value: 'CONFIRMED', label: 'Confirmed' },
  { value: 'DISMISSED', label: 'Dismissed' },
  { value: 'UNRESOLVED', label: 'Cannot be determined' },
];

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
  const { detail, run } = useSessionScope();
  const { open } = useEvidence();
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
  const [status, setStatus] = useState('ALL');
  const { mode, setMode, asOf } = useSessionScope();
  const list = (findings.data ?? []).filter((f) => status === 'ALL' || f.finding.status === status);
  const selectedId = params.get('finding') ?? list[0]?.finding.id ?? null;
  const selected = findings.data?.find((f) => f.finding.id === selectedId) ?? null;
  const select = (id: string) =>
    setParams(
      (p) => {
        const n = new URLSearchParams(p);
        n.set('finding', id);
        return n;
      },
      { replace: true },
    );

  if (findings.isError && !findings.data)
    return (
      <div className="card p-6">
        <ErrorState error={findings.error} onRetry={() => findings.refetch()} />
      </div>
    );

  return (
    <div className="grid grid-cols-1 flex-1 items-start gap-5 lg:grid-cols-[minmax(250px,300px)_minmax(0,1fr)] xl:grid-cols-[minmax(260px,290px)_minmax(270px,320px)_minmax(0,1fr)] 2xl:grid-cols-[300px_minmax(300px,370px)_minmax(0,1fr)]">
      <section aria-labelledby="findings-list" className="card p-3 lg:sticky lg:top-6">
        <div className="flex items-center justify-between gap-2 px-2 pb-3 pt-1.5">
          <h2 id="findings-list" className="whitespace-nowrap text-[15.5px] font-semibold text-ink">
            Findings in session
          </h2>
          <Select size="sm" label="Filter by status" value={status} onValueChange={setStatus} options={STATUS_FILTER} className="h-9 pl-3 pr-2.5 text-[13.5px]" />
        </div>
        {!findings.data ? (
          <LoadingRows rows={3} className="px-2" />
        ) : list.length === 0 ? (
          <EmptyState className="py-8" title="No findings in this view">
            {mode === 'AS_KNOWN' ? (
              <>
                Nothing matching is available at {formatOffset(asOf)}.{' '}
                <button type="button" className="font-medium text-data hover:underline" onClick={() => setMode('DEBRIEF')}>
                  Switch to Debrief
                </button>
              </>
            ) : (
              'Try another status filter.'
            )}
          </EmptyState>
        ) : (
          <FindingList findings={list} selected={selectedId} onSelect={select} />
        )}
      </section>

      {selected ? (
        <>
          <section aria-label="Finding detail" className="card p-6">
            <FindingDetail f={selected} />
          </section>
          <section aria-label="Evidence" className="card p-5 lg:col-span-2 xl:col-span-1">
            <EvidencePanel id={selected.finding.id} headingId="findings-evidence-title" embedded />
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
