import { ChevronLeft, ChevronRight, CircleHelp, Filter, Flag, Loader2, MoreHorizontal, Pause, Play, RefreshCw, Search, Sparkles, Volume2, VolumeX, WifiOff } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { toast } from 'sonner';
import { hasCode, isApiError } from '@/api/errors';
import type { TranscriptRow, WaveformView } from '@/api/types';
import { useAuth } from '@/app/providers/AuthProvider';
import { useAudio } from '@/features/replay/audio';
import { useReplay } from '@/features/replay/store';
import { useFindings, useWaveforms } from '@/features/workspace/queries';
import { MoreButton, StatusPill } from '@/components/domain/primitives';
import { Callout, DesktopOnly, EmptyState, ErrorState, LoadingRows } from '@/components/domain/states';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioRow, Select } from '@/components/ui/controls';
import { Input, Label, Textarea } from '@/components/ui/input';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/menu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Tooltip } from '@/components/ui/tooltip';
import { DraftGuard } from '@/hooks/useDraftGuard';
import { useEvidence } from '@/hooks/useEvidence';
import { useConnected } from '@/hooks/useSessionStream';
import { useSessionScope } from '@/hooks/useSessionScope';
import { STATUS } from '@/lib/status';
import { formatClock, formatDateTimeUtc, formatOffset } from '@/lib/time';
import { cn } from '@/lib/utils';
import { useCorrectTranscript, useReanalyze, useReviewAssociation, useTranscript } from './queries';

const CHANNEL_PILL = ['bg-data-tint text-data-strong', 'bg-discrepancy-tint text-discrepancy', 'bg-notice-tint text-notice', 'bg-track text-ink-2'];

function AssociationCell({ row }: { row: TranscriptRow }) {
  const act = row.intent?.speech_act ?? 'UNKNOWN';
  const ambiguous = row.association?.status === 'AMBIGUOUS';
  const reviewed = row.association?.status === 'CONFIRMED_BY_REVIEW' || row.association?.status === 'REJECTED';
  if (ambiguous)
    return (
      <span className="inline-flex items-center gap-2">
        <span aria-hidden className="size-2 rounded-full bg-[#e0a21a]" />
        <span className="inline-flex h-7 items-center rounded-[8px] bg-notice-tint px-2.5 text-[12px] font-semibold tracking-[0.03em] text-notice">AMBIGUOUS</span>
      </span>
    );
  const meta = STATUS.speechAct[act];
  const dot = act === 'CORRECTION' ? 'bg-[#d63384]' : act === 'UNKNOWN' ? 'bg-[#a3aab5]' : 'bg-[#22a35f]';
  return (
    <span className="inline-flex items-center gap-2">
      <span aria-hidden className={cn('size-2 rounded-full', dot)} />
      <span className="inline-flex h-7 items-center rounded-[8px] bg-track px-2.5 text-[13px] font-medium text-ink">{meta.label}</span>
      {reviewed && <span className="text-[12px] text-ready">reviewed</span>}
    </span>
  );
}

