import { AudioLines, ChevronFirst, ChevronLast, ChevronsDownUp, ChevronsUpDown, Keyboard, ListVideo, Loader2, LocateFixed, Pause, Play, Settings2, TriangleAlert, Volume1, Volume2, VolumeX, X } from 'lucide-react';
import { useCallback, useEffect, useId, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';
import { Link } from 'react-router';
import type { TimeRange, WaveformView, WorkspaceSnapshot } from '@/api/types';
import { Card } from '@/components/domain/primitives';
import { Button } from '@/components/ui/button';
import { Segmented } from '@/components/ui/controls';
import { Input, Kbd, Label } from '@/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/menu';
import { Tooltip } from '@/components/ui/tooltip';
import { useElementSize } from '@/hooks/useElementSize';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { useStreamState } from '@/hooks/useSessionStream';
import { clamp, formatClock, formatOffset, parseOffset } from '@/lib/time';
import { cn } from '@/lib/utils';
import { useAudio } from './audio';
import { SPEEDS, useReplay, type Speed } from './store';

type Marker = WorkspaceSnapshot['event_markers'][number];

const MARKER_STYLE: Record<Marker['kind'], { cls: string; name: string }> = {
  INSTRUCTION: { cls: 'h-3.5 w-[3px] rounded-full bg-data', name: 'Instruction' },
  READBACK: { cls: 'h-3.5 w-[3px] rounded-full bg-[#8fb0f0]', name: 'Readback' },
  REPORT: { cls: 'h-3 w-[3px] rounded-full bg-[#9aa3b2]', name: 'Report' },
  CORRECTION: { cls: 'size-[9px] rounded-full border-2 border-data bg-surface', name: 'Correction' },
  FINDING: { cls: 'size-[9px] rotate-45 rounded-[2px] bg-[#d63384]', name: 'Finding' },
};

function isTyping(target: EventTarget | null) {
  const el = target as HTMLElement | null;
  if (!el) return false;
  return el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName) || !!el.closest('[role="dialog"],[role="menu"],[role="listbox"]');
}

/** Keyboard shortcuts for the replay clock (ignored while typing or inside dialogs). */
export function useReplayShortcuts(markers: Marker[]) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(e.target)) return;
      const r = useReplay.getState();
      const step = e.shiftKey ? 1000 : 5000;
      switch (e.key) {
        case ' ':
          if ((e.target as HTMLElement)?.tagName === 'BUTTON') return;
          e.preventDefault();
          r.toggle();
          break;
        case 'ArrowLeft':
          if ((e.target as HTMLElement)?.getAttribute('role') === 'slider') return;
          e.preventDefault();
          r.seek(r.cursor - step);
          break;
        case 'ArrowRight':
          if ((e.target as HTMLElement)?.getAttribute('role') === 'slider') return;
          e.preventDefault();
          r.seek(r.cursor + step);
          break;
        case '[': {
          const prev = [...markers].reverse().find((m) => m.t < r.cursor - 250);
          if (prev) r.seek(prev.t);
          break;
        }
        case ']': {
          const next = markers.find((m) => m.t > r.cursor + 250);
          if (next) r.seek(next.t);
          break;
        }
        case 'f':
        case 'F':
          if (!useAudio.getState().available) r.setView(r.view === 'FOLLOW' ? 'LOCAL' : 'FOLLOW');
          break;
        case 'm':
        case 'M':
          if (useAudio.getState().available) useAudio.getState().toggleMute();
          break;
        case 'Home':
          r.seek(0);
          break;
        case 'End':
          r.seek(r.duration);
          break;
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [markers]);
}

function bars(peaks: number[], count: number) {
  if (!count || !peaks.length) return [];
  const out: number[] = [];
  const per = peaks.length / count;
  for (let i = 0; i < count; i++) {
    let max = 0;
    const from = Math.floor(i * per);
    const to = Math.max(from + 1, Math.floor((i + 1) * per));
    for (let j = from; j < to; j++) max = Math.max(max, peaks[j] ?? 0);
    out.push(max);
  }
  return out;
}

