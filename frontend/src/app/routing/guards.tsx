import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';
import type { Capability } from '@/api/types';
import { AccessDenied } from '@/components/domain/states';
import { Card } from '@/components/domain/primitives';
import { useAuth } from '@/app/providers/AuthProvider';
import { LogoMark } from '@/components/layout/Logo';

export function FullPageLoader() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-canvas" aria-busy="true" aria-label="Loading">
      <LogoMark className="size-11 animate-pulse" />
    </div>
  );
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth();
  const location = useLocation();
  if (loading) return <FullPageLoader />;
  if (!session) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  return <>{children}</>;
}

/** UI gate only — the server (mock adapter) enforces the same capability on every request. */
export function RequireCapability({ cap, children, title }: { cap: Capability; children: ReactNode; title?: string }) {
  const { can } = useAuth();
  if (!can(cap)) {
    return (
      <Card className="mx-auto mt-10 max-w-xl">
        <AccessDenied title={title ?? 'Access restricted'} message={`Your role does not include ${cap}. Content is not loaded.`} recovery="Ask an administrator for a grant that includes this capability." />
      </Card>
    );
  }
  return <>{children}</>;
}

/** Relative redirect that keeps the query string (run · mode · t survive index redirects). */
export function RedirectKeepSearch({ to }: { to: string }) {
  const { search } = useLocation();
  return <Navigate to={`${to}${search}`} replace />;
}

/** /settings → admins land on Users, everyone else on Account. */
export function SettingsIndex() {
  const { can } = useAuth();
  return <Navigate to={can('admin.manage') ? '/settings/users' : '/settings/account'} replace />;
}
