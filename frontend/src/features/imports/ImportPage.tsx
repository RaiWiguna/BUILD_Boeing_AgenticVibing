/**
 * Import (DEMO track, ADR 0003): a session name plus the main recording (radio audio +
 * ADS-B CSV), with optional recordings before and after it. The demo backend
 * recognises the scenario files by name and checksum, stores the session in
 * PostgreSQL and runs the processing schedule. No source kind is asked.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ArrowRight, Check, CircleCheck, FolderUp, Loader2, ServerOff, TriangleAlert, Upload } from 'lucide-react';
import { useEffect, useRef, useState, type DragEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { toast } from 'sonner';
import { demoCode, type DemoWorkspace, type ProcessingStep } from '@/api/demo';
import { qk } from '@/api/queryKeys';
import { Card, SectionLabel } from '@/components/domain/primitives';
import { Callout, ErrorState } from '@/components/domain/states';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/controls';
import { Input, Label } from '@/components/ui/input';
import { useApi, useDemo } from '@/hooks/useApi';
import { RequireCapability } from '@/app/routing/guards';
import { formatBytes } from '@/lib/time';
import { cn } from '@/lib/utils';
import { EMPTY_SLOTS, place, placedFiles, RecordingSlots, slotsReady, type Slots } from './RecordingSlots';

export function ImportPage() {
  return (
    <RequireCapability cap="session.import" title="Import not available">
      <ImportFlow />
    </RequireCapability>
  );
}

function ImportFlow() {
  const [params, setParams] = useSearchParams();
  const workspaceId = params.get('workspace');
  return (
    <>
      <PageHeader breadcrumb={[{ label: 'Sessions', to: '/sessions' }, { label: workspaceId ? 'Processing' : 'Import' }]} title={workspaceId ? 'Processing' : 'Import session'} />
      {workspaceId ? <ProcessingView workspaceId={workspaceId} /> : <UploadForm onCreated={(w) => setParams({ workspace: w.id }, { replace: true })} />}
    </>
  );
}

/** Scenario file list for placing and checking files. */
function useScenarioFiles() {
  const demoApi = useDemo();
  const health = useQuery({ queryKey: ['demo', 'health'], queryFn: () => demoApi.health(), retry: false, refetchInterval: (q) => (q.state.status === 'error' ? 4000 : false) });
  const scenarios = useQuery({ queryKey: ['demo', 'scenarios'], queryFn: () => demoApi.scenarios(), enabled: health.isSuccess });
  return { offline: health.isError, known: scenarios.data };
}

/* ── Upload ──────────────────────────────────────────────────────────── */

