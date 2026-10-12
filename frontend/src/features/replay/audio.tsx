/**
 * DEMO track (ADR 0003): real audio playback as the replay master clock.
 *
 * The replay store stays the single source of truth for the UI. This engine mirrors
 * store intent onto the recordings' <audio> elements (play / pause / seek / speed)
 * and writes the playing element's time back as the cursor. Seeks are told apart
 * from our own writes by remembering the last cursor we wrote.
 */
import { useEffect, useMemo, useRef } from 'react';
import { create } from 'zustand';
import { toast } from 'sonner';
import type { DemoMedia, DemoRecording } from '@/api/types';
import { useDemo } from '@/hooks/useApi';
import { useReplay } from './store';

interface AudioState {
  /** True while a DEMO workspace with playable audio is open. */
  available: boolean;
  buffering: boolean;
  failed: boolean;
  volume: number;
  muted: boolean;
  labels: string[];
  setVolume: (v: number) => void;
  toggleMute: () => void;
}

const VOLUME_KEY = 'flowlens.demo.volume';

function storedVolume() {
  try {
    const v = Number(localStorage.getItem(VOLUME_KEY));
    return Number.isFinite(v) && v > 0 && v <= 1 ? v : 0.9;
  } catch {
    return 0.9;
  }
}

export const useAudio = create<AudioState>((set) => ({
  available: false,
  buffering: false,
  failed: false,
  volume: storedVolume(),
  muted: false,
  labels: [],
  setVolume: (volume) => {
    set({ volume, muted: volume === 0 });
    try {
      localStorage.setItem(VOLUME_KEY, String(volume));
    } catch {
      /* preference only */
    }
  },
  toggleMute: () => set((s) => ({ muted: !s.muted })),
}));

type ReplayState = ReturnType<typeof useReplay.getState>;

function applyVolume(els: (HTMLAudioElement | null)[], volume: number, muted: boolean) {
  for (const el of els) {
    if (!el) continue;
    el.volume = volume;
    el.muted = muted;
  }
}

/** Session time inside a recording (ms before its end, so the last frame never re-triggers it). */
function recordingAt(recs: DemoRecording[], ms: number) {
  return recs.findIndex((r) => ms >= r.offset_ms && ms < r.offset_ms + r.duration_ms - 40);
}

/**
 * Renders nothing visible; owns one audio element per recording of the open DEMO
 * workspace. The element of the recording under the cursor drives the clock; between
 * recordings (not recorded) the cursor advances with wall time, silently.
 */
