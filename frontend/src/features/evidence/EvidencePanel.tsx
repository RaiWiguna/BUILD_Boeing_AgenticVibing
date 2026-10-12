import { ArrowUpRight, ChevronDown, CircleCheck, CircleHelp, Copy, Info, Layers, Lock, MapPin, Pause, Play, RadioTower, VolumeX, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router';
import { toast } from 'sonner';
import type { EvidenceBundle, EvidenceItemView, FindingView } from '@/api/types';
import { useAuth } from '@/app/providers/AuthProvider';
import { useFindings, useWaveforms } from '@/features/workspace/queries';
import { CodeChip, StatusPill } from '@/components/domain/primitives';
import { Callout, DesktopOnly, ErrorState, LoadingRows } from '@/components/domain/states';
import { Quote } from '@/components/domain/evidence';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Tooltip } from '@/components/ui/tooltip';
import { useSessionScope } from '@/hooks/useSessionScope';
import { STATUS } from '@/lib/status';
import { formatClock, formatOffset } from '@/lib/time';
import { cn } from '@/lib/utils';
import { FindingReviewForm } from './FindingReviewForm';
import { useEvidenceBundle } from './queries';

const ROLE_META: Record<EvidenceItemView['role'], { name: string; letter: string; avatar: string; tone: 'data' | 'discrepancy' }> = {
  SAID: { name: 'Said', letter: 'S', avatar: 'bg-data text-white', tone: 'data' },
  HEARD: { name: 'Heard', letter: 'H', avatar: 'bg-[#d63384] text-white', tone: 'discrepancy' },
  OBSERVED: { name: 'Observed', letter: 'O', avatar: 'bg-ink text-white', tone: 'data' },
  EVENT: { name: 'Event', letter: 'E', avatar: 'bg-[#596273] text-white', tone: 'data' },
  POLICY: { name: 'Policy', letter: 'P', avatar: 'bg-[#596273] text-white', tone: 'data' },
};

function QuoteCard({ item, mismatch }: { item: EvidenceItemView; mismatch: boolean }) {
  const meta = ROLE_META[item.role];
  const quote = item.evidence.quote;
  return (
    <article className="flex min-w-0 flex-col rounded-[18px] border border-hairline-soft bg-surface p-4 shadow-control fit:p-3.5">
      <header className="flex items-center gap-2 text-[14px]">
        <span aria-hidden className={cn('inline-flex size-6 items-center justify-center rounded-full text-[12px] font-bold', meta.avatar)}>
          {meta.letter}
        </span>
        <span className="font-semibold text-ink">{meta.name}</span>
        <span className="truncate text-ink-2 tabular">
          · {item.label} · {item.evidence.start_ms != null ? formatClock(item.evidence.start_ms) : '—'}
        </span>
      </header>
      <div className="mt-3 flex-1 fit:mt-2">{quote ? <Quote text={quote} highlight={item.highlight} tone={mismatch && item.role === 'HEARD' ? 'discrepancy' : 'data'} className="text-[19px] leading-snug tracking-[-0.01em] fit:text-[17px]" /> : <p className="text-[14px] text-ink-2">No quote — {item.evidence.kind.toLowerCase()} evidence.</p>}</div>
      <footer className="mt-3 flex items-center justify-between gap-2 fit:mt-2">
        <span className="inline-flex h-7 fit:h-6 max-w-full items-center truncate rounded-[8px] bg-track px-2.5 text-[12.5px] font-medium text-ink-2">{item.speaker}</span>
        {quote && (
          <Tooltip content="Copy quote">
            <button
              type="button"
              aria-label={`Copy quote ${item.label}`}
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(`“${quote}” (${item.label})`);
                  toast.success(`Quote ${item.label} copied`);
                } catch {
                  toast.error('Clipboard is not available in this browser.');
                }
              }}
              className="inline-flex size-8 items-center justify-center rounded-[8px] text-ink-2 hover:bg-track hover:text-ink"
            >
              <Copy aria-hidden className="size-4" />
            </button>
          </Tooltip>
        )}
      </footer>
    </article>
  );
}

