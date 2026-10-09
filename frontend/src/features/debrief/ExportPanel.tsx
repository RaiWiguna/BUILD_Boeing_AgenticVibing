import { AudioLines, CircleCheck, Clock3, Download, FileText, Fingerprint, Loader2, Lock, ShieldAlert, ShieldCheck, XCircle } from 'lucide-react';
import { useId, useState, type ReactNode } from 'react';
import { toast } from 'sonner';
import { isApiError } from '@/api/errors';
import type { BriefView, ExportFormat, ExportJob } from '@/api/types';
import { StatusPill } from '@/components/domain/primitives';
import { DesktopOnly, LoadingRows } from '@/components/domain/states';
import { Button } from '@/components/ui/button';
import { Segmented, Switch } from '@/components/ui/controls';
import { useConnected } from '@/hooks/useSessionStream';
import { useSessionScope } from '@/hooks/useSessionScope';
import type { StatusMeta } from '@/lib/status';
import { formatBytes, formatDateTimeUtc } from '@/lib/time';
import { cn } from '@/lib/utils';
import { useCreateExport, useDownloadExport, useExportPolicy, useExports } from './queries';

const JOB_STATUS: Record<ExportJob['status'], StatusMeta> = {
  PREPARING: { label: 'Preparing', tone: 'data', icon: Loader2 },
  READY: { label: 'Ready', tone: 'ready', icon: CircleCheck },
  FAILED: { label: 'Failed', tone: 'discrepancy', icon: XCircle },
  EXPIRED: { label: 'Expired', tone: 'muted', icon: Clock3 },
  REVOKED: { label: 'Revoked', tone: 'muted', icon: ShieldAlert },
};

function ToggleRow({ icon: Icon, title, hint, checked, onChange, disabled, locked }: { icon: typeof FileText; title: ReactNode; hint: ReactNode; checked: boolean; onChange?: (v: boolean) => void; disabled?: boolean; locked?: boolean }) {
  const id = useId();
  return (
    <div className="flex items-center gap-3.5 py-3">
      <span aria-hidden className="inline-flex size-10 shrink-0 items-center justify-center rounded-full border border-hairline-soft text-ink-2">
        <Icon className="size-[18px]" />
      </span>
      <div className="min-w-0 flex-1">
        <label htmlFor={id} className={cn('flex items-center gap-1.5 text-[15px] font-medium', disabled && !locked ? 'text-ink-2' : 'text-ink')}>
          {title}
          {locked && <Lock aria-label="Locked" className="size-3.5 text-ink-2" />}
        </label>
        <p id={`${id}-hint`} className="mt-0.5 text-[13px] text-ink-3">
          {hint}
        </p>
      </div>
      <Switch id={id} checked={checked} onCheckedChange={onChange} disabled={disabled} aria-describedby={`${id}-hint`} className={locked ? 'disabled:cursor-default disabled:opacity-100' : undefined} />
    </div>
  );
}

function JobRow({ job, current }: { job: ExportJob; current: boolean }) {
  const download = useDownloadExport();
  const meta = JOB_STATUS[job.status];
  return (
    <li className="flex items-start justify-between gap-3 py-3">
      <div className="min-w-0">
        <p className="flex items-center gap-2 text-[14px] font-medium text-ink">
          {job.format}
          <StatusPill size="sm" meta={meta} className={job.status === 'PREPARING' ? '[&_svg]:animate-spin' : undefined} />
        </p>
        <p className="mt-0.5 text-[12.5px] text-ink-3 tabular">
          {formatDateTimeUtc(job.created_at)}
          {job.size_bytes != null && ` · ${formatBytes(job.size_bytes)}`}
          {job.redacted && ' · redacted'}
          {!current && ' · other brief'}
        </p>
        {job.status === 'READY' && <p className="mt-0.5 text-[12.5px] text-ink-3 tabular">Expires {formatDateTimeUtc(job.expires_at)}</p>}
        {job.failure && <p className="mt-0.5 text-[12.5px] text-ink-2">{job.failure}</p>}
      </div>
      {job.status === 'READY' ? (
        <Button
          size="xs"
          variant="data"
          disabled={download.isPending}
          onClick={() =>
            download.mutate(job.id, {
              onSuccess: (name) => toast.success('Download started', { description: `${name} · generated locally (MOCK)` }),
              onError: (e) => toast.error(isApiError(e) ? e.message : 'Download failed.', { description: isApiError(e) ? e.recovery : undefined }),
            })
          }
        >
          {download.isPending ? <Loader2 className="animate-spin" /> : <Download />} Download
        </Button>
      ) : null}
    </li>
  );
}

