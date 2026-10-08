import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  ArrowRight,
  AudioLines,
  BrainCircuit,
  Check,
  CircleCheck,
  CircleSlash,
  Clock3,
  Cloud,
  FileAudio,
  FileJson,
  FileSpreadsheet,
  FileText,
  Folder,
  Info,
  Loader2,
  Map,
  Play,
  Plus,
  Save,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  TriangleAlert,
  Upload,
  Volume2,
  ChevronRight,
  ChevronDown,
  Sparkles,
} from 'lucide-react';
import { useRef, useState, type DragEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { toast } from 'sonner';
import { isApiError } from '@/api/errors';
import { qk } from '@/api/queryKeys';
import type { ImportDraft, ImportFileInput, ImportFileView, PermissionKey, PermissionState, SourceKind } from '@/api/types';
import { useAuth } from '@/app/providers/AuthProvider';
import { MiniWave } from '@/components/domain/MiniWave';
import { Card, CodeChip, IconTile, MoreButton, Pill, SectionLabel, StatusPill } from '@/components/domain/primitives';
import { Callout, ErrorState } from '@/components/domain/states';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { Progress, RadioGroup, RadioRow, Select, Skeleton } from '@/components/ui/controls';
import { Dialog, DialogContent, DialogFooter } from '@/components/ui/dialog';
import { Input, Label, Textarea } from '@/components/ui/input';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/menu';
import { useApi } from '@/hooks/useApi';
import { useSessionStream } from '@/hooks/useSessionStream';
import { idemKey, releaseKeys } from '@/lib/idempotency';
import { STATUS } from '@/lib/status';
import { formatBytes, formatDate, formatDuration, formatTimeUtc } from '@/lib/time';
import { cn, plural } from '@/lib/utils';
import { RequireCapability } from '@/app/routing/guards';

type Step = 'source' | 'preview' | 'analysis';

const STEPS: { key: Step; label: string }[] = [
  { key: 'source', label: 'Source' },
  { key: 'preview', label: 'Preview & permissions' },
  { key: 'analysis', label: 'Analysis' },
];

const SAMPLE: ImportFileInput[] = [
  { name: 'tower.wav', size: 15_728_640, type: 'audio/wav' },
  { name: 'ground.flac', size: 9_437_184, type: 'audio/flac' },
  { name: 'layout.json', size: 23_552, type: 'application/json' },
];

export function ImportPage() {
  return (
    <RequireCapability cap="session.import" title="Import not available">
      <ImportWizard />
    </RequireCapability>
  );
}

function ImportWizard() {
  const [params, setParams] = useSearchParams();
  const step = (params.get('step') as Step) ?? 'source';
  const draftId = params.get('draft');
  const sessionId = params.get('session');
  const go = (next: Partial<Record<'step' | 'draft' | 'session', string>>) =>
    setParams((p) => {
      const n = new URLSearchParams(p);
      Object.entries(next).forEach(([k, v]) => v && n.set(k, v));
      return n;
    });

  return (
    <>
      <PageHeader breadcrumb={[{ label: 'Sessions', to: '/sessions' }, { label: 'Import' }]} title="Import session" />
      <Stepper current={step} />
      <div className="mt-6">
        {step === 'source' && <SourceStep onCreated={(d) => go({ step: 'preview', draft: d.id })} />}
        {step === 'preview' && draftId && <PreviewStep draftId={draftId} onSaved={(sid) => go({ step: 'analysis', session: sid })} />}
        {step === 'analysis' && sessionId && <AnalysisStep sessionId={sessionId} />}
        {((step === 'preview' && !draftId) || (step === 'analysis' && !sessionId)) && (
          <Card className="p-2">
            <ErrorState error={new Error('This import step needs a draft. Start again from Source.')} />
          </Card>
        )}
      </div>
    </>
  );
}

function Stepper({ current }: { current: Step }) {
  const idx = STEPS.findIndex((s) => s.key === current);
  return (
    <ol className="relative mx-auto flex max-w-[720px] items-center justify-center gap-3" aria-label="Import steps">
      {STEPS.map((s, i) => {
        const state = i < idx ? 'done' : i === idx ? 'current' : 'todo';
        return (
          <li key={s.key} className="flex items-center gap-3" aria-current={state === 'current' ? 'step' : undefined}>
            <span className={cn('inline-flex size-9 items-center justify-center rounded-full border text-[15px] font-semibold tabular transition-colors', state === 'current' ? 'border-data bg-data text-white shadow-[0_4px_12px_rgba(37,99,235,0.3)]' : state === 'done' ? 'border-data bg-data-tint text-data' : 'border-hairline-strong bg-surface text-ink-2')}>
              {state === 'done' ? <Check className="size-4" /> : i + 1}
            </span>
            <span className={cn('whitespace-nowrap text-[15px]', state === 'current' ? 'font-semibold text-ink' : 'text-ink-2 max-sm:sr-only')}>{s.label}</span>
            {i < STEPS.length - 1 && <span aria-hidden className={cn('mx-1 hidden h-px w-14 sm:block', i < idx ? 'bg-data' : 'bg-hairline-strong')} />}
          </li>
        );
      })}
    </ol>
  );
}

function fileIcon(name: string) {
  const n = name.toLowerCase();
  if (n.endsWith('.wav') || n.endsWith('.flac')) return FileAudio;
  if (n.endsWith('.json') || n.endsWith('.jsonl')) return FileJson;
  if (n.endsWith('.csv')) return FileSpreadsheet;
  return FileText;
}

function Dropzone({ onFiles, compact }: { onFiles: (files: ImportFileInput[]) => void; compact?: boolean }) {
  const ref = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const take = (list: FileList | null) => list && onFiles(Array.from(list).map((f) => ({ name: f.name, size: f.size, type: f.type })));
  return (
    <div
      onDragOver={(e: DragEvent) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e: DragEvent) => {
        e.preventDefault();
        setOver(false);
        take(e.dataTransfer.files);
      }}
      className={cn('flex flex-col items-center justify-center rounded-[16px] border-[1.5px] border-dashed text-center transition-colors', compact ? 'py-5' : 'py-12', over ? 'border-data bg-data-tint' : 'border-[#9db7ef] bg-[#fafcff]')}
    >
      <input ref={ref} type="file" multiple accept=".wav,.flac,.json,.jsonl,.csv" className="sr-only" onChange={(e) => take(e.target.files)} tabIndex={-1} aria-hidden />
      {!compact && <IconTile icon={Upload} tone="data" size="lg" />}
      <button type="button" onClick={() => ref.current?.click()} className={cn('inline-flex items-center gap-2 rounded-[10px] px-2 text-[16px] font-semibold text-data hover:underline underline-offset-4', !compact && 'mt-3')}>
        <span className="inline-flex size-6 items-center justify-center rounded-full bg-data text-white">
          <Plus className="size-4" />
        </span>
        {compact ? 'Add file' : 'Choose files'}
      </button>
      <p className="mt-1.5 text-[14px] text-ink-2">{compact ? 'WAV / FLAC · JSON / JSONL · CSV' : 'or drag them here · WAV / FLAC · JSON / JSONL · CSV · max 512 MiB per file'}</p>
    </div>
  );
}

