import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, CheckCheck } from 'lucide-react';
import { useNavigate } from 'react-router';
import { qk } from '@/api/queryKeys';
import type { NotificationItem } from '@/api/types';
import { Dot } from '@/components/domain/primitives';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/menu';
import { useApi } from '@/hooks/useApi';
import { formatDateTimeUtc } from '@/lib/time';
import { cn } from '@/lib/utils';

export function NotificationsPopover({ collapsed, unread, items }: { collapsed: boolean; unread: number; items: NotificationItem[] }) {
  const api = useApi();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const markRead = useMutation({ mutationFn: () => api.markNotificationsRead(), onSuccess: () => qc.invalidateQueries({ queryKey: qk.notifications }) });
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button type="button" aria-label={`Notifications, ${unread} unread`} className={cn('group flex h-11 short:h-10 w-full items-center gap-3 rounded-[12px] text-[15.5px] font-medium text-ink transition-colors hover:bg-[#eceef1] data-[state=open]:bg-[#eceef1]', collapsed ? 'relative justify-center' : 'px-3.5')}>
          <Bell aria-hidden className="size-[20px] text-ink-2 group-hover:text-ink" strokeWidth={1.8} />
          {!collapsed && <span>Notifications</span>}
          {unread > 0 && <span className={cn('inline-flex size-[22px] items-center justify-center rounded-full bg-badge text-[12px] font-semibold text-white tabular', collapsed ? 'absolute right-1 top-0.5 size-[18px] text-[11px]' : 'ml-auto')}>{unread}</span>}
        </button>
      </PopoverTrigger>
      <PopoverContent side="right" align="end" sideOffset={14} className="w-[380px] p-2">
        <div className="flex items-center justify-between px-3 pb-2 pt-2">
          <div>
            <p className="text-[16px] font-semibold text-ink">Notifications</p>
            <p className="text-[13px] text-ink-2">{unread ? `${unread} unread` : 'All caught up'}</p>
          </div>
          <Button variant="ghost" size="xs" disabled={!unread || markRead.isPending} onClick={() => markRead.mutate()}>
            <CheckCheck /> Mark all read
          </Button>
        </div>
        <ul className="max-h-[420px] overflow-y-auto scrollbar-thin">
          {items.length === 0 && <li className="px-3 py-8 text-center text-[14px] text-ink-2">No notifications.</li>}
          {items.map((n) => (
            <li key={n.id}>
              <button type="button" disabled={!n.href} onClick={() => n.href && navigate(n.href)} className="flex w-full items-start gap-3 rounded-[12px] px-3 py-3 text-left transition-colors hover:bg-sunken disabled:cursor-default">
                <Dot tone={n.tone === 'ready' ? 'ready' : n.tone} className={cn('mt-[7px]', n.read && 'opacity-30')} />
                <span className="min-w-0">
                  <span className={cn('block text-[14px] text-ink', !n.read && 'font-semibold')}>{n.title}</span>
                  <span className="block text-[13px] text-ink-2">{n.detail}</span>
                  <span className="mt-0.5 block text-[12px] text-ink-3 tabular">{formatDateTimeUtc(n.at)}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </PopoverContent>
    </Popover>
  );
}
