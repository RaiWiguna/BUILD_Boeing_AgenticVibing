/**
 * DEMO track (ADR 0003): transcript that appears while the audio plays.
 *
 * Timing mirrors a streaming recogniser: each word shows 400 ms after it is spoken
 * (interim, grey), the segment turns final after its modelled STT latency, and the
 * speaker role is shown 400 ms after that. Text is the cached STT hypothesis — never
 * a verified record. Everything is derived from the replay cursor, so seeking
 * backwards hides words again.
 */
import { AudioLines, FastForward, Loader2, MessageSquareText } from 'lucide-react';
import { Fragment, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import type { DemoLiveSegment, DemoMedia } from '@/api/types';
import { Card, CodeChip } from '@/components/domain/primitives';
import { Button } from '@/components/ui/button';
import { useReplay } from '@/features/replay/store';
import { formatClock } from '@/lib/time';
import { cn } from '@/lib/utils';

/** Delay between a word being spoken and shown. */
export const WORD_LAG_MS = 400;
/** Delay between a segment turning final and its speaker role being shown. */
export const SPEAKER_LAG_MS = 400;
/** Silence longer than this offers a skip to the next transmission. */
const SKIP_AFTER_MS = 6000;

/** Words heard and recognised by `cursor` (interim view). */
export function revealedWords(seg: DemoLiveSegment, cursor: number) {
  return seg.words.filter((w) => w.end_ms + WORD_LAG_MS <= cursor);
}

export type LivePhase = 'HIDDEN' | 'LISTENING' | 'INTERIM' | 'FINAL';

export function phaseOf(seg: DemoLiveSegment, cursor: number): LivePhase {
  if (cursor < seg.start_ms) return 'HIDDEN';
  if (cursor >= seg.final_ms) return 'FINAL';
  return revealedWords(seg, cursor).length ? 'INTERIM' : 'LISTENING';
}

/** The speaker role is shown only once recognition is final, after a short delay. */
export function speakerShown(seg: DemoLiveSegment, cursor: number) {
  return cursor >= seg.final_ms + SPEAKER_LAG_MS;
}

function clockOf(iso: string) {
  return iso ? iso.slice(11, 19) : '';
}

export function LiveTranscript({ media, transcriptHref, className }: { media: DemoMedia; transcriptHref: (segmentId: string) => string; className?: string }) {
  // 100 ms resolution is enough for word timing and keeps re-renders cheap.
  const cursor = useReplay((s) => Math.floor(s.cursor / 100) * 100);
  const playing = useReplay((s) => s.status === 'PLAYING');
  const seek = useReplay((s) => s.seek);
  const shown = media.segments.filter((s) => s.start_ms <= cursor);
  const scroller = useRef<HTMLDivElement>(null);
  const [stick, setStick] = useState(true);
  const recordings = media.recordings;
  const multi = recordings.length > 1;
  const gaps = recordings.slice(1).map((r, i) => ({ start: recordings[i]!.offset_ms + recordings[i]!.duration_ms, end: r.offset_ms, before: r.part })).filter((g) => g.end - g.start > 1000);
  const passedGaps = gaps.filter((g) => cursor >= g.start).length;
  const revealCount = shown.reduce((n, s) => n + revealedWords(s, cursor).length + (speakerShown(s, cursor) ? 1 : 0), 0) + shown.length + passedGaps;

  // Autoscroll to the newest words unless the reader scrolled up.
  useLayoutEffect(() => {
    const el = scroller.current;
    if (el && stick) el.scrollTop = el.scrollHeight;
  }, [revealCount, stick]);

  const onScroll = () => {
    const el = scroller.current;
    if (!el) return;
    setStick(el.scrollHeight - el.scrollTop - el.clientHeight < 24);
  };

  const next = media.segments.find((s) => s.start_ms > cursor);
  const speaking = media.segments.some((s) => cursor >= s.start_ms - 300 && cursor < s.end_ms);
  const canSkip = !!next && !speaking && next.start_ms - cursor > SKIP_AFTER_MS;
  const skip = () => next && seek(Math.max(0, next.start_ms - 800));
  const finals = shown.filter((s) => speakerShown(s, cursor));
  const announce = finals[finals.length - 1];
  const recordingName = (part: string) => recordings.find((r) => r.part === part);

  return (
    <Card as="section" aria-labelledby="live-transcript-title" className={cn('flex min-h-0 flex-col p-5', className)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="live-transcript-title" className="flex items-center gap-2 whitespace-nowrap text-[20px] font-semibold tracking-[-0.02em] text-ink">
          Transcript
          {playing && shown.some((s) => phaseOf(s, cursor) !== 'FINAL') && (
            <span className="relative inline-flex size-2.5" aria-hidden>
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-data/60" />
              <span className="relative inline-flex size-2.5 rounded-full bg-data" />
            </span>
          )}
        </h2>
        <div className="flex items-center gap-2">
          {canSkip && shown.length > 0 && (
            <Button size="xs" variant="secondary" onClick={skip} aria-label={`Skip to ${formatClock(next!.start_ms)}`}>
              <FastForward /> {formatClock(next!.start_ms)}
            </Button>
          )}
          <CodeChip title={media.stt_label}>Automatic · unreviewed</CodeChip>
        </div>
      </div>

      {/* One transmission tall: the latest stays in view, earlier ones scroll. */}
      <div ref={scroller} onScroll={onScroll} className="relative mt-2.5 h-[96px] shrink-0 overflow-y-auto overscroll-contain pr-1" tabIndex={0} aria-label="Transcript so far">
        {shown.length === 0 ? (
          <div className="flex h-full items-center justify-center gap-3 text-[14px] text-ink-2">
            <AudioLines aria-hidden className="size-5 shrink-0 text-ink-3" />
            {next ? (cursor === 0 && !playing ? 'Press play to start.' : `Next transmission at ${formatClock(next.start_ms)}`) : 'No speech in this part of the recording.'}
            {canSkip && (
              <Button size="xs" variant="secondary" onClick={skip}>
                <FastForward /> Skip to {formatClock(next!.start_ms)}
              </Button>
            )}
          </div>
        ) : (
          <ol className="space-y-2.5">
            {shown.map((seg, i) => {
              const prev = shown[i - 1];
              const newRecording = multi && (!prev || seg.recording !== prev.recording);
              const rec = recordingName(seg.recording);
              const gap = prev && gaps.find((g) => g.start >= prev.end_ms && g.end <= seg.start_ms + 500);
              return (
                <Fragment key={seg.key}>
                  {gap && <GapRow start={gap.start} end={gap.end} />}
                  {newRecording && rec && (
                    <li aria-hidden className="flex items-center gap-2 pt-1 text-[11.5px] font-medium text-ink-3">
                      <span className="h-px flex-1 bg-hairline" />
                      {rec.name} · {clockOf(rec.recorded_at)}
                      <span className="h-px flex-1 bg-hairline" />
                    </li>
                  )}
                  <li>
                    <SegmentRow seg={seg} cursor={cursor} onSeek={() => seek(seg.start_ms)} href={transcriptHref(seg.segment_id)} />
                  </li>
                </Fragment>
              );
            })}
            {gaps
              .filter((g) => cursor >= g.start && !shown.some((s) => s.start_ms + 500 >= g.end))
              .map((g) => (
                <GapRow key={g.start} start={g.start} end={g.end} />
              ))}
          </ol>
        )}
        {!stick && shown.length > 0 && (
          <button type="button" onClick={() => setStick(true)} className="sticky bottom-1 left-full mt-2 rounded-full bg-data px-3 py-1 text-[12.5px] font-medium text-white shadow-pop">
            Jump to latest
          </button>
        )}
      </div>
      <p className="sr-only" aria-live="polite">
        {announce ? `${announce.speaker}: ${announce.words.map((w) => w.text).join(' ')}` : ''}
      </p>
      <p className="mt-2 truncate text-[11.5px] text-ink-3" title={media.attribution}>
        {media.attribution}
      </p>
    </Card>
  );
}

function GapRow({ start, end }: { start: number; end: number }) {
  return (
    <li className="flex items-center gap-2 rounded-[12px] border border-dashed border-hairline-strong px-3 py-2 text-[12.5px] text-ink-2">
      <span className="size-1.5 shrink-0 rounded-full bg-ink-3" aria-hidden />
      Not recorded · {formatClock(start)}–{formatClock(end)}
    </li>
  );
}

function SegmentRow({ seg, cursor, onSeek, href }: { seg: DemoLiveSegment; cursor: number; onSeek: () => void; href: string }) {
  const phase = phaseOf(seg, cursor);
  const words = phase === 'FINAL' ? seg.words : revealedWords(seg, cursor);
  const active = cursor >= seg.start_ms && cursor < seg.end_ms;
  const role = speakerShown(seg, cursor);
  const atc = /ATC/.test(seg.speaker);
  return (
    <div className={cn('group rounded-[14px] px-3 py-2 transition-colors', active ? 'bg-data-tint/70' : 'hover:bg-sunken')}>
      <div className="flex min-h-5 items-center gap-2 text-[12.5px]">
        <button type="button" onClick={onSeek} className="font-medium tabular text-data hover:underline" aria-label={`Play from ${formatClock(seg.start_ms)}`}>
          {formatClock(seg.start_ms)}
        </button>
        {role && <span className={cn('font-medium animate-in fade-in duration-300', atc ? 'text-ink' : 'text-ink-2')}>{seg.speaker}</span>}
        <span className="ml-auto flex items-center gap-1.5 text-ink-3">
          {phase === 'FINAL' ? (
            <>
              {seg.confidence != null && <span className="tabular">conf {seg.confidence.toFixed(2)}</span>}
              <Link to={href} className="inline-flex items-center gap-1 opacity-0 transition-opacity hover:text-data group-hover:opacity-100 focus-visible:opacity-100" aria-label={`Open ${seg.key} in Review`}>
                <MessageSquareText aria-hidden className="size-3.5" /> {seg.key}
              </Link>
            </>
          ) : (
            <span className="inline-flex items-center gap-1 text-data-strong">
              <Loader2 aria-hidden className="size-3 animate-spin" /> {phase === 'LISTENING' ? 'Listening' : 'Recognising'}
            </span>
          )}
        </span>
      </div>
      <p className={cn('mt-0.5 text-[14.5px] leading-snug', phase === 'FINAL' ? 'text-ink' : 'text-ink-2 italic')}>
        {words.map((w) => w.text).join(' ')}
        {phase !== 'FINAL' && <span aria-hidden className="ml-0.5 inline-block h-[1em] w-[2px] animate-pulse bg-data align-[-2px]" />}
      </p>
    </div>
  );
}

/**
 * Keeps the finding IDs that became available while watching, for a short "New"
 * highlight. `ids` is null until the first answer, so findings already visible on
 * load are never flagged.
 */
export function useRecentlyAvailable(ids: string[] | null, holdMs = 5000) {
  const [recent, setRecent] = useState<Set<string>>(new Set());
  const seen = useRef<Set<string> | null>(null);
  const key = ids == null ? null : ids.join('|');
  useEffect(() => {
    if (key == null) return;
    const now = new Set(key ? key.split('|') : []);
    if (seen.current == null) {
      seen.current = now;
      return;
    }
    const fresh = [...now].filter((id) => !seen.current!.has(id));
    seen.current = now;
    if (!fresh.length) return;
    setRecent((r) => new Set([...r, ...fresh]));
    const t = setTimeout(() => setRecent((r) => new Set([...r].filter((id) => !fresh.includes(id)))), holdMs);
    return () => clearTimeout(t);
  }, [key, holdMs]);
  return recent;
}
