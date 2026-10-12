import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  ArrowDown,
  ArrowRight,
  BookOpenCheck,
  ChevronRight,
  CircleCheck,
  Clock3,
  FileText,
  Filter,
  FolderOpen,
  History,
  Layers,
  Link2,
  NotebookText,
  Search,
  ServerOff,
  ShieldAlert,
  TriangleAlert,
  Upload,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { SessionList } from '@/components/layout/SessionSwitcher';
import { sessionHref, type SessionArea } from '@/lib/links';
import { lastArea, lastSession } from '@/hooks/useSessionScope';
import { toast } from 'sonner';
import { qk } from '@/api/queryKeys';
import { useDemoBackend } from '@/api/demo';
import type { Notice, SessionSummary } from '@/api/types';
import { useAuth } from '@/app/providers/AuthProvider';
import { LayoutMini } from '@/components/domain/LayoutMini';
import { Card, Dot, IconTile, MoreButton } from '@/components/domain/primitives';
import { EmptyState, ErrorState, LoadingRows } from '@/components/domain/states';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { Progress, Select, Skeleton } from '@/components/ui/controls';
import { Input } from '@/components/ui/input';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/menu';
import { PillTabsList, PillTabsTrigger, Tabs } from '@/components/ui/tabs';
import { Tooltip } from '@/components/ui/tooltip';
import { useApi } from '@/hooks/useApi';
import { STATUS, type Tone } from '@/lib/status';
import { formatDate, formatDateTimeUtc, formatDuration, formatTimeUtc } from '@/lib/time';
import { cn, plural } from '@/lib/utils';

type TabKey = 'all' | 'active' | 'archived';

