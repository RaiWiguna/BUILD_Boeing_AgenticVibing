import { Activity, Archive, HardDrive, KeyRound, ScrollText, ServerCog, UserRound, Users } from 'lucide-react';
import type { ReactNode } from 'react';
import { NavLink, Outlet } from 'react-router';
import { useAuth } from '@/app/providers/AuthProvider';
import { AccessDenied } from '@/components/domain/states';
import { PageHeader } from '@/components/layout/PageHeader';
import { ROLE_LABEL } from '@/lib/roles';
import { cn } from '@/lib/utils';

const ADMIN_NAV = [
  { to: 'users', label: 'Users', icon: Users },
  { to: 'access', label: 'Session access', icon: KeyRound },
  { to: 'providers', label: 'Providers', icon: ServerCog },
  { to: 'jobs', label: 'Jobs & budget', icon: Activity },
  { to: 'storage', label: 'Storage', icon: HardDrive },
  { to: 'audit', label: 'Audit log', icon: ScrollText },
  { to: 'retention', label: 'Retention', icon: Archive },
] as const;

function Item({ to, label, icon: Icon }: { to: string; label: string; icon: typeof Users }) {
  return (
    <NavLink
      to={`/settings/${to}`}
      className={({ isActive }) =>
        cn(
          'flex h-11 items-center gap-3 whitespace-nowrap rounded-[12px] px-3 text-[15px] font-medium transition-colors duration-[140ms]',
          isActive ? 'bg-action text-on-action shadow-action' : 'text-ink-2 hover:bg-track hover:text-ink',
        )
      }
    >
      <Icon aria-hidden className="size-[18px]" />
      {label}
    </NavLink>
  );
}

export function SettingsLayout() {
  const { session, can } = useAuth();
  const admin = can('admin.manage');
  return (
    <div>
      <PageHeader title="Settings" subtitle={admin ? 'Account and workspace administration' : 'Your account'} />
      <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[230px_minmax(0,1fr)]">
        <nav aria-label="Settings sections" className="card p-2.5 lg:sticky lg:top-6">
          <p className="px-3 pb-1.5 pt-2 text-[12px] font-medium uppercase tracking-[0.06em] text-ink-3">You</p>
          <Item to="account" label="Account" icon={UserRound} />
          {admin && (
            <>
              <p className="px-3 pb-1.5 pt-4 text-[12px] font-medium uppercase tracking-[0.06em] text-ink-3">Administration</p>
              {ADMIN_NAV.map((n) => (
                <Item key={n.to} {...n} />
              ))}
            </>
          )}
          {!admin && session && <p className="px-3 pb-2 pt-4 text-[12.5px] leading-snug text-ink-3">Administration is available to the {ROLE_LABEL.ADMIN} role.</p>}
        </nav>
        <div className="min-w-0">
          <Outlet />
        </div>
      </div>
    </div>
  );
}

/** Admin-only content; the API also refuses, this keeps restricted UI from loading at all. */
export function AdminOnly({ children }: { children: ReactNode }) {
  const { can } = useAuth();
  if (!can('admin.manage'))
    return (
      <div className="card">
        <AccessDenied message="This section needs the admin.manage capability. Nothing was loaded." recovery="Ask an administrator if you need access." />
      </div>
    );
  return <>{children}</>;
}

export function SettingsCard({ title, description, actions, children, className }: { title: ReactNode; description?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn('card p-5 md:p-6', className)}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-[20px] font-semibold tracking-[-0.02em] text-ink">{title}</h2>
          {description && <p className="mt-1 text-[14px] text-ink-2">{description}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}
