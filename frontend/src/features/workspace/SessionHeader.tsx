import { useQuery } from '@tanstack/react-query';
import { Check, ChevronDown, Database, EyeOff, FlaskConical, History, Loader2, RefreshCw, ServerOff, Timer, WifiOff } from 'lucide-react';
import type { ReactNode } from 'react';
import { qk } from '@/api/queryKeys';
import { useApi } from '@/hooks/useApi';
import { useReplay } from '@/features/replay/store';
import { CodeChip } from '@/components/domain/primitives';
import { Breadcrumb, MetaSep } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { Segmented } from '@/components/ui/controls';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger, Popover, PopoverContent, PopoverTrigger } from '@/components/ui/menu';
import { Tooltip } from '@/components/ui/tooltip';
import { useSessionScope } from '@/hooks/useSessionScope';
import { useStreamState } from '@/hooks/useSessionStream';
import { STATUS } from '@/lib/status';
import { formatDate, formatDateTimeUtc, formatDuration, formatOffset } from '@/lib/time';
import { cn } from '@/lib/utils';

const CONNECTION = {
  CONNECTED: { label: 'Connected', dot: 'bg-[#22a35f]' },
  RECONNECTING: { label: 'Reconnecting…', dot: 'bg-[#e0a21a]' },
  RESYNCING: { label: 'Resyncing…', dot: 'bg-data' },
  OFFLINE: { label: 'Offline', dot: 'bg-[#a3aab5]' },
} as const;

/**
 * "05:22.0 · ● Connected" — the as-of clock plus one status button whose popover
 * explains the connection, where results come from, and that no provider is called.
 */
export function ClockConnectionPill() {
  const cursor = useReplay((s) => s.cursor);
  const playing = useReplay((s) => s.status === 'PLAYING');
  const connection = useStreamState((s) => s.connection);
  const seq = useStreamState((s) => s.lastSequence);
  const c = CONNECTION[connection];
  const shown = playing ? Math.floor(cursor / 100) * 100 : cursor;
  return (
    <div className="inline-flex h-11 items-center rounded-[14px] border border-hairline bg-surface text-[15px] font-medium text-ink shadow-control">
      <Tooltip content="As-of position on the replay clock (session offset, not wall-clock time).">
        <span tabIndex={0} className="inline-flex h-full items-center gap-2 rounded-l-[14px] pl-3.5 pr-3 tabular" aria-label={`As of ${formatOffset(shown)}`}>
          <Timer aria-hidden className="size-[18px] text-ink-2" />
          {formatOffset(shown)}
        </span>
      </Tooltip>
      <span aria-hidden className="h-5 w-px bg-hairline" />
      <Popover>
        <PopoverTrigger asChild>
          <button type="button" aria-label={`Status: ${c.label}, cached results. Show details`} className="inline-flex h-full items-center gap-2 rounded-r-[14px] pl-3 pr-3 transition-colors hover:bg-sunken data-[state=open]:bg-sunken">
            <span aria-hidden className={cn('size-2.5 rounded-full', c.dot, connection !== 'CONNECTED' && 'animate-pulse')} />
            <span role="status" aria-live="polite">
              {c.label}
            </span>
            <ChevronDown aria-hidden className="size-3.5 text-ink-2" />
          </button>
        </PopoverTrigger>
        <PopoverContent align="end" className="w-[320px] p-4">
          <dl className="space-y-3.5 text-[13.5px]">
            <div className="flex gap-3">
              <span aria-hidden className={cn('mt-1.5 size-2.5 shrink-0 rounded-full', c.dot)} />
              <div>
                <dt className="font-semibold text-ink">Server stream · {c.label}</dt>
                <dd className="text-ink-2">FlowLens server, sequence {seq}. While disconnected, review changes pause and nothing is queued.</dd>
              </div>
            </div>
            <div className="flex gap-3">
              <Database aria-hidden className="mt-0.5 size-4 shrink-0 text-ink-2" />
              <div>
                <dt className="font-semibold text-ink">Cached results</dt>
                <dd className="text-ink-2">Results come from stored analysis. Seeking or switching the lens never calls a provider.</dd>
              </div>
            </div>
            <div className="flex gap-3">
              <ServerOff aria-hidden className="mt-0.5 size-4 shrink-0 text-ink-2" />
              <div>
                <dt className="font-semibold text-ink">Analysis provider · not called</dt>
                <dd className="text-ink-2">Replay is offline. Provider status is shown in Settings › Providers.</dd>
              </div>
            </div>
          </dl>
        </PopoverContent>
      </Popover>
    </div>
  );
}

