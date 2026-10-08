import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { qk } from '@/api/queryKeys';
import type { AuditEntry, Capability, JobView } from '@/api/types';
import { useApi } from '@/hooks/useApi';
import { idemKey, releaseKeys } from '@/lib/idempotency';

export const useAccounts = () => {
  const api = useApi();
  return useQuery({ queryKey: qk.admin.accounts, queryFn: () => api.listAccounts() });
};
export const useGrants = () => {
  const api = useApi();
  return useQuery({ queryKey: qk.admin.grants(), queryFn: () => api.listGrants() });
};
export const useProviders = () => {
  const api = useApi();
  return useQuery({ queryKey: qk.admin.providers, queryFn: () => api.listProviderProfiles() });
};
export const useJobs = () => {
  const api = useApi();
  return useQuery({
    queryKey: qk.admin.jobs,
    queryFn: () => api.listJobs(),
    refetchInterval: (q) => ((q.state.data as JobView[] | undefined)?.some((j) => ['QUEUED', 'LEASED', 'RUNNING'].includes(j.status)) ? 900 : false),
  });
};
export const useBudget = () => {
  const api = useApi();
  return useQuery({ queryKey: qk.admin.budget, queryFn: () => api.getBudget() });
};
export const useStorage = () => {
  const api = useApi();
  return useQuery({ queryKey: qk.admin.storage, queryFn: () => api.getStorage() });
};
export const useAudit = (query: string, result: AuditEntry['result'] | 'ALL') => {
  const api = useApi();
  return useQuery({ queryKey: qk.admin.audit(query, result), queryFn: () => api.listAudit({ query, result }) });
};
export const useRetention = () => {
  const api = useApi();
  return useQuery({ queryKey: qk.admin.retention, queryFn: () => api.listRetention() });
};
export const useSessionsList = () => {
  const api = useApi();
  return useQuery({ queryKey: qk.sessions, queryFn: () => api.listSessions() });
};

/** Admin mutation: idempotent, invalidates the given key plus the audit log. */
function useAdminMutation<I, O>(scope: string, fn: (input: I, key: string) => Promise<O>, invalidate: readonly unknown[][]) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: I) => fn(input, idemKey(scope, input)),
    onSuccess: () => releaseKeys(scope),
    onSettled: () => {
      invalidate.forEach((k) => qc.invalidateQueries({ queryKey: k }));
      qc.invalidateQueries({ queryKey: ['admin', 'audit'] });
    },
  });
}

export function useSetActive() {
  const api = useApi();
  return useAdminMutation('admin:active', (i: { id: string; active: boolean }, k) => api.setAccountActive(i.id, i.active, { idempotencyKey: k }), [[...qk.admin.accounts]]);
}
export function useResetPassword() {
  const api = useApi();
  return useAdminMutation('admin:reset', (id: string, k) => api.resetAccountPassword(id, { idempotencyKey: k }), [[...qk.admin.accounts]]);
}
export function useAddGrant() {
  const api = useApi();
  return useAdminMutation('admin:grant', (i: { sessionId: string; accountId: string; capabilities: Capability[] }, k) => api.addGrant(i, { idempotencyKey: k }), [['admin', 'grants']]);
}
export function useRevokeGrant() {
  const api = useApi();
  return useAdminMutation('admin:revoke', (id: string, k) => api.revokeGrant(id, { idempotencyKey: k }), [['admin', 'grants']]);
}
export function useCheckProvider() {
  const api = useApi();
  return useAdminMutation('admin:provider', (id: string, k) => api.checkProviderProfile(id, { idempotencyKey: k }), [[...qk.admin.providers]]);
}
export function useRetryJob() {
  const api = useApi();
  return useAdminMutation('admin:retry', (id: string, k) => api.retryJob(id, { idempotencyKey: k }), [[...qk.admin.jobs]]);
}
export function useCancelJob() {
  const api = useApi();
  return useAdminMutation('admin:cancel', (id: string, k) => api.cancelJob(id, { idempotencyKey: k }), [[...qk.admin.jobs]]);
}
export function useRequestPurge() {
  const api = useApi();
  return useAdminMutation('admin:purge', (i: { sessionId: string; reason: string }, k) => api.requestPurge(i.sessionId, i.reason, { idempotencyKey: k }), [[...qk.admin.retention]]);
}
