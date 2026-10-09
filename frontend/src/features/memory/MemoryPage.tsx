import { AudioWaveform, Car, ChevronRight, Clock3, Eye, FileText, Layers, Link2, Pause, Play, Plane, VolumeX } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link, Navigate, NavLink, useParams } from 'react-router';
import type { EntityInfo, EntityMemoryView, HistoryItem, OpenLoop } from '@/api/types';
import { useReplay } from '@/features/replay/store';
import { useEntityMemory, useRunwayMemory, useSnapshot } from '@/features/workspace/queries';
import { LensSummary, ModeToggle, RunSelector, ScopeBanners } from '@/features/workspace/SessionHeader';
import { LayoutMini } from '@/components/domain/LayoutMini';
import { Card, CardHeader, CodeChip, MoreButton } from '@/components/domain/primitives';
import { EmptyState, ErrorState, LoadingRows } from '@/components/domain/states';
import { Quote } from '@/components/domain/evidence';
import { Breadcrumb, MetaSep } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from '@/components/ui/menu';
import { Tooltip } from '@/components/ui/tooltip';
import { useEvidence } from '@/hooks/useEvidence';
import { useSessionScope } from '@/hooks/useSessionScope';
import { LOOP_KIND_LABEL, STATUS, type Tone } from '@/lib/status';
import { clamp, formatClock, formatDate, formatDateTimeUtc, formatDuration, formatOffset } from '@/lib/time';
import { cn } from '@/lib/utils';
import { RunwayTab } from './RunwayTab';

export function useMemoryLinks() {
  const { sid, carry } = useSessionScope();
  return (path: string) => `/s/${sid}/${path}${carry ? `?${carry}` : ''}`;
}