function WaveLane({ peaks, width, height, cursorX, tone }: { peaks: number[]; width: number; height: number; cursorX: number; tone: 'data' | 'muted' }) {
  const id = useId();
  const gap = 3.6;
  const values = useMemo(() => bars(peaks, Math.floor(width / gap)), [peaks, width]);
  const shapes = useMemo(
    () =>
      values.map((v, i) => {
        const h = v < 0.01 ? 2 : Math.max(3, v * (height - 6));
        return <rect key={i} x={i * gap} y={(height - h) / 2} width={1.7} height={h} rx={0.85} />;
      }),
    [values, height],
  );
  const base = tone === 'data' ? '#a9bfe9' : '#c5cbd5';
  const played = tone === 'data' ? '#2563eb' : '#7d8899';
  return (
    <svg width={width} height={height} aria-hidden className="block">
      <defs>
        <clipPath id={`${id}-p`}>
          <rect x={0} y={0} width={Math.max(0, cursorX)} height={height} />
        </clipPath>
      </defs>
      <g fill={base}>{shapes}</g>
      <g fill={played} clipPath={`url(#${id}-p)`}>
        {shapes}
      </g>
    </svg>
  );
}

function RangeEditor({ range, onApply, onClear, duration }: { range: { start: number; end: number }; onApply: (r: { start: number; end: number }) => void; onClear: () => void; duration: number }) {
  const [open, setOpen] = useState(false);
  const [start, setStart] = useState(formatOffset(range.start));
  const [end, setEnd] = useState(formatOffset(range.end));
  const [error, setError] = useState<string | null>(null);
  const onOpenChange = (next: boolean) => {
    if (next) {
      setStart(formatOffset(range.start));
      setEnd(formatOffset(range.end));
      setError(null);
    }
    setOpen(next);
  };
  const apply = () => {
    const s = parseOffset(start);
    const e = parseOffset(end);
    if (s == null || e == null) return setError('Use mm:ss or mm:ss.s, for example 05:12.0.');
    if (e <= s) return setError('End must be after start.');
    if (e > duration) return setError(`End must be within the session (${formatClock(duration)}).`);
    onApply({ start: s, end: e });
    setOpen(false);
  };
  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>
        <button type="button" className="pointer-events-auto inline-flex h-7 items-center rounded-[9px] border border-hairline bg-surface px-2.5 text-[13px] font-medium text-ink shadow-pop tabular hover:bg-sunken" aria-label={`Evidence range ${formatClock(range.start)} to ${formatClock(range.end)}. Edit range`}>
          {formatClock(range.start)} – {formatClock(range.end)}
        </button>
      </PopoverTrigger>
      <PopoverContent align="center" side="bottom" className="w-[280px] p-4">
        <p className="text-[14px] font-semibold text-ink">Evidence range</p>
        <p className="mt-0.5 text-[12.5px] text-ink-2">Highlights a span on the replay clock. Drag handles or type exact offsets.</p>
        <form
          className="mt-3 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            apply();
          }}
        >
          <div className="grid grid-cols-2 gap-2.5">
            <div className="space-y-1">
              <Label htmlFor="range-start" className="text-[12.5px]">
                Start
              </Label>
              <Input id="range-start" value={start} onChange={(e) => setStart(e.target.value)} className="h-9 tabular" inputMode="decimal" aria-invalid={!!error} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="range-end" className="text-[12.5px]">
                End
              </Label>
              <Input id="range-end" value={end} onChange={(e) => setEnd(e.target.value)} className="h-9 tabular" inputMode="decimal" aria-invalid={!!error} />
            </div>
          </div>
          {error && (
            <p role="alert" className="text-[12.5px] text-discrepancy">
              {error}
            </p>
          )}
          <div className="flex justify-between gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                onClear();
                setOpen(false);
              }}
            >
              <X /> Clear
            </Button>
            <Button size="sm" variant="primary" type="submit">
              Apply
            </Button>
          </div>
        </form>
      </PopoverContent>
    </Popover>
  );
}

