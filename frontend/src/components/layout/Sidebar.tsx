import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, BookOpenCheck, Brain, HelpCircle, LayoutGrid, MessageSquareText, Monitor, NotebookText, PanelLeft, Search, Settings } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { NavLink, useLocation, useMatch } from 'react-router';
import { qk } from '@/api/queryKeys';
import { useAuth } from '@/app/providers/AuthProvider';
import { Kbd } from '@/components/ui/input';
import { Tooltip } from '@/components/ui/tooltip';
import { useApi } from '@/hooks/useApi';
import { carryParams, lastSession } from '@/hooks/useSessionScope';
import { cn } from '@/lib/utils';
import { NotificationsPopover } from './NotificationsPopover';
import { areaFromPath } from '@/lib/links';
import { SessionSwitcher } from './SessionSwitcher';
import { UserMenu } from './UserMenu';
import { Wordmark } from './Logo';

interface Item {
  to: string;
  label: string;
  icon: LucideIcon;
  match: string;
  badge?: string;
}

function NavItem({ item, collapsed }: { item: Item; collapsed: boolean }) {
  const active = !!useMatch({ path: item.match, end: false });
  const link = (
    <NavLink
      to={item.to}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'group flex h-11 short:h-10 items-center gap-3 rounded-[12px] text-[15.5px] font-medium transition-[background-color,color,box-shadow] duration-[140ms]',
        collapsed ? 'justify-center px-0' : 'px-3.5',
        active ? 'bg-action text-on-action shadow-action' : 'text-ink hover:bg-[#eceef1]',
      )}
    >
      <item.icon aria-hidden className={cn('size-[20px] shrink-0', active ? 'text-on-action' : 'text-ink-2 group-hover:text-ink')} strokeWidth={1.8} />
      {!collapsed && <span className="truncate">{item.label}</span>}
      {!collapsed && item.badge && <span className="ml-auto rounded-full bg-track px-1.5 py-0.5 text-[10.5px] font-semibold uppercase tracking-[0.04em] text-ink-2 group-aria-[current=page]:bg-white/15 group-aria-[current=page]:text-white">{item.badge}</span>}
      {collapsed && <span className="sr-only">{item.label}</span>}
    </NavLink>
  );
  return collapsed ? (
    <Tooltip content={item.label} side="right">
      {link}
    </Tooltip>
  ) : (
    link
  );
}

