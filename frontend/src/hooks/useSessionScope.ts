import { useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useRef } from 'react';
import { useLocation, useParams, useSearchParams } from 'react-router';
import { qk } from '@/api/queryKeys';
import type { ReplayMode } from '@/api/types';
import { useReplay, useQueryAsOf } from '@/features/replay/store';
import { areaFromPath, lensAreaOf, parseLens, scopeFromParams, sessionHref, type LinkFocus, type SessionArea } from '@/lib/links';
import { useApi } from './useApi';

const LAST_SESSION_KEY = 'flowlens.lastSession';

export function rememberSession(id: string) {
  try {
    localStorage.setItem(LAST_SESSION_KEY, id);
  } catch {
    /* preference only */
  }
}

const LAST_AREA_KEY = 'flowlens.lastArea';

/** Area last opened in the remembered session, for the Sessions "Continue" card. */
export function lastArea(): SessionArea {
  try {
    return (localStorage.getItem(LAST_AREA_KEY) as SessionArea | null) ?? 'workspace';
  } catch {
    return 'workspace';
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
 * session + explicit run (never silently switched) + lens + as-of, all in the URL.
 *
 * Lens (decision D-1): `mode=debrief|as-known` when the user chose one; otherwise the
 * area default — Workspace/Memory replay As-known at the cursor, Review/Debrief/Ask/
 * Metrics read the full session (Debrief at the session end). The replay cursor `t`
 * is kept separately and only drives the as-of in As-known or on replay screens.
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
  const { pathname } = useLocation();
  const lensArea = lensAreaOf(pathname);
  const lensParam = parseLens(params.get('mode'));
  const mode: ReplayMode = lensParam === 'debrief' ? 'DEBRIEF' : lensParam === 'as-known' ? 'AS_KNOWN' : lensArea === 'analysis' ? 'DEBRIEF' : 'AS_KNOWN';
  /** Analysis screens in Debrief read everything up to the session end. */
  const fullSession = lensArea === 'analysis' && mode === 'DEBRIEF';
  const init = useReplay((s) => s.init);
  const replayAsOf = useQueryAsOf();
  const asOf = fullSession && detail ? detail.duration_ms : replayAsOf;
  const cursor = useReplay((s) => s.cursor);
  const status = useReplay((s) => s.status);

  const area = areaFromPath(pathname);
  useEffect(() => {
    if (!sid) return;
    try {
      localStorage.setItem(LAST_AREA_KEY, area);
    } catch {
      /* preference only */
    }
  }, [sid, area]);

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
    /** Replay cursor (bucketed) — differs from `asOf` when the full session is shown. */
    replayAsOf,
    fullSession,
    lensArea,
    archived: detail?.lifecycle === 'ARCHIVED',
    /** An explicit lens choice is written to the URL and carried to other screens. */
    setMode: (m: ReplayMode) => setParam('mode', m === 'DEBRIEF' ? 'debrief' : 'as-known'),
    setRun: (id: string) => setParam('run', id),
    label: (id: string) => detail?.labels[id] ?? '—',
    scope: runId ? { sessionId: sid, runId } : null,
    search: params.toString(),
    /** Scope params carried across session screens (run · mode · t) — never evidence/selection. */
    carry: carryParams(params),
    /** Link to another session screen keeping run · lens · t (plus an optional focus). */
    href: (area: SessionArea, focus?: LinkFocus) => sessionHref(area, { sid, ...scopeFromParams(params), focus }),
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
