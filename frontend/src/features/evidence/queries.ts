import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { qk } from '@/api/queryKeys';
import type { ReviewDecision } from '@/api/types';
import { useApi } from '@/hooks/useApi';
import { useSessionScope } from '@/hooks/useSessionScope';
import { idemKey, releaseKeys } from '@/lib/idempotency';

export function useEvidenceBundle(id: string | null) {
  const api = useApi();
  const { sid, runId, mode, asOf, scope } = useSessionScope();
  return useQuery({
    queryKey: qk.evidence(sid, runId ?? '-', id ?? '-', mode, asOf),
    queryFn: () => api.getEvidence(scope!, id!, { asOfMs: asOf, mode }),
    enabled: !!scope && !!id,
    placeholderData: keepPreviousData,
  });
}

/** Append-only finding review. Never retried automatically; keeps the same key for identical payloads. */
export function useReviewFinding(findingId: string) {
  const api = useApi();
  const qc = useQueryClient();
  const { scope, sid, runId } = useSessionScope();
  return useMutation({
    mutationFn: (input: { decision: Extract<ReviewDecision, 'CONFIRMED' | 'DISMISSED' | 'UNRESOLVED'>; reason: string; expectedVersion?: number }) =>
      api.reviewFinding(scope!, findingId, { decision: input.decision, reason: input.reason }, { idempotencyKey: idemKey(`finding-review:${findingId}`, input), expectedVersion: input.expectedVersion }),
    onSuccess: () => {
      releaseKeys(`finding-review:${findingId}`);
    },
    onSettled: () => {
      if (runId) qc.invalidateQueries({ queryKey: qk.scoped(sid, runId) });
      qc.invalidateQueries({ queryKey: qk.notifications });
    },
  });
}