function UploadForm({ onCreated }: { onCreated: (w: DemoWorkspace) => void }) {
  const api = useApi();
  const demoApi = useDemo();
  const qc = useQueryClient();
  const [name, setName] = useState('');
  const [slots, setSlots] = useState<Slots>(EMPTY_SLOTS);
  const [rejected, setRejected] = useState<string[]>([]);
  // Files chosen before the scenario list loads are placed once it arrives.
  const [unplaced, setUnplaced] = useState<File[]>([]);
  const [upload, setUpload] = useState<{ loaded: number; total: number } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const abort = useRef<AbortController | null>(null);
  const { offline, known: catalogue } = useScenarioFiles();
  const [caseId, setCaseId] = useState('');
  const choice = catalogue?.scenarios?.find((x) => x.id === caseId);
  // Legacy uploads use the existing default case; new cases are explicitly scoped.
  const legacy = catalogue?.scenarios?.find((x) => !x.limits);
  const selected = choice ?? legacy;
  const known = selected ? { files: selected.files, expected_files: selected.files.map((f) => f.name), limits: selected.limits } : catalogue;
  if (known && unplaced.length) {
    const r = place(slots, unplaced, known, 'main');
    setSlots(r.slots);
    setRejected(r.rejected);
    setUnplaced([]);
  }
  const sessions = useQuery({ queryKey: qk.sessions, queryFn: () => api.listSessions() });
  const trimmed = name.trim();
  const duplicate = !!trimmed && (sessions.data ?? []).some((s) => s.title.trim().toLowerCase() === trimmed.toLowerCase());
  const nameTaken = demoCode(error) === 'NAME_TAKEN';
  const uploading = upload != null;
  const files = placedFiles(slots);
  const ready = slotsReady(slots, known) && !!trimmed && !duplicate && !offline && !uploading;

  useEffect(() => () => abort.current?.abort(), []);

  const change = (next: Slots, bad: string[]) => {
    setSlots(next);
    setRejected(bad);
    setError(null);
  };

  const submit = async () => {
    if (!ready) return;
    setError(null);
    abort.current = new AbortController();
    setUpload({ loaded: 0, total: files.reduce((n, f) => n + f.file.size, 0) });
    try {
      const w = await demoApi.createWorkspace(trimmed, files, (loaded, total) => setUpload({ loaded, total }), abort.current.signal, selected?.id);
      qc.invalidateQueries({ queryKey: qk.sessions });
      onCreated(w);
    } catch (e) {
      setError(e);
      setUpload(null);
    }
  };

  return (
    <div className="mx-auto mt-6 max-w-[860px]">
      <Card className="p-7">
        {offline && (
          <Callout tone="notice" icon={ServerOff} title="Import is unavailable" className="mb-5">
            The server is not reachable. Existing sessions still open.
          </Callout>
        )}
        <div className="max-w-[460px] space-y-2">
          <Label htmlFor="imp-name">Session name</Label>
          <Input id="imp-name" value={name} maxLength={80} placeholder="e.g. KAGC ground · 10 Sep" onChange={(e) => (setName(e.target.value), nameTaken && setError(null))} aria-invalid={duplicate || nameTaken || undefined} aria-describedby={duplicate || nameTaken ? 'imp-name-error' : undefined} disabled={uploading} />
          {(duplicate || nameTaken) && (
            <p id="imp-name-error" className="text-[13px] text-discrepancy">
              A session with this name already exists.
            </p>
          )}
        </div>

        {catalogue?.scenarios && catalogue.scenarios.length > 1 && (
          <div className="mt-5 space-y-2">
            <Label htmlFor="imp-case">Case</Label>
            <select id="imp-case" className="h-11 w-full rounded-[12px] border border-hairline bg-surface px-3 text-[14px]" value={selected?.id ?? ''} disabled={uploading} onChange={(e) => {
              setCaseId(e.target.value); setSlots(EMPTY_SLOTS); setUnplaced([]); setRejected([]); setError(null);
            }}>
              {catalogue.scenarios.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
          </div>
        )}
        <div className="mt-7 flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-[17px] font-semibold text-ink">Recordings</h2>
          <BulkPicker
            disabled={uploading}
            onFiles={(list) => {
              if (!known) return setUnplaced((u) => [...u, ...list]);
              const r = place(slots, list, known, 'main');
              change(r.slots, r.rejected);
            }}
          />
        </div>
        <div className="mt-3">
          <RecordingSlots slots={slots} onChange={change} known={known} disabled={uploading} />
        </div>
        {rejected.length > 0 && <p className="mt-2 text-[13px] text-discrepancy">Not added: {rejected.join(', ')}. Check the selected case, file type, and recording limits.</p>}

        {uploading && (
          <div className="mt-5" aria-live="polite">
            <div className="flex items-center justify-between text-[14px]">
              <span className="font-medium text-ink">Uploading…</span>
              <span className="tabular text-ink-2">
                {formatBytes(upload.loaded)} / {formatBytes(upload.total)}
              </span>
            </div>
            <Progress className="mt-2" value={upload.total ? (upload.loaded / upload.total) * 100 : 0} label="Upload progress" />
          </div>
        )}
        {error != null && !nameTaken && <ErrorState compact className="mt-4" error={error} />}

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <Button asChild variant="ghost">
            <Link to="/sessions">
              <ArrowLeft /> Cancel
            </Link>
          </Button>
          <Button variant="primary" disabled={!ready} onClick={submit}>
            {uploading ? <Loader2 className="animate-spin" /> : <Upload />}
            Upload and process
          </Button>
        </div>
      </Card>
    </div>
  );
}

/** "Choose files" for several files at once; also a drop target. Files are placed by name. */
function BulkPicker({ onFiles, disabled }: { onFiles: (files: File[]) => void; disabled?: boolean }) {
  const ref = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  return (
    <div
      onDragOver={(e: DragEvent) => {
        e.preventDefault();
        if (!disabled) setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e: DragEvent) => {
        e.preventDefault();
        setOver(false);
        if (!disabled) onFiles(Array.from(e.dataTransfer.files));
      }}
      className={cn('rounded-[12px] transition-colors', over && 'bg-data-tint ring-2 ring-data')}
    >
      <input ref={ref} type="file" multiple accept=".wav,.csv" className="sr-only" onChange={(e) => (e.target.files && onFiles(Array.from(e.target.files)), (e.target.value = ''))} tabIndex={-1} aria-hidden />
      <Button variant="secondary" size="sm" disabled={disabled} onClick={() => ref.current?.click()}>
        <FolderUp /> Choose files
      </Button>
    </div>
  );
}

/* ── Processing ──────────────────────────────────────────────────────── */

function ProcessingView({ workspaceId }: { workspaceId: string }) {
  const demoApi = useDemo();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [openError, setOpenError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const started = useRef(-1);
  const ws = useQuery({
    queryKey: ['demo', 'workspace', workspaceId],
    queryFn: () => demoApi.getWorkspace(workspaceId),
    refetchInterval: (q) => (q.state.data?.status === 'PROCESSING' || q.state.status === 'error' ? 500 : false),
    // Keep the steps moving when the tab is in the background, so returning never shows a stale state.
    refetchIntervalInBackground: true,
    retry: false,
  });
  const w = ws.data;
  const done = w?.status === 'READY';

  useEffect(() => {
    if (!done || started.current === attempt) return;
    started.current = attempt;
    demoApi
      .registerWorkspace(workspaceId)
      .then(() => {
        qc.invalidateQueries({ queryKey: qk.sessions });
        // Drop the previous version of a reprocessed session so it never renders on reopen.
        qc.removeQueries({ queryKey: qk.session(workspaceId) });
        toast.success(`${w!.name} is ready to play`);
        navigate(`/s/${workspaceId}/workspace`, { replace: true });
      })
      .catch((e: unknown) => setOpenError(e));
  }, [done, attempt, workspaceId, qc, navigate, w, demoApi]);

  if (ws.isPending) return <Card className="mx-auto mt-6 max-w-[860px] p-7"><Loader2 className="mx-auto size-6 animate-spin text-data" aria-label="Loading" /></Card>;
  if (!w) return <Card className="mx-auto mt-6 max-w-[860px] p-2"><ErrorState error={ws.error} onRetry={() => ws.refetch()} /></Card>;

  const pct = Math.round(w.progress * 100);
  return (
    <div className="mx-auto mt-6 max-w-[860px]">
      <Card className="p-7">
        <div className="min-w-0">
          <SectionLabel>{w.recordings.length > 1 ? `${w.recordings.length} recordings` : 'Session'}</SectionLabel>
          <h2 className="mt-1 truncate text-section font-semibold text-ink">{w.name}</h2>
        </div>
        <div className="mt-5" aria-live="polite">
          <div className="flex items-center justify-between text-[14px]">
            <span className="font-medium text-ink">{done ? 'Ready · opening…' : (w.steps.find((s) => s.status === 'RUNNING')?.label ?? 'Starting…')}</span>
            <span className="tabular text-ink-2">
              {pct}%{!done && w.eta_ms > 0 ? ` · about ${Math.ceil(w.eta_ms / 1000)} s left` : ''}
            </span>
          </div>
          <Progress className="mt-2 h-2.5" value={pct} tone={done ? 'ready' : 'data'} label="Processing progress" />
        </div>
        <ol className="mt-6 space-y-1" aria-label="Processing steps">
          {w.steps.map((s, i) => (
            <StepRow key={s.key} step={s} index={i} />
          ))}
        </ol>
        {ws.isError && <p className="mt-4 text-[13px] text-notice">Connection lost. Retrying…</p>}
        {openError != null && (
          <ErrorState
            compact
            className="mt-4"
            error={openError}
            onRetry={() => {
              setOpenError(null);
              setAttempt((a) => a + 1);
            }}
          />
        )}
        <p className="mt-5 text-[13px] text-ink-3">You can leave this page. The session keeps processing and appears in Sessions.</p>
        <div className="mt-5 flex flex-wrap justify-between gap-3">
          <Button asChild variant="ghost">
            <Link to="/sessions">
              <ArrowLeft /> Back to sessions
            </Link>
          </Button>
          {done && (
            <Button variant="primary" onClick={() => navigate(`/s/${workspaceId}/workspace`)} disabled={openError == null}>
              Open workspace <ArrowRight />
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}

function StepRow({ step, index }: { step: ProcessingStep; index: number }) {
  const running = step.status === 'RUNNING';
  const doneStep = step.status === 'DONE';
  // Running: lines appear as the step advances. Done: one summary line plus warnings.
  const lines = running ? step.detail.slice(0, Math.max(1, Math.ceil(step.detail.length * step.progress))) : doneStep ? (step.summary ?? step.detail) : [];
  return (
    <li className={cn('rounded-[14px] px-3 py-2.5 transition-colors', running && 'bg-data-tint/60')} aria-current={running ? 'step' : undefined}>
      <div className="flex items-center gap-3">
        <span className={cn('inline-flex size-7 shrink-0 items-center justify-center rounded-full text-[12px] font-semibold tabular', doneStep ? 'bg-ready-tint text-ready' : running ? 'bg-data text-white' : 'bg-track text-ink-3')}>
          {doneStep ? <Check className="size-4" aria-label="Done" /> : running ? <Loader2 className="size-4 animate-spin" aria-label="Running" /> : index + 1}
        </span>
        <span className={cn('min-w-0 flex-1 text-[15px]', step.status === 'PENDING' ? 'text-ink-3' : 'font-medium text-ink')}>{step.label}</span>
        {running && <span className="w-10 text-right text-[12.5px] tabular text-data-strong">{Math.round(step.progress * 100)}%</span>}
        {doneStep && <CircleCheck aria-hidden className="size-4 text-ready" />}
      </div>
      {lines.length > 0 && (
        <ul className="ml-10 mt-1 space-y-0.5">
          {lines.map((d) => {
            const warn = d.startsWith('⚠');
            return (
              <li key={d} className={cn('flex items-start gap-1.5 text-[13px]', warn ? 'text-notice' : 'text-ink-2', running && 'animate-in fade-in duration-300')}>
                {warn ? <TriangleAlert aria-hidden className="mt-0.5 size-3.5 shrink-0" /> : <span aria-hidden className="mt-[7px] size-1 shrink-0 rounded-full bg-ink-3" />}
                <span className="min-w-0">{warn ? d.replace(/^⚠\s*/, '') : d}</span>
              </li>
            );
          })}
        </ul>
      )}
    </li>
  );
}