function SourceStep({ onCreated }: { onCreated: (d: ImportDraft) => void }) {
  const api = useApi();
  const [title, setTitle] = useState('Audio-only · Tower');
  const [kind, setKind] = useState<SourceKind>('SYNTHETIC');
  const [files, setFiles] = useState<ImportFileInput[]>([]);
  const payload = { title, sourceKind: kind, files };
  const create = useMutation({
    mutationFn: () => api.createImport(payload, { idempotencyKey: idemKey('import.create', payload) }),
    onSuccess: (d) => {
      releaseKeys('import.create');
      onCreated(d);
    },
  });
  return (
    <div className="mx-auto grid max-w-[1080px] grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
      <Card className="p-7">
        <h2 className="text-section font-semibold text-ink">Source files</h2>
        <p className="mt-1 text-[14px] text-ink-2">Files are validated on the server before anything is stored. Preview never sends data to a cloud provider.</p>
        <div className="mt-6 grid gap-5 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="imp-title">Session name</Label>
            <Input id="imp-title" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Source kind</Label>
            <Select
              label="Source kind"
              className="w-full"
              value={kind}
              onValueChange={(v) => setKind(v as SourceKind)}
              options={[
                { value: 'SYNTHETIC', label: 'Synthetic (labelled)' },
                { value: 'ROLEPLAY', label: 'Consented role-play' },
              ]}
            />
          </div>
        </div>
        <div className="mt-6">
          <Dropzone onFiles={(f) => setFiles((cur) => [...cur, ...f])} />
        </div>
        {files.length > 0 && (
          <ul className="mt-4 divide-y divide-hairline rounded-[16px] border border-hairline">
            {files.map((f, i) => {
              const Icon = fileIcon(f.name);
              return (
                <li key={`${f.name}-${i}`} className="flex items-center gap-3 px-4 py-3">
                  <IconTile icon={Icon} tone="data" size="sm" />
                  <span className="min-w-0 flex-1 truncate text-[15px] text-ink">{f.name}</span>
                  <span className="text-[13px] text-ink-2 tabular">{formatBytes(f.size)}</span>
                  <Button variant="ghost" size="icon-sm" aria-label={`Remove ${f.name}`} onClick={() => setFiles((cur) => cur.filter((_, j) => j !== i))}>
                    <Trash2 />
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
        {create.isError && <ErrorState compact className="mt-4" error={create.error} />}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <Button asChild variant="ghost">
            <Link to="/sessions">
              <ArrowLeft /> Cancel
            </Link>
          </Button>
          <Button variant="primary" disabled={!files.length || !title.trim() || create.isPending} onClick={() => create.mutate()}>
            {create.isPending ? <Loader2 className="animate-spin" /> : null}
            Continue to preview <ArrowRight />
          </Button>
        </div>
      </Card>
      <div className="space-y-5">
        <Card className="p-6">
          <IconTile icon={Sparkles} tone="data" />
          <h3 className="mt-3 text-[17px] font-semibold text-ink">Try a sample bundle</h3>
          <p className="mt-1 text-[14px] text-ink-2">Adds a synthetic tower recording, a ground recording and a fictional layout file.</p>
          <Button variant="data" size="sm" className="mt-4" onClick={() => setFiles(SAMPLE)}>
            <Plus /> Use sample files
          </Button>
        </Card>
        <Card className="p-6">
          <SectionLabel>What happens next</SectionLabel>
          <ol className="mt-3 space-y-3 text-[14px] text-ink">
            {['Validate type, duration, channels and checksum', 'Record permissions and coverage', 'Save an immutable source', 'Start analysis only when you confirm'].map((t, i) => (
              <li key={t} className="flex gap-3">
                <span className="inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-track text-[12px] font-semibold text-ink-2 tabular">{i + 1}</span>
                {t}
              </li>
            ))}
          </ol>
        </Card>
      </div>
    </div>
  );
}

const PERMISSION_ROWS: { key: PermissionKey; label: string; icon: typeof Folder }[] = [
  { key: 'local_read', label: 'Local read', icon: Folder },
  { key: 'cloud_audio', label: 'Audio to cloud', icon: Cloud },
  { key: 'cloud_transcript', label: 'Transcript to cloud', icon: FileText },
  { key: 'reviewer_access', label: 'Reviewer access', icon: ShieldCheck },
  { key: 'report_export', label: 'Report export', icon: FileSpreadsheet },
  { key: 'audio_export', label: 'Audio export', icon: Volume2 },
];

function PreviewStep({ draftId, onSaved }: { draftId: string; onSaved: (sid: string) => void }) {
  const api = useApi();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { can } = useAuth();
  const draft = useQuery({
    queryKey: qk.import(draftId),
    queryFn: () => api.getImport(draftId),
    refetchInterval: (q) => (q.state.data?.status === 'VALIDATING' ? 600 : false),
  });
  const [editing, setEditing] = useState<PermissionKey | null>(null);
  const [advanced, setAdvanced] = useState(false);
  const setDraft = (d: ImportDraft) => qc.setQueryData(qk.import(draftId), d);
  const add = useMutation({ mutationFn: (files: ImportFileInput[]) => api.addImportFiles(draftId, files, { idempotencyKey: idemKey(`import.add.${draftId}`, files) }), onSuccess: setDraft });
  const remove = useMutation({ mutationFn: (fileId: string) => api.removeImportFile(draftId, fileId, { idempotencyKey: idemKey(`import.remove.${draftId}`, fileId) }), onSuccess: setDraft });
  const commit = useMutation({
    mutationFn: () => api.commitImport(draftId, { idempotencyKey: idemKey(`import.commit.${draftId}`, {}) }),
    onSuccess: (s) => {
      qc.invalidateQueries({ queryKey: qk.sessions });
      toast.success('Session saved', { description: `${s.title} · source stored, not analysed yet.` });
      onSaved(s.id);
    },
  });

  if (draft.isPending)
    return (
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
        <Card className="p-7">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="mt-6 h-48 w-full" />
        </Card>
        <Card className="p-7">
          <Skeleton className="h-48 w-full" />
        </Card>
      </div>
    );
  if (draft.isError) return <Card className="p-2"><ErrorState error={draft.error} onRetry={() => draft.refetch()} /></Card>;
  const d = draft.data;
  const validating = d.status === 'VALIDATING';
  const audio = d.files.filter((f) => f.kind === 'AUDIO');
  const duration = Math.max(0, ...audio.map((f) => f.duration_ms ?? 0));
  const blocking = d.issues.filter((i) => i.blocking);
  const notes = d.issues.filter((i) => !i.blocking);
  const cloudBlocked = d.permissions.cloud_audio.state !== 'ALLOWED' || d.permissions.cloud_transcript.state !== 'ALLOWED';
  const canSave = d.status === 'READY' && d.permissions.local_read.state === 'ALLOWED';
  const saveReason = validating ? 'Validation in progress…' : blocking.length ? `Resolve ${plural(blocking.length, 'blocking issue')} first.` : d.permissions.local_read.state !== 'ALLOWED' ? 'Local read permission is required.' : null;

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
      <div className="min-w-0 space-y-5">
        <Card className="p-7">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-section font-semibold text-ink">Source preview</h2>
              <div className="mt-2 flex flex-wrap items-center gap-2.5">
                <span className="text-[19px] font-semibold tracking-[-0.015em] text-ink">{d.title}</span>
                <CodeChip>{d.source_kind}</CodeChip>
                {validating ? <Pill tone="data" icon={Loader2} size="sm" className="[&_svg]:animate-spin">Validating</Pill> : d.status === 'READY' ? <Pill tone="ready" icon={CircleCheck} size="sm">Valid</Pill> : <Pill tone="discrepancy" icon={TriangleAlert} size="sm">Needs remediation</Pill>}
              </div>
              <p className="mt-1 text-[15px] text-ink-2 tabular">
                {plural(d.files.length, 'file')} · {plural(audio.reduce((n, f) => n + (f.channels ?? 0), 0), 'channel')} · {duration ? formatDuration(duration) : '—'} · {formatDate(d.clock.source_start_utc ?? new Date().toISOString())}
              </p>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <MoreButton label="Preview actions" />
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onSelect={() => setAdvanced((v) => !v)}>
                  <SlidersHorizontal /> {advanced ? 'Hide' : 'Show'} advanced metadata
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => navigate('/sessions')}>
                  <ArrowLeft /> Discard and return
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          <ul className="mt-5 divide-y divide-hairline overflow-hidden rounded-[18px] border border-hairline">
            {d.files.map((f) => (
              <FileRow key={f.id} f={f} validating={validating} onRemove={() => remove.mutate(f.id)} />
            ))}
          </ul>
          <div className="mt-3">
            <Dropzone compact onFiles={(files) => add.mutate(files)} />
          </div>

          <dl className="mt-4 grid grid-cols-2 divide-hairline rounded-[18px] border border-hairline sm:grid-cols-4 sm:divide-x">
            <Meta icon={Clock3} label="Source clock" value={d.clock.source_start_utc ? `${formatDate(d.clock.source_start_utc)}, ${formatTimeUtc(d.clock.source_start_utc)}` : 'Relative only'} />
            <Meta icon={SlidersHorizontal} label="Offset" value={`${d.clock.offset_ms ?? 0} ms ± ${d.clock.uncertainty_ms ?? '?'} ms`} />
            <Meta icon={Map} label="Fictional layout" value={d.layout_version ?? 'Not provided'} />
            <Meta icon={ShieldCheck} label="Checksum" value={validating ? 'Checking…' : d.checksum_verified ? 'Verified' : 'Pending'} ok={!validating && d.checksum_verified} />
          </dl>

          <button type="button" onClick={() => setAdvanced((v) => !v)} aria-expanded={advanced} className="mt-4 inline-flex items-center gap-1.5 text-[14px] font-medium text-ink-2 hover:text-ink">
            <ChevronDown className={cn('size-4 transition-transform', advanced && 'rotate-180')} /> Advanced metadata
          </button>
          {advanced && (
            <dl className="mt-3 grid gap-x-8 gap-y-2 rounded-[16px] bg-sunken p-4 text-[14px] sm:grid-cols-2">
              {[
                ['Timezone (origin)', d.clock.timezone],
                ['Clock mapping', d.clock.mapping_version ?? '—'],
                ['Coordinate system', d.layout_version ? 'FICTIONAL_LOCAL_XY' : '—'],
                ['Units', 'metres'],
                ['Identity mapping', 'From observation at import time'],
                ['Retention', d.retention_days ? `${d.retention_days} days` : 'Not set — blocks restricted data'],
                ['Coverage · audio', d.coverage.audio ? 'Yes' : 'No'],
                ['Coverage · tracks', d.coverage.tracks ? 'Yes' : 'No — movement disabled'],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 border-b border-hairline py-1.5 last:border-0">
                  <dt className="text-ink-2">{k}</dt>
                  <dd className="text-right text-ink">{v}</dd>
                </div>
              ))}
            </dl>
          )}
        </Card>

        {(blocking.length > 0 || notes.length > 0) && !validating && (
          <Card className="p-7" aria-labelledby="validation">
            <h2 id="validation" className="text-section font-semibold text-ink">Validation</h2>
            <ul className="mt-4 space-y-2.5">
              {[...blocking, ...notes].map((i) => (
                <li key={`${i.code}-${i.file}`} className={cn('flex items-start gap-3 rounded-[14px] p-4', i.blocking ? 'bg-discrepancy-tint' : 'bg-notice-tint')}>
                  <TriangleAlert aria-hidden className={cn('mt-0.5 size-[18px] shrink-0', i.blocking ? 'text-discrepancy' : 'text-notice')} />
                  <div className="min-w-0 flex-1">
                    <p className="text-[15px] font-semibold text-ink">
                      {i.message} <span className="font-normal text-ink-2">{i.blocking ? '· Blocking' : '· Non-blocking'}</span>
                    </p>
                    <p className="mt-0.5 text-[13px] text-ink-2 tabular">
                      {i.file !== '—' && <>File {i.file} · </>}
                      {i.field && <>Field {i.field} · </>}
                      {i.row != null && <>Row {i.row} · </>}
                      Code {i.code}
                    </p>
                    <p className="mt-1 text-[14px] text-ink">{i.recovery}</p>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        )}

        <Card className="p-7" aria-labelledby="perm-title">
          <h2 id="perm-title" className="text-section font-semibold text-ink">Processing permissions</h2>
          <p className="mt-1 text-[14px] text-ink-2">Undetermined is never treated as allowed. Record the basis for each right.</p>
          <ul className="mt-4 divide-y divide-hairline">
            {PERMISSION_ROWS.map((r) => {
              const p = d.permissions[r.key];
              return (
                <li key={r.key}>
                  <button type="button" onClick={() => setEditing(r.key)} className="group grid w-full grid-cols-[24px_150px_160px_1fr_20px] items-center gap-3 py-3 text-left max-md:grid-cols-[24px_1fr_auto]">
                    <r.icon aria-hidden className="size-[19px] text-ink-2" />
                    <span className="text-[15px] text-ink">{r.label}</span>
                    <StatusPill meta={STATUS.permission[p.state]} />
                    <span className="truncate text-[14px] text-ink-2 max-md:col-span-3 max-md:pl-9">{p.note}</span>
                    <ChevronRight aria-hidden className="size-4 text-ink-3 transition-transform group-hover:translate-x-0.5 max-md:hidden" />
                  </button>
                </li>
              );
            })}
          </ul>
        </Card>
      </div>

      <div className="space-y-5 xl:sticky xl:top-7 xl:self-start">
        <Card className="p-7" aria-labelledby="readiness">
          <h2 id="readiness" className="text-section font-semibold text-ink">Session readiness</h2>
          <ul className="mt-5 space-y-5">
            <Readiness tone={validating ? 'data' : blocking.length ? 'discrepancy' : 'ready'} icon={validating ? Loader2 : blocking.length ? TriangleAlert : CircleCheck} spin={validating} title={validating ? 'Validating source' : blocking.length ? 'Source needs remediation' : 'Source ready'} detail={validating ? 'Checking type, duration and checksum.' : blocking.length ? plural(blocking.length, 'blocking issue') : `${plural(d.files.length, 'file')} loaded successfully.`} />
            <Readiness tone={cloudBlocked ? 'discrepancy' : 'notice'} icon={CircleSlash} title={cloudBlocked ? 'Analysis blocked' : 'Analysis after save'} detail={cloudBlocked ? `Cloud audio permission is ${d.permissions.cloud_audio.state.toLowerCase()}.` : 'Provider readiness is checked when you start.'} />
            <Readiness tone="notice" icon={TriangleAlert} title="Domain review not done" detail="Needs review by a domain researcher." />
          </ul>
          {!d.coverage.tracks && !validating && (
            <Callout tone="discrepancy" title="Track not available." className="mt-5" action={<a href="#validation" className="inline-flex items-center gap-1 text-[14px] font-medium text-data hover:underline">View validation details <ChevronRight className="size-4" /></a>}>
              Movement conformance cannot be assessed.
            </Callout>
          )}
          <div className="mt-6 border-t border-hairline pt-5">
            <div className="flex items-center justify-between">
              <h3 className="text-[17px] font-semibold text-ink">Analysis profile</h3>
            </div>
            <div className="mt-3 flex items-center gap-3 rounded-[16px] border border-hairline p-3.5">
              <IconTile icon={BrainCircuit} tone="data" />
              <div className="min-w-0 flex-1">
                <p className="flex flex-wrap items-center gap-2 text-[15px] font-semibold text-ink">
                  Google STT + Gemini <Pill tone="notice" size="sm">Not verified</Pill>
                </p>
                <p className="text-[13px] text-ink-2">Transcript and conversation analysis.</p>
              </div>
            </div>
          </div>
          {commit.isError && <ErrorState compact className="mt-4" error={commit.error} />}
          <div className="mt-5 space-y-2.5">
            <Button variant="primary" className="w-full" disabled={!canSave || commit.isPending} onClick={() => commit.mutate()}>
              {commit.isPending ? <Loader2 className="animate-spin" /> : <Save />} Save session
            </Button>
            {saveReason && <p className="text-center text-[13px] text-ink-2">{saveReason}</p>}
            <Button variant="tonal" className="w-full" disabled aria-describedby="start-reason">
              <Play /> Start analysis
            </Button>
            <p id="start-reason" className="text-center text-[13px] text-ink-2">Save the session first{cloudBlocked ? '; cloud audio permission is undetermined' : ''}.</p>
            <Button variant="secondary" className="w-full" onClick={() => navigate(-1)}>
              <ArrowLeft /> Back
            </Button>
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-2 text-[12.5px] text-ink-2">
            <Info className="size-4 text-ink-3" /> Preview does not run cloud analysis.
            <CodeChip className="h-5 text-[10px]">SYNTHETIC</CodeChip>
          </div>
        </Card>
      </div>

      {editing && can('session.import') && <PermissionDialog draft={d} keyName={editing} onClose={() => setEditing(null)} onSaved={setDraft} />}
    </div>
  );
}

function FileRow({ f, validating, onRemove }: { f: ImportFileView; validating: boolean; onRemove: () => void }) {
  const Icon = fileIcon(f.name);
  return (
    <li className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-4 px-4 py-3.5 md:grid-cols-[auto_minmax(140px,1.1fr)_64px_120px_minmax(120px,1.4fr)_auto]">
      <IconTile icon={Icon} tone={f.status === 'INVALID' ? 'discrepancy' : 'data'} className="rounded-[12px]" />
      <div className="min-w-0">
        <p className="truncate text-[15.5px] font-semibold text-ink">{f.name}</p>
        <p className="truncate text-[13px] text-ink-2">{f.channel_label ?? formatBytes(f.size_bytes)}</p>
      </div>
      <span className="hidden md:block">
        <CodeChip tone={f.status === 'INVALID' ? 'discrepancy' : 'neutral'}>{f.detected_type}</CodeChip>
      </span>
      <span className="hidden text-[14px] text-ink-2 tabular md:block">{f.kind === 'AUDIO' ? `${f.channels} ch · ${f.duration_ms ? formatDuration(f.duration_ms) : '—'}` : formatBytes(f.size_bytes)}</span>
      <div className="hidden md:block">
        {validating || f.status === 'VALIDATING' ? (
          <Progress value={60} label={`Validating ${f.name}`} className="h-1.5" />
        ) : f.kind === 'AUDIO' ? (
          <MiniWave seed={f.name} />
        ) : f.kind === 'LAYOUT' ? (
          <span className="inline-flex h-8 items-center gap-2 text-[13px] text-ink-2"><Map className="size-4" /> Layout geometry · metres</span>
        ) : (
          <span className={cn('inline-flex h-8 items-center gap-2 text-[13px]', f.status === 'INVALID' ? 'text-discrepancy' : 'text-ink-2')}>
            {f.status === 'INVALID' ? <TriangleAlert className="size-4" /> : <AudioLines className="size-4" />} {f.status === 'INVALID' ? 'Not accepted' : f.kind.toLowerCase()}
          </span>
        )}
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <MoreButton label={`Actions for ${f.name}`} className="size-9 border-transparent" />
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem onSelect={onRemove}>
            <Trash2 /> Remove file
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </li>
  );
}

function Meta({ icon: Icon, label, value, ok }: { icon: typeof Clock3; label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3.5">
      <Icon aria-hidden className="size-[19px] shrink-0 text-ink-2" />
      <div className="min-w-0 flex-1">
        <dt className="text-[13px] text-ink">{label}</dt>
        <dd className="text-[13px] leading-snug text-ink-2 tabular">{value}</dd>
      </div>
      {ok && <CircleCheck aria-label="Verified" className="size-[18px] shrink-0 fill-ready text-white" />}
    </div>
  );
}

function Readiness({ tone, icon, title, detail, spin }: { tone: 'ready' | 'discrepancy' | 'notice' | 'data'; icon: typeof CircleCheck; title: string; detail: string; spin?: boolean }) {
  return (
    <li className="flex items-start gap-4">
      <IconTile icon={icon} tone={tone} size="lg" className={spin ? '[&_svg]:animate-spin' : undefined} />
      <div className="pt-1">
        <p className="text-[16px] font-semibold text-ink">{title}</p>
        <p className="text-[14px] text-ink-2">{detail}</p>
      </div>
    </li>
  );
}

function PermissionDialog({ draft, keyName, onClose, onSaved }: { draft: ImportDraft; keyName: PermissionKey; onClose: () => void; onSaved: (d: ImportDraft) => void }) {
  const api = useApi();
  const row = PERMISSION_ROWS.find((r) => r.key === keyName)!;
  const [state, setState] = useState<PermissionState>(draft.permissions[keyName].state);
  const [basis, setBasis] = useState('');
  const save = useMutation({
    mutationFn: () => api.setImportPermission(draft.id, keyName, state, basis, { idempotencyKey: idemKey(`perm.${draft.id}.${keyName}`, { state, basis }), expectedVersion: draft.version }),
    onSuccess: (d) => {
      onSaved(d);
      toast.success(`${row.label}: ${STATUS.permission[state].label}`);
      onClose();
    },
  });
  const needsBasis = state === 'ALLOWED' && keyName !== 'local_read';
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent title={row.label} description="Record the right and its basis. FlowLens does not infer legality from a file being available.">
        <RadioGroup value={state} onValueChange={(v) => setState(v as PermissionState)} aria-label={`${row.label} permission`}>
          <RadioRow value="ALLOWED" label="Allowed" description="A documented right covers this processing." />
          <RadioRow value="UNDETERMINED" label="Undetermined" description="Not yet known — treated as not allowed." />
          <RadioRow value="DENIED" label="Denied" description="Processing is not permitted." />
        </RadioGroup>
        <div className="mt-4 space-y-2">
          <Label htmlFor="perm-basis">Basis {needsBasis && <span className="text-ink-2">(required)</span>}</Label>
          <Textarea id="perm-basis" value={basis} onChange={(e) => setBasis(e.target.value)} placeholder="e.g. Synthetic data created for this project; no third-party rights." maxLength={300} />
        </div>
        {isApiError(save.error) && <ErrorState compact className="mt-4" error={save.error} />}
        <DialogFooter>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={save.isPending || (needsBasis && basis.trim().length < 6)} onClick={() => save.mutate()}>
            {save.isPending && <Loader2 className="animate-spin" />} Save permission
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AnalysisStep({ sessionId }: { sessionId: string }) {
  const api = useApi();
  const qc = useQueryClient();
  const { can } = useAuth();
  useSessionStream(sessionId);
  const session = useQuery({ queryKey: qk.session(sessionId), queryFn: () => api.getSession(sessionId), refetchInterval: (q) => (['QUEUED', 'RUNNING'].includes(q.state.data?.analysis ?? '') ? 800 : false) });
  const profileId = session.data?.provider_profile_ids[0] ?? '';
  const estimate = useQuery({ queryKey: qk.estimate(sessionId, profileId), queryFn: () => api.estimateAnalysis(sessionId, profileId), enabled: !!profileId });
  const [confirm, setConfirm] = useState(false);
  const start = useMutation({
    mutationFn: () => api.startAnalysis(sessionId, profileId, { idempotencyKey: idemKey(`analysis.${sessionId}`, profileId) }),
    onSuccess: () => {
      releaseKeys(`analysis.${sessionId}`);
      setConfirm(false);
      qc.invalidateQueries({ queryKey: qk.session(sessionId) });
    },
  });
  if (session.isPending || estimate.isPending) return <Card className="mx-auto max-w-[880px] p-7"><Skeleton className="h-40 w-full" /></Card>;
  if (session.isError) return <Card className="p-2"><ErrorState error={session.error} /></Card>;
  const s = session.data;
  const e = estimate.data;
  const run = s.runs[s.runs.length - 1];
  const running = s.analysis === 'QUEUED' || s.analysis === 'RUNNING';
  const done = s.analysis === 'COMPLETED' || s.analysis === 'PARTIAL';
  const blocked = (e?.blockers.length ?? 0) > 0;

  return (
    <div className="mx-auto grid max-w-[1080px] grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
      <Card className="p-7">
        <div className="flex items-center gap-3">
          <IconTile icon={CircleCheck} tone="ready" />
          <div>
            <h2 className="text-section font-semibold text-ink">{s.title} saved</h2>
            <p className="text-[14px] text-ink-2">Source records are immutable. No provider call has been made.</p>
          </div>
        </div>
        <h3 className="mt-7 text-[17px] font-semibold text-ink">Estimated request volume</h3>
        <dl className="mt-3 grid grid-cols-3 divide-x divide-hairline rounded-[18px] border border-hairline">
          {[
            ['STT requests', e?.stt_requests ?? '—'],
            ['Gemini requests', e?.gemini_requests ?? '—'],
            ['Audio minutes', e?.audio_minutes ?? '—'],
          ].map(([k, v]) => (
            <div key={k} className="px-5 py-4">
              <dt className="text-[13px] text-ink-2">{k}</dt>
              <dd className="mt-1 text-[28px] font-medium tracking-[-0.03em] text-ink tabular">{v}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-2 text-[13px] text-ink-2">{e?.budget_label}</p>

        {blocked && !done && (
          <Callout tone="discrepancy" icon={CircleSlash} title="Analysis is blocked" className="mt-6">
            <ul className="mt-1 list-disc space-y-1 pl-5">
              {e!.blockers.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
            {can('admin.manage') && (
              <Link to="/settings/providers" className="mt-2 inline-flex items-center gap-1 text-[14px] font-medium text-data hover:underline">
                Open provider readiness <ChevronRight className="size-4" />
              </Link>
            )}
          </Callout>
        )}

        {(running || done) && run && (
          <div className="mt-6 rounded-[18px] border border-hairline p-5">
            <div className="flex items-center justify-between">
              <p className="text-[15px] font-semibold text-ink">Run {run.label}</p>
              <StatusPill meta={STATUS.analysis[s.analysis]} />
            </div>
            <Progress className="mt-3" value={done ? 100 : run.run.status === 'QUEUED' ? 8 : 55} label="Analysis progress" tone={done ? 'ready' : 'data'} />
            <p className="mt-2 text-[13px] text-ink-2">{done ? 'Results are available in the workspace.' : 'Jobs are processed by the worker; you can leave this page.'}</p>
          </div>
        )}
        {start.isError && <ErrorState compact className="mt-4" error={start.error} />}
        <div className="mt-6 flex flex-wrap justify-between gap-3">
          <Button asChild variant="secondary">
            <Link to={`/sessions?selected=${s.id}`}>Back to sessions</Link>
          </Button>
          {done ? (
            <Button asChild variant="primary">
              <Link to={`/s/${s.id}/workspace?run=${s.latest_run_id}`}>
                Open workspace <ArrowRight />
              </Link>
            </Button>
          ) : (
            <Button variant="primary" disabled={blocked || running || !can('analysis.create')} onClick={() => setConfirm(true)}>
              {running ? <Loader2 className="animate-spin" /> : <Play />} {running ? 'Analysis running' : 'Start analysis'}
            </Button>
          )}
        </div>
      </Card>
      <Card className="p-6">
        <SectionLabel>Before you start</SectionLabel>
        <ul className="mt-3 space-y-3 text-[14px] text-ink">
          <li className="flex gap-2.5"><Check className="mt-0.5 size-4 text-ready" /> Results are hypotheses until reviewed.</li>
          <li className="flex gap-2.5"><Check className="mt-0.5 size-4 text-ready" /> Re-running creates a new run; earlier runs stay readable.</li>
          <li className="flex gap-2.5"><Check className="mt-0.5 size-4 text-ready" /> Seeking during replay never starts provider jobs.</li>
        </ul>
      </Card>
      <Dialog open={confirm} onOpenChange={setConfirm}>
        <DialogContent title="Start analysis?" description={`${e?.stt_requests} STT and ${e?.gemini_requests} Gemini requests for ${e?.audio_minutes} audio minutes. A new analysis run is created.`}>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setConfirm(false)}>Cancel</Button>
            <Button variant="primary" disabled={start.isPending} onClick={() => start.mutate()}>
              {start.isPending && <Loader2 className="animate-spin" />} Confirm and start
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