export function AudioEngine({ media, sessionId }: { media: DemoMedia; sessionId: string }) {
  const demo = useDemo();
  const refs = useRef<(HTMLAudioElement | null)[]>([]);
  const recs = useMemo<DemoRecording[]>(
    () => (media.recordings.length ? media.recordings : [{ part: 'main', name: '', url: media.audio_url, offset_ms: 0, duration_ms: Number.MAX_SAFE_INTEGER, recorded_at: '' }]),
    [media.recordings, media.audio_url],
  );

  useEffect(() => {
    const els = recs.map((_, i) => refs.current[i]).filter((el): el is HTMLAudioElement => !!el);
    if (els.length !== recs.length) return;
    useAudio.setState({ available: true, failed: false, buffering: false });
    let written = useReplay.getState().cursor;
    let raf = 0;
    // Only save positions this engine produced (an unchanged cursor must not overwrite the server's).
    let lastSaved = Math.round(written);
    let active = -1;
    let starting = false;
    let lastTick = performance.now();

    const save = () => {
      const ms = Math.round(useReplay.getState().cursor);
      if (useReplay.getState().sessionId !== sessionId || ms === lastSaved) return;
      lastSaved = ms;
      demo.rememberPlayback(sessionId, ms);
      demo.savePlayback(media.workspace_id, ms).catch(() => undefined);
    };

    const write = (ms: number, extra: Partial<ReplayState> = {}) => {
      written = ms;
      useReplay.setState({ cursor: ms, ...extra });
    };

    const stopAll = (except = -1) => {
      els.forEach((el, i) => {
        if (i !== except && !el.paused) el.pause();
      });
      if (except < 0) {
        active = -1;
        starting = false;
      }
    };

    /** Position element i on session time `ms` (cheap when it is already there). */
    const cue = (i: number, ms: number) => {
      const local = Math.max(0, (ms - recs[i]!.offset_ms) / 1000);
      if (Math.abs(els[i]!.currentTime - local) > 0.12) els[i]!.currentTime = local;
    };

    const engage = (i: number, ms: number, st: ReplayState) => {
      stopAll(i);
      const el = els[i]!;
      cue(i, ms);
      el.playbackRate = st.speed;
      active = i;
      starting = true;
      el.play()
        .then(() => {
          starting = false;
        })
        .catch((e: unknown) => {
          starting = false;
          if ((e as { name?: string })?.name === 'AbortError') return;
          stopAll();
          useReplay.setState({ status: 'PAUSED', stopAt: null });
          toast.error('Audio could not start', { description: 'Press play again.' });
        });
    };

    const loop = (now: number) => {
      const dt = now - lastTick;
      lastTick = now;
      const st = useReplay.getState();
      if (st.sessionId === sessionId && st.status === 'PLAYING') {
        const el = active >= 0 ? els[active]! : null;
        let ms: number;
        if (el && starting) ms = written;
        else if (el && !el.paused) ms = recs[active]!.offset_ms + el.currentTime * 1000;
        else ms = written + Math.min(dt, 250) * st.speed;
        if (el && !starting && (el.ended || ms >= recs[active]!.offset_ms + recs[active]!.duration_ms - 40)) {
          if (!el.paused) el.pause();
          active = -1;
        }
        const i = recordingAt(recs, ms);
        if (i >= 0 && i !== active) engage(i, ms, st);
        if (st.stopAt != null && ms >= st.stopAt) {
          stopAll();
          write(st.stopAt, { status: 'PAUSED', stopAt: null });
          save();
        } else if (ms >= st.duration) {
          stopAll();
          write(st.duration, { status: 'ENDED', stopAt: null });
          save();
        } else write(ms);
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);

    const apply = (st: ReplayState, prev: ReplayState) => {
      if (st.sessionId !== sessionId) return;
      if (st.cursor !== written) {
        // External seek (timeline, shortcuts, transcript click, evidence range).
        written = st.cursor;
        const i = recordingAt(recs, st.cursor);
        if (i !== active) stopAll();
        if (i >= 0) cue(i, st.cursor);
      }
      if (st.speed !== prev.speed) els.forEach((el) => (el.playbackRate = st.speed));
      if (st.status === 'PLAYING' && prev.status !== 'PLAYING') {
        if (st.cursor >= st.duration - 50) write(0);
        lastTick = performance.now();
        const i = recordingAt(recs, written);
        if (i >= 0) engage(i, written, st);
      } else if (st.status !== 'PLAYING' && prev.status === 'PLAYING') {
        stopAll();
        save();
      }
    };
    const unsub = useReplay.subscribe(apply);

    // Initial position (saved playback cursor or ?t=).
    const cleanups = els.map((el, i) => {
      const onMeta = () => {
        const st = useReplay.getState();
        if (st.sessionId === sessionId && recordingAt(recs, st.cursor) === i) cue(i, st.cursor);
      };
      const onWaiting = () => i === active && useAudio.setState({ buffering: true });
      const onPlaying = () => useAudio.setState({ buffering: false });
      const onError = () => {
        useAudio.setState({ failed: true, buffering: false });
        stopAll();
        useReplay.setState({ status: 'PAUSED', stopAt: null });
      };
      if (el.readyState >= 1) onMeta();
      el.addEventListener('loadedmetadata', onMeta);
      el.addEventListener('waiting', onWaiting);
      el.addEventListener('playing', onPlaying);
      el.addEventListener('canplay', onPlaying);
      el.addEventListener('error', onError);
      return () => {
        el.removeEventListener('loadedmetadata', onMeta);
        el.removeEventListener('waiting', onWaiting);
        el.removeEventListener('playing', onPlaying);
        el.removeEventListener('canplay', onPlaying);
        el.removeEventListener('error', onError);
      };
    });
    const onHide = () => document.visibilityState === 'hidden' && save();
    document.addEventListener('visibilitychange', onHide);
    window.addEventListener('pagehide', save);

    return () => {
      cancelAnimationFrame(raf);
      unsub();
      save();
      stopAll();
      cleanups.forEach((c) => c());
      document.removeEventListener('visibilitychange', onHide);
      window.removeEventListener('pagehide', save);
      useAudio.setState({ available: false, buffering: false, failed: false, labels: [] });
      if (useReplay.getState().status === 'PLAYING') useReplay.setState({ status: 'PAUSED', stopAt: null });
    };
  }, [media.workspace_id, sessionId, demo, recs]);

  useEffect(() => useAudio.setState({ labels: media.labels }), [media.labels]);

  const volume = useAudio((s) => s.volume);
  const muted = useAudio((s) => s.muted);
  useEffect(() => applyVolume(refs.current, volume, muted), [volume, muted, recs]);

  return (
    <>
      {recs.map((r, i) => (
        <audio
          key={`${r.part}:${r.url}`}
          ref={(el) => {
            refs.current[i] = el;
          }}
          src={r.url}
          preload="auto"
          className="hidden"
          aria-hidden
        />
      ))}
    </>
  );
}