/** Export report panel (comp 08). Provenance is always included; audio export stays off. */
export function ExportPanel({ brief }: { brief: BriefView; sid: string }) {
  const { run, archived } = useSessionScope();
  const connected = useConnected();
  const policy = useExportPolicy();
  const exports = useExports();
  const create = useCreateExport();
  const [format, setFormat] = useState<ExportFormat>('HTML');
  const [journal, setJournal] = useState(true);
  const [redactDraft, setRedact] = useState(true);
  const p = policy.data;
  const redacted = p?.redaction_required ? true : redactDraft;
  const allowed = !!p?.report_allowed && !archived;
  const ready = allowed && connected && !create.isPending;
  const jobs = exports.data ?? [];

  const submit = () =>
    create.mutate(
      { format, briefId: brief.brief.id, includeJournal: journal, redacted },
      {
        onSuccess: () => toast.success(`${format} export is being prepared`, { description: 'You will be notified when it is ready to download.' }),
        onError: (e) => toast.error(isApiError(e) ? e.message : 'Export could not be created.', { description: isApiError(e) ? e.recovery : undefined }),
      },
    );

  return (
    // Rendered inside the "Export report" sheet (decision D-4); the sheet provides the title.
    <section aria-label="Export options">

      {!p ? (
        <LoadingRows rows={4} />
      ) : (
        <>
          <p className="mb-2 text-[14.5px] font-medium text-ink">Format</p>
          <Segmented
            label="Export format"
            tone="data"
            value={format}
            onChange={setFormat}
            className="flex w-full"
            options={(['HTML', 'CSV', 'JSON'] as const).map((f) => ({ value: f, label: f }))}
          />
          <div className="mt-3 divide-y divide-hairline-soft">
            <div>
              <ToggleRow icon={Fingerprint} title="Include provenance" hint="Required metadata · model, prompt, rule, schema" checked disabled locked />
              <ToggleRow icon={FileText} title="Include journal" hint="Events and findings list" checked={journal} onChange={setJournal} disabled={!allowed} />
              <ToggleRow
                icon={ShieldCheck}
                title="Redact restricted evidence"
                hint={p.redaction_required ? 'Required by your grant' : 'Hide sensitive detail'}
                checked={redacted}
                onChange={setRedact}
                disabled={!allowed || p.redaction_required}
                locked={p.redaction_required}
              />
            </div>
            <ToggleRow icon={AudioLines} title="Include audio" hint={p.audio_allowed ? 'Not available in this build — no audio is bundled.' : 'Audio export permission is not available.'} checked={false} disabled />
          </div>

          {allowed ? (
            <div className="mt-3 flex gap-3 rounded-[16px] bg-ready-tint px-4 py-3.5">
              <CircleCheck aria-hidden className="mt-0.5 size-5 shrink-0 text-ready" />
              <div className="text-[13.5px] leading-snug">
                <p className="text-[15px] font-semibold text-ready">Report allowed</p>
                <p className="mt-1 text-ink-2">
                  Scope: this session · Run {run?.label} · {brief.label.replace('Brief revision', 'Revision')}
                </p>
                <p className="text-ink-2">Expiry: profile {p.expiry_hours} h</p>
              </div>
            </div>
          ) : (
            <div className="mt-3 flex gap-3 rounded-[16px] bg-notice-tint px-4 py-3.5">
              <ShieldAlert aria-hidden className="mt-0.5 size-5 shrink-0 text-notice" />
              <div className="text-[13.5px] leading-snug">
                <p className="text-[15px] font-semibold text-notice">Export not available</p>
                <p className="mt-1 text-ink-2">{archived ? 'Archived sessions are read-only.' : (p.reason ?? 'Report export is not allowed for this session.')}</p>
              </div>
            </div>
          )}
          {brief.stale && allowed && <p className="mt-2 text-[12.5px] text-notice">This brief is stale. The export will carry its stale label.</p>}

          <div className="mt-4">
          <DesktopOnly what="Exporting">
          <Button variant="primary" size="lg" className="w-full" onClick={submit} disabled={!ready}>
            {create.isPending ? <Loader2 className="animate-spin" /> : <Download />}
            {create.isPending ? 'Creating export…' : 'Create export'}
          </Button>
          </DesktopOnly>
          </div>
          <p className="mt-2.5 text-center text-[13px] text-ink-3">{connected ? 'The original source stays stored.' : 'Export is paused while disconnected.'}</p>

          {jobs.length > 0 && (
            <div className="mt-4 border-t border-hairline-soft pt-3">
              <p className="text-[13px] font-medium text-ink-2">Recent exports</p>
              <ul className="divide-y divide-hairline-soft">
                {jobs.slice(0, 4).map((j) => (
                  <JobRow key={j.id} job={j} current={j.brief_id === brief.brief.id} />
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}
