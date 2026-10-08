import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { createContext, useCallback, useContext, useMemo, type ReactNode } from 'react';
import type { AuthSession, Capability } from '@/api/types';
import { qk } from '@/api/queryKeys';
import { useApi } from '@/hooks/useApi';

interface AuthValue {
  session: AuthSession | null;
  loading: boolean;
  can: (cap: Capability) => boolean;
  login: (email: string, password: string) => Promise<AuthSession>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

/** Remove every cached query except the auth query itself (its observer must stay attached). */
function clearScoped(qc: QueryClient) {
  qc.cancelQueries({ predicate: (q) => q.queryKey[0] !== 'auth' });
  qc.removeQueries({ predicate: (q) => q.queryKey[0] !== 'auth' });
  qc.getMutationCache().clear();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const api = useApi();
  const qc = useQueryClient();
  const { data, isPending } = useQuery({ queryKey: qk.auth, queryFn: () => api.getAuthSession(), staleTime: 60_000 });
  const session = data ?? null;

  const login = useCallback(
    async (email: string, password: string) => {
      const next = await api.login(email, password);
      // Account/role switch: drop every scoped cache entry before showing new data.
      clearScoped(qc);
      qc.setQueryData(qk.auth, next);
      return next;
    },
    [api, qc],
  );

  const logout = useCallback(async () => {
    await api.logout();
    clearScoped(qc);
    qc.setQueryData(qk.auth, null);
  }, [api, qc]);

  const value = useMemo<AuthValue>(() => ({ session, loading: isPending, can: (cap) => !!session?.capabilities.includes(cap), login, logout }), [session, isPending, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('AuthContext missing');
  return ctx;
}