/** Visual-only range player (D-3): progress animates over the evidence range; no audio is loaded. */
function RangePlayer({ bundle }: { bundle: EvidenceBundle }) {
  const waves = useWaveforms();
  const range = bundle.range;
  const dur = range ? range.end_ms - range.start_ms : 0;
  const [pos, setPos] = useState(0);
  const [playing, setPlaying] = useState(false);
  const denied = bundle.audio_access === 'DENIED';

  useEffect(() => {
    if (!playing) return;
    let last = performance.now();
    const iv = setInterval(() => {
      const now = performance.now();
      setPos((p) => {
        const next = p + (now - last);
        if (next >= dur) {
          setPlaying(false);
          return dur;
        }
        return next;
      });
      last = now;
    }, 50);
    return () => clearInterval(iv);
  }, [playing, dur]);

  const bars = useMemo(() => {
    if (!range || !waves.data?.length) return [];
    const n = 64;
    const step = dur / n;
    return Array.from({ length: n }, (_, i) => {
      const t = range.start_ms + i * step;
      let v = 0;
      for (const w of waves.data!) v = Math.max(v, w.peaks[Math.floor(t / w.bucket_ms)] ?? 0);
      const owner = bundle.items.find((it) => it.evidence.start_ms != null && it.evidence.end_ms != null && t >= it.evidence.start_ms && t <= it.evidence.end_ms);
      return { v, role: owner?.role ?? null, t };
    });
  }, [range, waves.data, dur, bundle.items]);

  if (!range) return null;
  const progress = dur ? pos / dur : 0;
  return (
    <section aria-label="Evidence range" className="rounded-[18px] border border-hairline-soft bg-surface p-4 shadow-control">
      <div className="flex items-center justify-between gap-2 text-[14px]">
        <p className="font-semibold text-ink">
          Listen to range <span className="font-normal text-ink-2 tabular">· {formatClock(range.start_ms)}–{formatClock(range.end_ms)}</span>
        </p>
        <span className="text-[13px] text-ink-2 tabular">
          {formatOffset(pos, { tenths: false }).replace(/^0/, '')} / {formatOffset(dur, { tenths: false }).replace(/^0/, '')}
        </span>
      </div>
      <div className="mt-3 flex items-center gap-3.5">
        <button
          type="button"
          disabled={denied}
          onClick={() => {
            if (pos >= dur) setPos(0);
            setPlaying((p) => !p);
          }}
          aria-label={denied ? 'Audio playback not permitted' : playing ? 'Pause range' : 'Play range (visual only)'}
          className="inline-flex size-12 shrink-0 items-center justify-center rounded-full bg-data text-white shadow-[0_6px_16px_-6px_rgba(37,99,235,0.6)] transition-colors hover:bg-data-strong disabled:bg-track disabled:text-ink-3 disabled:shadow-none"
        >
          {denied ? <Lock aria-hidden className="size-5" /> : playing ? <Pause aria-hidden className="size-5 fill-current" /> : <Play aria-hidden className="ml-0.5 size-5 fill-current" />}
        </button>
        <svg aria-hidden viewBox={`0 0 ${bars.length * 6} 44`} preserveAspectRatio="none" className="h-11 min-w-0 flex-1">
          {bars.map((b, i) => {
            const h = b.v < 0.01 ? 3 : Math.max(5, b.v * 40);
            const played = i / bars.length <= progress;
            const color = b.role === 'HEARD' ? (played ? '#d63384' : '#efa3c6') : b.role === 'SAID' ? (played ? '#2563eb' : '#9db8ef') : played ? '#7d8899' : '#cfd5dd';
            return <rect key={i} x={i * 6 + 1.5} y={(44 - h) / 2} width={2.6} height={h} rx={1.3} fill={color} />;
          })}
        </svg>
      </div>
      <p className="mt-2.5 flex items-center gap-1.5 text-[12.5px] text-ink-2">
        {denied ? (
          <>
            <Lock aria-hidden className="size-3.5" /> Audio playback is not permitted for your role. Quotes remain readable.
          </>
        ) : (
          <>
            <VolumeX aria-hidden className="size-3.5" /> No audio for this session.
          </>
        )}
      </p>
    </section>
  );
}

