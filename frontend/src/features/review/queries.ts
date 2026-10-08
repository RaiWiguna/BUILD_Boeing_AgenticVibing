import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { qk } from '@/api/queryKeys';
import type { OptionReviewStatus } from '@/api/types';
import { useApi } from '@/hooks/useApi';
import { useSessionScope } from '@/hooks/useSessionScope';
import { idemKey, releaseKeys } from '@/lib/idempotency';

export function useTranscript() {
  const api = useApi();
  const { sid, runId, mode, asOf, scope } = useSessionScope();
  return useQuery({
    queryKey: qk.transcript(sid, runId ?? '-', mode, asOf),
    queryFn: () => api.getTranscript(scope!, { asOfMs: asOf, mode }),
    enabled: !!scope,
    placeholderData: keepPreviousData,
  });
}

export function useOptions() {
  const api = useApi();
  const { sid, runId, mode, asOf, scope } = useSessionScope();
  return useQuery({
    queryKey: qk.options(sid, runId ?? '-', mode, asOf),
    queryFn: () => api.listOptions(scope!, { asOfMs: asOf, mode }),
    enabled: !!scope,
    placeholderData: keepPreviousData,
  });
}

function useInvalidateScoped() {
  const qc = useQueryClient();
  const { sid, runId } = useSessionScope();
  return () => {
    if (runId) qc.invalidateQueries({ queryKey: qk.scoped(sid, runId) });
    qc.invalidateQueries({ queryKey: qk.session(sid), exact: true });
    qc.invalidateQueries({ queryKey: qk.notifications });
  };
}

export function useCorrectTranscript(segmentId: string) {
  const api = useApi();
  const { scope } = useSessionScope();
  const invalidate = useInvalidateScoped();
  return useMutation({
    mutationFn: (input: { text: string; reason: string; expectedVersion: number }) =>
      api.correctTranscript(scope!, segmentId, { text: input.text, reason: input.reason }, { idempotencyKey: idemKey(`transcript:${segmentId}`, input), expectedVersion: input.expectedVersion }),
    onSuccess: () => releaseKeys(`transcript:${segmentId}`),
    onSettled: invalidate,
  });
}

export function useReviewAssociation(segmentId: string) {
  const api = useApi();
  const { scope } = useSessionScope();
  const invalidate = useInvalidateScoped();
  return useMutation({
    mutationFn: (input: { targetId: string | null; reason: string }) => api.reviewAssociation(scope!, segmentId, input, { idempotencyKey: idemKey(`association:${segmentId}`, input) }),
    onSuccess: () => releaseKeys(`association:${segmentId}`),
    onSettled: invalidate,
  });
}

export function useReviewOption(optionId: string) {
  const api = useApi();
  const { scope } = useSessionScope();
  const invalidate = useInvalidateScoped();
  return useMutation({
    mutationFn: (input: { decision: Exclude<OptionReviewStatus, 'UNREVIEWED'>; reason: string }) => api.reviewOption(scope!, optionId, input, { idempotencyKey: idemKey(`option:${optionId}`, input) }),
    onSuccess: () => releaseKeys(`option:${optionId}`),
    onSettled: invalidate,
  });
}

export function useReanalyze() {
  const api = useApi();
  const qc = useQueryClient();
  const { scope, sid } = useSessionScope();
  return useMutation({
    mutationFn: () => api.reanalyze(scope!, { idempotencyKey: idemKey(`reanalyze:${sid}`, scope) }),
    onSuccess: () => releaseKeys(`reanalyze:${sid}`),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: qk.session(sid), exact: true });
      qc.invalidateQueries({ queryKey: qk.sessions });
    },
  });
}