function SegmentWave({ row, waves }: { row: TranscriptRow; waves: WaveformView[] | undefined }) {
  const start = row.segment.start_ms ?? 0;
  const end = row.segment.end_ms ?? start + 3000;
  const pad = Math.max(8000, (30_000 - (end - start)) / 2);
  const from = Math.max(0, start - pad);
  const to = end + pad;
  const total = to - from;
  const [localPos, setPos] = useState(0);
  const [localPlaying, setPlaying] = useState(false);
  // DEMO workspaces (ADR 0003): play the real recording through the replay clock.
  const audio = useAudio((s) => s.available);
  const cursor = useReplay((s) => Math.floor(s.cursor / 50) * 50);
  const replayPlaying = useReplay((s) => s.status === 'PLAYING');
  const pos = audio ? Math.min(total, Math.max(0, cursor - from)) : localPos;
  const playing = audio ? replayPlaying && cursor >= from && cursor <= to : localPlaying;
  useEffect(() => {
    if (audio || !localPlaying) return;
    let last = performance.now();
    const iv = setInterval(() => {
      const now = performance.now();
      setPos((p) => {
        const n = p + (now - last);
        if (n >= total) {
          setPlaying(false);
          return total;
        }
        return n;
      });
      last = now;
    }, 50);
    return () => clearInterval(iv);
  }, [audio, localPlaying, total]);
  const n = 120;
  const lanes = (waves ?? []).map((w) => ({
    label: w.label,
    bars: Array.from({ length: n }, (_, i) => w.peaks[Math.floor((from + (i / n) * total) / w.bucket_ms)] ?? 0),
  }));
  const selL = ((start - from) / total) * 100;
  const selW = ((end - start) / total) * 100;
  return (
    <section aria-labelledby="audio-evidence" className="card p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 id="audio-evidence" className="text-[19px] font-semibold tracking-[-0.02em] text-ink">
          Audio & evidence
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-[15px] text-ink tabular">
            {formatClock(start)} – {formatClock(end)}
          </span>
          <Tooltip content={audio ? 'Play recording' : 'No audio for this session'}>
            <span tabIndex={0} className="inline-flex size-9 items-center justify-center rounded-full border border-hairline text-ink-2">
              {audio ? <Volume2 aria-hidden className="size-4" /> : <VolumeX aria-hidden className="size-4" />}
              <span className="sr-only">{audio ? 'Audio available' : 'Audio not loaded'}</span>
            </span>
          </Tooltip>
        </div>
      </div>
      <div className="relative mt-3 grid grid-cols-[64px_minmax(0,1fr)] items-center gap-x-3 gap-y-1.5">
        {lanes.map((l, li) => (
          <div key={l.label} className="contents">
            <span className="text-[14px] text-ink-2">{l.label}</span>
            <svg aria-hidden viewBox={`0 0 ${n * 5} 40`} preserveAspectRatio="none" className={cn('h-10 w-full rounded-[6px]', li === 1 ? 'bg-discrepancy-tint/30' : 'bg-sunken/60')}>
              {l.bars.map((v, i) => {
                const h = v < 0.01 ? 2 : Math.max(4, v * 36);
                const played = i / n <= pos / total;
                const color = li === 0 ? (played ? '#2563eb' : '#9db8ef') : played ? '#d63384' : '#efa3c6';
                return <rect key={i} x={i * 5 + 1} y={(40 - h) / 2} width={2.2} height={h} rx={1.1} fill={color} />;
              })}
            </svg>
          </div>
        ))}
        <div aria-hidden className="pointer-events-none absolute inset-y-[-4px] right-0 left-[76px]">
          <div className="absolute inset-y-0 rounded-[6px] border-x-2 border-data bg-data/10" style={{ left: `${selL}%`, width: `${selW}%` }}>
            <span className="absolute -left-[5px] -top-1 size-2 rounded-full bg-data" />
            <span className="absolute -right-[5px] -top-1 size-2 rounded-full bg-data" />
          </div>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <button
          type="button"
          onClick={() => {
            if (audio) {
              const r = useReplay.getState();
              if (playing) r.pause();
              else r.playRange({ start, end });
              return;
            }
            if (pos >= total) setPos(0);
            setPlaying((p) => !p);
          }}
          aria-label={playing ? 'Pause segment' : audio ? 'Play segment' : 'Play segment (visual only)'}
          className="inline-flex size-11 items-center justify-center rounded-full bg-data text-white shadow-[0_6px_16px_-6px_rgba(37,99,235,0.6)] hover:bg-data-strong"
        >
          {playing ? <Pause aria-hidden className="size-[18px] fill-current" /> : <Play aria-hidden className="ml-0.5 size-[18px] fill-current" />}
        </button>
        <span className="w-[92px] text-[13px] text-ink-2 tabular">
          {formatClock(pos)} / {formatClock(total)}
        </span>
        <input type="range" min={0} max={total} step={100} value={Math.round(pos)} onChange={(e) => (audio ? useReplay.getState().seek(from + Number(e.target.value)) : setPos(Number(e.target.value)))} aria-label="Segment position" className="h-1.5 flex-1 cursor-pointer accent-[#2563eb]" />
        <span className="inline-flex h-8 items-center rounded-[10px] border border-hairline px-2.5 text-[13px] font-medium text-ink">1×</span>
      </div>
    </section>
  );
}

