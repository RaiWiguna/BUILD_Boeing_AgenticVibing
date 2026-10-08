import { useQuery } from '@tanstack/react-query';
import { Command } from 'cmdk';
import { Dialog as DialogPrimitive } from 'radix-ui';
import { BookOpenCheck, CornerDownLeft, FolderOpen, HelpCircle, LayoutGrid, NotebookText, Search, Settings, Upload } from 'lucide-react';
import { useNavigate } from 'react-router';
import { qk } from '@/api/queryKeys';
import { useApi } from '@/hooks/useApi';
import { lastSession } from '@/hooks/useSessionScope';
import { Kbd } from '@/components/ui/input';

export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const api = useApi();
  const navigate = useNavigate();
  const sessions = useQuery({ queryKey: qk.sessions, queryFn: () => api.listSessions(), enabled: open });
  const sid = lastSession();
  const detail = useQuery({ queryKey: qk.session(sid ?? ''), queryFn: () => api.getSession(sid!), enabled: open && !!sid });
  const go = (to: string) => {
    onOpenChange(false);
    navigate(to);
  };
  const item = 'flex h-11 cursor-pointer items-center gap-3 rounded-[12px] px-3 text-[15px] text-ink data-[selected=true]:bg-track [&_svg]:size-[18px] [&_svg]:text-ink-2';
  const group = '[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pb-1.5 [&_[cmdk-group-heading]]:pt-3 [&_[cmdk-group-heading]]:text-[12px] [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.05em] [&_[cmdk-group-heading]]:text-ink-3';
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-[rgba(25,27,32,0.24)] backdrop-blur-[2px] data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <DialogPrimitive.Content className="fixed left-1/2 top-[14vh] z-50 w-[min(640px,calc(100vw-32px))] -translate-x-1/2 overflow-hidden rounded-[22px] border border-hairline-soft bg-surface shadow-pop data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-[0.98]">
          <DialogPrimitive.Title className="sr-only">Search</DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">Search sessions, objects, findings and pages</DialogPrimitive.Description>
          <Command label="Search FlowLens" loop>
            <div className="flex items-center gap-3 border-b border-hairline px-5">
              <Search aria-hidden className="size-5 text-ink-2" />
              <Command.Input autoFocus placeholder="Search sessions, callsigns, findings…" className="h-[58px] flex-1 bg-transparent text-[16px] text-ink outline-none placeholder:text-ink-3" />
              <Kbd>Esc</Kbd>
            </div>
            <Command.List className="max-h-[420px] overflow-y-auto p-2 scrollbar-thin">
              <Command.Empty className="px-3 py-10 text-center text-[14px] text-ink-2">No matches in sessions you can access.</Command.Empty>
              <Command.Group heading="Go to" className={group}>
                <Command.Item className={item} onSelect={() => go('/sessions')}><LayoutGrid /> Sessions</Command.Item>
                <Command.Item className={item} onSelect={() => go('/sessions/import')}><Upload /> Import session</Command.Item>
                {sid && <Command.Item className={item} onSelect={() => go(`/s/${sid}/workspace`)}><FolderOpen /> Workspace</Command.Item>}
                {sid && <Command.Item className={item} onSelect={() => go(`/s/${sid}/review/findings`)}><NotebookText /> Review</Command.Item>}
                {sid && <Command.Item className={item} onSelect={() => go(`/s/${sid}/debrief`)}><BookOpenCheck /> Debrief</Command.Item>}
                <Command.Item className={item} onSelect={() => go('/settings')}><Settings /> Settings</Command.Item>
                <Command.Item className={item} onSelect={() => go('/help')}><HelpCircle /> Help & legend</Command.Item>
              </Command.Group>
              {!!sessions.data?.length && (
                <Command.Group heading="Sessions" className={group}>
                  {sessions.data.map((s) => (
                    <Command.Item key={s.id} value={`${s.title} ${s.context}`} className={item} onSelect={() => go(`/sessions?selected=${s.id}`)}>
                      <LayoutGrid />
                      <span className="flex-1 truncate">{s.title}</span>
                      <span className="text-[13px] text-ink-3">{s.context}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
              {detail.data && (
                <Command.Group heading={`Objects · ${detail.data.title}`} className={group}>
                  {detail.data.entities.map((e) => (
                    <Command.Item key={e.id} value={`${e.callsign} ${e.aliases.join(' ')}`} className={item} onSelect={() => go(`/s/${detail.data!.id}/memory/object/${e.id}`)}>
                      <FolderOpen />
                      <span className="flex-1">{e.callsign}</span>
                      <span className="text-[13px] text-ink-3">{e.type} · {e.role}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
            </Command.List>
            <div className="flex items-center gap-4 border-t border-hairline px-5 py-3 text-[12px] text-ink-3">
              <span className="inline-flex items-center gap-1.5"><Kbd>↑</Kbd><Kbd>↓</Kbd> navigate</span>
              <span className="inline-flex items-center gap-1.5"><Kbd><CornerDownLeft className="size-3" /></Kbd> open</span>
            </div>
          </Command>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
