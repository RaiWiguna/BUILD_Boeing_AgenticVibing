import { useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useRef } from 'react';
import { useParams, useSearchParams } from 'react-router';
import { qk } from '@/api/queryKeys';
import type { ReplayMode } from '@/api/types';
import { useReplay, useQueryAsOf } from '@/features/replay/store';
import { useApi } from './useApi';

const LAST_SESSION_KEY = 'flowlens.lastSession';

export function rememberSession(id: string) {
  try {
    localStorage.setItem(LAST_SESSION_KEY, id);
  } catch {
    /* preference only */
  }
}

export function lastSession() {
  try {
    return localStorage.getItem(LAST_SESSION_KEY);
  } catch {
    return null;
  }
}

/**
 * Session-scoped context shared by Workspace / Review / Debrief:
 * session + explicit run (never silently switched) + mode + as-of, all in the URL.
 */
export function useSessionScope() {
  const api = useApi();
  const { sid = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const session = useQuery({ queryKey: qk.session(sid), queryFn: () => api.getSession(sid), enabled: !!sid });
  const detail = session.data;
  const runParam = params.get('run');
  const runId = runParam ?? detail?.latest_run_id ?? null;
  const run = detail?.runs.find((r) => r.run.id === runId) ?? null;
  const latestRunId = detail?.latest_run_id ?? null;
  const mode: ReplayMode = params.get('mode') === 'debrief' ? 'DEBRIEF' : 'AS_KNOWN';
  const init = useReplay((s) => s.init);
  const asOf = useQueryAsOf();
  const cursor = useReplay((s) => s.cursor);
  const status = useReplay((s) => s.status);

  const tParam = params.get('t');
  useEffect(() => {
    if (!detail) return;
    rememberSession(detail.id);
    init(detail.id, detail.duration_ms, tParam != null ? Number(tParam) : detail.default_as_of_ms);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail?.id, detail?.duration_ms]);

  // Persist the replay position in the URL when paused (not every frame).
  const lastWritten = useRef<number | null>(null);
  useEffect(() => {
    if (!detail || status === 'PLAYING') return;
    const t = Math.round(cursor);
    if (lastWritten.current === t || String(t) === tParam) return;
    lastWritten.current = t;
    setParams(
      (p) => {
        const next = new URLSearchParams(p);
        next.set('t', String(t));
        return next;
      },
      { replace: true },
    );
  }, [cursor, status, detail, setParams, tParam]);

  const setParam = useCallback(
    (key: string, value: string | null) =>
      setParams((p) => {
        const next = new URLSearchParams(p);
        if (value == null) next.delete(key);
        else next.set(key, value);
        return next;
      }),
    [setParams],
  );

  return {
    sid,
    session,
    detail,
    runId,
    run,
    latestRunId,
    isLatestRun: !!runId && runId === latestRunId,
    mode,
    asOf,
    archived: detail?.lifecycle === 'ARCHIVED',
    setMode: (m: ReplayMode) => setParam('mode', m === 'DEBRIEF' ? 'debrief' : null),
    setRun: (id: string) => setParam('run', id),
    label: (id: string) => detail?.labels[id] ?? '—',
    scope: runId ? { sessionId: sid, runId } : null,
    search: params.toString(),
    /** Scope params carried across session screens (run · mode · t) — never evidence/selection. */
    carry: carryParams(params),
  };
}

export function carryParams(params: URLSearchParams) {
  const out = new URLSearchParams();
  for (const k of ['run', 'mode', 't']) {
    const v = params.get(k);
    if (v != null) out.set(k, v);
  }
  return out.toString();
}
