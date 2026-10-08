import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { create } from 'zustand';
import type { ConnectionState } from '@/api/client';
import type { PlaybackState } from '@/api/types';
import { qk } from '@/api/queryKeys';
import { useReplay } from '@/features/replay/store';
import { useStreamClient } from './useApi';

interface StreamState {
  connection: ConnectionState;
  lastSequence: number;
  leaderCursor: number | null;
  leaderName: string;
  set: (p: Partial<StreamState>) => void;
}

export const useStreamState = create<StreamState>((set) => ({ connection: 'CONNECTED', lastSequence: 0, leaderCursor: null, leaderName: 'Dana Whitfield', set: (p) => set(p) }));

/**
 * Subscribes to the session stream. Events are applied in sequence order; duplicates
 * and gaps are ignored and recovered via snapshot (RESYNC_REQUIRED) so state is never doubled.
 */
export function useSessionStream(sessionId: string | undefined) {
  const stream = useStreamClient();
  const qc = useQueryClient();
  useEffect(() => {
    if (!sessionId) return;
    let last = 0;
    const set = useStreamState.getState().set;
    const unsubscribe = stream.subscribe(
      sessionId,
      (event) => {
        if (event.sequence <= last) return; // duplicate or replayed event
        const gap = last > 0 && event.sequence > last + 1 && event.type !== 'RESYNC_REQUIRED';
        last = event.sequence;
        set({ lastSequence: event.sequence });
        if (gap) {
          qc.invalidateQueries({ queryKey: qk.session(sessionId) });
          return;
        }
        switch (event.type) {
          case 'PLAYBACK_CHANGED': {
            const p = event.payload as PlaybackState;
            set({ leaderCursor: p.cursor_ms });
            const replay = useReplay.getState();
            if (replay.view === 'FOLLOW' && replay.sessionId === sessionId) useReplay.setState({ cursor: Math.min(p.cursor_ms, replay.duration), status: 'PLAYING' });
            break;
          }
          case 'JOB_PROGRESS':
            qc.invalidateQueries({ queryKey: qk.session(sessionId), exact: true });
            qc.invalidateQueries({ queryKey: qk.sessions });
            break;
          case 'RESYNC_REQUIRED':
            qc.invalidateQueries({ queryKey: qk.session(sessionId) });
            break;
          default:
            qc.invalidateQueries({ queryKey: qk.session(sessionId) });
        }
      },
      (connection, seq) => {
        set({ connection, lastSequence: seq });
        if (connection === 'CONNECTED') last = Math.max(last, seq);
      },
    );
    return unsubscribe;
  }, [sessionId, stream, qc]);
  return useStreamState((s) => s.connection);
}

export function useConnected() {
  return useStreamState((s) => s.connection === 'CONNECTED');
}