function SegmentPanel({ row, rows, onNavigate, stale }: { row: TranscriptRow; rows: TranscriptRow[]; onNavigate: (id: string) => void; stale: boolean }) {
  const { can } = useAuth();
  const { open } = useEvidence();
  const { archived, run, latestRunId, setRun, detail, href } = useSessionScope();
  const findings = useFindings();
  // Findings whose evidence cites this segment (cross-link to Review › Findings).
  const related = (findings.data ?? []).filter((f) => f.finding.evidence.some((e) => detail?.labels[e.id] === row.evidence_label));
  const connected = useConnected();
  const idx = rows.findIndex((r) => r.original.id === row.original.id);
  const writable = can('review.write') && !archived;
  const [target, setTarget] = useState<string>('');
  const [pairReason, setPairReason] = useState('');
  const [text, setText] = useState(row.segment.text);
  const [reason, setReason] = useState('');
  const [touched, setTouched] = useState(false);
  // Revisions get new ids; the original STT segment id is the stable identity for writes.
  const pairing = useReviewAssociation(row.original.id);
  const correction = useCorrectTranscript(row.original.id);
  const reanalyze = useReanalyze();
  const conflict = correction.error && hasCode(correction.error, 'VERSION_CONFLICT');
  const textChanged = text.trim() !== row.segment.text.trim();
  const ambiguous = row.association?.status === 'AMBIGUOUS';

  const savePairing = () => {
    if (!target || !pairReason.trim()) return;
    pairing.mutate(
      { targetId: target === 'UNDETERMINED' ? null : target, reason: pairReason.trim() },
      {
        onSuccess: () => {
          toast.success(`Pairing review saved for ${row.label}`, { description: 'Append-only · transcript text unchanged' });
          setTarget('');
          setPairReason('');
        },
      },
    );
  };
  const saveRevision = () => {
    setTouched(true);
    if (!textChanged || !reason.trim()) return;
    correction.mutate(
      { text: text.trim(), reason: reason.trim(), expectedVersion: row.segment.revision },
      {
        onSuccess: () => {
          toast.success(`Revision saved for ${row.label}`, { description: 'Original STT kept. Dependent results are now stale.' });
          setReason('');
          setTouched(false);
        },
      },
    );
  };

  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-[26px] font-semibold tracking-[-0.03em] text-ink">Segment {row.label}</h2>
        <div className="flex gap-1.5">
          <button type="button" disabled={idx <= 0} onClick={() => onNavigate(rows[idx - 1]!.original.id)} aria-label="Previous segment" className="inline-flex size-10 items-center justify-center rounded-full border border-hairline bg-surface text-ink hover:bg-sunken disabled:opacity-40">
            <ChevronLeft aria-hidden className="size-[18px]" />
          </button>
          <button type="button" disabled={idx >= rows.length - 1} onClick={() => onNavigate(rows[idx + 1]!.original.id)} aria-label="Next segment" className="inline-flex size-10 items-center justify-center rounded-full border border-hairline bg-surface text-ink hover:bg-sunken disabled:opacity-40">
            <ChevronRight aria-hidden className="size-[18px]" />
          </button>
        </div>
      </div>
      <DraftGuard dirty={textChanged || !!reason.trim() || !!target || !!pairReason.trim()} what="transcript edit" />
      <p className="mt-1 text-[13.5px] text-ink-2 tabular">
        {formatOffset(row.segment.start_ms ?? 0)} · {detail?.channels[row.segment.channel]?.label ?? `Channel ${row.segment.channel}`} · {row.evidence_label} · revision {row.segment.revision}
      </p>

      {stale && (
        <Callout
          className="mt-4"
          tone="notice"
          icon={RefreshCw}
          title="Derived results are stale"
          action={
            can('analysis.create') && (
              <Button
                size="sm"
                variant="secondary"
                disabled={reanalyze.isPending || !connected}
                onClick={() =>
                  reanalyze.mutate(undefined, {
                    onSuccess: (r) => toast.success(`Run ${r.label} queued`, { description: 'You stay on the current run until you open the new one.', action: { label: `Open ${r.label}`, onClick: () => setRun(r.run.id) } }),
                    onError: (e) => toast.error(isApiError(e) ? e.message : 'Re-analysis failed.'),
                  })
                }
              >
                {reanalyze.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw />} Re-analyse as new run
              </Button>
            )
          }
        >
          A transcript revision changed inputs used by findings and memory in Run {run?.label}. They stay readable but marked stale; nothing is recomputed silently.
          {latestRunId && latestRunId !== run?.run.id && ' A newer run exists.'}
        </Callout>
      )}

      {related.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-[13px] text-ink-2">Cited by</span>
          {related.map((f) => (
            <Link key={f.finding.id} to={href('review/findings', { finding: f.finding.id })} className="inline-flex h-8 items-center gap-1.5 rounded-full bg-data-tint px-3 text-[13px] font-medium text-data-strong hover:bg-data-soft">
              <Flag aria-hidden className="size-3.5" /> {f.label} · {f.title}
            </Link>
          ))}
        </div>
      )}

      <div className="mt-5">
        <p className="flex items-center gap-1.5 text-[15px] font-semibold text-ink">
          Original STT hypothesis
          <Tooltip content="Raw speech-to-text output. It is never edited; corrections are stored as new revisions.">
            <CircleHelp tabIndex={0} aria-label="About the original hypothesis" className="size-4 text-ink-3" />
          </Tooltip>
        </p>
        <blockquote className="mt-2 rounded-[14px] bg-sunken px-4 py-3 text-[15.5px] leading-relaxed text-ink">“{row.original.text}”</blockquote>
        <p className="mt-1.5 text-[12.5px] text-ink-3">
          {row.original.origin} · {row.original.provider_profile_version} · {STATUS.quality[row.original.quality].label}
        </p>
      </div>

      <Tabs defaultValue={ambiguous ? 'pairing' : 'correction'} className="mt-6">
        <TabsList>
          <TabsTrigger value="correction">Correction{row.revisions.length > 0 && <span className="ml-1.5 tabular text-ink-3">{row.revisions.length}</span>}</TabsTrigger>
          <TabsTrigger value="pairing">Pairing{ambiguous && <span aria-label="ambiguous" className="ml-1.5 inline-block size-1.5 rounded-full bg-notice" />}</TabsTrigger>
        </TabsList>
        <TabsContent value="correction" className="mt-4">

          <DesktopOnly what="Correcting the transcript">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              saveRevision();
            }}
          >
            <Label htmlFor="correction" className="text-[15px] font-semibold">
              Transcript correction
            </Label>
            <Textarea id="correction" value={text} onChange={(e) => setText(e.target.value)} disabled={!writable || !connected} className="mt-2 min-h-[84px] text-[15px]" />
            <Label htmlFor="correction-reason" className="mt-4 block text-[15px] font-semibold">
              Correction reason
            </Label>
            <Input id="correction-reason" value={reason} onChange={(e) => setReason(e.target.value)} onBlur={() => setTouched(true)} disabled={!writable || !connected} placeholder="Fill in after listening to the original audio" aria-invalid={touched && textChanged && !reason.trim()} className="mt-2" />
            {touched && textChanged && !reason.trim() && <p className="mt-1.5 text-[12.5px] text-discrepancy">A reason is required to save a revision.</p>}
            {conflict && (
              <Callout className="mt-3" tone="notice" icon={RefreshCw} title="A newer revision exists" action={<Button size="sm" variant="secondary" onClick={() => correction.reset()}>Keep my draft and retry</Button>}>
                Someone saved a revision while you were editing. Your text is kept here; compare with the latest row, then save again.
              </Callout>
            )}
            {correction.error && !conflict && <p role="alert" className="mt-3 rounded-[12px] bg-discrepancy-tint px-3.5 py-2.5 text-[13.5px] text-discrepancy">{isApiError(correction.error) ? correction.error.message : 'Saving failed. Your draft is kept.'}</p>}
            {!connected && (
              <p role="status" className="mt-3 flex items-center gap-2 rounded-[12px] bg-notice-tint px-3.5 py-2.5 text-[13.5px] text-notice">
                <WifiOff aria-hidden className="size-4" /> Saving is paused while disconnected.
              </p>
            )}
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div>
                <Button variant="secondary" size="lg" className="w-full" onClick={() => open(row.segment.evidence[0]?.id ?? row.segment.id)}>
                  <Play /> Listen to evidence
                </Button>
                <p className="mt-1.5 text-[12px] text-ink-3">The original source stays stored.</p>
              </div>
              <div>
                <Button type="submit" variant="primary" size="lg" className="w-full" disabled={!writable || !connected || correction.isPending || !textChanged}>
                  {correction.isPending && <Loader2 className="animate-spin" />} Save revision
                </Button>
                <p className="mt-1.5 text-[12px] text-ink-3">A new revision can make derived results stale.</p>
              </div>
            </div>
            {!writable && <p className="mt-3 text-[13px] text-ink-2">{archived ? 'Archived session — read-only.' : 'Your role can read the transcript but not correct it.'}</p>}
          </form>
          </DesktopOnly>
        </TabsContent>
        <TabsContent value="pairing" className="mt-4">
          <div>
            <p className="text-[15px] font-semibold text-ink">Association candidate</p>
            {row.association_targets.length === 0 ? (
              <p className="mt-2 text-[14px] text-ink-2">{row.intent?.speech_act === 'INSTRUCTION' ? 'Instructions are pairing targets, not candidates.' : 'No pairing candidates for this segment.'}</p>
            ) : (
              <>
                <div className="mt-1.5 flex items-center gap-2 text-[13px] text-ink-2">
                  Current: {row.association ? <StatusPill size="sm" meta={STATUS.association[row.association.status]} /> : 'none'}
                </div>
                <RadioGroup value={target} onValueChange={setTarget} aria-label="Pairing decision" className="mt-2" disabled={!writable || !connected}>
                  {row.association_targets.map((t) => (
                    <RadioRow key={t.id} value={t.id} label={t.label} className="py-2" />
                  ))}
                  <RadioRow value="UNDETERMINED" label="Cannot be determined yet" className="py-2" />
                </RadioGroup>
                {(ambiguous || row.association?.unknowns.length) ? (
                  <p className="mt-2 flex items-center gap-2 rounded-[12px] bg-notice-tint px-3.5 py-2.5 text-[13.5px] text-notice">
                    <CircleHelp aria-hidden className="size-4 shrink-0" /> {row.association?.unknowns.length ? `Unknown: ${row.association.unknowns.join(', ')}.` : 'Pairing is ambiguous.'}
                  </p>
                ) : null}
                {writable && target && (
                  <DesktopOnly what="Saving a pairing">
                  <div className="mt-3 space-y-2">
                    <Label htmlFor="pair-reason">Pairing reason (required)</Label>
                    <Input id="pair-reason" value={pairReason} onChange={(e) => setPairReason(e.target.value)} placeholder="What in the audio supports this pairing?" />
                    <div className="flex justify-end gap-2">
                      <Button size="sm" variant="ghost" onClick={() => setTarget('')}>
                        Cancel
                      </Button>
                      <Button size="sm" variant="primary" disabled={!pairReason.trim() || pairing.isPending || !connected} onClick={savePairing}>
                        {pairing.isPending && <Loader2 className="animate-spin" />} Save pairing
                      </Button>
                    </div>
                    {pairing.error && <p role="alert" className="text-[13px] text-discrepancy">{isApiError(pairing.error) ? pairing.error.message : 'Saving failed.'}</p>}
                  </div>
                  </DesktopOnly>
                )}
              </>
            )}
          </div>
        </TabsContent>
      </Tabs>
      {row.revisions.length > 0 && (
        <div className="mt-6">
          <p className="text-[14px] font-semibold text-ink">Revision history</p>
          <ol className="mt-2 space-y-2">
            {[...row.revisions].reverse().map((r) => (
              <li key={r.id} className="rounded-[14px] border border-hairline-soft px-3.5 py-2.5 text-[13.5px]">
                <p className="flex flex-wrap items-center justify-between gap-2 text-[12px] text-ink-3 tabular">
                  <span>
                    Revision {r.revision} · {r.origin}
                  </span>
                  <span>{formatDateTimeUtc(r.recorded_at)}</span>
                </p>
                <p className="mt-1 text-ink">“{r.text}”</p>
                {r.reason && <p className="mt-1 text-ink-2">Reason: {r.reason}</p>}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

export function TranscriptPage() {
  const transcript = useTranscript();
  const findings = useFindings();
  const waves = useWaveforms();
  const { open } = useEvidence();
  const { mode, setMode, asOf } = useSessionScope();
  const [params, setParams] = useSearchParams();
  const [query, setQuery] = useState('');
  const [channel, setChannel] = useState('ALL');
  const rows = useMemo(() => transcript.data?.rows ?? [], [transcript.data?.rows]);
  const filtered = rows.filter((r) => (channel === 'ALL' || String(r.segment.channel) === channel) && (!query || `${r.segment.text} ${r.label} ${r.evidence_label} ${r.intent?.callsign?.value ?? ''}`.toLowerCase().includes(query.toLowerCase())));
  const defaultRow = rows.find((r) => r.association?.status === 'AMBIGUOUS') ?? rows.find((r) => r.evidence_label === 'E-13') ?? rows[0];
  // Selection is keyed by the original segment id so it survives a saved revision.
  const selectedId = params.get('segment') ?? defaultRow?.original.id ?? null;
  const selected = rows.find((r) => r.original.id === selectedId || r.revisions.some((v) => v.id === selectedId)) ?? null;
  const stale = rows.some((r) => r.revisions.length > 0) || !!findings.data?.some((f) => f.finding.stale);
  const tableRef = useRef<HTMLDivElement>(null);
  // Keep the selected row visible inside the table's own scroller (never scrolls the page).
  useEffect(() => {
    const box = tableRef.current;
    const key = selected?.original.id;
    const row = key ? box?.querySelector<HTMLElement>(`[data-segment="${CSS.escape(key)}"]`) : null;
    if (!box || !row) return;
    const head = box.querySelector('thead')?.getBoundingClientRect().height ?? 0;
    const top = row.offsetTop - head;
    if (top < box.scrollTop || row.offsetTop + row.offsetHeight > box.scrollTop + box.clientHeight) box.scrollTo({ top: Math.max(0, top - (box.clientHeight - head - row.offsetHeight) / 2), behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }, [selected?.original.id, filtered.length]);
  const select = (id: string) =>
    setParams(
      (p) => {
        const n = new URLSearchParams(p);
        n.set('segment', id);
        return n;
      },
      { replace: true },
    );

  if (transcript.isError && !transcript.data)
    return (
      <div className="card p-6">
        <ErrorState error={transcript.error} onRetry={() => transcript.refetch()} />
      </div>
    );

  return (
    <div className="grid grid-cols-1 flex-1 items-start gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(360px,420px)]">
      <div className="min-w-0 space-y-5">
        <section aria-label="Transcript" className="card p-5">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative min-w-[220px] flex-1">
              <Search aria-hidden className="pointer-events-none absolute left-3.5 top-1/2 size-[18px] -translate-y-1/2 text-ink-3" />
              <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search quote or callsign" aria-label="Search transcript" className="pl-10" />
            </div>
            <Select label="Filter by channel" value={channel} onValueChange={setChannel} icon={<Filter aria-hidden className="text-ink-2" />} options={[{ value: 'ALL', label: 'All channels' }, ...(transcript.data?.channels ?? []).map((c) => ({ value: String(c.index), label: c.label }))]} />
          </div>
          {!transcript.data ? (
            <LoadingRows rows={6} className="mt-4" />
          ) : filtered.length === 0 ? (
            <EmptyState className="py-10" icon={Search} title="No segments match">
              {rows.length === 0 && mode === 'AS_KNOWN' ? (
                <>
                  Nothing is available at {formatOffset(asOf)}.{' '}
                  <button type="button" className="font-medium text-data hover:underline" onClick={() => setMode('DEBRIEF')}>
                    Switch to Debrief
                  </button>
                </>
              ) : (
                'Try a different search or channel.'
              )}
            </EmptyState>
          ) : (
            <div ref={tableRef} className="scrollbar-thin relative mt-3 max-h-[min(520px,calc(100dvh-400px))] min-h-[280px] overflow-auto">
              <table className="w-full border-separate border-spacing-0 text-left">
                <caption className="sr-only">Transcript segments with channel and association</caption>
                <thead className="sticky top-0 z-10 bg-surface text-[14px] text-ink-2">
                  <tr>
                    <th scope="col" className="w-[76px] py-3 pl-3 font-medium">Time</th>
                    <th scope="col" className="w-[100px] py-3 font-medium">Channel</th>
                    <th scope="col" className="py-3 font-medium">Transcript</th>
                    <th scope="col" className="w-[160px] py-3 font-medium">Association</th>
                    <th scope="col" className="w-[44px] py-3"><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r) => {
                    const active = r.original.id === selected?.original.id;
                    const ch = transcript.data!.channels.find((c) => c.index === r.segment.channel);
                    return (
                      <tr key={r.original.id} data-segment={r.original.id} onClick={() => select(r.original.id)} aria-selected={active} className={cn('cursor-pointer transition-colors [&>td]:border-t [&>td]:border-hairline-soft', active ? 'bg-data-tint/70 [&>td:first-child]:shadow-[inset_3px_0_0_0_#2563eb]' : 'hover:bg-sunken/70')}>
                        <td className="py-3.5 pl-3 align-top text-[15px] text-ink tabular">
                          <button type="button" onClick={(e) => { e.stopPropagation(); select(r.original.id); }} className="rounded-[6px] outline-offset-2" aria-label={`Select segment ${r.label} at ${formatClock(r.segment.start_ms ?? 0)}`}>
                            {formatClock(r.segment.start_ms ?? 0)}
                          </button>
                        </td>
                        <td className="py-3.5 align-top">
                          <span className={cn('inline-flex h-7 items-center rounded-[8px] px-2.5 text-[13px] font-medium', CHANNEL_PILL[r.segment.channel] ?? CHANNEL_PILL[3])}>{ch?.label ?? r.segment.channel}</span>
                        </td>
                        <td className="py-3.5 pr-4 align-top text-[15px] leading-snug text-ink">
                          {r.segment.text}
                          {r.revisions.length > 0 && (
                            <span className="ml-2 inline-flex h-5 items-center gap-1 rounded-full bg-data-tint px-2 align-middle text-[11.5px] font-semibold text-data-strong">
                              <Sparkles aria-hidden className="size-3" /> Revised
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 align-top"><AssociationCell row={r} /></td>
                        <td className="py-2.5 pr-1 align-top">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <MoreButton label={`Actions for ${r.label}`} className="size-8 border-transparent bg-transparent" onClick={(e) => e.stopPropagation()} />
                            </DropdownMenuTrigger>
                            <DropdownMenuContent className="w-[220px]">
                              <DropdownMenuItem onSelect={() => open(r.segment.evidence[0]?.id ?? r.segment.id)}>
                                <Play /> Open evidence {r.evidence_label}
                              </DropdownMenuItem>
                              <DropdownMenuItem asChild>
                                <Link to={`../../workspace?t=${r.segment.start_ms ?? 0}${mode === 'DEBRIEF' ? '&mode=debrief' : ''}`} relative="path">
                                  <MoreHorizontal /> Show in workspace
                                </Link>
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          {mode === 'AS_KNOWN' && (transcript.data?.hidden_after_as_of ?? 0) > 0 && (
            <p className="mt-3 text-[13px] text-ink-3">
              {transcript.data!.hidden_after_as_of} later segments are hidden in As-known at {formatOffset(asOf)}.
            </p>
          )}
        </section>
        {selected && <SegmentWave row={selected} waves={waves.data} />}
      </div>

      <section aria-label="Segment detail" className="card p-6 xl:sticky xl:top-6">
        {selected ? <SegmentPanel key={`${selected.original.id}:${selected.segment.revision}`} row={selected} rows={rows} onNavigate={select} stale={stale} /> : <EmptyState title="Select a segment" />}
      </section>
    </div>
  );
}