const SHORTCUTS: [string, string][] = [
  ['Space', 'Play / pause'],
  ['← →', 'Seek 5 s'],
  ['Shift + ← →', 'Seek 1 s'],
  ['[  ]', 'Previous / next event'],
  ['F', 'Follow leader'],
  ['M', 'Mute audio (demo workspaces)'],
  ['Shift + drag', 'Mark a range'],
  ['Home / End', 'Start / end'],
];

/** Volume, mute and buffering state for DEMO audio playback. */
function AudioControl({ compact }: { compact: boolean }) {
  const volume = useAudio((s) => s.volume);
  const muted = useAudio((s) => s.muted);
  const buffering = useAudio((s) => s.buffering);
  const failed = useAudio((s) => s.failed);
  const playing = useReplay((s) => s.status === 'PLAYING');
  const Icon = muted || volume === 0 ? VolumeX : volume < 0.5 ? Volume1 : Volume2;
  if (failed)
    return (
      <span role="status" className="inline-flex h-8 items-center gap-1.5 rounded-full bg-notice-tint px-3 text-[12.5px] font-medium text-notice">
        <TriangleAlert aria-hidden className="size-3.5" /> Audio unavailable · replay is visual
      </span>
    );
  return (
    <div className={cn('inline-flex items-center gap-2 rounded-[14px] border border-hairline bg-surface pl-1 pr-3 shadow-control', compact ? 'h-9' : 'h-11')}>
      <Tooltip content={muted ? 'Unmute (M)' : 'Mute (M)'}>
        <button type="button" aria-label={muted ? 'Unmute audio' : 'Mute audio'} aria-pressed={muted} onClick={() => useAudio.getState().toggleMute()} className="inline-flex size-8 items-center justify-center rounded-[10px] text-ink hover:bg-sunken">
          <Icon aria-hidden className="size-[18px]" />
        </button>
      </Tooltip>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={muted ? 0 : volume}
        onChange={(e) => useAudio.getState().setVolume(Number(e.target.value))}
        aria-label="Volume"
        className="h-1.5 w-20 cursor-pointer accent-[var(--color-data)]"
      />
      {buffering && playing ? (
        <span role="status" className="inline-flex items-center gap-1 text-[12.5px] text-ink-2">
          <Loader2 aria-hidden className="size-3.5 animate-spin" /> Buffering
        </span>
      ) : (
        <span className="text-[12.5px] font-medium text-ink-2">Audio</span>
      )}
    </div>
  );
}

/**
 * Replay band (comp 03): transport, speed, follow-leader, multi-channel waveform,
 * gaps, event markers, playhead and evidence range. Visual only for MOCK sessions;
 * DEMO workspaces (ADR 0003) play real audio and show a volume control instead.
 */
