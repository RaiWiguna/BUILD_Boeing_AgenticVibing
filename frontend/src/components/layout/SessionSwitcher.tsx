import { useQuery } from '@tanstack/react-query';
import { Check, ChevronsUpDown, FolderOpen, LayoutGrid } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { qk } from '@/api/queryKeys';
import type { SessionSummary } from '@/api/types';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/menu';
import { Tooltip } from '@/components/ui/tooltip';
import { useApi } from '@/hooks/useApi';
import { cn } from '@/lib/utils';

/** Where a picked session opens: the same area when one is open, else the workspace. */
export function SessionList({ sessions, currentId, onPick }: { sessions: SessionSummary[]; currentId: string | null; onPick: (s: SessionSummary) => void }) {
  return (
    <ul className="space-y-0.5" aria-label="Sessions">
      {sessions.map((s) => {
        const current = s.id === currentId;
        return (
          <li key={s.id}>
            <button
              type="button"
              onClick={() => onPick(s)}
              aria-current={current ? 'true' : undefined}
              className="flex w-full items-start gap-3 rounded-[12px] px-3 py-2.5 text-left transition-colors hover:bg-sunken aria-[current=true]:bg-data-tint/60"
            >
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[14.5px] font-medium text-ink">{s.title}</span>
                <span className="block truncate text-[12.5px] text-ink-2">
                  {s.latest_run_label ? `Run ${s.latest_run_label.split(' ')[0]}` : 'Not analysed'} · {s.open_findings} open · {s.lifecycle === 'ARCHIVED' ? 'Archived' : s.context}
                </span>
              </span>
              {current && <Check aria-label="Current session" className="mt-1 size-4 shrink-0 text-data" />}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/**
 * Current-session block in the sidebar: the session every session screen belongs to,
 * with a popover to switch. Switching keeps the area but never carries the run/as-of.
 */
export function SessionSwitcher({ collapsed, currentId, area }: { collapsed: boolean; currentId: string | null; area: string }) {
  const api = useApi();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const sessions = useQuery({ queryKey: qk.sessions, queryFn: () => api.listSessions() });
  const current = sessions.data?.find((s) => s.id === currentId) ?? null;
  const pick = (s: SessionSummary) => {
    setOpen(false);
    navigate(s.latest_run_id ? `/s/${s.id}/${area}?run=${s.latest_run_id}` : `/sessions?selected=${s.id}`);
  };
  const label = current ? `Current session: ${current.title}. Switch session` : 'No session open. Choose session';

  const trigger = (
    <PopoverTrigger asChild>
      <button
        type="button"
        aria-label={label}
        className={cn(
          'flex w-full items-center gap-3 rounded-[14px] border border-hairline bg-surface text-left shadow-control transition-colors hover:border-hairline-strong data-[state=open]:border-hairline-strong',
          collapsed ? 'h-11 justify-center px-0' : 'min-h-[54px] px-3 py-2 short:min-h-[48px]',
        )}
      >
        <FolderOpen aria-hidden className="size-[18px] shrink-0 text-ink-2" />
        {!collapsed && (
          <>
            <span className="min-w-0 flex-1">
              {current ? (
                <>
                  <span title={current.title} className="block truncate text-[14px] font-semibold text-ink">{current.title}</span>
                  <span className="mt-0.5 block truncate text-[12px] text-ink-2">
                    {current.latest_run_label ? `Run ${current.latest_run_label.split(' ')[0]}` : 'Not analysed'} · <span className="font-semibold uppercase tracking-[0.04em] text-[10.5px]">{current.source_kind}</span>
                  </span>
                </>
              ) : (
                <>
                  <span className="block text-[14px] font-semibold text-ink">No session open</span>
                  <span className="block text-[12px] text-data">Choose session</span>
                </>
              )}
            </span>
            <ChevronsUpDown aria-hidden className="size-4 shrink-0 text-ink-3" />
          </>
        )}
      </button>
    </PopoverTrigger>
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      {collapsed ? (
        <Tooltip content={current ? current.title : 'Choose session'} side="right">
          {trigger}
        </Tooltip>
      ) : (
        trigger
      )}
      <PopoverContent side="right" align="start" sideOffset={14} className="w-[340px] p-2">
        <p className="px-3 pb-1.5 pt-2 text-[12px] font-medium uppercase tracking-[0.05em] text-ink-3">Switch session</p>
        <div className="max-h-[360px] overflow-y-auto scrollbar-thin">
          {sessions.data ? <SessionList sessions={sessions.data} currentId={currentId} onPick={pick} /> : <p className="px-3 py-6 text-[14px] text-ink-2">Loading sessions…</p>}
        </div>
        <div className="mt-1 border-t border-hairline pt-1">
          <Link to="/sessions" onClick={() => setOpen(false)} className="flex h-10 items-center gap-2.5 rounded-[10px] px-3 text-[14px] font-medium text-ink hover:bg-sunken">
            <LayoutGrid aria-hidden className="size-4 text-ink-2" /> All sessions
          </Link>
        </div>
      </PopoverContent>
    </Popover>
  );
}
