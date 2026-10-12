import { useEffect } from 'react';
import { create } from 'zustand';

export type ReplayStatus = 'PAUSED' | 'PLAYING' | 'ENDED';
export type ReplayView = 'LOCAL' | 'FOLLOW';
export const SPEEDS = [0.5, 1, 2] as const;
export type Speed = (typeof SPEEDS)[number];

interface ReplayState {
  sessionId: string | null;
  cursor: number;
  duration: number;
  status: ReplayStatus;
  speed: Speed;
  view: ReplayView;
  /** Evidence range highlighted on the timeline (not a selection of truth). */
  range: { start: number; end: number } | null;
  /** Pause automatically when the cursor reaches this time (listen to an evidence range). */
  stopAt: number | null;
  playRange: (r: { start: number; end: number }) => void;
  setRange: (r: { start: number; end: number } | null) => void;
  init: (sessionId: string, duration: number, cursor: number) => void;
  play: () => void;
  pause: () => void;
  toggle: () => void;
  seek: (ms: number) => void;
  setSpeed: (s: Speed) => void;
  setView: (v: ReplayView) => void;
  tick: (dtMs: number) => void;
}

/**
 * Local replay clock. MOCK sessions replay visually (no audio, decision D-3); DEMO
 * workspaces (ADR 0003) drive it from a real audio element (see audio.tsx).
 * Seeking never triggers analysis; queries read the bucketed as-of.
 */
export const useReplay = create<ReplayState>((set, get) => ({
  sessionId: null,
  cursor: 0,
  duration: 0,
  status: 'PAUSED',
  speed: 1,
  view: 'LOCAL',
  range: null,
  stopAt: null,
  playRange: (r) => {
    get().setRange(r);
    const { duration } = get();
    const start = Math.max(0, Math.min(r.start, duration));
    set({ cursor: start, status: 'PLAYING', view: 'LOCAL', stopAt: Math.min(duration, Math.max(r.end, start + 500)) });
  },
  setRange: (r) => {
    if (!r) return set({ range: null });
    const { duration } = get();
    const start = Math.max(0, Math.min(r.start, r.end));
    const end = Math.min(duration, Math.max(r.start, r.end));
    set({ range: end - start < 200 ? null : { start, end } });
  },
  init: (sessionId, duration, cursor) => {
    if (get().sessionId === sessionId && get().duration === duration) return;
    set({ sessionId, duration, cursor: Math.min(Math.max(0, cursor), duration), status: 'PAUSED', view: 'LOCAL', range: null, stopAt: null });
  },
  play: () => {
    const { cursor, duration } = get();
    set({ status: 'PLAYING', cursor: cursor >= duration ? 0 : cursor, view: get().view });
  },
  pause: () => set({ status: 'PAUSED', stopAt: null }),
  toggle: () => (get().status === 'PLAYING' ? get().pause() : get().play()),
  seek: (ms) => {
    const { duration, status } = get();
    const cursor = Math.min(Math.max(0, Math.round(ms)), duration);
    set({ cursor, status: status === 'ENDED' && cursor < duration ? 'PAUSED' : status, view: 'LOCAL', stopAt: null });
  },
  setSpeed: (speed) => set({ speed }),
  setView: (view) => set({ view }),
  tick: (dt) => {
    const { cursor, duration, speed, status, stopAt } = get();
    if (status !== 'PLAYING') return;
    const next = cursor + dt * speed;
    if (stopAt != null && next >= stopAt) set({ cursor: stopAt, status: 'PAUSED', stopAt: null });
    else if (next >= duration) set({ cursor: duration, status: 'ENDED' });
    else set({ cursor: next });
  },
}));

/** Cursor used for server queries: 1 s steps while playing, exact when paused. */
export function useQueryAsOf() {
  return useReplay((s) => (s.status === 'PLAYING' ? Math.floor(s.cursor / 1000) * 1000 : Math.round(s.cursor)));
}

/** Drives the local replay clock with requestAnimationFrame while playing (in FOLLOW view the stream re-anchors it every second). */
export function useReplayDriver(enabled = true) {
  const status = useReplay((s) => s.status);
  useEffect(() => {
    if (!enabled || status !== 'PLAYING') return;
    let raf = 0;
    let last = performance.now();
    const update = () => {
      const now = performance.now();
      const dt = now - last;
      if (dt < 8) return;
      last = now;
      useReplay.getState().tick(Math.min(1000, dt));
    };
    const loop = () => {
      update();
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    // rAF is throttled in background panes; the interval keeps the clock honest.
    const iv = setInterval(update, 100);
    return () => {
      cancelAnimationFrame(raf);
      clearInterval(iv);
    };
  }, [status, enabled]);
}
