/**
 * MOCK session stream: typed StreamEvent envelopes with monotonically increasing
 * sequence numbers, a simulated playback leader, and connection loss / resync.
 */
import type { ConnectionState, StreamClient } from '../../client';
import type { PlaybackState, StreamEvent, StreamEventType } from '../../types';
import { mockControl } from './control';

type Listener = { onEvent: (e: StreamEvent) => void; onState: (s: ConnectionState, seq: number) => void };

const LEADER_START_MS = 312_000; // 05:12

export class MockStream implements StreamClient {
  private listeners = new Map<string, Set<Listener>>();
  private sequence = new Map<string, number>();
  private state: ConnectionState = 'CONNECTED';
  private leader = new Map<string, { cursor: number; startedAt: number; speed: number }>();
  private timer: ReturnType<typeof setInterval> | null = null;
  private runIdFor: (sessionId: string) => string | null;
  private leaderIdFor: () => string | null;

  constructor(runIdFor: (sessionId: string) => string | null, leaderIdFor: () => string | null) {
    this.runIdFor = runIdFor;
    this.leaderIdFor = leaderIdFor;
    let wasLost = mockControl.getState().connectionLost;
    mockControl.subscribe((s) => {
      if (s.connectionLost === wasLost) return;
      wasLost = s.connectionLost;
      if (s.connectionLost) this.setState('RECONNECTING');
      else this.resync();
    });
  }

  subscribe(sessionId: string, onEvent: (event: StreamEvent) => void, onState: (state: ConnectionState, lastSequence: number) => void) {
    const set = this.listeners.get(sessionId) ?? new Set<Listener>();
    const listener = { onEvent, onState };
    set.add(listener);
    this.listeners.set(sessionId, set);
    onState(mockControl.getState().connectionLost ? 'RECONNECTING' : this.state, this.sequence.get(sessionId) ?? 0);
    if (!this.leader.has(sessionId)) this.leader.set(sessionId, { cursor: LEADER_START_MS, startedAt: Date.now(), speed: 1 });
    this.ensureTimer();
    return () => {
      set.delete(listener);
      if (!set.size) this.listeners.delete(sessionId);
      if (!this.listeners.size && this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }
    };
  }

  emit(sessionId: string, type: StreamEventType, payload: StreamEvent['payload']) {
    if (mockControl.getState().connectionLost) return; // events during loss are recovered by resync
    const seq = (this.sequence.get(sessionId) ?? 0) + 1;
    this.sequence.set(sessionId, seq);
    const event: StreamEvent = {
      session_id: sessionId,
      analysis_run_id: this.runIdFor(sessionId),
      sequence: seq,
      type,
      recorded_at: new Date().toISOString(),
      payload,
    };
    this.listeners.get(sessionId)?.forEach((l) => l.onEvent(event));
  }

  leaderCursor(sessionId: string) {
    const l = this.leader.get(sessionId);
    if (!l) return LEADER_START_MS;
    return l.cursor + (Date.now() - l.startedAt) * l.speed;
  }

  private ensureTimer() {
    if (this.timer) return;
    this.timer = setInterval(() => {
      for (const sessionId of this.listeners.keys()) {
        const payload: PlaybackState = {
          session_id: sessionId,
          analysis_run_id: this.runIdFor(sessionId),
          revision: 1,
          cursor_ms: Math.round(this.leaderCursor(sessionId)),
          leader_id: this.leaderIdFor(),
          speed: 1,
          status: 'PLAYING',
          view: 'LEADER',
        };
        this.emit(sessionId, 'PLAYBACK_CHANGED', payload);
      }
    }, 1000);
  }

  private setState(state: ConnectionState) {
    this.state = state;
    this.listeners.forEach((set, sessionId) => set.forEach((l) => l.onState(state, this.sequence.get(sessionId) ?? 0)));
  }

  private resync() {
    this.setState('RESYNCING');
    setTimeout(() => {
      this.listeners.forEach((_set, sessionId) => {
        // Events missed during the outage are recovered through a fresh snapshot.
        const seq = (this.sequence.get(sessionId) ?? 0) + 3;
        this.sequence.set(sessionId, seq - 1);
        this.emit(sessionId, 'RESYNC_REQUIRED', {
          session_id: sessionId,
          analysis_run_id: this.runIdFor(sessionId),
          revision: 1,
          reason: 'SEQUENCE_GAP',
          snapshot_sequence: seq,
        });
      });
      this.setState('CONNECTED');
    }, 900);
  }
}