function SlotTable({ bundle }: { bundle: EvidenceBundle }) {
  if (!bundle.slots.length) return null;
  const tone = { MATCHED: 'text-ink', MISMATCH: 'text-discrepancy font-semibold', MISSING: 'text-ink-3', AMBIGUOUS: 'text-notice' } as const;
  const pill = { MATCHED: STATUS.readback.MATCHED, MISMATCH: STATUS.readback.MISMATCH, MISSING: { label: 'Not stated', tone: 'muted', icon: CircleHelp } as const, AMBIGUOUS: STATUS.readback.AMBIGUOUS } as const;
  return (
    <div className="overflow-hidden rounded-[16px] border border-hairline-soft">
      <table className="w-full text-left text-[13.5px]">
        <caption className="sr-only">Critical slot comparison between what was said and what was heard</caption>
        <thead className="bg-sunken text-[12px] uppercase tracking-[0.05em] text-ink-3">
          <tr>
            <th scope="col" className="px-3.5 py-2 font-medium">
              Slot
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              Said
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              Heard
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              Compare
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-hairline-soft">
          {bundle.slots.map((s) => (
            <tr key={s.slot} className={s.status === 'MISMATCH' ? 'bg-discrepancy-tint/50' : undefined}>
              <th scope="row" className="px-3.5 py-2.5 font-medium capitalize text-ink-2">
                {s.slot.toLowerCase()}
              </th>
              <td className={cn('px-3 py-2.5', tone[s.status])}>{s.said ?? '—'}</td>
              <td className={cn('px-3 py-2.5', tone[s.status])}>{s.heard ?? '—'}</td>
              <td className="px-3 py-2.5 text-right">
                <StatusPill size="sm" meta={pill[s.status]} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Provenance({ bundle }: { bundle: EvidenceBundle }) {
  const [open, setOpen] = useState(false);
  const p = bundle.provenance;
  return (
    <div className="rounded-[16px] border border-hairline">
      <button type="button" aria-expanded={open} onClick={() => setOpen((v) => !v)} className="flex h-12 w-full items-center gap-3 px-4 text-left text-[15px] font-medium text-ink">
        <Layers aria-hidden className="size-[18px] text-ink-2" />
        <span className="flex-1">Alternatives & provenance</span>
        <ChevronDown aria-hidden className={cn('size-[18px] text-ink-2 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="space-y-4 border-t border-hairline-soft px-4 py-3.5 text-[13.5px]">
          <div>
            <p className="text-[12px] font-medium uppercase tracking-[0.05em] text-ink-3">Alternatives considered</p>
            <ul className="mt-1.5 list-disc space-y-1 pl-5 text-ink">
              {bundle.alternatives.length ? bundle.alternatives.map((a) => <li key={a}>{a}</li>) : <li>No alternatives recorded.</li>}
            </ul>
          </div>
          <dl className="grid grid-cols-[130px_1fr] gap-x-3 gap-y-1.5">
            <dt className="text-ink-2">Model</dt>
            <dd className="text-ink">{p.model_version}</dd>
            <dt className="text-ink-2">Prompt</dt>
            <dd className="text-ink">{p.prompt_version}</dd>
            <dt className="text-ink-2">Rules</dt>
            <dd className="text-ink">{p.rule_version}</dd>
            <dt className="text-ink-2">Input revision</dt>
            <dd className="text-ink">{p.input_revision}</dd>
            <dt className="text-ink-2">Source quality</dt>
            <dd>
              <StatusPill size="sm" meta={STATUS.quality[p.source_quality]} />
            </dd>
            {p.applicability && (
              <>
                <dt className="text-ink-2">Applicability</dt>
                <dd>
                  <CodeChip>{p.applicability}</CodeChip>
                </dd>
              </>
            )}
          </dl>
        </div>
      )}
    </div>
  );
}

function AssociationBar({ bundle }: { bundle: EvidenceBundle }) {
  if (!bundle.association) return null;
  const meta = STATUS.association[bundle.association.status];
  const tint = meta.tone === 'data' || meta.tone === 'ready' ? 'bg-data-tint' : meta.tone === 'notice' ? 'bg-notice-tint' : 'bg-sunken';
  return (
    <p className={cn('flex items-center gap-3 rounded-[14px] px-4 py-3 text-[14px]', tint)}>
      {meta.tone === 'notice' ? <CircleHelp aria-hidden className="size-[18px] shrink-0 text-notice" /> : <CircleCheck aria-hidden className="size-[18px] shrink-0 text-data" />}
      <span>
        <span className={cn('font-medium', meta.tone === 'notice' ? 'text-notice' : 'text-data-strong')}>Association {meta.label.toLowerCase()}</span>
        <span className="text-ink-2"> · {bundle.association.note}</span>
      </span>
    </p>
  );
}

/** Evidence panel (comp 06 right column). Used embedded on Findings and as a drawer elsewhere. */
export function EvidencePanel({ id, onClose, className, headingId = 'evidence-title', embedded = false, onNext, nextLabel }: { id: string; onClose?: () => void; className?: string; headingId?: string; embedded?: boolean; onNext?: () => void; nextLabel?: string | null }) {
  const { run, asOf, detail, sid, carry } = useSessionScope();
  const bundle = useEvidenceBundle(id);
  const findings = useFindings();
  const b = bundle.data;
  const finding: FindingView | undefined = findings.data?.find((f) => f.finding.id === id);
  const mismatch = !!b?.slots.some((s) => s.status === 'MISMATCH');
  const quoteItems = b?.items.filter((i) => i.role === 'SAID' || i.role === 'HEARD') ?? [];
  const otherItems = b?.items.filter((i) => i.role !== 'SAID' && i.role !== 'HEARD') ?? [];

  return (
    <div className={cn('flex min-h-0 flex-col', className)}>
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id={headingId} className="text-[24px] font-semibold tracking-[-0.03em] text-ink">
            Evidence · {b?.label ?? detail?.labels[id] ?? '…'}
          </h2>
          <p className="mt-0.5 text-[14px] text-ink-2 tabular">
            As of {formatOffset(b?.as_of_ms ?? asOf)} · Run {run?.label ?? '—'}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <CodeChip>{detail?.source_kind ?? 'SYNTHETIC'}</CodeChip>
          <span className="hidden h-6 items-center rounded-full bg-track px-2.5 text-[12px] font-medium text-ink-2 sm:inline-flex">Replay offline</span>
          {onClose && (
            <button type="button" onClick={onClose} aria-label="Close evidence" className="ml-1 inline-flex size-9 items-center justify-center rounded-full text-ink-2 hover:bg-track hover:text-ink">
              <X aria-hidden className="size-5" />
            </button>
          )}
        </div>
      </header>

      {bundle.isError && !b ? (
        <ErrorState compact className="mt-5" error={bundle.error} onRetry={() => bundle.refetch()} />
      ) : !b ? (
        <LoadingRows rows={5} className="mt-5" />
      ) : embedded ? (
        <>
          {/* Fit layout: evidence scrolls inside the card; the decision stays pinned below it, never over it. */}
          <ScrollArea className="mt-4 space-y-4 fit:-mx-1 fit:min-h-0 fit:flex-1 fit:px-1 fit:short:overflow-visible">
            {quoteItems.length > 0 && (
              <div className={cn('grid gap-3', quoteItems.length > 1 && 'sm:grid-cols-2')}>
                {quoteItems.map((it) => (
                  <QuoteCard key={it.evidence.id} item={it} mismatch={mismatch} />
                ))}
              </div>
            )}
            <RangePlayer bundle={b} />
            <details className="group rounded-[16px] border border-hairline-soft px-4 py-3 open:pb-4">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-[14.5px] font-semibold text-ink [&::-webkit-details-marker]:hidden">
                Evidence details
                <span className="text-[13px] font-normal text-ink-2">
                  Slots, provenance, events, track · <span className="group-open:hidden">Show</span>
                  <span className="hidden group-open:inline">Hide</span>
                </span>
              </summary>
              <EvidenceTabs bundle={b} finding={finding} otherItems={otherItems} className="mt-3" />
            </details>
            {!finding && b.label.startsWith('F-') && <NotAvailableNote />}
          </ScrollArea>
          {finding && <ReviewSlot finding={finding} onNext={onNext} nextLabel={nextLabel} className="mt-4 shrink-0 border-t border-hairline pt-4" />}
        </>
      ) : (
        <div className="mt-4 space-y-4">
          {quoteItems.length > 0 && (
            <div className={cn('grid gap-3', quoteItems.length > 1 && 'sm:grid-cols-2')}>
              {quoteItems.map((it) => (
                <QuoteCard key={it.evidence.id} item={it} mismatch={mismatch} />
              ))}
            </div>
          )}
          <RangePlayer bundle={b} />
          <EvidenceTabs bundle={b} finding={finding} otherItems={otherItems} note=" AI findings and source alerts are recorded separately." />
          {finding && <ReviewSlot finding={finding} className="border-t border-hairline pt-4" />}
          {!finding && b.label.startsWith('F-') && <NotAvailableNote />}
          {b.label.startsWith('F-') && (
            <Link to={`/s/${sid}/review/findings?finding=${id}${carry ? `&${carry}` : ''}`} className="inline-flex items-center gap-1.5 text-[14px] font-medium text-data underline-offset-4 hover:underline">
              Open in Findings <ArrowUpRight aria-hidden className="size-4" />
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

function NotAvailableNote() {
  return (
    <p className="flex items-center gap-2 text-[13px] text-ink-2">
      <Info aria-hidden className="size-4" /> This finding is not available at the current as-of; review it from Debrief.
    </p>
  );
}

/** Reviewer decision, or a read-only note for roles without review.write. */
function ReviewSlot({ finding, onNext, nextLabel, className }: { finding: FindingView; onNext?: () => void; nextLabel?: string | null; className?: string }) {
  const { can } = useAuth();
  return (
    <div className={className}>
      {can('review.write') ? (
        <DesktopOnly>
          <FindingReviewForm key={finding.finding.id} finding={finding} onNext={onNext} nextLabel={nextLabel} />
        </DesktopOnly>
      ) : (
        <Callout tone="muted" icon={Lock} title="Review is read-only for your role">
          {finding.reviews.length ? `${finding.reviews.length} review ${finding.reviews.length === 1 ? 'revision' : 'revisions'} recorded.` : 'No reviews recorded yet.'}
        </Callout>
      )}
    </div>
  );
}

function EvidenceTabs({ bundle: b, finding, otherItems, note = '', className }: { bundle: EvidenceBundle; finding?: FindingView; otherItems: EvidenceBundle['items']; note?: string; className?: string }) {
  return (
    <Tabs defaultValue="audio" className={className}>
      <TabsList>
        <TabsTrigger value="audio">Audio</TabsTrigger>
        <TabsTrigger value="event">Event</TabsTrigger>
        <TabsTrigger value="track">Track</TabsTrigger>
      </TabsList>
      <TabsContent value="audio" className="mt-4 space-y-3">
        <AssociationBar bundle={b} />
        <SlotTable bundle={b} />
        <Provenance bundle={b} />
      </TabsContent>
      <TabsContent value="event" className="mt-4 space-y-3">
        {finding && (
          <Callout tone={finding.source_alert.status === 'PRESENT' ? 'notice' : 'muted'} icon={RadioTower} title={finding.source_alert.status === 'PRESENT' ? `Source alert recorded${finding.source_alert.severity ? ` · ${finding.source_alert.severity}` : ''}` : 'Source alert not available'}>
            {finding.source_alert.note}
            {note}
          </Callout>
        )}
        {b.source_events.length === 0 && otherItems.length === 0 ? (
          <p className="rounded-[14px] bg-sunken px-4 py-3 text-[14px] text-ink-2">No source events are recorded for this range.</p>
        ) : (
          <ul className="space-y-2">
            {b.source_events.map((e) => (
              <li key={e.id} className="flex items-start gap-3 rounded-[14px] bg-sunken px-4 py-3 text-[14px]">
                <span className="w-12 shrink-0 text-ink-2 tabular">{formatClock(e.event_time_ms)}</span>
                <span className="flex-1 text-ink">{e.statement}</span>
                <StatusPill size="sm" meta={STATUS.quality[e.quality]} />
              </li>
            ))}
            {otherItems.map((it) => (
              <li key={it.evidence.id} className="flex items-start gap-3 rounded-[14px] bg-sunken px-4 py-3 text-[14px]">
                <span className="w-12 shrink-0 text-ink-2 tabular">{it.evidence.start_ms != null ? formatClock(it.evidence.start_ms) : '—'}</span>
                <span className="flex-1 text-ink">
                  {ROLE_META[it.role].name} · {it.label} — {it.speaker}
                </span>
              </li>
            ))}
          </ul>
        )}
      </TabsContent>
      <TabsContent value="track" className="mt-4">
        <Callout tone="muted" icon={MapPin} title={finding ? STATUS.movement[finding.movement].code! : 'Track'}>
          {b.track_note ?? 'No track note for this evidence.'}
        </Callout>
      </TabsContent>
    </Tabs>
  );
}