export function Sidebar({ collapsed, onToggle, onSearch, footer }: { collapsed: boolean; onToggle: () => void; onSearch: () => void; footer?: ReactNode }) {
  const location = useLocation();
  const { can } = useAuth();
  const api = useApi();
  const routeSid = /^\/s\/([^/]+)/.exec(location.pathname)?.[1] ?? null;
  const sessions = useQuery({ queryKey: qk.sessions, queryFn: () => api.listSessions() });
  const remembered = lastSession();
  // A remembered session counts only while it still exists (mock data resets on reload).
  const scoped = routeSid ?? (remembered && sessions.data?.some((x) => x.id === remembered) ? remembered : null);
  // Run · lens · t only carry within the session being viewed.
  const q = routeSid ? `?${carryParams(new URLSearchParams(location.search))}`.replace(/\?$/, '') : '';
  const s = (path: string) => `/s/${scoped}/${path}${q}`;
  const notif = useQuery({ queryKey: qk.notifications, queryFn: () => api.listNotifications(), refetchInterval: 8000 });
  const unread = notif.data?.filter((n) => !n.read).length ?? 0;

  const main: Item[] = [
    { to: s('workspace'), label: 'Workspace', icon: Monitor, match: '/s/:sid/workspace' },
    { to: s('review/findings'), label: 'Review', icon: NotebookText, match: '/s/:sid/review' },
    { to: s('debrief'), label: 'Debrief', icon: BookOpenCheck, match: '/s/:sid/debrief' },
  ];
  const analyze: Item[] = [
    { to: s('memory'), label: 'Memory', icon: Brain, match: '/s/:sid/memory' },
    { to: s('metrics'), label: 'Metrics', icon: BarChart3, match: '/s/:sid/metrics', badge: 'P1' },
    { to: s('ask'), label: 'Ask', icon: MessageSquareText, match: '/s/:sid/ask', badge: 'P1' },
  ];

  return (
    <nav aria-label="Primary" className={cn('sticky top-0 flex h-dvh shrink-0 flex-col overflow-y-auto overscroll-contain py-6 short:py-4 transition-[width] duration-200 [scrollbar-width:none]', collapsed ? 'w-[var(--sidebar-collapsed)] px-3' : 'w-[var(--sidebar-width)] px-4')}>
      <div className={cn('flex items-center', collapsed ? 'flex-col gap-3' : 'justify-between pl-1.5')}>
        <NavLink to="/sessions" aria-label="FlowLens home" className="rounded-[12px]">
          <Wordmark collapsed={collapsed} />
        </NavLink>
        <Tooltip content={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} side="right">
          <button type="button" onClick={onToggle} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} aria-expanded={!collapsed} className="inline-flex size-9 items-center justify-center rounded-full border border-hairline bg-surface text-ink-2 transition-colors hover:text-ink">
            <PanelLeft className="size-[17px]" />
          </button>
        </Tooltip>
      </div>

      <button
        type="button"
        onClick={onSearch}
        className={cn('mt-6 short:mt-4 flex h-11 short:h-10 shrink-0 items-center gap-2.5 rounded-[12px] border border-hairline bg-surface text-[15px] text-ink-3 shadow-control transition-colors hover:border-hairline-strong', collapsed ? 'justify-center px-0' : 'px-3.5')}
        aria-label="Search (Command K)"
      >
        <Search aria-hidden className="size-[18px] text-ink-2" />
        {!collapsed && (
          <>
            <span>Search</span>
            <Kbd className="ml-auto">⌘K</Kbd>
          </>
        )}
      </button>

      <div className="mt-6 short:mt-4">
        <NavItem item={{ to: '/sessions', label: 'Sessions', icon: LayoutGrid, match: '/sessions' }} collapsed={collapsed} />
      </div>
      <div role="group" aria-label="Current session" className="mt-5 short:mt-3">
        {!collapsed && <p className="mb-2 px-3.5 text-[13px] font-medium text-ink-3 short:mb-1">Current session</p>}
        <SessionSwitcher collapsed={collapsed} currentId={scoped} area={areaFromPath(location.pathname)} />
        {scoped && (
          <>
            <div className="mt-2 space-y-1.5 short:space-y-1">
              {main.map((i) => (
                <NavItem key={i.label} item={i} collapsed={collapsed} />
              ))}
            </div>
            {!collapsed ? <p className="mb-2 mt-5 px-3.5 text-[13px] font-medium text-ink-3 short:mb-1 short:mt-3">Analyze</p> : <div className="mx-3 my-4 h-px shrink-0 bg-hairline short:my-3" />}
            <div className="space-y-1.5 short:space-y-1">
              {analyze.map((i) => (
                <NavItem key={i.label} item={i} collapsed={collapsed} />
              ))}
            </div>
          </>
        )}
      </div>

      <div className="mt-auto space-y-1.5 pt-6 short:space-y-1 short:pt-4">
        <NotificationsPopover collapsed={collapsed} unread={unread} items={notif.data ?? []} />
        {can('admin.manage') ? (
          <NavItem item={{ to: '/settings/users', label: 'Settings', icon: Settings, match: '/settings' }} collapsed={collapsed} />
        ) : (
          <NavItem item={{ to: '/settings/account', label: 'Settings', icon: Settings, match: '/settings' }} collapsed={collapsed} />
        )}
        <NavItem item={{ to: '/help', label: 'Help', icon: HelpCircle, match: '/help' }} collapsed={collapsed} />
        {footer}
      </div>
      <div className="mt-4 border-t border-hairline pt-4 short:mt-3 short:pt-3">
        <UserMenu collapsed={collapsed} />
      </div>
    </nav>
  );
}

