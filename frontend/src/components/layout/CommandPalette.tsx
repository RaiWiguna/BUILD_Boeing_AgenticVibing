import { useQuery } from '@tanstack/react-query';
import { Command } from 'cmdk';
import { Dialog as DialogPrimitive } from 'radix-ui';
import { BookOpenCheck, Brain, CornerDownLeft, Flag, FolderOpen, HelpCircle, History, LayoutGrid, MessageSquareText, Monitor, NotebookText, Search, Settings, Upload } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router';
import { qk } from '@/api/queryKeys';
import { useApi } from '@/hooks/useApi';
import { lastSession } from '@/hooks/useSessionScope';
import { Kbd } from '@/components/ui/input';
import { scopeFromParams, sessionHref, type LinkFocus, type SessionArea } from '@/lib/links';
import { formatClock } from '@/lib/time';

export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const api = useApi();
  const navigate = useNavigate();
  const location = useLocation();
  const routeSid = /^\/s\/([^/]+)/.exec(location.pathname)?.[1] ?? null;
  const sessions = useQuery({ queryKey: qk.sessions, queryFn: () => api.listSessions(), enabled: open });
  const remembered = lastSession();
  const sid = routeSid ?? (remembered && sessions.data?.some((s) => s.id === remembered) ? remembered : null);
  const detail = useQuery({ queryKey: qk.session(sid ?? ''), queryFn: () => api.getSession(sid!), enabled: open && !!sid });
  // Inside a session the palette keeps run · lens · t; from elsewhere it opens the latest run.
  const carried = routeSid ? scopeFromParams(new URLSearchParams(location.search)) : {};
  const runId = carried.run ?? detail.data?.latest_run_id ?? null;
  const scope = sid && runId ? { sessionId: sid, runId } : null;
  const end = detail.data?.duration_ms ?? 0;
  // Search covers the whole session (Debrief) so every finding and segment can be found.
  const findings = useQuery({ queryKey: qk.findings(sid ?? '', runId ?? '-', 'DEBRIEF', end), queryFn: () => api.listFindings(scope!, { asOfMs: end, mode: 'DEBRIEF' }), enabled: open && !!scope && !!detail.data });
  const transcript = useQuery({ queryKey: qk.transcript(sid ?? '', runId ?? '-', 'DEBRIEF', end), queryFn: () => api.getTranscript(scope!, { asOfMs: end, mode: 'DEBRIEF' }), enabled: open && !!scope && !!detail.data });

  const go = (to: string) => {
    onOpenChange(false);
    navigate(to);
  };
  const to = (area: SessionArea, focus?: LinkFocus) => sessionHref(area, { sid: sid!, ...carried, run: runId, focus });
  // A searched finding or segment must be visible when it opens, so it opens in the full-session lens.
  const toItem = (area: SessionArea, focus: LinkFocus) => sessionHref(area, { sid: sid!, ...carried, lens: null, run: runId, focus });
  const title = detail.data?.title;
  const item = 'flex h-11 cursor-pointer items-center gap-3 rounded-[12px] px-3 text-[15px] text-ink data-[selected=true]:bg-track [&_svg]:size-[18px] [&_svg]:shrink-0 [&_svg]:text-ink-2';
  const group = '[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pb-1.5 [&_[cmdk-group-heading]]:pt-3 [&_[cmdk-group-heading]]:text-[12px] [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.05em] [&_[cmdk-group-heading]]:text-ink-3';
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-[rgba(25,27,32,0.24)] backdrop-blur-[2px] data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <DialogPrimitive.Content className="fixed left-1/2 top-[14vh] z-50 w-[min(640px,calc(100vw-32px))] -translate-x-1/2 overflow-hidden rounded-[22px] border border-hairline-soft bg-surface shadow-pop data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-[0.98]">
          <DialogPrimitive.Title className="sr-only">Search</DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">Search sessions, objects, findings, transcript and pages</DialogPrimitive.Description>
          <Command label="Search FlowLens" loop>
            <div className="flex items-center gap-3 border-b border-hairline px-5">
              <Search aria-hidden className="size-5 text-ink-2" />
              <Command.Input autoFocus placeholder="Search sessions, callsigns, findings, transcript…" className="h-[58px] flex-1 bg-transparent text-[16px] text-ink outline-none placeholder:text-ink-3" />
              <Kbd>Esc</Kbd>
            </div>
            <Command.List className="max-h-[min(460px,60vh)] overflow-y-auto p-2 scrollbar-thin">
              <Command.Empty className="px-3 py-10 text-center text-[14px] text-ink-2">No matches in sessions you can access.</Command.Empty>
              {sid && title && runId && (
                <Command.Group heading={`Session · ${title}`} className={group}>
                  <Command.Item value={`workspace ${title}`} className={item} onSelect={() => go(to('workspace'))}><Monitor /> Workspace</Command.Item>
                  <Command.Item value={`review findings ${title}`} className={item} onSelect={() => go(to('review/findings'))}><NotebookText /> Review findings</Command.Item>
                  <Command.Item value={`review transcript ${title}`} className={item} onSelect={() => go(to('review/transcript'))}><NotebookText /> Review transcript</Command.Item>
                  <Command.Item value={`debrief ${title}`} className={item} onSelect={() => go(to('debrief'))}><BookOpenCheck /> Debrief</Command.Item>
                  <Command.Item value={`memory ${title}`} className={item} onSelect={() => go(to('memory'))}><Brain /> Memory</Command.Item>
                  <Command.Item value={`ask ${title}`} className={item} onSelect={() => go(to('ask'))}><MessageSquareText /> Ask</Command.Item>
                </Command.Group>
              )}
              {findings.data && findings.data.length > 0 && (
                <Command.Group heading="Findings" className={group}>
                  {findings.data.map((f) => (
                    <Command.Item key={f.finding.id} value={`${f.label} ${f.title} ${f.entity_label} finding`} className={item} onSelect={() => go(toItem('review/findings', { finding: f.finding.id }))}>
                      <Flag />
                      <span className="w-11 shrink-0 font-medium tabular">{f.label}</span>
                      <span className="min-w-0 flex-1 truncate">{f.title}</span>
                      <span className="text-[13px] text-ink-3">{f.entity_label}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
              {detail.data && runId && (
                <Command.Group heading="Objects" className={group}>
                  {detail.data.entities.map((e) => (
                    <Command.Item key={e.id} value={`${e.callsign} ${e.aliases.join(' ')} object memory`} className={item} onSelect={() => go(to(`memory/${e.id}`))}>
                      <FolderOpen />
                      <span className="flex-1">{e.callsign}</span>
                      <span className="text-[13px] text-ink-3">{e.type} · {e.role}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
              {transcript.data && transcript.data.rows.length > 0 && (
                <Command.Group heading="Transcript" className={group}>
                  {transcript.data.rows.map((r) => (
                    <Command.Item key={r.original.id} value={`${r.label} ${r.segment.text} transcript`} className={item} onSelect={() => go(toItem('review/transcript', { segment: r.original.id }))}>
                      <History />
                      <span className="w-11 shrink-0 font-medium tabular">{r.label}</span>
                      <span className="min-w-0 flex-1 truncate">“{r.segment.text}”</span>
                      <span className="text-[13px] text-ink-3 tabular">{formatClock(r.segment.start_ms ?? 0)}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
              {!!sessions.data?.length && (
                <Command.Group heading="Sessions" className={group}>
                  {sessions.data.map((s) => (
                    <Command.Item key={s.id} value={`${s.title} ${s.context} session`} className={item} onSelect={() => go(s.latest_run_id ? sessionHref('workspace', { sid: s.id, run: s.latest_run_id }) : `/sessions?selected=${s.id}`)}>
                      <LayoutGrid />
                      <span className="flex-1 truncate">{s.title}</span>
                      <span className="text-[13px] text-ink-3">{s.latest_run_id ? s.context : 'Not analysed'}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
              <Command.Group heading="Go to" className={group}>
                <Command.Item className={item} onSelect={() => go('/sessions')}><LayoutGrid /> All sessions</Command.Item>
                <Command.Item className={item} onSelect={() => go('/sessions/import')}><Upload /> Import session</Command.Item>
                <Command.Item className={item} onSelect={() => go('/settings')}><Settings /> Settings</Command.Item>
                <Command.Item className={item} onSelect={() => go('/help')}><HelpCircle /> Help & shortcuts</Command.Item>
              </Command.Group>
            </Command.List>
            <div className="flex items-center gap-4 border-t border-hairline px-5 py-3 text-[12px] text-ink-3">
              <span className="inline-flex items-center gap-1.5"><Kbd>↑</Kbd><Kbd>↓</Kbd> navigate</span>
              <span className="inline-flex items-center gap-1.5"><Kbd><CornerDownLeft className="size-3" /></Kbd> open</span>
              {title && <span className="ml-auto truncate">Searching {title} · full session</span>}
            </div>
          </Command>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