export function SessionsPage() {
  const api = useApi();
  const { can } = useAuth();
  const [params, setParams] = useSearchParams();
  const [tab, setTab] = useState<TabKey>('all');
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('ALL');
  // DEMO track: poll while a demo workspace is still processing so it turns ready in place.
  const sessions = useQuery({ queryKey: qk.sessions, queryFn: () => api.listSessions(), refetchInterval: (q) => (q.state.data?.some(isProcessing) ? 1500 : false) });
  const demoStatus = useDemoBackend((d) => d.status);
  const all = useMemo(() => sessions.data ?? [], [sessions.data]);
  const selectedId = params.get('selected') ?? all.find((s) => s.latest_run_id)?.id ?? all[0]?.id ?? null;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return all.filter((s) => {
      if (tab === 'active' && s.lifecycle === 'ARCHIVED') return false;
      if (tab === 'archived' && s.lifecycle !== 'ARCHIVED') return false;
      if (status !== 'ALL' && s.analysis !== status) return false;
      if (q && !`${s.title} ${s.context} ${s.source_kind}`.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [all, tab, status, query]);

  const counts = {
    all: all.length,
    active: all.filter((s) => s.lifecycle !== 'ARCHIVED').length,
    archived: all.filter((s) => s.lifecycle === 'ARCHIVED').length,
  };

  const select = (id: string) =>
    setParams(
      (p) => {
        const next = new URLSearchParams(p);
        next.set('selected', id);
        return next;
      },
      { replace: true },
    );

  const importButton = can('session.import') ? (
    <Button asChild variant="primary">
      <Link to="/sessions/import">
        <Upload /> Import session
      </Link>
    </Button>
  ) : (
    <Tooltip content="Your role does not include session.import.">
      <span tabIndex={0}>
        <Button variant="primary" disabled>
          <Upload /> Import session
        </Button>
      </span>
    </Tooltip>
  );

  return (
    <>
      <PageHeader title="Sessions" subtitle="Choose a replay to review context and evidence." actions={importButton} />

      <ContinueCard sessions={all} />

      <SummaryStrip sessions={all} loading={sessions.isPending} />

      <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_380px] 2xl:grid-cols-[minmax(0,1fr)_420px]">
        <Card className="min-w-0 p-5 pb-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Tabs value={tab} onValueChange={(v) => setTab(v as TabKey)}>
              <PillTabsList aria-label="Session lifecycle" className="bg-transparent p-0">
                {(['all', 'active', 'archived'] as const).map((k) => (
                  <PillTabsTrigger key={k} value={k} aria-controls="session-table" className="h-10 px-4 data-[state=active]:bg-data-tint data-[state=active]:text-data-strong data-[state=active]:shadow-none">
                    {k === 'all' ? 'All' : k === 'active' ? 'Active' : 'Archived'} <span className="tabular opacity-80">({counts[k]})</span>
                  </PillTabsTrigger>
                ))}
              </PillTabsList>
            </Tabs>
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="relative">
                <Search aria-hidden className="pointer-events-none absolute left-3.5 top-1/2 size-[17px] -translate-y-1/2 text-ink-3" />
                <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search sessions or sources" aria-label="Search sessions or sources" className="h-10 w-[240px] pl-10 text-[14px]" />
              </div>
              <Select
                size="sm"
                className="h-10"
                label="Analysis status"
                value={status}
                onValueChange={setStatus}
                icon={<Filter className="text-ink-2" />}
                options={[
                  { value: 'ALL', label: 'All statuses' },
                  { value: 'COMPLETED', label: 'Completed' },
                  { value: 'PARTIAL', label: 'Partial' },
                  { value: 'NOT_ANALYZED', label: 'Not analysed' },
                  { value: 'RUNNING', label: 'Running' },
                ]}
              />
            </div>
          </div>

          {demoStatus === 'OFFLINE' && (
            <p className="mt-3 flex items-center gap-2 rounded-[12px] bg-sunken px-3 py-2 text-[13px] text-ink-2">
              <ServerOff aria-hidden className="size-4 shrink-0 text-ink-3" /> Server offline. Imported sessions are hidden until it is back.
            </p>
          )}
          <div className="mt-4">
            {sessions.isPending ? (
              <LoadingRows rows={6} />
            ) : sessions.isError ? (
              <ErrorState error={sessions.error} onRetry={() => sessions.refetch()} />
            ) : all.length === 0 ? (
              <EmptyState icon={FolderOpen} title="No sessions yet" action={importButton}>
                Import a permitted recording to start a replay. Nothing is shared with your account yet.
              </EmptyState>
            ) : filtered.length === 0 ? (
              <EmptyState icon={Search} title="No sessions match">
                Adjust the search or the status filter.
              </EmptyState>
            ) : (
              <SessionTable rows={filtered} selectedId={selectedId} onSelect={select} />
            )}
          </div>
        </Card>

        <div className="flex min-w-0 flex-col gap-5">
          {sessions.isPending ? (
            <Card className="p-6">
              <Skeleton className="h-7 w-2/3" />
              <Skeleton className="mt-6 h-40 w-full" />
            </Card>
          ) : (
            selectedId &&
            (() => {
              const sel = all.find((s) => s.id === selectedId);
              if (!sel) return null;
              return isProcessing(sel) ? <ProcessingRail s={sel} /> : <SessionDetailRail id={selectedId} />;
            })()
          )}
          <NeedsChecking sessions={all} onSelect={select} />
        </div>
      </div>
    </>
  );
}

const CONTINUE_LABEL: Record<string, string> = { workspace: 'Workspace', memory: 'Memory', 'memory/runway': 'Runway memory', 'review/findings': 'Review · Findings', 'review/transcript': 'Review · Transcript', 'review/options': 'Review · Options', debrief: 'Debrief', metrics: 'Metrics', ask: 'Ask' };

/** Picks up where the user left off: the last session and screen they had open. */
function ContinueCard({ sessions }: { sessions: SessionSummary[] }) {
  const id = lastSession();
  const s = sessions.find((x) => x.id === id && x.latest_run_id);
  if (!s) return null;
  const area = lastArea();
  const label = CONTINUE_LABEL[area] ?? 'Workspace';
  const scope = { sid: s.id, run: s.latest_run_id };
  return (
    <Card className="mb-5 flex flex-wrap items-center gap-x-5 gap-y-3 px-5 py-4" aria-labelledby="continue-title">
      <IconTile icon={History} tone="data" />
      <div className="min-w-0 flex-1">
        <p className="text-[13px] font-medium uppercase tracking-[0.06em] text-ink-2">Continue where you left off</p>
        <p id="continue-title" className="truncate text-[17px] font-semibold tracking-[-0.01em] text-ink" title={s.title}>
          {s.title} <span className="font-normal text-ink-2">· {label} · run {s.latest_run_label?.split(' ')[0]}</span>
        </p>
        <p className="text-[14px] text-ink-2">{s.open_findings ? `${plural(s.open_findings, 'open finding')} to review` : 'No open findings'}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2.5">
        {s.open_findings > 0 && area !== 'review/findings' && (
          <Button asChild variant="secondary">
            <Link to={sessionHref('review/findings', scope)}>
              <NotebookText /> Review findings
            </Link>
          </Button>
        )}
        <Button asChild variant="primary">
          <Link to={sessionHref(area, scope)}>
            Continue <ArrowRight />
          </Link>
        </Button>
      </div>
    </Card>
  );
}

function SummaryStrip({ sessions, loading }: { sessions: SessionSummary[]; loading: boolean }) {
  const ready = sessions.filter((s) => s.source_ready).length;
  const partial = sessions.filter((s) => s.analysis === 'PARTIAL').length;
  const notReviewed = sessions.filter((s) => s.domain_validation !== 'DOMAIN_REVIEWED').length;
  const items: { icon: typeof FileText; tone: Tone; title: string; detail: string }[] = [
    { icon: FileText, tone: 'data', title: plural(sessions.length, 'session'), detail: 'Total in workspace' },
    { icon: CircleCheck, tone: 'ready', title: `${ready} sources ready`, detail: ready === sessions.length ? 'All source data available' : 'Some sources still preparing' },
    { icon: Clock3, tone: 'discrepancy', title: `${partial} partial ${partial === 1 ? 'analysis' : 'analyses'}`, detail: 'Need further review' },
    { icon: TriangleAlert, tone: 'notice', title: 'Not domain reviewed', detail: notReviewed === sessions.length ? 'All sessions awaiting review' : `${notReviewed} awaiting review` },
  ];
  return (
    <Card className="grid grid-cols-1 divide-y divide-hairline px-2 sm:grid-cols-2 sm:divide-y-0 xl:grid-cols-4 xl:divide-x">
      {items.map((i) => (
        <div key={i.title} className="flex items-center gap-3.5 px-4 py-3.5">
          <IconTile icon={i.icon} tone={i.tone} />
          {loading ? (
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3.5 w-32" />
            </div>
          ) : (
            <div className="min-w-0">
              <p className="text-[16px] font-semibold tracking-[-0.01em] text-ink">{i.title}</p>
              <p className="text-[14px] text-ink-2">{i.detail}</p>
            </div>
          )}
        </div>
      ))}
    </Card>
  );
}

function AnalysisCell({ s }: { s: SessionSummary }) {
  const meta = STATUS.analysis[s.analysis];
  return (
    <span className="inline-flex items-center gap-2.5 whitespace-nowrap text-[15px] text-ink">
      <Dot tone={meta.tone} />
      {meta.label}
    </span>
  );
}

/** DEMO track: a backend workspace whose MOCK processing has not finished. */
function isProcessing(s: SessionSummary) {
  return s.origin === 'DEMO_BACKEND' && s.lifecycle === 'PREPARING';
}

const progressHref = (s: SessionSummary) => `/sessions/import?workspace=${s.id}`;

function ProcessingRail({ s }: { s: SessionSummary }) {
  const note = s.notices[0];
  const pct = Number(/(\d+)%/.exec(note?.title ?? '')?.[1] ?? 0);
  return (
    <Card className="p-6" aria-labelledby="session-detail-title">
      <h2 id="session-detail-title" className="text-[22px] font-semibold leading-tight tracking-[-0.02em] text-ink">
        {s.title}
      </h2>
      <p className="mt-1 text-[13px] text-ink-2">Demo workspace · processing</p>
      <div className="mt-5">
        <div className="flex items-center justify-between text-[14px]">
          <span className="font-medium text-ink">{note?.detail ?? 'Processing'}</span>
          <span className="tabular text-ink-2">{pct}%</span>
        </div>
        <Progress className="mt-2" value={pct} label="Processing progress" />
      </div>
      <Button asChild variant="primary" className="mt-5 w-full">
        <Link to={progressHref(s)}>
          View progress <ChevronRight />
        </Link>
      </Button>
      <p className="mt-2 text-center text-[13px] text-ink-2">The workspace opens when processing finishes.</p>
    </Card>
  );
}

function SessionTable({ rows, selectedId, onSelect }: { rows: SessionSummary[]; selectedId: string | null; onSelect: (id: string) => void }) {
  const navigate = useNavigate();
  return (
    <div id="session-table" className="relative -mx-2 overflow-x-auto">
      <table className="w-full min-w-[600px] border-separate border-spacing-0 text-left">
        <caption className="sr-only">Sessions</caption>
        <thead>
          <tr className="text-[14px] text-ink-2">
            <th scope="col" className="px-5 pb-3 font-normal">Session</th>
            <th scope="col" className="px-3 pb-3 font-normal">Duration</th>
            <th scope="col" className="px-3 pb-3 font-normal">Analysis</th>
            <th scope="col" aria-sort="descending" className="px-3 pb-3 font-normal">
              <span className="inline-flex items-center gap-1">Updated <ArrowDown aria-hidden className="size-3.5" /></span>
            </th>
            <th scope="col" className="w-14 pb-3"><span className="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((s) => {
            const selected = s.id === selectedId;
            return (
              <tr key={s.id} onClick={() => onSelect(s.id)} aria-selected={selected} className={cn('group cursor-pointer transition-colors duration-[140ms]', selected ? 'bg-data-tint' : 'hover:bg-sunken')}>
                <td className={cn('relative rounded-l-[14px] border-t border-hairline px-5 py-3.5 group-first:border-t-0', selected && 'border-transparent')}>
                  {selected && <span aria-hidden className="absolute inset-y-1 left-0 w-[3px] rounded-full bg-data" />}
                  {/* The title opens the workspace (Enter on focus); clicking elsewhere in the row selects. */}
                  <span className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
                    {isProcessing(s) ? (
                      <Link to={progressHref(s)} onClick={(e) => e.stopPropagation()} className="text-[16px] font-semibold tracking-[-0.01em] text-ink underline-offset-4 hover:underline focus-visible:outline-offset-4">
                        {s.title}
                      </Link>
                    ) : s.latest_run_id ? (
                      <Link to={sessionHref('workspace', { sid: s.id, run: s.latest_run_id })} onClick={(e) => e.stopPropagation()} className="text-[16px] font-semibold tracking-[-0.01em] text-ink underline-offset-4 hover:underline focus-visible:outline-offset-4">
                        {s.title}
                      </Link>
                    ) : (
                      <button type="button" onClick={() => onSelect(s.id)} className="text-left text-[16px] font-semibold tracking-[-0.01em] text-ink focus-visible:outline-offset-4">
                        {s.title}
                      </button>
                    )}
                    {s.lifecycle === 'ARCHIVED' && <span className="rounded-full border border-hairline px-2 py-px text-[12px] font-medium text-ink-2">Archived</span>}
                  </span>
                  <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[14px] text-ink-2">
                    {s.context}
                  </span>
                </td>
                <td className={cn('border-t border-hairline px-3 py-3.5 text-[15px] text-ink tabular group-first:border-t-0', selected && 'border-transparent')}>{formatDuration(s.duration_ms)}</td>
                <td className={cn('border-t border-hairline px-3 py-3.5 group-first:border-t-0', selected && 'border-transparent')}>
                  <AnalysisCell s={s} />
                </td>
                <td className={cn('border-t border-hairline px-3 py-3.5 group-first:border-t-0', selected && 'border-transparent')}>
                  <span className="block whitespace-nowrap text-[15px] text-ink tabular">{formatDate(s.updated_at)}</span>
                  <span className="block text-[13px] text-ink-2 tabular">{formatTimeUtc(s.updated_at)}</span>
                </td>
                <td className={cn('rounded-r-[14px] border-t border-hairline py-3.5 pr-3 text-right group-first:border-t-0', selected && 'border-transparent')} onClick={(e) => e.stopPropagation()}>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <MoreButton label={`Actions for ${s.title}`} className="size-9 border-transparent bg-transparent hover:bg-surface" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                      <DropdownMenuItem disabled={!s.latest_run_id} onSelect={() => navigate(sessionHref('workspace', { sid: s.id, run: s.latest_run_id }))}>
                        <FolderOpen /> Open workspace
                      </DropdownMenuItem>
                      <DropdownMenuItem disabled={!s.latest_run_id} onSelect={() => navigate(sessionHref('review/findings', { sid: s.id, run: s.latest_run_id }))}>
                        <NotebookText /> Review findings
                      </DropdownMenuItem>
                      <DropdownMenuItem disabled={!s.latest_run_id} onSelect={() => navigate(sessionHref('debrief', { sid: s.id, run: s.latest_run_id }))}>
                        <BookOpenCheck /> Debrief
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onSelect={() => {
                          void navigator.clipboard?.writeText(`${window.location.origin}/sessions?selected=${s.id}`);
                          toast.success('Link copied', { description: 'Only accounts with a grant can open it.' });
                        }}
                      >
                        <Link2 /> Copy link
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ReadinessRow({ tone, icon, title, detail }: { tone: Tone; icon: typeof CircleCheck; title: string; detail: string }) {
  return (
    <li className="flex items-start gap-3.5">
      <IconTile icon={icon} tone={tone} size="sm" className="mt-0.5" />
      <div className="min-w-0">
        <p className="text-[15px] font-semibold text-ink">{title}</p>
        <p className="text-[14px] text-ink-2">{detail}</p>
      </div>
    </li>
  );
}

function SessionDetailRail({ id }: { id: string }) {
  const api = useApi();
  const navigate = useNavigate();
  const detail = useQuery({ queryKey: qk.session(id), queryFn: () => api.getSession(id) });
  if (detail.isPending)
    return (
      <Card className="p-6">
        <Skeleton className="h-7 w-2/3" />
        <Skeleton className="mt-6 h-40 w-full" />
      </Card>
    );
  if (detail.isError)
    return (
      <Card className="p-2">
        <ErrorState error={detail.error} onRetry={() => detail.refetch()} />
      </Card>
    );
  const s = detail.data;
  const run = s.runs.find((r) => r.run.id === s.latest_run_id);
  const analysis = (() => {
    switch (s.analysis) {
      case 'COMPLETED':
        return { tone: 'ready' as Tone, icon: CircleCheck, title: 'Analysis stored', detail: run?.completed_at ? `Last updated ${formatDateTimeUtc(run.completed_at)}` : 'Results available' };
      case 'PARTIAL':
        return { tone: 'discrepancy' as Tone, icon: Clock3, title: 'Analysis partial', detail: run?.coverage_note ?? 'Some segments were not analysed' };
      case 'RUNNING':
      case 'QUEUED':
        return { tone: 'data' as Tone, icon: Activity, title: 'Analysis running', detail: 'Results appear as jobs complete' };
      case 'FAILED':
        return { tone: 'discrepancy' as Tone, icon: ShieldAlert, title: 'Analysis failed', detail: run?.failure?.message ?? 'See jobs in Settings' };
      default:
        return { tone: 'muted' as Tone, icon: Clock3, title: 'Not analysed', detail: s.permissions.cloud_audio.state !== 'ALLOWED' ? `Cloud audio permission is ${s.permissions.cloud_audio.state.toLowerCase()}` : 'Start an analysis when ready' };
    }
  })();
  const canOpen = !!s.latest_run_id;

  return (
    <Card className="p-6" aria-labelledby="session-detail-title">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id="session-detail-title" className="text-[22px] font-semibold leading-tight tracking-[-0.02em] text-ink">{s.title}</h2>
          {s.lifecycle === 'ARCHIVED' && <p className="mt-1 text-[13px] text-ink-2">Archived · read-only</p>}
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <MoreButton label="Session actions" />
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem disabled={!canOpen} onSelect={() => navigate(sessionHref('review/transcript', { sid: s.id, run: s.latest_run_id }))}>
              <NotebookText /> Review transcript
            </DropdownMenuItem>
            <DropdownMenuItem disabled={!canOpen} onSelect={() => navigate(sessionHref('debrief', { sid: s.id, run: s.latest_run_id }))}>
              <BookOpenCheck /> Open debrief
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <ul className="mt-5 space-y-4" aria-label="Readiness">
        <ReadinessRow tone={s.source_ready ? 'ready' : 'muted'} icon={CircleCheck} title={s.source_ready ? 'Source ready' : 'Source preparing'} detail={`${plural(s.channels.length, 'audio channel')} available`} />
        <ReadinessRow {...analysis} />
        <ReadinessRow tone="notice" icon={TriangleAlert} title="Domain review not done" detail="Needs review by a domain researcher" />
      </ul>

      <dl className="mt-5 divide-y divide-hairline border-t border-hairline">
        <FactRow icon={Activity} label={plural(s.channels.length, 'audio channel')} value={s.channels.map((c) => c.role.split(' ')[0]).join(' · ')} />
        <FactRow icon={Layers} label={s.has_tracks ? 'Track & layout available' : s.has_layout ? 'Layout only · no tracks' : 'Audio only · no layout'} value={s.layout_label ?? '—'} />
        <FactRow icon={FileText} label={run ? `Run ${run.label} · revision ${run.input_revision}` : 'No analysis run'} value={run ? `v${run.input_revision}` : '—'} />
        {canOpen ? (
          <div>
            <dt className="sr-only">Findings</dt>
            <dd>
              <Link to={sessionHref('review/findings', { sid: s.id, run: s.latest_run_id })} className="group flex items-center gap-3 py-3 text-[15px] text-ink">
                <NotebookText aria-hidden className="size-[18px] text-ink-2" />
                <span className="flex-1">{plural(s.open_findings, 'open finding')}</span>
                <ChevronRight aria-hidden className="size-4 text-ink-2 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </dd>
          </div>
        ) : (
          <FactRow icon={NotebookText} label="No findings yet" value="—" />
        )}
      </dl>

      {canOpen ? (
        <Button asChild variant="primary" className="mt-4 w-full">
          <Link to={sessionHref('workspace', { sid: s.id, run: s.latest_run_id })}>
            Open workspace <ChevronRight />
          </Link>
        </Button>
      ) : (
        <div className="mt-4 space-y-2">
          <Button variant="primary" className="w-full" disabled>
            Open workspace <ChevronRight />
          </Button>
          <p className="text-center text-[13px] text-ink-2">Available after an analysis run completes.</p>
        </div>
      )}

      {s.layout && (
        <figure className="mt-4 overflow-hidden rounded-[16px] border border-hairline-soft">
          <div className="h-[104px]">
            <LayoutMini layout={s.layout} />
          </div>
          <figcaption className="flex items-center justify-between gap-2 bg-surface px-3 py-2 text-[12px] text-ink-2">
            <span className="truncate">{s.layout.caption}</span>
            {s.media && <span className="inline-flex h-5 items-center rounded-full bg-track px-2 text-[11px] text-ink-2">{s.media.recordings.length > 1 ? `${s.media.recordings.length} recordings` : 'Audio'}</span>}
          </figcaption>
        </figure>
      )}
    </Card>
  );
}

function FactRow({ icon: Icon, label, value }: { icon: typeof FileText; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 py-3">
      <Icon aria-hidden className="size-[18px] text-ink-2" />
      <dt className="flex-1 text-[15px] text-ink">{label}</dt>
      <dd className="text-[14px] text-ink-2">{value}</dd>
    </div>
  );
}

/**
 * Where a notice is resolved: findings to Review, divergence and gaps to the
 * Workspace attention rail; permission and partial-analysis notices stay on Sessions,
 * where the detail rail explains them.
 */
function noticeHref(s: SessionSummary, n: Notice): string | null {
  if (!s.latest_run_id) return null;
  const scope = { sid: s.id, run: s.latest_run_id };
  if (/finding/i.test(n.title)) return sessionHref('review/findings', scope);
  if (/divergence|discrepan|gap/i.test(n.title)) return sessionHref('workspace', scope);
  return null;
}

function NeedsChecking({ sessions, onSelect }: { sessions: SessionSummary[]; onSelect: (id: string) => void }) {
  const navigate = useNavigate();
  const items = sessions.flatMap((s) => s.notices.map((n) => ({ ...n, session: s, href: noticeHref(s, n) })));
  return (
    <Card className="p-6" aria-labelledby="needs-checking">
      <h2 id="needs-checking" className="text-[19px] font-semibold tracking-[-0.015em] text-ink">Needs checking</h2>
      <p className="text-[14px] text-ink-2">{items.length ? plural(items.length, 'item') : 'Nothing needs checking'}</p>
      {items.length > 0 && (
        <ul className="mt-3 divide-y divide-hairline">
          {items.slice(0, 5).map((n) => (
            <li key={n.id}>
              <button type="button" onClick={() => (n.href ? navigate(n.href) : onSelect(n.session.id))} className="group flex w-full items-center gap-3.5 py-3 text-left">
                <IconTile icon={n.tone === 'discrepancy' ? Clock3 : TriangleAlert} tone={n.tone} />
                <span className="min-w-0 flex-1">
                  <span className="block text-[15px] font-semibold text-ink">{n.title}</span>
                  <span className="block truncate text-[13.5px] text-ink-2">{n.session.title} · {n.detail}</span>
                </span>
                <ChevronRight aria-hidden className="size-4 text-ink-2 transition-transform group-hover:translate-x-0.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

const AREA_LABEL: Record<string, string> = { workspace: 'Workspace', review: 'Review', debrief: 'Debrief', memory: 'Memory', metrics: 'Metrics', ask: 'Ask' };

/** Session picker for links that name an area but no session (e.g. a bookmarked /choose/review). */
export function ChooseSessionPage() {
  const api = useApi();
  const navigate = useNavigate();
  const { area = 'workspace' } = useParams();
  const target = area === 'review' ? 'review/findings' : AREA_LABEL[area] ? area : 'workspace';
  const sessions = useQuery({ queryKey: qk.sessions, queryFn: () => api.listSessions() });
  const ready = (sessions.data ?? []).filter((s) => s.latest_run_id);
  return (
    <Card className="mx-auto mt-10 max-w-xl p-6">
      <h1 className="text-[26px] font-semibold tracking-[-0.03em] text-ink">Choose a session</h1>
      <p className="mt-1 text-[15px] text-ink-2">{AREA_LABEL[area] ?? 'Workspace'} opens within one session and analysis run.</p>
      <div className="mt-4">
        {sessions.isPending ? (
          <LoadingRows rows={4} />
        ) : sessions.isError ? (
          <ErrorState error={sessions.error} onRetry={() => sessions.refetch()} />
        ) : ready.length ? (
          <SessionList sessions={ready} currentId={null} onPick={(s) => navigate(sessionHref(target as SessionArea, { sid: s.id, run: s.latest_run_id }))} />
        ) : (
          <EmptyState icon={FolderOpen} title="No analysed sessions yet" action={<Button asChild variant="primary"><Link to="/sessions">Go to sessions</Link></Button>}>
            A session needs a completed analysis run before it can be opened here.
          </EmptyState>
        )}
      </div>
    </Card>
  );
}