/* ── Header ─────────────────────────────────────────────────────────── */
function MemoryHeader({ title, entity, onOpenEvidence }: { title: string; entity: EntityInfo | null; onOpenEvidence: (() => void) | null }) {
  const { detail, run } = useSessionScope();
  const link = useMemoryLinks();
  if (!detail) return null;
  return (
    <header className="mb-5">
      <Breadcrumb items={[{ label: 'Sessions', to: `/sessions?selected=${detail.id}` }, { label: detail.title, to: link('workspace') }, { label: 'Memory' }, ...(entity ? [{ label: entity.callsign }] : [])]} />
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <h1 className="text-[40px] font-medium leading-none tracking-[-0.045em] text-ink xl:text-[48px]">{title}</h1>
            <div className="flex items-center gap-2">
              <CodeChip>{detail.source_kind}</CodeChip>
              <CodeChip tone="neutral" className="bg-[#fff1e8] text-[#a2470f]">
                Mock
              </CodeChip>
            </div>
          </div>
          <p className="mt-2.5 flex flex-wrap items-center gap-x-2 text-[18px] text-ink-2 tabular">
            {run ? <RunSelector /> : 'No run'}
            <MetaSep />
            <LensSummary />
            {entity && (
              <>
                <MetaSep />
                {entity.type} · {entity.role}
              </>
            )}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <ModeToggle />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <MoreButton label="Memory options" className="size-11" />
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-[250px]">
              <DropdownMenuLabel>Objects</DropdownMenuLabel>
              {detail.entities.map((e) => (
                <DropdownMenuItem key={e.id} asChild>
                  <Link to={link(`memory/${e.id}`)}>
                    {e.kind === 'VEHICLE' ? <Car /> : <Plane />} {e.callsign}
                  </Link>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          {onOpenEvidence && (
            <Button variant="primary" size="lg" onClick={onOpenEvidence}>
              <FileText /> Open evidence
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}

function MemoryTabs({ entityId }: { entityId: string | null }) {
  const link = useMemoryLinks();
  const { detail } = useSessionScope();
  const cls = ({ isActive }: { isActive: boolean }) =>
    cn('relative -mb-px inline-flex h-11 items-center px-4 text-[16px] font-medium transition-colors after:absolute after:inset-x-2 after:-bottom-px after:h-[2px] after:rounded-full', isActive ? 'text-data after:bg-data' : 'text-ink-2 hover:text-ink after:bg-transparent');
  return (
    <nav aria-label="Memory views" className="mb-5 flex flex-wrap items-end justify-between gap-3 border-b border-hairline">
      <div className="flex">
        <NavLink to={link(`memory/${entityId ?? detail?.entities[0]?.id ?? ''}`)} end className={(p) => cls({ isActive: p.isActive && !!entityId })}>
          Object
        </NavLink>
        <NavLink to={link('memory/runway')} className={cls}>
          Runway
        </NavLink>
      </div>
      {entityId && (
        <div className="mb-2 flex flex-wrap gap-1.5" aria-label="Switch object">
          {detail?.entities.map((e) => (
            <Link key={e.id} to={link(`memory/${e.id}`)} aria-current={e.id === entityId ? 'page' : undefined} className={cn('inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-[13.5px] font-medium transition-colors', e.id === entityId ? 'bg-ink text-white' : 'bg-track text-ink-2 hover:text-ink')}>
              {e.kind === 'VEHICLE' ? <Car aria-hidden className="size-3.5" /> : <Plane aria-hidden className="size-3.5 -rotate-45" />}
              {e.callsign}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}

/* ── Active context rows ────────────────────────────────────────────── */
function ContextRow({ icon: Icon, tone, title, chip, chipTone, children, footer }: { icon: typeof FileText; tone: 'data' | 'discrepancy' | 'muted'; title: string; chip: string; chipTone: Tone; children: ReactNode; footer: ReactNode }) {
  const bg = { data: 'bg-data-tint/55', discrepancy: 'bg-discrepancy-tint/70', muted: 'bg-sunken' }[tone];
  const tile = { data: 'bg-data-soft/70 text-data', discrepancy: 'bg-discrepancy-soft/70 text-discrepancy', muted: 'bg-track text-ink' }[tone];
  return (
    <div className={cn('flex gap-4 rounded-[18px] p-4 sm:p-5', bg)}>
      <span aria-hidden className={cn('inline-flex size-12 shrink-0 items-center justify-center rounded-full', tile)}>
        <Icon className="size-[22px]" strokeWidth={1.9} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <h3 className="text-[15.5px] font-semibold text-ink">{title}</h3>
          <CodeChip tone={chipTone} className={chipTone === 'neutral' ? 'bg-surface/80' : undefined}>
            {chip}
          </CodeChip>
        </div>
        <div className="mt-1.5">{children}</div>
        <div className="mt-3 flex flex-wrap items-center gap-x-0 gap-y-1.5 text-[13.5px] text-ink-2 [&>*+*]:ml-3 [&>*+*]:border-l [&>*+*]:border-hairline-strong/60 [&>*+*]:pl-3">{footer}</div>
      </div>
    </div>
  );
}

function EvidenceLink({ id, label }: { id: string | null; label: string }) {
  const { open } = useEvidence();
  if (!id) return <span className="text-ink-3">{label}</span>;
  return (
    <button type="button" onClick={() => open(id)} className="inline-flex items-center gap-1.5 font-medium text-data hover:underline underline-offset-4">
      <Link2 aria-hidden className="size-4" /> {label}
    </button>
  );
}

function ActiveContext({ mem }: { mem: EntityMemoryView }) {
  const { detail, label, asOf } = useSessionScope();
  const { said, heard, observed, state } = mem;
  const rbTone = heard ? STATUS.readback[heard.readback].tone : 'muted';
  return (
    <Card aria-labelledby="active-context" className="p-5 sm:p-6">
      <CardHeader id="active-context" title="Active context" subtitle={`Object state at ${detail ? formatDate(detail.recorded_at) : ''}, ${formatOffset(asOf)}`} />
      <div className="mt-4 space-y-3">
        <ContextRow
          icon={FileText}
          tone="data"
          title="Said · Instruction"
          chip={said ? STATUS.instruction[said.lifecycle].code! : 'UNKNOWN'}
          chipTone={said ? STATUS.instruction[said.lifecycle].tone : 'muted'}
          footer={
            said ? (
              <>
                <EvidenceLink id={said.evidence_id} label={said.evidence_id ? label(said.evidence_id) : 'No evidence'} />
                <span>Interpretation: <span className="text-ink">{STATUS.interpretation[said.interpretation].label}</span></span>
                <span>Reviewer: <span className="text-ink">{STATUS.reviewer[said.reviewer].label}</span></span>
              </>
            ) : (
              <span>No instruction available at this as-of</span>
            )
          }
        >
          {said?.quote ? <Quote text={said.quote} highlight={said.highlight} className="text-[19px] leading-snug" /> : <p className="text-[15px] text-ink-2">No instruction is known for this object yet.</p>}
        </ContextRow>

        <ContextRow
          icon={AudioWaveform}
          tone={rbTone === 'discrepancy' ? 'discrepancy' : rbTone === 'muted' ? 'muted' : 'data'}
          title={`Heard · ${heard?.speaker.startsWith('Candidate') ? 'Candidate readback' : 'Readback'}`}
          chip={heard ? STATUS.readback[heard.readback].code! : 'NOT_OBSERVED'}
          chipTone={heard ? (STATUS.readback[heard.readback].tone === 'ready' ? 'data' : STATUS.readback[heard.readback].tone) : 'neutral'}
          footer={
            heard ? (
              <>
                <EvidenceLink id={heard.evidence_id} label={heard.evidence_id ? label(heard.evidence_id) : 'No evidence'} />
                <span>Interpretation: <span className="text-ink">{STATUS.interpretation[heard.interpretation].label}</span></span>
                <span>Reviewer: <span className="text-ink">{STATUS.reviewer[heard.reviewer].label}</span></span>
              </>
            ) : (
              <span>No readback observed in the stored coverage</span>
            )
          }
        >
          {heard?.quote ? <Quote text={heard.quote} highlight={heard.highlight} tone={heard.readback === 'MISMATCH' ? 'discrepancy' : 'data'} className="text-[19px] leading-snug" /> : <p className="text-[15px] text-ink-2">Not observed. A missing readback is not treated as confirmation.</p>}
        </ContextRow>

        <ContextRow
          icon={Eye}
          tone="muted"
          title="Observed · Movement"
          chip={STATUS.movement[observed.movement].code!}
          chipTone={observed.movement === 'DIVERGENCE_CANDIDATE' ? 'discrepancy' : observed.movement === 'CONSISTENT' ? 'data' : 'neutral'}
          footer={
            <>
              <span className="inline-flex items-center gap-1.5 font-medium text-data">
                <Link2 aria-hidden className="size-4" />
                {state.track_status === 'MISSING' ? 'Track not available' : state.track_status === 'POINT_ONLY' ? 'Centre point only' : state.track_status === 'STALE' ? 'Track stale' : 'Track with footprint'}
              </span>
              <span>Interpretation: <span className="text-ink">{STATUS.interpretation[observed.interpretation].label}</span></span>
              <span>Reviewer: <span className="text-ink">{STATUS.reviewer[observed.reviewer].label}</span></span>
            </>
          }
        >
          <p className="text-[16px] leading-relaxed text-ink-2">{observed.statement}</p>
        </ContextRow>
      </div>
    </Card>
  );
}

/* ── Context history ────────────────────────────────────────────────── */
const HISTORY_DOT: Record<HistoryItem['tone'], string> = { data: 'bg-data', discrepancy: 'bg-[#d63384]', muted: 'bg-[#9aa3b2]', notice: 'bg-[#e0a21a]', ready: 'bg-[#22a35f]' };

function ContextHistory({ mem }: { mem: EntityMemoryView }) {
  const { detail, label, asOf, mode } = useSessionScope();
  const { open } = useEvidence();
  return (
    <Card aria-labelledby="context-history" className="p-5 sm:p-6">
      <CardHeader id="context-history" title="Context history" subtitle={`Changes to this object up to ${detail ? formatDate(detail.recorded_at) : ''}, ${formatOffset(asOf)}`} />
      {mem.history.length === 0 ? (
        <EmptyState className="py-8" title="No context yet">
          Nothing is known about this object at this as-of.
        </EmptyState>
      ) : (
        <ol className="relative mt-4">
          <span aria-hidden className="absolute bottom-6 left-[7px] top-3 w-px bg-hairline" />
          {mem.history.map((h, i) => (
            <li key={h.id} className={cn('relative grid grid-cols-[16px_56px_minmax(0,1fr)_auto] items-start gap-x-3 py-3', i > 0 && 'border-t border-hairline-soft [&]:ml-0')}>
              <span aria-hidden className={cn('relative z-10 mt-1.5 size-[13px] rounded-full ring-[3px] ring-surface', HISTORY_DOT[h.tone])} />
              <span className="pt-px text-[15px] text-ink-2 tabular">{formatClock(h.t)}</span>
              <div className="min-w-0">
                <p className="text-[15.5px] font-medium text-ink">
                  {h.title}
                  {h.debrief_only && mode === 'DEBRIEF' && <span className="ml-2 align-middle text-[12px] font-medium text-ink-3">available {h.available_ms != null ? formatClock(h.available_ms) : 'later'}</span>}
                </p>
                <p className="mt-0.5 text-[14px] text-ink-2">{h.detail}</p>
              </div>
              <div className="pt-0.5">
                {h.evidence_id && label(h.evidence_id).startsWith('E-') ? (
                  <button type="button" onClick={() => open(h.evidence_id!)} className="inline-flex items-center gap-1.5 rounded-[8px] px-1.5 py-0.5 text-[14px] font-medium text-data hover:bg-data-tint" aria-label={`Open evidence ${label(h.evidence_id)}`}>
                    <Link2 aria-hidden className="size-4" /> {label(h.evidence_id)}
                  </button>
                ) : h.evidence_id ? (
                  <Tooltip content={`Open ${label(h.evidence_id)} evidence`}>
                    <button type="button" onClick={() => open(h.evidence_id!)} className="inline-flex size-8 items-center justify-center rounded-[8px] text-ink-2 hover:bg-track hover:text-ink" aria-label={`Open ${label(h.evidence_id)} evidence`}>
                      <FileText aria-hidden className="size-[18px]" />
                    </button>
                  </Tooltip>
                ) : (
                  <span className="inline-flex w-8 justify-center text-ink-3" aria-label="No evidence">
                    —
                  </span>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
      <p className="mt-2 text-[13px] text-ink-3">{mode === 'AS_KNOWN' ? `Changes after as-of are not shown${mem.hidden_after_as_of ? ` (${mem.hidden_after_as_of} later)` : ''}.` : 'Debrief view — includes information that became available later.'}</p>
    </Card>
  );
}

/* ── Right column ───────────────────────────────────────────────────── */
function RunwayCard() {
  const { detail } = useSessionScope();
  const link = useMemoryLinks();
  const runway = detail?.layout?.runways[0];
  const rw = useRunwayMemory(runway?.id ?? null);
  if (!detail) return null;
  const coverage = rw.data?.coverage;
  return (
    <Card aria-labelledby="runway-card" className="p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 id="runway-card" className="text-section font-semibold text-ink">
          {runway ? `Runway ${runway.ends[1]}` : 'Runway'}
        </h2>
        {coverage && coverage !== 'COMPLETE' && (
          <span className="inline-flex h-8 items-center gap-1.5 rounded-full bg-notice-tint px-3 text-[13.5px] font-medium text-notice">
            <Clock3 aria-hidden className="size-3.5" /> {coverage === 'AUDIO_ONLY' ? 'Audio-only coverage' : 'Partial coverage'}
          </span>
        )}
      </div>
      {detail.layout ? (
        <Link to={link('memory/runway')} className="mt-3 block overflow-hidden rounded-[16px] ring-1 ring-hairline-soft transition-shadow hover:shadow-pop" aria-label="Open runway memory">
          <LayoutMini layout={detail.layout} className="h-[132px]" />
        </Link>
      ) : (
        <div className="mt-3 flex h-[120px] items-center justify-center rounded-[16px] bg-sunken text-[14px] text-ink-2">No layout imported</div>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {rw.data?.objects.map((o) => (
          <Link key={o.entity.id} to={link(`memory/${o.entity.id}`)} className="inline-flex h-7 items-center rounded-[8px] border border-data/25 bg-surface px-2 text-[12.5px] font-semibold text-data-strong hover:bg-data-tint">
            {o.entity.callsign}
          </Link>
        ))}
      </div>
      <p className="mt-2 text-[12.5px] text-ink-3">Runway context illustration · not actual positions</p>
    </Card>
  );
}

function StillOpen({ loops, entities }: { loops: OpenLoop[]; entities: EntityInfo[] }) {
  const { open } = useEvidence();
  const { asOf } = useSessionScope();
  return (
    <Card aria-labelledby="still-open" className="p-5">
      <CardHeader id="still-open" title="Still open" subtitle="Items to verify for this object" />
      {loops.length === 0 ? (
        <p className="mt-4 rounded-[14px] bg-sunken px-4 py-3 text-[14px] text-ink-2">No open loops for this object at this as-of.</p>
      ) : (
        <ul className="mt-3 divide-y divide-hairline-soft">
          {loops.map((l) => {
            const ent = l.entity_ids.map((id) => entities.find((e) => e.id === id)?.callsign).filter(Boolean).join(', ');
            const elapsed = Math.max(0, asOf - l.started_ms);
            const overdue = l.expected_window_ms != null && elapsed > l.expected_window_ms;
            const isReadback = l.kind === 'READBACK_EXPECTED';
            return (
              <li key={l.id}>
                <button type="button" onClick={() => l.evidence[0] && open(l.evidence[0].id)} className="group flex w-full items-center gap-3.5 py-3 text-left">
                  <span aria-hidden className={cn('inline-flex size-11 shrink-0 items-center justify-center rounded-full', isReadback ? 'bg-discrepancy-tint text-discrepancy' : 'bg-notice-tint text-notice')}>
                    <Clock3 className="size-5" strokeWidth={1.9} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[15px] font-medium text-ink">{isReadback ? 'Matching readback' : `${LOOP_KIND_LABEL[l.kind] ?? l.kind} · ${ent}`}</span>
                    <span className="block text-[13.5px] text-ink-2">
                      {isReadback ? `Readback confirming the instruction from ${formatClock(l.started_ms)}.` : `Awaiting since ${formatClock(l.started_ms)}.`}
                      {overdue && <span className="text-notice"> Window passed.</span>}
                    </span>
                  </span>
                  <span className="hidden shrink-0 text-[12.5px] text-ink-3 sm:block">{l.timer_profile_version}</span>
                  <ChevronRight aria-hidden className="size-[18px] shrink-0 text-ink-2 transition-transform group-hover:translate-x-0.5" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

function Provenance({ mem }: { mem: EntityMemoryView }) {
  const { label, run } = useSessionScope();
  const { open } = useEvidence();
  const link = useMemoryLinks();
  const ev = mem.provenance.evidence_ids;
  const rows: { icon: typeof FileText; title: string; detail: string; to?: string; onClick?: () => void }[] = [
    { icon: FileText, title: `Input revision ${mem.provenance.input_revision}`, detail: `Updated ${formatDateTimeUtc(mem.provenance.updated_at)}`, to: link('review/transcript') },
    { icon: Layers, title: `Reducer ${mem.provenance.reducer_version.replace('reducer-', '')}`, detail: `Context processing and time alignment · rules ${mem.provenance.rule_version}${run ? ` · run ${run.label}` : ''}`, to: '/help#provenance' },
    { icon: Link2, title: `Evidence · ${ev.length} ${ev.length === 1 ? 'item' : 'items'}`, detail: ev.length ? ev.map(label).join(', ') : 'None at this as-of', onClick: ev.length ? () => open(ev[ev.length - 1]!) : undefined },
  ];
  return (
    <Card aria-labelledby="provenance" className="p-5">
      <CardHeader id="provenance" title="Provenance" subtitle="Source and versions behind this object" />
      <ul className="mt-2 divide-y divide-hairline-soft">
        {rows.map((r) => {
          const inner = (
            <>
              <span aria-hidden className="inline-flex size-10 shrink-0 items-center justify-center rounded-full text-ink">
                <r.icon className="size-5" strokeWidth={1.8} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[15px] font-medium text-ink">{r.title}</span>
                <span className="block truncate text-[13.5px] text-ink-2">{r.detail}</span>
              </span>
              <ChevronRight aria-hidden className="size-[18px] shrink-0 text-ink-2" />
            </>
          );
          return (
            <li key={r.title}>
              {r.to ? (
                <Link to={r.to} className="flex items-center gap-3 py-2.5 hover:[&_span.block:first-child]:text-data">
                  {inner}
                </Link>
              ) : (
                <button type="button" disabled={!r.onClick} onClick={r.onClick} className="flex w-full items-center gap-3 py-2.5 text-left">
                  {inner}
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

/** Compact replay control for memory pages (shares the session replay clock). */
export function MiniPlayer({ className }: { className?: string }) {
  const cursor = useReplay((s) => s.cursor);
  const duration = useReplay((s) => s.duration);
  const status = useReplay((s) => s.status);
  const toggle = useReplay((s) => s.toggle);
  const seek = useReplay((s) => s.seek);
  const pct = duration ? (cursor / duration) * 100 : 0;
  return (
    <Card className={cn('flex items-center gap-3 px-4 py-3', className)} aria-label="Replay">
      <button type="button" onClick={toggle} aria-label={status === 'PLAYING' ? 'Pause replay' : 'Play replay'} className="inline-flex size-11 shrink-0 items-center justify-center rounded-full bg-data-tint text-data transition-colors hover:bg-data-soft">
        {status === 'PLAYING' ? <Pause aria-hidden className="size-[18px] fill-current" /> : <Play aria-hidden className="ml-0.5 size-[18px] fill-current" />}
      </button>
      <div className="min-w-0 flex-1">
        <input
          type="range"
          min={0}
          max={duration}
          step={100}
          value={Math.round(cursor)}
          onChange={(e) => seek(Number(e.target.value))}
          aria-label="Replay position"
          aria-valuetext={formatOffset(cursor)}
          className="h-5 w-full cursor-pointer appearance-none bg-transparent [&::-webkit-slider-runnable-track]:h-[5px] [&::-webkit-slider-runnable-track]:rounded-full [&::-webkit-slider-runnable-track]:bg-[linear-gradient(to_right,#2563eb_var(--p),#e4e8ee_var(--p))] [&::-webkit-slider-thumb]:-mt-[6px] [&::-webkit-slider-thumb]:size-[17px] [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-[3px] [&::-webkit-slider-thumb]:border-data [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:shadow-pop"
          style={{ ['--p' as string]: `${clamp(pct, 0, 100)}%` }}
        />
        <p className="text-right text-[12.5px] text-ink-2 tabular">
          <span className="font-semibold text-ink">{formatOffset(cursor)}</span> / {formatDuration(duration)}
        </p>
      </div>
      <Tooltip content="Visual replay only — audio is not loaded in MOCK mode">
        <span tabIndex={0} className="inline-flex size-9 items-center justify-center rounded-full text-ink-3">
          <VolumeX aria-hidden className="size-[18px]" />
          <span className="sr-only">Audio not loaded</span>
        </span>
      </Tooltip>
      <span className="hidden h-8 shrink-0 items-center rounded-full bg-track px-3 text-[12.5px] font-medium text-ink-2 sm:inline-flex">Replay offline</span>
    </Card>
  );
}

/* ── Pages ──────────────────────────────────────────────────────────── */
export function MemoryObjectPage() {
  const { entityId = '' } = useParams();
  const { detail } = useSessionScope();
  const mem = useEntityMemory(entityId);
  const snapshot = useSnapshot();
  const { open } = useEvidence();
  const entity = detail?.entities.find((e) => e.id === entityId) ?? null;
  if (!detail) return null;
  if (!entity) return <Navigate to={`../memory/${detail.entities[0]?.id ?? ''}`} replace />;
  const evidence = mem.data?.heard?.evidence_id ?? mem.data?.said?.evidence_id ?? null;
  const loops = (snapshot.data?.open_loops ?? []).filter((l) => l.entity_ids.includes(entity.id) && (l.status === 'OPEN' || l.status === 'PARTIAL'));

  return (
    <div>
      <MemoryHeader title={entity.callsign} entity={entity} onOpenEvidence={evidence ? () => open(evidence) : null} />
      <MemoryTabs entityId={entity.id} />
      <ScopeBanners />
      {mem.isError && !mem.data ? (
        <Card className="p-6">
          <ErrorState error={mem.error} onRetry={() => mem.refetch()} />
        </Card>
      ) : !mem.data ? (
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,1fr)]">
          <Card className="p-6">
            <LoadingRows rows={4} />
          </Card>
          <Card className="p-6">
            <LoadingRows rows={4} />
          </Card>
        </div>
      ) : (
        <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,1fr)]">
          <div className="space-y-5">
            <ActiveContext mem={mem.data} />
            <ContextHistory mem={mem.data} />
          </div>
          <div className="space-y-5 xl:sticky xl:top-6">
            <RunwayCard />
            <StillOpen loops={loops} entities={detail.entities} />
            <Provenance mem={mem.data} />
            <MiniPlayer />
          </div>
        </div>
      )}
    </div>
  );
}

export function MemoryRunwayPage() {
  const { detail } = useSessionScope();
  if (!detail) return null;
  const runway = detail.layout?.runways[0];
  return (
    <div>
      <MemoryHeader title={runway ? `Runway ${runway.ends[1]}` : 'Runway'} entity={null} onOpenEvidence={null} />
      <MemoryTabs entityId={null} />
      <ScopeBanners />
      <RunwayTab />
    </div>
  );
}

export function MemoryIndex() {
  const { detail, carry } = useSessionScope();
  if (!detail) return null;
  const first = detail.entities[0];
  return <Navigate to={first ? `${first.id}${carry ? `?${carry}` : ''}` : `runway${carry ? `?${carry}` : ''}`} replace />;
}
