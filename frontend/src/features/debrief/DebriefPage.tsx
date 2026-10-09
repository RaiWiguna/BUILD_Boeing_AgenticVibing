import {
  AlertTriangle,
  ArrowRight,
  CalendarClock,
  ChevronRight,
  CircleDot,
  Download,
  FileDiff,
  FilePlus2,
  FileText,
  Flag,
  History,
  Layers,
  Loader2,
  MoreHorizontal,
  Play,
  Sparkles,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { toast } from 'sonner';
import { isApiError } from '@/api/errors';
import type { BriefSection, BriefView, JournalEntry } from '@/api/types';
import { ScopeBanners } from '@/features/workspace/SessionHeader';
import { SessionPageHeader } from '@/features/workspace/SessionPageHeader';
import { IconTile, MoreButton } from '@/components/domain/primitives';
import { EvidenceChip } from '@/components/domain/evidence';
import { Callout, EmptyState, ErrorState, LoadingRows } from '@/components/domain/states';
import { Button } from '@/components/ui/button';
import { Segmented, Select } from '@/components/ui/controls';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/menu';
import { useAuth } from '@/app/providers/AuthProvider';
import { useEvidence } from '@/hooks/useEvidence';
import { useConnected } from '@/hooks/useSessionStream';
import { useSessionScope } from '@/hooks/useSessionScope';
import { formatClock, formatDateTimeUtc } from '@/lib/time';
import { cn } from '@/lib/utils';
import { ExportPanel } from './ExportPanel';
import { useFindings } from '@/features/workspace/queries';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { useBriefs, useCreateBrief, useJournal } from './queries';

const JOURNAL_DOT: Record<JournalEntry['tone'], string> = { data: 'bg-data', discrepancy: 'bg-discrepancy', muted: 'bg-[#a7adb6]' };

const SECTION_STYLE: Record<BriefSection, { icon: typeof FileText; tone: 'data' | 'discrepancy' | 'muted'; accent: string; wash: string }> = {
  KNOWN_SITUATION: { icon: FileText, tone: 'data', accent: 'before:bg-data', wash: '' },
  ACTIVE_RESTRICTIONS: { icon: FileText, tone: 'data', accent: 'before:bg-data', wash: '' },
  CONTEXT_CHANGES: { icon: FileDiff, tone: 'data', accent: 'before:bg-data', wash: '' },
  OPEN_LOOPS: { icon: CircleDot, tone: 'discrepancy', accent: 'before:bg-discrepancy', wash: 'bg-gradient-to-r from-discrepancy-tint/60 to-transparent' },
  FINDINGS: { icon: Flag, tone: 'discrepancy', accent: 'before:bg-discrepancy', wash: '' },
  REVIEW_STATUS: { icon: History, tone: 'muted', accent: 'before:bg-[#c3c8cf]', wash: '' },
  UNKNOWN_COVERAGE: { icon: AlertTriangle, tone: 'muted', accent: '', wash: '' },
};

/* Journal ─────────────────────────────────────────────────────────── */

function JournalRow({ e, last }: { e: JournalEntry; last: boolean }) {
  const { open } = useEvidence();
  const { sid, carry } = useSessionScope();
  const evidence = e.kind !== 'REVIEW';
  const ws = new URLSearchParams(carry);
  ws.set('t', String(e.t));
  ws.set('mode', 'debrief');
  return (
    <li className="relative grid grid-cols-[14px_48px_minmax(0,1fr)_32px] gap-x-3 pb-6 last:pb-1">
      {!last && <span aria-hidden className="absolute left-[6px] top-[18px] bottom-0 w-px bg-hairline" />}
      <span aria-hidden className={cn('relative mt-[6px] size-[11px] rounded-full ring-4 ring-surface', JOURNAL_DOT[e.tone])} />
      <span className="text-[15px] text-ink-2 tabular">{e.kind === 'REVIEW' ? 'After' : formatClock(e.t)}</span>
      <div className="min-w-0">
        <p className="text-[15.5px] font-semibold tracking-[-0.01em] text-ink">
          {e.title}
          {e.kind !== 'FINDING' && e.kind !== 'REVIEW' && <span className="font-semibold"> · {e.label}</span>}
        </p>
        <p className="mt-1 text-[14.5px] leading-snug text-ink-2">{e.detail}</p>
        {evidence && <EvidenceChip id={e.id} label={e.label} size="sm" className="mt-2" />}
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <MoreButton label={`Actions for ${e.title} ${e.label}`} className="size-8 border-transparent bg-transparent shadow-none" />
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-[220px]">
          {evidence && (
            <DropdownMenuItem onSelect={() => open(e.id)}>
              <Play /> Open evidence {e.label}
            </DropdownMenuItem>
          )}
          <DropdownMenuItem asChild>
            <Link to={`/s/${sid}/workspace?${ws}`}>
              <MoreHorizontal /> Show in workspace
            </Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </li>
  );
}

function Journal({ brief }: { brief: BriefView }) {
  const journal = useJournal(brief.brief.as_of_ms);
  const [scope, setScope] = useState<'KEY' | 'ALL'>('KEY');
  const cited = useMemo(() => new Set(brief.sections.flatMap((s) => s.items.flatMap((i) => i.evidence_labels))), [brief]);
  const all = journal.data ?? [];
  // "Key" = events the brief cites, plus findings, corrections and reviews.
  const entries = scope === 'ALL' ? all : all.filter((e) => cited.has(e.label) || e.kind === 'FINDING' || e.kind === 'CORRECTION' || e.kind === 'REVIEW');
  return (
    <section aria-labelledby="journal-title" className="card p-5">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h2 id="journal-title" className="text-[22px] font-semibold tracking-[-0.025em] text-ink">
            Journal
          </h2>
          {journal.data && <span className="inline-flex h-7 items-center whitespace-nowrap rounded-full bg-track px-2.5 text-[13px] font-medium text-ink-2 tabular">{entries.length} events</span>}
        </div>
        <Segmented
          size="sm"
          label="Journal scope"
          value={scope}
          onChange={setScope}
          options={[
            { value: 'KEY', label: 'Key' },
            { value: 'ALL', label: 'All' },
          ]}
        />
      </div>
      {journal.isError && !journal.data ? (
        <ErrorState compact error={journal.error} onRetry={() => journal.refetch()} />
      ) : !journal.data ? (
        <LoadingRows rows={5} />
      ) : entries.length === 0 ? (
        <EmptyState className="py-8" title="No journal events yet" />
      ) : (
        <ScrollArea
          as="ol"
          aria-label="Journal events"
          className="-mr-2 max-h-[calc(100dvh-250px)] min-h-[240px] pr-2"
          moreLabel={() => <p className="pt-2 text-center text-[12.5px] text-ink-3">Scroll for more · {entries.length} events</p>}
        >
          {entries.map((e, i) => (
            <JournalRow key={e.id} e={e} last={i === entries.length - 1} />
          ))}
        </ScrollArea>
      )}
    </section>
  );
}

/* Session summary ─────────────────────────────────────────────────── */

function Spotlight({ brief }: { brief: BriefView }) {
  const { sid, carry } = useSessionScope();
  const s = brief.spotlight;
  if (!s) return null;
  const q = new URLSearchParams(carry);
  q.set('finding', s.finding_id);
  return (
    <article aria-labelledby="spotlight-title" className="spotlight-mesh relative overflow-hidden rounded-[22px] p-5 text-white shadow-[0_18px_40px_-22px_rgba(31,79,209,0.65)]">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[14px] font-medium text-white/90">Key item to review</p>
        <span className="inline-flex h-6 items-center gap-1.5 rounded-full bg-white/20 px-2.5 text-[11.5px] font-semibold uppercase tracking-[0.05em] text-white backdrop-blur-sm">
          <Sparkles aria-hidden className="size-3" /> AI interpretation · Mock
        </span>
      </div>
      <div className="mt-3 flex flex-wrap items-end gap-x-5 gap-y-2">
        <p className="text-[56px] font-medium leading-none tracking-[-0.05em] tabular">{s.metric}</p>
        <p className="pb-1.5 text-[14px] font-medium capitalize text-white/85">{s.metric_label}</p>
      </div>
      <h3 id="spotlight-title" className="mt-3 text-[17px] font-semibold tracking-[-0.01em]">
        {s.title}
      </h3>
      <p className="mt-1 max-w-[52ch] text-[14.5px] leading-snug text-white/90">{s.detail}</p>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <Button asChild size="sm" className="border-transparent bg-white text-ink shadow-[0_4px_14px_rgba(0,0,0,0.12)] hover:bg-white/90">
          <Link to={`/s/${sid}/review/findings?${q}`}>
            Review finding <ArrowRight />
          </Link>
        </Button>
        <p className="text-[12px] text-white/80">Interpretation, not a fact · linked to evidence</p>
      </div>
    </article>
  );
}

function SummarySection({ section }: { section: BriefView['sections'][number] }) {
  const st = SECTION_STYLE[section.section];
  if (section.section === 'UNKNOWN_COVERAGE') {
    return (
      <div className="flex gap-4 rounded-[18px] bg-notice-tint p-4 pr-5">
        <IconTile icon={AlertTriangle} tone="notice" className="bg-[#fde6c4]" />
        <div className="min-w-0">
          <h3 className="text-[16px] font-semibold text-ink">{section.title}</h3>
          <ul className="mt-1 space-y-1 text-[14.5px] leading-snug text-ink">
            {section.items.map((it) => (
              <li key={it.statement}>{it.statement}</li>
            ))}
          </ul>
        </div>
      </div>
    );
  }
  return (
    <div className={cn('relative overflow-hidden rounded-[18px] border border-hairline-soft p-4 pl-5 before:absolute before:inset-y-0 before:left-0 before:w-[3px]', st.accent, st.wash)}>
      <div className="flex gap-4">
        <IconTile icon={st.icon} tone={st.tone} />
        <div className="min-w-0 flex-1">
          <h3 className="text-[16px] font-semibold text-ink">{section.title}</h3>
          <ul className="mt-1 divide-y divide-hairline-soft">
            {section.items.map((it) => (
              <li key={it.statement} className="py-2 first:pt-0 last:pb-0">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-[14.5px] leading-snug text-ink">{it.statement}</p>
                  {it.evidence_labels.length === 1 && <EvidenceChip id={it.evidence_ids[0]!} label={it.evidence_labels[0]!} size="sm" />}
                </div>
                {it.detail && <p className="mt-1 text-[13px] text-ink-3">{it.detail}</p>}
                {it.unknowns.length > 0 && <p className="mt-1 text-[12.5px] text-notice">Unknown: {it.unknowns.join(', ')}</p>}
                {it.evidence_labels.length > 1 && (
                  <span className="mt-2 flex flex-wrap gap-1.5">
                    {it.evidence_labels.map((l, i) => (
                      <EvidenceChip key={l + i} id={it.evidence_ids[i]!} label={l} size="sm" />
                    ))}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function Summary({ brief, latest, onOpenLatest }: { brief: BriefView; latest: BriefView | null; onOpenLatest: () => void }) {
  const { open } = useEvidence();
  const firstEvidence = brief.brief.evidence[0]?.id;
  const order: BriefSection[] = ['KNOWN_SITUATION', 'ACTIVE_RESTRICTIONS', 'CONTEXT_CHANGES', 'OPEN_LOOPS', 'FINDINGS', 'REVIEW_STATUS', 'UNKNOWN_COVERAGE'];
  const sections = [...brief.sections].sort((a, b) => order.indexOf(a.section) - order.indexOf(b.section));
  return (
    <section aria-labelledby="summary-title" className="card p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 id="summary-title" className="text-[22px] font-semibold tracking-[-0.025em] text-ink">
          Session summary
        </h2>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <MoreButton label="Summary options" />
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-[230px]">
            {firstEvidence && (
              <DropdownMenuItem onSelect={() => open(firstEvidence)}>
                <Play /> Open first evidence
              </DropdownMenuItem>
            )}
            <DropdownMenuItem asChild>
              <Link to="/help#provenance">
                <Layers /> About provenance
              </Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {brief.stale && (
        <Callout
          tone="notice"
          icon={History}
          title={`${brief.label} is stale`}
          className="mb-4"
          action={
            latest && latest.brief.id !== brief.brief.id ? (
              <Button size="sm" variant="secondary" onClick={onOpenLatest}>
                Open {latest.label.toLowerCase()}
              </Button>
            ) : undefined
          }
        >
          {brief.stale_reason ?? 'Inputs changed after this brief was created.'} It is kept for the record; create a new revision to reflect the change.
        </Callout>
      )}

      <div className="space-y-3">
        <Spotlight brief={brief} />
        {sections.map((s) => (
          <SummarySection key={s.section} section={s} />
        ))}
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-hairline-soft pt-4">
        <p className="flex items-center gap-2.5 text-[13.5px] text-ink-2">
          <FileText aria-hidden className="size-[18px] text-ink-3" /> Facts, interpretation and reviews stay separate.
        </p>
        {firstEvidence && (
          <Button size="sm" variant="tonal" onClick={() => open(firstEvidence)}>
            Open evidence <ChevronRight />
          </Button>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-[14px] bg-sunken px-4 py-3 text-[12.5px] text-ink-2">
        <span className="flex items-center gap-2">
          <Layers aria-hidden className="size-4 text-ink-3" /> Model {brief.brief.model_version} · prompt {brief.brief.prompt_version} · schema {brief.brief.schema_version ?? '1.0.0'} included
        </span>
        <span className="tabular">
          {brief.brief.labels.filter((l) => l !== 'DEBRIEF').join(' · ')} · as of {formatClock(brief.brief.as_of_ms)}
        </span>
      </div>
    </section>
  );
}

/* Review status ───────────────────────────────────────────────────── */

/** Review progress for the full session, with a direct link to the next unreviewed finding. */
function ReviewStatus() {
  const findings = useFindings();
  const { href } = useSessionScope();
  const all = findings.data ?? [];
  const open = all.filter((f) => f.finding.status === 'OPEN' || f.finding.status === 'UNDER_REVIEW');
  const done = all.length - open.length;
  return (
    <section aria-labelledby="review-status-title" className="card p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 id="review-status-title" className="text-[18px] font-semibold tracking-[-0.02em] text-ink">
          Review status
        </h2>
        <span className="text-[13.5px] text-ink-2 tabular">
          <span className="font-semibold text-ink">{done}</span> of {all.length} reviewed
        </span>
      </div>
      <div role="progressbar" aria-label="Findings reviewed" aria-valuemin={0} aria-valuemax={all.length} aria-valuenow={done} className="mt-3 h-1.5 overflow-hidden rounded-full bg-track">
        <div className="h-full rounded-full bg-data" style={{ width: `${all.length ? (done / all.length) * 100 : 0}%` }} />
      </div>
      {findings.data &&
        (open[0] ? (
          <Button asChild size="sm" variant="secondary" className="mt-4 w-full">
            <Link to={href('review/findings', { finding: open[0].finding.id })}>
              Continue reviewing · {open[0].label} <ArrowRight />
            </Link>
          </Button>
        ) : (
          <p className="mt-3 text-[13.5px] text-ink-2">Every finding has a reviewer decision. A new brief revision reflects them.</p>
        ))}
    </section>
  );
}

/* Page ─────────────────────────────────────────────────────────────── */

export function DebriefPage() {
  const { detail, archived, sid } = useSessionScope();
  const { can } = useAuth();
  const connected = useConnected();
  const briefs = useBriefs();
  const create = useCreateBrief();
  const [params, setParams] = useSearchParams();
  const list = briefs.data ?? [];
  const latest = list[0] ?? null;
  const selected = list.find((b) => b.brief.id === params.get('brief')) ?? latest;
  const setBrief = (id: string) =>
    setParams(
      (p) => {
        const n = new URLSearchParams(p);
        n.set('brief', id);
        return n;
      },
      { replace: true },
    );
  if (!detail) return null;
  const canCreate = can('export.create') && !archived && connected && !create.isPending;

  const createRevision = () =>
    create.mutate(detail.duration_ms, {
      onSuccess: (b) => {
        setBrief(b.brief.id);
        toast.success(`${b.label} created`, { description: `As of ${formatClock(b.brief.as_of_ms)} · earlier revisions are kept` });
      },
      onError: (e) => toast.error(isApiError(e) ? e.message : 'Could not create a brief revision.', { description: isApiError(e) ? e.recovery : 'Stored briefs remain readable.' }),
    });

  return (
    <div className="flex min-h-full flex-col">
      <SessionPageHeader
        title="Debrief"
        area="Debrief"
        lens={false}
        chips={
          detail.manifest.domain_validation !== 'DOMAIN_REVIEWED' && (
            <span className="inline-flex h-[30px] items-center gap-1.5 rounded-full bg-notice-tint px-3 text-[13.5px] font-medium text-notice">
              <AlertTriangle aria-hidden className="size-[15px]" /> Not domain reviewed
            </span>
          )
        }
        actions={
          <>
            {list.length > 0 && selected && (
              <Select
                label="Brief revision"
                value={selected.brief.id}
                onValueChange={setBrief}
                icon={<FileText aria-hidden className="text-ink-2" />}
                options={list.map((b) => ({ value: b.brief.id, label: `${b.label.replace('Brief revision', 'Brief rev.')}${b.stale ? ' · stale' : ''}` }))}
              />
            )}
            {selected && (
              <span className="inline-flex h-11 items-center gap-2 rounded-control border border-hairline bg-surface px-3.5 text-[14px] font-medium text-ink shadow-control tabular">
                <CalendarClock aria-hidden className="size-4 text-ink-2" /> Brief as of {formatClock(selected.brief.as_of_ms)}
              </span>
            )}
            {can('export.create') && (
              <Button variant="secondary" className="hidden md:inline-flex" onClick={createRevision} disabled={!canCreate}>
                {create.isPending ? <Loader2 className="animate-spin" /> : <FilePlus2 />}
                {create.isPending ? 'Creating…' : 'Create brief revision'}
              </Button>
            )}
            {selected && (
              <Sheet>
                <SheetTrigger asChild>
                  <Button variant="primary">
                    <Download /> Export report
                  </Button>
                </SheetTrigger>
                <SheetContent title="Export report" description={`${selected.label} · as of ${formatClock(selected.brief.as_of_ms)} · generated locally by the MOCK adapter; original sources stay stored.`}>
                  <ExportPanel brief={selected} sid={sid} />
                </SheetContent>
              </Sheet>
            )}
          </>
        }
      />
      <ScopeBanners />

      {briefs.isError && !briefs.data ? (
        <div className="card p-6">
          <ErrorState error={briefs.error} onRetry={() => briefs.refetch()} />
        </div>
      ) : !briefs.data ? (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(300px,360px)]">
          {[0, 1].map((i) => (
            <div key={i} className="card p-5">
              <LoadingRows rows={5} />
            </div>
          ))}
        </div>
      ) : !selected ? (
        <div className="card p-8">
          <EmptyState icon={FileText} title="No brief yet" action={can('export.create') ? <Button variant="primary" onClick={createRevision} disabled={!canCreate}><FilePlus2 /> Create first brief</Button> : undefined}>
            A brief summarises facts, open items and unknowns with evidence. It is created as a new revision and never overwrites earlier ones.
          </EmptyState>
        </div>
      ) : (
        // Two columns (UX-4.1): the summary is the main reading area; review status and journal sit beside it.
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(300px,360px)] 2xl:grid-cols-[minmax(0,1fr)_400px]">
          <Summary brief={selected} latest={latest} onOpenLatest={() => latest && setBrief(latest.brief.id)} />
          <div className="space-y-5 lg:sticky lg:top-6">
            <ReviewStatus />
            <Journal brief={selected} />
          </div>
        </div>
      )}
      {selected && <p className="mt-4 text-[12.5px] text-ink-3">Brief recorded {formatDateTimeUtc(selected.brief.recorded_at)} · revisions are append-only.</p>}
    </div>
  );
}