export function TimelineBand({ waveforms, gaps, markers, transcriptHref, className }: { waveforms: WaveformView[] | undefined; gaps: TimeRange[]; markers: Marker[]; transcriptHref: string; className?: string }) {
  const cursor = useReplay((s) => s.cursor);
  const duration = useReplay((s) => s.duration);
  const status = useReplay((s) => s.status);
  const speed = useReplay((s) => s.speed);
  const view = useReplay((s) => s.view);
  const range = useReplay((s) => s.range);
  const leaderName = useStreamState((s) => s.leaderName);
  const streamConnected = useStreamState((s) => s.connection === 'CONNECTED');
  const audio = useAudio((s) => s.available);
  // Following another reviewer would fight the local audio clock.
  const connected = streamConnected && !audio;
  const [showMarkers, setShowMarkers] = useState(true);
  // Compact by default below 1000 px tall so the workspace fits the viewport (D-2); the user can expand.
  const isShort = useMediaQuery('(max-height: 999px)');
  const [expanded, setExpanded] = useState<boolean | null>(null);
  const compact = !(expanded ?? !isShort);
  const [lanesRef, lanes] = useElementSize<HTMLDivElement>();
  const drag = useRef<{ kind: 'seek' | 'range' | 'start' | 'end'; anchor: number } | null>(null);
  useReplayShortcuts(markers);

  const width = lanes.width;
  const [zoom, setZoom] = useState<'ALL' | '5m' | '1m'>('5m');
  const win = !duration ? 1 : zoom === 'ALL' ? duration : Math.min(duration, zoom === '5m' ? 300_000 : 60_000);
  // Paged window: the playhead moves between 10 % and 90 % of the view, then the page turns.
  const page = win * 0.8;
  const start = win >= duration ? 0 : clamp(Math.floor(cursor / page) * page - win * 0.1, 0, duration - win);
  const end = start + win;
  const xOf = useCallback((ms: number) => ((ms - start) / win) * width, [start, win, width]);
  const span = (a: number, b: number) => {
    const l = Math.max(0, xOf(a));
    const rgt = Math.min(width, xOf(b));
    return rgt <= l ? null : { left: l, width: rgt - l };
  };
  const inView = (ms: number) => ms >= start && ms <= end;
  const msAt = useCallback(
    (clientX: number) => {
      const rect = lanesRef.current?.getBoundingClientRect();
      if (!rect || !duration) return 0;
      return clamp(start + ((clientX - rect.left) / rect.width) * win, 0, duration);
    },
    [duration, lanesRef, start, win],
  );
  const sliced = useMemo(
    () =>
      (waveforms ?? []).map((w) => {
        const from = Math.floor(start / w.bucket_ms);
        const to = Math.ceil(end / w.bucket_ms);
        return { wave: w, peaks: w.peaks.slice(from, to) };
      }),
    [waveforms, start, end],
  );

  const r = useReplay.getState;
  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    const target = e.target as HTMLElement;
    if (target.closest('[data-no-scrub]')) return;
    const handle = target.closest<HTMLElement>('[data-handle]')?.dataset.handle as 'start' | 'end' | undefined;
    const ms = msAt(e.clientX);
    e.currentTarget.setPointerCapture(e.pointerId);
    if (handle) drag.current = { kind: handle, anchor: ms };
    else if (e.shiftKey) {
      drag.current = { kind: 'range', anchor: ms };
      r().setRange(null);
    } else {
      drag.current = { kind: 'seek', anchor: ms };
      r().seek(ms);
    }
  };
  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    if (!d) return;
    const ms = msAt(e.clientX);
    const cur = r().range;
    if (d.kind === 'seek') r().seek(ms);
    else if (d.kind === 'range') r().setRange({ start: d.anchor, end: ms });
    else if (d.kind === 'start' && cur) r().setRange({ start: Math.min(ms, cur.end - 500), end: cur.end });
    else if (d.kind === 'end' && cur) r().setRange({ start: cur.start, end: Math.max(ms, cur.start + 500) });
  };
  const onPointerUp = () => {
    drag.current = null;
  };

  const channelRows = waveforms ?? [];
  const laneH = compact ? 20 : 40;
  const ctl = compact ? 'size-9 rounded-[11px]' : 'size-11 rounded-[13px]';
  const cursorX = xOf(cursor);
  const playing = status === 'PLAYING';
  const following = view === 'FOLLOW';
  const ticks = useMemo(() => {
    if (!duration) return [];
    // Pick the finest step that keeps labels ≥ 56 px apart at the current lane width.
    const steps = [10_000, 30_000, 60_000, 120_000, 300_000, 600_000];
    const step = steps.find((st) => (st / win) * (width || 600) >= 56) ?? 600_000;
    const out: number[] = [];
    for (let t = Math.ceil(start / step) * step; t <= end; t += step) out.push(t);
    return out;
  }, [duration, win, start, end, width]);

  return (
    <Card as="section" aria-label="Replay timeline" className={cn('p-4 sm:px-5', compact ? 'sm:py-3' : 'sm:py-4', className)}>
      {/* Transport */}
      <div className={cn('flex flex-wrap items-center gap-y-3', compact ? 'gap-x-2' : 'gap-x-3')}>
        <button
          type="button"
          onClick={() => r().toggle()}
          aria-label={playing ? 'Pause replay' : 'Play replay'}
          className={cn('inline-flex shrink-0 items-center justify-center rounded-full bg-action text-on-action shadow-action transition-colors hover:bg-action-hover', compact ? 'size-10' : 'size-[52px]')}
        >
          {playing ? <Pause aria-hidden className="size-5 fill-current" /> : <Play aria-hidden className="ml-0.5 size-5 fill-current" />}
        </button>
        <p className={cn('min-w-[118px] font-medium text-ink tabular', compact ? 'text-[15.5px]' : 'text-[17px]')} aria-live="off">
          {formatClock(cursor)} <span className="text-ink-3">/</span> {formatClock(duration)}
        </p>
        <div className="flex items-center gap-1.5">
          <Tooltip content="Previous event  [">
            <button
              type="button"
              aria-label="Previous event"
              onClick={() => {
                const prev = [...markers].reverse().find((m) => m.t < cursor - 250);
                r().seek(prev ? prev.t : 0);
              }}
              className={cn('inline-flex items-center justify-center border border-hairline bg-surface text-ink shadow-control hover:bg-sunken', ctl)}
            >
              <ChevronFirst aria-hidden className="size-[19px]" />
            </button>
          </Tooltip>
          <Tooltip content="Next event  ]">
            <button
              type="button"
              aria-label="Next event"
              onClick={() => {
                const next = markers.find((m) => m.t > cursor + 250);
                if (next) r().seek(next.t);
              }}
              className={cn('inline-flex items-center justify-center border border-hairline bg-surface text-ink shadow-control hover:bg-sunken', ctl)}
            >
              <ChevronLast aria-hidden className="size-[19px]" />
            </button>
          </Tooltip>
        </div>
        <Segmented
          label="Playback speed"
          tone="data"
          value={String(speed)}
          onChange={(v) => r().setSpeed(Number(v) as Speed)}
          className={cn('gap-0.5 rounded-[14px] border border-hairline bg-surface p-[3px] shadow-control [&>button]:min-w-[50px] [&>button]:rounded-[11px] [&>button]:px-3 [&>button]:text-[15px] [&>button]:tabular', compact ? 'h-9 [&>button]:h-[28px]' : 'h-11 [&>button]:h-[36px]')}
          options={SPEEDS.map((s) => ({ value: String(s), label: `${s}×` }))}
        />
        <Tooltip content={connected ? `Follow ${leaderName}'s replay position (F)` : audio ? 'Follow leader is not available while audio plays locally' : 'Follow leader is unavailable while disconnected'}>
          <button
            type="button"
            aria-pressed={following}
            disabled={!connected}
            onClick={() => r().setView(following ? 'LOCAL' : 'FOLLOW')}
            className={cn(
              'inline-flex items-center gap-2 rounded-[14px] border px-4 text-[15px] font-medium shadow-control transition-colors disabled:cursor-not-allowed disabled:opacity-60',
              compact ? 'h-9 px-3 text-[14px]' : 'h-11',
              following ? 'border-data/30 bg-data-tint text-data-strong' : 'border-hairline bg-surface text-ink hover:bg-sunken',
            )}
          >
            <LocateFixed aria-hidden className="size-[18px]" />
            {following ? `Following ${leaderName.split(' ')[0]}` : 'Follow leader'}
          </button>
        </Tooltip>
        {audio ? (
          <AudioControl compact={compact} />
        ) : (
          <span className="inline-flex h-8 items-center gap-1.5 rounded-full bg-track px-3 text-[12.5px] font-medium text-ink-2">
            <VolumeX aria-hidden className="size-3.5" /> No audio
          </span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <Tooltip content={compact ? 'Expand timeline lanes' : 'Compact timeline lanes'}>
            <button
              type="button"
              aria-pressed={!compact}
              aria-label="Expanded timeline lanes"
              onClick={() => setExpanded(compact)}
              className={cn('inline-flex items-center justify-center border border-hairline bg-surface text-ink shadow-control transition-colors hover:bg-sunken', ctl)}
            >
              {compact ? <ChevronsUpDown aria-hidden className="size-[19px]" /> : <ChevronsDownUp aria-hidden className="size-[19px]" />}
            </button>
          </Tooltip>
          <Tooltip content={showMarkers ? 'Hide event markers' : 'Show event markers'}>
            <button
              type="button"
              aria-pressed={showMarkers}
              aria-label="Event markers"
              onClick={() => setShowMarkers((v) => !v)}
              className={cn('inline-flex items-center justify-center border shadow-control transition-colors', ctl, showMarkers ? 'border-data/25 bg-data-tint text-data-strong' : 'border-hairline bg-surface text-ink hover:bg-sunken')}
            >
              <AudioLines aria-hidden className="size-[19px]" />
            </button>
          </Tooltip>
          <Tooltip content="Open transcript at this position">
            <Link to={transcriptHref} aria-label="Open transcript" className={cn('inline-flex items-center justify-center border border-hairline bg-surface text-ink shadow-control hover:bg-sunken', ctl)}>
              <ListVideo aria-hidden className="size-[19px]" />
            </Link>
          </Tooltip>
          <Popover>
            <Tooltip content="Keyboard shortcuts">
              <PopoverTrigger asChild>
                <button type="button" aria-label="Keyboard shortcuts" className={cn('inline-flex items-center justify-center border border-hairline bg-surface text-ink shadow-control hover:bg-sunken', ctl)}>
                  <Settings2 aria-hidden className="size-[19px]" />
                </button>
              </PopoverTrigger>
            </Tooltip>
            <PopoverContent className="w-[270px] p-4">
              <p className="flex items-center gap-2 text-[14px] font-semibold text-ink">
                <Keyboard aria-hidden className="size-4 text-ink-2" /> Replay shortcuts
              </p>
              <dl className="mt-3 space-y-2">
                {SHORTCUTS.map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between gap-3 text-[13px]">
                    <dt className="text-ink-2">{v}</dt>
                    <dd>
                      <Kbd>{k}</Kbd>
                    </dd>
                  </div>
                ))}
              </dl>
            </PopoverContent>
          </Popover>
        </div>
      </div>

      {/* Lanes */}
      <div className={cn('grid grid-cols-[96px_minmax(0,1fr)] gap-x-3 sm:grid-cols-[112px_minmax(0,1fr)]', compact ? 'mt-1.5' : 'mt-3')}>
        <div className={cn('flex items-end', compact ? 'h-6' : 'h-7')}>
          <Segmented
            label="Timeline zoom"
            size="sm"
            value={zoom}
            onChange={setZoom}
            className="h-7 gap-0 rounded-[9px] p-0.5 [&>button]:h-6 [&>button]:rounded-[7px] [&>button]:px-2 [&>button]:text-[12px]"
            options={[
              { value: '1m', label: '1m' },
              { value: '5m', label: '5m' },
              { value: 'ALL', label: 'All' },
            ]}
          />
        </div>
        <div className={cn('relative', compact ? 'h-6' : 'h-7')}>
          {gaps
            .filter((g) => g.end_ms >= start && g.start_ms <= end)
            .map((g) => (
              <span key={g.start_ms} className="absolute bottom-0.5 -translate-x-1/2 whitespace-nowrap text-[12px] font-medium text-ink-2" style={{ left: clamp(xOf((Math.max(g.start_ms, start) + Math.min(g.end_ms, end)) / 2), 30, width - 30) }}>
                Audio gap
              </span>
            ))}
          {showMarkers &&
            markers.filter((m) => inView(m.t)).map((m) => {
              const st = MARKER_STYLE[m.kind];
              return (
                <Tooltip key={m.id} content={`${formatClock(m.t)} · ${st.name} · ${m.label}`}>
                  <button
                    type="button"
                    data-no-scrub
                    onClick={() => r().seek(m.t)}
                    aria-label={`Seek to ${st.name.toLowerCase()} ${m.label} at ${formatClock(m.t)}`}
                    className="absolute bottom-0 flex h-5 w-3 -translate-x-1/2 items-center justify-center rounded-[4px] hover:bg-track"
                    style={{ left: xOf(m.t) }}
                  >
                    <span aria-hidden className={st.cls} />
                  </button>
                </Tooltip>
              );
            })}
        </div>

        <div className="space-y-1">
          {channelRows.map((w, i) => (
            <div key={w.channel} className={cn('flex items-center gap-2.5 font-medium text-ink', compact ? 'text-[13.5px]' : 'text-[15.5px]')} style={{ height: laneH }}>
              <AudioLines aria-hidden className={cn(compact ? 'size-4' : 'size-[18px]', i === 0 ? 'text-data' : 'text-ink-3')} />
              {w.label}
            </div>
          ))}
        </div>
        {/* The slider must not contain interactive children; the range editor is its sibling. */}
        <div className="relative">
        <div
          ref={lanesRef}
          role="slider"
          tabIndex={0}
          aria-label="Replay position"
          aria-valuemin={0}
          aria-valuemax={duration}
          aria-valuenow={Math.round(cursor)}
          aria-valuetext={`${formatOffset(cursor)} of ${formatClock(duration)}`}
          onKeyDown={(e) => {
            const step = e.shiftKey ? 1000 : 5000;
            if (e.key === 'ArrowLeft') {
              e.preventDefault();
              r().seek(cursor - step);
            } else if (e.key === 'ArrowRight') {
              e.preventDefault();
              r().seek(cursor + step);
            }
          }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          className="relative cursor-pointer touch-none select-none space-y-1 rounded-[10px] outline-offset-4"
        >
          {/* gaps */}
          {gaps.map((g) => {
            const sp = span(g.start_ms, g.end_ms);
            return sp && <div key={g.start_ms} aria-hidden className="hatch-muted pointer-events-none absolute -inset-y-1 rounded-[6px] opacity-80" style={{ left: sp.left, width: Math.max(2, sp.width) }} />;
          })}
          {/* range */}
          {range &&
            (() => {
              const sp = span(range.start, range.end);
              return sp && <div aria-hidden className="pointer-events-none absolute -inset-y-1.5 rounded-[10px] bg-data/[0.09] ring-1 ring-data/15" style={{ left: sp.left, width: sp.width }} />;
            })()}
          {sliced.map(({ wave, peaks }, i) => (
            <div key={wave.channel} style={{ height: laneH }}>
              {width > 0 && <WaveLane peaks={peaks} width={width} height={laneH} cursorX={cursorX} tone={i === 0 ? 'data' : 'muted'} />}
            </div>
          ))}
          {!channelRows.length && <div className="flex h-10 items-center text-[13px] text-ink-3">Loading waveform…</div>}
          {/* range handles */}
          {range && range.end >= start && range.start <= end && (
            <>
              {(['start', 'end'] as const).filter((h) => inView(range[h])).map((h) => (
                <span
                  key={h}
                  data-handle={h}
                  aria-hidden
                  className="absolute z-10 size-[15px] -translate-x-1/2 -translate-y-1/2 cursor-ew-resize rounded-full border-[2.5px] border-data bg-surface shadow-pop"
                  style={{ left: xOf(range[h]), top: laneH / 2 }}
                />
              ))}
            </>
          )}
          {/* playhead */}
          <div aria-hidden className="pointer-events-none absolute -top-8 bottom-[-6px] z-20 w-0" style={{ left: cursorX, display: inView(cursor) ? undefined : 'none' }}>
            <span className="absolute left-1/2 top-0 size-[11px] -translate-x-1/2 rounded-full border-2 border-surface bg-data shadow-[0_0_0_1px_rgba(37,99,235,0.35)]" />
            <span className="absolute bottom-0 left-1/2 top-2 w-[2px] -translate-x-1/2 rounded-full bg-data" />
          </div>
        </div>
        {range && range.end >= start && range.start <= end && (
          <div data-no-scrub className="pointer-events-none absolute z-10 -translate-x-1/2" style={{ left: clamp((xOf(range.start) + xOf(range.end)) / 2, 60, width - 60), top: laneH + 8 }}>
            <RangeEditor range={range} duration={duration} onApply={(v) => r().setRange(v)} onClear={() => r().setRange(null)} />
          </div>
        )}
        </div>

        <div aria-hidden />
        <div aria-hidden className="relative mt-1.5 h-4">
          {ticks.map((t) => (
            <span key={t} className={cn('absolute text-[11px] text-ink-3 tabular', t === start ? '' : '-translate-x-1/2')} style={{ left: xOf(t) }}>
              {xOf(t) > width - 24 ? '' : formatClock(t)}
            </span>
          ))}
        </div>
      </div>
    </Card>
  );
}
