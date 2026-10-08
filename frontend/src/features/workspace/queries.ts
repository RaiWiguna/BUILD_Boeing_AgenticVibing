import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { useCallback } from 'react';
import { useSearchParams } from 'react-router';
import { qk } from '@/api/queryKeys';
import { useApi } from '@/hooks/useApi';
import { useSessionScope } from '@/hooks/useSessionScope';

/**
 * Projection queries scoped by session · run · mode · as-of bucket.
 * `keepPreviousData` keeps the last frame visible while the next as-of loads, so
 * playback never flashes an empty state (old frames are replaced, never merged).
 */
export function useSnapshot() {
  const api = useApi();
  const { sid, runId, mode, asOf, scope } = useSessionScope();
  return useQuery({
    queryKey: qk.snapshot(sid, runId ?? '-', mode, asOf),
    queryFn: () => api.getSnapshot(scope!, { asOfMs: asOf, mode }),
    enabled: !!scope,
    placeholderData: keepPreviousData,
  });
}

export function useFindings() {
  const api = useApi();
  const { sid, runId, mode, asOf, scope } = useSessionScope();
  return useQuery({
    queryKey: qk.findings(sid, runId ?? '-', mode, asOf),
    queryFn: () => api.listFindings(scope!, { asOfMs: asOf, mode }),
    enabled: !!scope,
    placeholderData: keepPreviousData,
  });
}

export function useEntityMemory(entityId: string | null) {
  const api = useApi();
  const { sid, runId, mode, asOf, scope } = useSessionScope();
  return useQuery({
    queryKey: qk.entityMemory(sid, runId ?? '-', entityId ?? '-', mode, asOf),
    queryFn: () => api.getEntityMemory(scope!, entityId!, { asOfMs: asOf, mode }),
    enabled: !!scope && !!entityId,
    placeholderData: keepPreviousData,
  });
}

export function useRunwayMemory(runwayId: string | null) {
  const api = useApi();
  const { sid, runId, mode, asOf, scope } = useSessionScope();
  return useQuery({
    queryKey: qk.runwayMemory(sid, runId ?? '-', runwayId ?? '-', mode, asOf),
    queryFn: () => api.getRunwayMemory(scope!, runwayId!, { asOfMs: asOf, mode }),
    enabled: !!scope && !!runwayId,
    placeholderData: keepPreviousData,
  });
}

export function useWaveforms() {
  const api = useApi();
  const { sid } = useSessionScope();
  return useQuery({ queryKey: qk.waveforms(sid), queryFn: () => api.getWaveforms(sid), enabled: !!sid, staleTime: Infinity });
}

/** Selected object is URL state (?selected=) so it survives reloads and deep links. */
export function useSelectedEntity() {
  const [params, setParams] = useSearchParams();
  const selected = params.get('selected');
  const select = useCallback(
    (id: string | null) =>
      setParams(
        (p) => {
          const next = new URLSearchParams(p);
          if (id) next.set('selected', id);
          else next.delete('selected');
          return next;
        },
        { replace: true },
      ),
    [setParams],
  );
  return [selected, select] as const;
}