/** Run selector lives inline in the meta row ("Run #03 ▾"); runs never switch on their own. */
export function RunSelector({ className }: { className?: string }) {
  const { detail, runId, setRun, latestRunId } = useSessionScope();
  if (!detail) return null;
  const current = detail.runs.find((r) => r.run.id === runId);
  if (!current) return <span>No analysis run</span>;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button type="button" className={cn('-mx-1.5 inline-flex items-center gap-1 rounded-[8px] px-1.5 py-0.5 transition-colors hover:bg-track hover:text-ink', className)} aria-label={`Analysis run ${current.label}. Change run`}>
          Run {current.label}
          <ChevronDown aria-hidden className="size-3.5" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-[330px]">
        <DropdownMenuLabel>Analysis runs</DropdownMenuLabel>
        {[...detail.runs].reverse().map((r) => (
          <DropdownMenuItem key={r.run.id} onSelect={() => setRun(r.run.id)} className="h-auto items-start py-2.5">
            <History aria-hidden className="mt-0.5" />
            <span className="flex-1">
              <span className="flex items-center gap-2 font-medium">
                Run {r.label} · input revision {r.input_revision}
                {r.run.id === latestRunId && <span className="rounded-full bg-data-tint px-1.5 py-px text-[11px] font-semibold text-data-strong">Latest</span>}
              </span>
              <span className="block text-[12.5px] text-ink-2">
                {STATUS.analysis[r.run.status].label} · {formatDateTimeUtc(r.created_at)}
              </span>
            </span>
            {r.run.id === runId && <Check aria-label="Selected" className="mt-0.5 !text-data" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function ModeToggle({ className }: { className?: string }) {
  const { mode, setMode } = useSessionScope();
  return (
    <Segmented
      label="Replay viewpoint"
      tone="data"
      value={mode}
      onChange={setMode}
      className={cn('h-11 gap-0 rounded-[14px] border border-hairline bg-surface p-[3px] shadow-control [&>button]:h-[36px] [&>button]:rounded-[11px] [&>button]:px-[18px] [&>button]:text-[15px]', className)}
      options={[
        { value: 'AS_KNOWN', label: 'As-known' },
        { value: 'DEBRIEF', label: 'Debrief' },
      ]}
    />
  );
}

/** Session identity labels kept visible on every session screen (G-19). */
export function SessionLabels({ className }: { className?: string }) {
  const { detail } = useSessionScope();
  if (!detail) return null;
  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      <CodeChip title="Source kind — not validated for operations">{detail.source_kind}</CodeChip>
      <Tooltip content="Served by the in-browser MOCK adapter. No backend or provider was called.">
        <span tabIndex={0} className="inline-flex h-6 items-center gap-1.5 rounded-full bg-[#fff1e8] px-2.5 text-[11.5px] font-semibold uppercase tracking-[0.045em] text-[#a2470f]">
          <FlaskConical aria-hidden className="size-3" /> Mock
        </span>
      </Tooltip>
      <span className="inline-flex h-[30px] items-center gap-1.5 rounded-[10px] bg-data-tint px-2.5 text-[14px] font-medium text-data-strong">
        <ServerOff aria-hidden className="size-[15px]" /> Replay offline
      </span>
      {detail.lifecycle === 'ARCHIVED' && <CodeChip tone="muted">Archived · read-only</CodeChip>}
    </div>
  );
}

/**
 * Shared session header (comp 03): big screen title, then session identity on the
 * left and scope controls — mode · as-of · connection · cache — on the right.
 */
export function SessionHeader({ title, breadcrumb, actions, controls = 'full', titleExtra, meta }: { title: ReactNode; breadcrumb?: { label: string; to?: string }[]; actions?: ReactNode; controls?: 'full' | 'none'; titleExtra?: ReactNode; meta?: ReactNode }) {
  const { detail, mode } = useSessionScope();
  if (!detail) return null;
  const trail = breadcrumb ?? [{ label: 'Sessions', to: `/sessions?selected=${detail.id}` }, { label: detail.title }, { label: typeof title === 'string' ? title : 'Workspace' }];
  return (
    <header className="mb-6 fit:mb-4 fit:short:mb-3">
      {/* On short fit viewports the sidebar session switcher carries this context. */}
      <div className="fit:short:sr-only">
        <Breadcrumb items={trail} />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-4">
        <div className="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2">
          <h1 className="text-[34px] font-medium leading-[1.06] tracking-[-0.04em] text-ink xl:text-[44px] fit:text-[38px] short:text-[32px]">{title}</h1>
          {titleExtra}
        </div>
        {(controls === 'full' || actions) && (
          <div className="flex flex-wrap items-center gap-2.5">
            {controls === 'full' && (
              <>
                <ModeToggle />
                <ClockConnectionPill />
              </>
            )}
            {actions}
          </div>
        )}
      </div>
      {/* In the viewport-fit layout the session line and the meta line share one row. */}
      <div className="mt-2.5 min-w-0 fit:mt-1.5 fit:flex fit:flex-wrap fit:items-center fit:gap-x-4 fit:gap-y-1">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <span className="text-[25px] font-semibold leading-tight tracking-[-0.03em] text-ink fit:text-[21px]">{detail.title}</span>
          <SessionLabels />
        </div>
        <p className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[16px] text-ink-2 tabular fit:mt-0 fit:text-[15px]">
          {meta ?? (
            <>
              {formatDate(detail.recorded_at)}
              <MetaSep />
              <RunSelector />
              <MetaSep />
              {detail.context.split(' · ')[1] ?? detail.context}
              <MetaSep />
              Duration {formatDuration(detail.duration_ms)}
              {mode === 'DEBRIEF' && (
                <>
                  <MetaSep />
                  <span className="font-medium text-ink">Debrief · includes later information</span>
                </>
              )}
            </>
          )}
        </p>
      </div>
    </header>
  );
}

/** "Debrief · full session" / "As-known at 05:22" — the lens in words, same wording on every screen. */
export function LensSummary() {
  const { mode, fullSession, asOf } = useSessionScope();
  if (fullSession) return <span>Debrief · full session</span>;
  return (
    <span>
      {mode === 'DEBRIEF' ? 'Debrief' : 'As-known'} at {formatOffset(asOf)}
    </span>
  );
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

/**
 * As-known on an analysis screen hides what became available after the replay
 * position; say how much and offer the full session (decision D-1).
 */
export function LensBanner() {
  const api = useApi();
  const { sid, runId, scope, mode, lensArea, asOf, detail, setMode } = useSessionScope();
  const on = lensArea === 'analysis' && mode === 'AS_KNOWN' && !!scope && !!detail;
  const end = detail?.duration_ms ?? 0;
  const all = useQuery({ queryKey: qk.findings(sid, runId ?? '-', 'DEBRIEF', end), queryFn: () => api.listFindings(scope!, { asOfMs: end, mode: 'DEBRIEF' }), enabled: on });
  const known = useQuery({ queryKey: qk.findings(sid, runId ?? '-', 'AS_KNOWN', asOf), queryFn: () => api.listFindings(scope!, { asOfMs: asOf, mode: 'AS_KNOWN' }), enabled: on });
  const transcript = useQuery({ queryKey: qk.transcript(sid, runId ?? '-', 'AS_KNOWN', asOf), queryFn: () => api.getTranscript(scope!, { asOfMs: asOf, mode: 'AS_KNOWN' }), enabled: on });
  if (!on) return null;
  const laterFindings = all.data && known.data ? Math.max(0, all.data.length - known.data.length) : null;
  const laterSegments = transcript.data?.hidden_after_as_of ?? null;
  const counts = [laterFindings ? plural(laterFindings, 'finding') : null, laterSegments ? plural(laterSegments, 'segment') : null].filter(Boolean);
  return (
    <div role="status" className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-[16px] border border-data-tint bg-data-tint/50 px-4 py-3 text-[14px] text-ink">
      <EyeOff aria-hidden className="size-[18px] text-data" />
      <span className="flex-1">
        <strong className="font-semibold">Showing what was known at {formatOffset(asOf)}.</strong>{' '}
        {counts.length ? `${counts.join(' and ')} became available later in the session.` : laterFindings == null ? 'Counting what became available later…' : 'Nothing else became available later.'}
      </span>
      <Button size="sm" variant="secondary" onClick={() => setMode('DEBRIEF')}>
        Show full session
      </Button>
    </div>
  );
}

/** Banners that must stay visible: connection loss, not-latest run, As-known lens. */
export function ScopeBanners() {
  const { run, latestRunId, setRun, detail, isLatestRun, lensArea, mode } = useSessionScope();
  const connection = useStreamState((s) => s.connection);
  const latest = detail?.runs.find((r) => r.run.id === latestRunId);
  const showConnection = connection !== 'CONNECTED';
  const showRun = !!run && !isLatestRun && !!latest;
  const showLens = lensArea === 'analysis' && mode === 'AS_KNOWN';
  if (!showConnection && !showRun && !showLens) return null;
  return (
    <div className="mb-5 space-y-2.5">
      {showConnection && (
        <div role="status" className="flex flex-wrap items-center gap-3 rounded-[16px] border border-notice-soft bg-notice-tint px-4 py-3 text-[14px] text-ink">
          {connection === 'RESYNCING' ? <Loader2 aria-hidden className="size-[18px] animate-spin text-notice" /> : <WifiOff aria-hidden className="size-[18px] text-notice" />}
          <span className="flex-1">
            <strong className="font-semibold">{connection === 'RESYNCING' ? 'Resyncing with the server…' : 'Connection to the server lost.'}</strong> Review changes are paused until the stream resyncs — nothing is queued offline. Local replay keeps working from the last known state.
          </span>
        </div>
      )}
      {showRun && latest && run && (
        <div className="flex flex-wrap items-center gap-3 rounded-[16px] border border-hairline bg-surface px-4 py-3 text-[14px] text-ink shadow-control">
          <History aria-hidden className="size-[18px] text-ink-2" />
          <span className="flex-1">
            You are viewing <strong className="font-semibold">Run {run.label}</strong> (input revision {run.input_revision}). Run {latest.label} is newer; results are never merged across runs.
          </span>
          <Button size="sm" variant="secondary" onClick={() => setRun(latest.run.id)}>
            <RefreshCw /> Open run {latest.label}
          </Button>
        </div>
      )}
      {showLens && <LensBanner />}
    </div>
  );
}
