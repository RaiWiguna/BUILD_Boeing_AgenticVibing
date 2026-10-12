import { CircleCheck, CircleSlash, Clock3, KeyRound, Loader2, Plus, RefreshCw, RotateCcw, Search, ServerCog, ShieldAlert, Trash2, UserCheck, UserX, XCircle } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { isApiError } from '@/api/errors';
import type { Account, AuditEntry, Capability, JobView, RetentionPolicy, Role } from '@/api/types';
import { useAuth } from '@/app/providers/AuthProvider';
import { CodeChip, HatchedBar, MoreButton, StatusPill } from '@/components/domain/primitives';
import { EmptyState, ErrorState, LoadingRows } from '@/components/domain/states';
import { Avatar } from '@/components/layout/UserMenu';
import { Button } from '@/components/ui/button';
import { Progress, Select, Switch } from '@/components/ui/controls';
import { Dialog, DialogClose, DialogContent, DialogFooter } from '@/components/ui/dialog';
import { Input, Label, Textarea } from '@/components/ui/input';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/menu';
import type { StatusMeta } from '@/lib/status';
import { ROLE_LABEL } from '@/lib/roles';
import { formatBytes, formatDateTimeUtc, formatDuration } from '@/lib/time';
import { cn } from '@/lib/utils';
import { CAPABILITY_INFO } from './AccountPage';
import {
  useAccounts,
  useAddGrant,
  useAudit,
  useBudget,
  useCancelJob,
  useCheckProvider,
  useGrants,
  useJobs,
  useProviders,
  useRequestPurge,
  useResetPassword,
  useRetention,
  useRetryJob,
  useRevokeGrant,
  useSessionsList,
  useSetActive,
  useStorage,
} from './queries';
import { AdminOnly, SettingsCard } from './SettingsLayout';

const fail = (e: unknown, fallback: string) => toast.error(isApiError(e) ? e.message : fallback, { description: isApiError(e) ? (e.recovery ?? undefined) : undefined });

const TH = 'py-2.5 pr-4 text-left text-[13px] font-medium text-ink-2';
const TD = 'border-t border-hairline-soft py-3 pr-4 align-middle text-[14.5px]';

function Loading<T>({ q, children, rows = 4 }: { q: { data?: T; isError: boolean; error: unknown; refetch: () => unknown }; children: (d: T) => React.ReactNode; rows?: number }) {
  if (q.isError && !q.data) return <ErrorState compact error={q.error} onRetry={() => q.refetch()} />;
  if (!q.data) return <LoadingRows rows={rows} />;
  return <>{children(q.data)}</>;
}

/* Users ───────────────────────────────────────────────────────────── */

function UserRow({ a, self }: { a: Account; self: boolean }) {
  const setActive = useSetActive();
  const reset = useResetPassword();
  const [confirm, setConfirm] = useState(false);
  const toggle = (active: boolean) =>
    setActive.mutate(
      { id: a.id, active },
      { onSuccess: () => toast.success(`${a.name} ${active ? 'activated' : 'deactivated'}`, { description: 'Recorded in the audit log.' }), onError: (e) => fail(e, 'Could not update the account.'), onSettled: () => setConfirm(false) },
    );
  return (
    <tr>
      <td className={TD}>
        <span className="flex items-center gap-3">
          <Avatar name={a.name} className="size-9 text-[12.5px]" />
          <span className="min-w-0">
            <span className="block font-medium text-ink">
              {a.name} {self && <span className="text-[12.5px] font-normal text-ink-3">(you)</span>}
            </span>
            <span className="block text-[13px] text-ink-2">{a.email}</span>
          </span>
        </span>
      </td>
      <td className={TD}>
        <CodeChip tone={a.role === 'ADMIN' ? 'data' : 'neutral'}>{ROLE_LABEL[a.role]}</CodeChip>
      </td>
      <td className={cn(TD, 'text-ink-2 tabular')}>{a.last_login_at ? formatDateTimeUtc(a.last_login_at) : 'Never'}</td>
      <td className={TD}>
        <span className="flex items-center gap-2.5">
          <Switch checked={a.active} disabled={self || setActive.isPending} onCheckedChange={(v) => (v ? toggle(true) : setConfirm(true))} aria-label={`${a.name} active`} />
          <span className={cn('text-[13.5px]', a.active ? 'text-ink' : 'text-ink-3')}>{a.active ? 'Active' : 'Inactive'}</span>
          {a.must_change_password && <CodeChip tone="notice">Reset pending</CodeChip>}
        </span>
      </td>
      <td className={cn(TD, 'w-12 pr-0')}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <MoreButton label={`Actions for ${a.name}`} className="size-8 border-transparent bg-transparent shadow-none" />
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-[230px]">
            <DropdownMenuItem disabled={reset.isPending} onSelect={() => reset.mutate(a.id, { onSuccess: () => toast.success(`Password reset for ${a.name}`, { description: 'They choose a new password at next sign-in.' }), onError: (e) => fail(e, 'Reset failed.') })}>
              <RotateCcw /> Require password reset
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <Dialog open={confirm} onOpenChange={setConfirm}>
          <DialogContent title={`Deactivate ${a.name}?`} description="They are signed out and cannot open sessions. Their reviews stay in the record. You can reactivate them later.">
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="secondary">Cancel</Button>
              </DialogClose>
              <Button variant="danger" disabled={setActive.isPending} onClick={() => toggle(false)}>
                {setActive.isPending ? <Loader2 className="animate-spin" /> : <UserX />} Deactivate
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </td>
    </tr>
  );
}

export function UsersPage() {
  return (
    <AdminOnly>
      <UsersInner />
    </AdminOnly>
  );
}
function UsersInner() {
  const accounts = useAccounts();
  const { session } = useAuth();
  return (
    <SettingsCard title="Users" description="Individual accounts. Roles set default capabilities; session access refines them.">
      <Loading q={accounts}>
        {(list) => (
          <div className="relative overflow-x-auto">
            <table className="w-full min-w-[640px] border-separate border-spacing-0">
              <thead>
                <tr>
                  <th className={TH}>Name</th>
                  <th className={TH}>Role</th>
                  <th className={TH}>Last sign-in</th>
                  <th className={TH}>Status</th>
                  <th className={TH}>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {list.map((a) => (
                  <UserRow key={a.id} a={a} self={a.id === session?.account.id} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Loading>
    </SettingsCard>
  );
}

/* Session access (grants) ──────────────────────────────────────────── */

const GRANTABLE: Capability[] = ['session.read', 'audio.play', 'review.write', 'export.create', 'truth.read'];
const ROLE_DEFAULTS: Record<Role, Capability[]> = {
  EVALUATOR: ['session.read', 'audio.play', 'review.write', 'export.create'],
  CONTROLLER_REVIEW: ['session.read', 'audio.play', 'review.write'],
  OBSERVER: ['session.read'],
  ADMIN: ['session.read', 'audio.play', 'review.write', 'export.create', 'truth.read'],
};

function AddGrantDialog({ accounts, sessions }: { accounts: Account[]; sessions: { id: string; title: string }[] }) {
  const add = useAddGrant();
  const [open, setOpen] = useState(false);
  const [accountId, setAccount] = useState('');
  const [sessionId, setSession] = useState('');
  const [caps, setCaps] = useState<Capability[]>(['session.read']);
  const ready = !!accountId && !!sessionId && caps.length > 0 && !add.isPending;
  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        if (v) {
          setAccount('');
          setSession('');
          setCaps(['session.read']);
        }
      }}
    >
      <Button variant="primary" size="sm" onClick={() => setOpen(true)}>
        <Plus /> Add access
      </Button>
      <DialogContent title="Grant session access" description="Replaces any existing grant for this person on this session. Open screens re-sync immediately.">
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Person</Label>
              <Select label="Person" value={accountId} onValueChange={(v) => { setAccount(v); const r = accounts.find((a) => a.id === v)?.role; if (r) setCaps(ROLE_DEFAULTS[r]); }} options={accounts.filter((a) => a.active).map((a) => ({ value: a.id, label: a.name }))} className="w-full" />
            </div>
            <div className="space-y-1.5">
              <Label>Session</Label>
              <Select label="Session" value={sessionId} onValueChange={setSession} options={sessions.map((s) => ({ value: s.id, label: s.title }))} className="w-full" />
            </div>
          </div>
          <fieldset>
            <legend className="text-[14px] font-medium text-ink">Capabilities</legend>
            <div className="mt-2 grid gap-1.5">
              {GRANTABLE.map((c) => (
                <label key={c} className="flex cursor-pointer items-center justify-between gap-3 rounded-[12px] border border-hairline-soft px-3.5 py-2.5">
                  <span>
                    <span className="block text-[14.5px] font-medium text-ink">{CAPABILITY_INFO[c].label}</span>
                    <span className="block text-[12.5px] text-ink-3">{c}</span>
                  </span>
                  <Switch checked={caps.includes(c)} disabled={c === 'session.read'} onCheckedChange={(v) => setCaps((x) => (v ? [...x, c] : x.filter((y) => y !== c)))} aria-label={CAPABILITY_INFO[c].label} />
                </label>
              ))}
            </div>
          </fieldset>
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="secondary">Cancel</Button>
          </DialogClose>
          <Button
            variant="primary"
            disabled={!ready}
            onClick={() =>
              add.mutate(
                { accountId, sessionId, capabilities: caps },
                {
                  onSuccess: () => {
                    toast.success('Access granted', { description: 'Recorded in the audit log.' });
                    setOpen(false);
                  },
                  onError: (e) => fail(e, 'Could not grant access.'),
                },
              )
            }
          >
            {add.isPending ? <Loader2 className="animate-spin" /> : <KeyRound />} Grant access
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function AccessPage() {
  return (
    <AdminOnly>
      <AccessInner />
    </AdminOnly>
  );
}
function AccessInner() {
  const grants = useGrants();
  const accounts = useAccounts();
  const sessions = useSessionsList();
  const revoke = useRevokeGrant();
  const name = (id: string) => accounts.data?.find((a) => a.id === id)?.name ?? 'Unknown account';
  const title = (id: string) => sessions.data?.find((s) => s.id === id)?.title ?? 'Unknown session';
  return (
    <SettingsCard title="Session access" description="Per-session grants. Revoking applies at once — open screens re-sync and restricted content is removed." actions={accounts.data && sessions.data ? <AddGrantDialog accounts={accounts.data} sessions={sessions.data} /> : undefined}>
      <Loading q={grants}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState icon={KeyRound} title="No session grants" className="py-8">
              Role defaults apply until a grant is added.
            </EmptyState>
          ) : (
            <ul className="divide-y divide-hairline-soft">
              {list.map((g) => (
                <li key={g.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3.5">
                  <Avatar name={name(g.account_id)} className="size-9 text-[12.5px]" />
                  <div className="min-w-[200px] flex-1">
                    <p className="text-[15px] font-medium text-ink">
                      {name(g.account_id)} <span className="font-normal text-ink-3">·</span> <span className="font-normal text-ink-2">{title(g.session_id)}</span>
                    </p>
                    <p className="mt-0.5 text-[12.5px] text-ink-3">
                      Granted by {g.granted_by} · {formatDateTimeUtc(g.granted_at)}
                    </p>
                  </div>
                  <span className="flex flex-wrap gap-1.5">
                    {g.capabilities.map((c) => (
                      <CodeChip key={c} tone={c === 'truth.read' ? 'notice' : 'neutral'}>
                        {c}
                      </CodeChip>
                    ))}
                  </span>
                  <Button size="sm" variant="danger" disabled={revoke.isPending} onClick={() => revoke.mutate(g.id, { onSuccess: () => toast.success('Access revoked', { description: 'Open screens for this session re-sync now.' }), onError: (e) => fail(e, 'Could not revoke.') })}>
                    <Trash2 /> Revoke
                  </Button>
                </li>
              ))}
            </ul>
          )
        }
      </Loading>
    </SettingsCard>
  );
}

/* Providers ───────────────────────────────────────────────────────── */

const READINESS: Record<string, StatusMeta> = {
  READY: { label: 'Ready', tone: 'ready', icon: CircleCheck },
  UNVERIFIED: { label: 'Unverified', tone: 'muted', icon: CircleSlash },
  UNAVAILABLE: { label: 'Unavailable', tone: 'discrepancy', icon: XCircle },
};

export function ProvidersPage() {
  return (
    <AdminOnly>
      <ProvidersInner />
    </AdminOnly>
  );
}
function ProvidersInner() {
  const providers = useProviders();
  const check = useCheckProvider();
  return (
    <SettingsCard title="Provider profiles" description="Server-side profiles. Credentials never reach the browser.">
      <Loading q={providers}>
        {(list) => (
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
            {list.map((p) => (
              <article key={p.id} className="rounded-[18px] border border-hairline-soft p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span aria-hidden className="inline-flex size-10 items-center justify-center rounded-full bg-data-tint text-data">
                      <ServerCog className="size-[19px]" />
                    </span>
                    <div>
                      <p className="text-[15.5px] font-semibold text-ink">{p.provider === 'GOOGLE_STT' ? 'Speech-to-text' : 'Interpretation model'}</p>
                      <p className="text-[13px] text-ink-2">
                        {p.model} · {p.version}
                      </p>
                    </div>
                  </div>
                  <StatusPill size="sm" meta={READINESS[p.readiness] ?? READINESS.UNVERIFIED!} />
                </div>
                <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-[13.5px]">
                  {[
                    ['Transport', p.transport],
                    ['Region', p.region ?? 'Global'],
                    ['Locale', p.locale || '—'],
                    ['Timeout', `${p.timeout_seconds} s`],
                    ['Stored by provider', p.store ? 'Yes' : 'No'],
                    ['Profile', p.id.slice(0, 8)],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <dt className="text-ink-3">{k}</dt>
                      <dd className="truncate text-ink">{v}</dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-4 flex justify-end">
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={check.isPending && check.variables === p.id}
                    onClick={() =>
                      check.mutate(p.id, {
                        onSuccess: (r) => (r.readiness === 'READY' ? toast.success('Readiness check passed', { description: r.message }) : toast.warning('Provider unavailable', { description: r.message })),
                        onError: (e) => fail(e, 'Check failed.'),
                      })
                    }
                  >
                    {check.isPending && check.variables === p.id ? <Loader2 className="animate-spin" /> : <RefreshCw />} Check readiness
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </Loading>
    </SettingsCard>
  );
}

/* Jobs & budget ───────────────────────────────────────────────────── */

const JOB: Record<JobView['status'], StatusMeta> = {
  QUEUED: { label: 'Queued', tone: 'muted', icon: Clock3 },
  LEASED: { label: 'Leased', tone: 'data', icon: Loader2 },
  RUNNING: { label: 'Running', tone: 'data', icon: Loader2 },
  SUCCEEDED: { label: 'Succeeded', tone: 'ready', icon: CircleCheck },
  FAILED: { label: 'Failed', tone: 'discrepancy', icon: XCircle },
  CANCELLED: { label: 'Cancelled', tone: 'muted', icon: CircleSlash },
  RETRY_WAIT: { label: 'Waiting to retry', tone: 'notice', icon: Clock3 },
};

export function JobsPage() {
  return (
    <AdminOnly>
      <JobsInner />
    </AdminOnly>
  );
}
function JobsInner() {
  const jobs = useJobs();
  const budget = useBudget();
  const retry = useRetryJob();
  const cancel = useCancelJob();
  return (
    <div className="space-y-5">
      <SettingsCard title="Provider budget" description="Spend is tracked per period; jobs stop before the limit, never after.">
        <Loading q={budget} rows={2}>
          {(b) => {
            const ratio = b.spent_microunits / b.limit_microunits;
            return (
              <div className="grid grid-cols-1 gap-5 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)]">
                <div>
                  <p className="text-[14px] text-ink-2">{b.period}</p>
                  <p className="mt-1 text-[40px] font-medium leading-none tracking-[-0.04em] text-ink tabular">
                    {Math.round(ratio * 100)}%<span className="ml-2 text-[15px] font-medium tracking-normal text-ink-2">of limit used</span>
                  </p>
                  <Progress value={ratio * 100} tone={ratio > 0.8 ? 'notice' : 'data'} label="Budget used" className="mt-3 h-2.5" />
                  <p className="mt-2 text-[12.5px] text-ink-3 tabular">
                    {(b.spent_microunits / 1e6).toFixed(1)} of {(b.limit_microunits / 1e6).toFixed(0)} units
                  </p>
                </div>
                <div className="rounded-[16px] bg-sunken p-4">
                  <p className="text-[13px] text-ink-2">Speech-to-text audio</p>
                  <p className="mt-1 text-[24px] font-medium tracking-[-0.03em] text-ink tabular">{formatDuration(b.stt_audio_ms)}</p>
                </div>
                <div className="rounded-[16px] bg-sunken p-4">
                  <p className="text-[13px] text-ink-2">Model tokens</p>
                  <p className="mt-1 text-[24px] font-medium tracking-[-0.03em] text-ink tabular">{b.gemini_tokens.toLocaleString('en-US')}</p>
                </div>
              </div>
            );
          }}
        </Loading>
      </SettingsCard>
      <SettingsCard title="Analysis jobs" description="Retries are explicit and idempotent. Cancelling never deletes stored results.">
        <Loading q={jobs}>
          {(list) => (
            <div className="relative overflow-x-auto">
              <table className="w-full min-w-[720px] border-separate border-spacing-0">
                <thead>
                  <tr>
                    <th className={TH}>Session · run</th>
                    <th className={TH}>Stage</th>
                    <th className={TH}>Status</th>
                    <th className={TH}>Progress</th>
                    <th className={TH}>Updated</th>
                    <th className={TH}>
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((j) => {
                    const pct = j.total_units ? (j.completed_units / j.total_units) * 100 : 0;
                    return (
                      <tr key={j.id}>
                        <td className={TD}>
                          <span className="block font-medium text-ink">{j.session_title}</span>
                          <span className="text-[12.5px] text-ink-3">
                            Run {j.run_label} · attempt {j.attempt}
                          </span>
                        </td>
                        <td className={TD}>
                          <CodeChip>{j.stage}</CodeChip>
                        </td>
                        <td className={TD}>
                          <StatusPill size="sm" meta={JOB[j.status]} className={j.status === 'RUNNING' || j.status === 'LEASED' ? '[&_svg]:animate-spin' : undefined} />
                          {j.failure && <span className="mt-1 block text-[12px] text-discrepancy">{j.failure}</span>}
                        </td>
                        <td className={cn(TD, 'w-[160px]')}>
                          {j.total_units ? (
                            <>
                              <Progress value={pct} label={`${j.stage} progress`} tone={j.status === 'FAILED' ? 'discrepancy' : 'data'} />
                              <span className="mt-1 block text-[12px] text-ink-3 tabular">
                                {j.completed_units}/{j.total_units}
                              </span>
                            </>
                          ) : (
                            <span className="text-[13px] text-ink-3">Unknown total</span>
                          )}
                        </td>
                        <td className={cn(TD, 'text-[13px] text-ink-2 tabular')}>{formatDateTimeUtc(j.updated_at)}</td>
                        <td className={cn(TD, 'pr-0 text-right')}>
                          {(j.status === 'FAILED' || j.status === 'RETRY_WAIT') && (
                            <Button size="xs" variant="data" disabled={retry.isPending} onClick={() => retry.mutate(j.id, { onSuccess: () => toast.success('Retry queued'), onError: (e) => fail(e, 'Retry failed.') })}>
                              <RefreshCw /> Retry
                            </Button>
                          )}
                          {['QUEUED', 'LEASED', 'RUNNING'].includes(j.status) && (
                            <Button size="xs" variant="ghost" disabled={cancel.isPending} onClick={() => cancel.mutate(j.id, { onSuccess: () => toast.success('Job cancelled'), onError: (e) => fail(e, 'Cancel failed.') })}>
                              Cancel
                            </Button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Loading>
      </SettingsCard>
    </div>
  );
}

/* Storage ─────────────────────────────────────────────────────────── */

export function StoragePage() {
  return (
    <AdminOnly>
      <StorageInner />
    </AdminOnly>
  );
}
function StorageInner() {
  const storage = useStorage();
  return (
    <SettingsCard title="Storage" description="Local disk on the workspace host. Imports pause at the hold threshold so analysis never runs out of space.">
      <Loading q={storage}>
        {(s) => {
          const ratio = s.used_bytes / s.capacity_bytes;
          const tone = ratio >= s.hold_ratio ? 'discrepancy' : ratio >= s.warning_ratio ? 'notice' : 'data';
          return (
            <div>
              <div className="flex flex-wrap items-end justify-between gap-3">
                <p className="text-[40px] font-medium leading-none tracking-[-0.04em] text-ink tabular">
                  {formatBytes(s.used_bytes)} <span className="text-[16px] font-medium tracking-normal text-ink-2">of {formatBytes(s.capacity_bytes)}</span>
                </p>
                {s.imports_held ? <StatusPill meta={{ label: 'Imports on hold', tone: 'discrepancy', icon: ShieldAlert }} /> : <StatusPill meta={{ label: 'Imports accepted', tone: 'ready', icon: CircleCheck }} />}
              </div>
              <div className="relative mt-4">
                <Progress value={ratio * 100} tone={tone} label="Disk used" className="h-3" />
                {[s.warning_ratio, s.hold_ratio].map((r, i) => (
                  <span key={r} aria-hidden className="absolute -top-1 h-5 border-l-2 border-dashed border-ink-3/60" style={{ left: `${r * 100}%` }}>
                    <span className="absolute left-1 top-5 whitespace-nowrap text-[11.5px] text-ink-3">{i === 0 ? 'Warning' : 'Hold'} {Math.round(r * 100)}%</span>
                  </span>
                ))}
              </div>
              <ul className="mt-9 space-y-3">
                {s.breakdown.map((b) => (
                  <li key={b.key} className="grid grid-cols-[minmax(150px,220px)_minmax(0,1fr)_90px] items-center gap-4">
                    <span className="text-[14px] text-ink">{b.label}</span>
                    <HatchedBar value={b.bytes} max={s.used_bytes} variant={b.key === 'backup' ? 'muted' : 'data'} height={12} label={`${b.label} ${formatBytes(b.bytes)}`} />
                    <span className="text-right text-[13.5px] text-ink-2 tabular">{formatBytes(b.bytes)}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        }}
      </Loading>
    </SettingsCard>
  );
}

/* Audit ───────────────────────────────────────────────────────────── */

const RESULT_TONE: Record<AuditEntry['result'], 'ready' | 'discrepancy' | 'notice'> = { OK: 'ready', DENIED: 'discrepancy', CONFLICT: 'notice' };

export function AuditPage() {
  return (
    <AdminOnly>
      <AuditInner />
    </AdminOnly>
  );
}
function AuditInner() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<AuditEntry['result'] | 'ALL'>('ALL');
  const audit = useAudit(query, result);
  return (
    <SettingsCard title="Audit log" description="Append-only record of access, reviews, exports and admin actions. Content and secrets are never logged.">
      <div className="mb-4 flex flex-wrap gap-3">
        <div className="relative min-w-[240px] flex-1">
          <Search aria-hidden className="pointer-events-none absolute left-3.5 top-1/2 size-[18px] -translate-y-1/2 text-ink-3" />
          <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search actor, action, session or correlation ID" aria-label="Search audit log" className="pl-10" />
        </div>
        <Select
          label="Filter by result"
          value={result}
          onValueChange={(v) => setResult(v as typeof result)}
          options={[
            { value: 'ALL', label: 'All results' },
            { value: 'OK', label: 'OK' },
            { value: 'DENIED', label: 'Denied' },
            { value: 'CONFLICT', label: 'Conflict' },
          ]}
        />
      </div>
      <Loading q={audit}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState icon={Search} title="No matching entries" className="py-8" />
          ) : (
            <div className="scrollbar-thin relative max-h-[560px] overflow-auto">
              <table className="w-full min-w-[760px] border-separate border-spacing-0">
                <thead className="sticky top-0 bg-surface">
                  <tr>
                    <th className={TH}>Time (UTC)</th>
                    <th className={TH}>Actor</th>
                    <th className={TH}>Action</th>
                    <th className={TH}>Session</th>
                    <th className={TH}>Result</th>
                    <th className={TH}>Correlation</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((a) => (
                    <tr key={a.id}>
                      <td className={cn(TD, 'whitespace-nowrap text-[13px] text-ink-2 tabular')}>{formatDateTimeUtc(a.at)}</td>
                      <td className={TD}>{a.actor}</td>
                      <td className={TD}>
                        <span className="font-mono text-[13px] text-ink">{a.action}</span>
                        <span className="block text-[12px] text-ink-3">{a.capability}</span>
                      </td>
                      <td className={cn(TD, 'text-ink-2')}>{a.session_title ?? '—'}</td>
                      <td className={TD}>
                        <CodeChip tone={RESULT_TONE[a.result]}>{a.result}</CodeChip>
                      </td>
                      <td className={cn(TD, 'font-mono text-[12px] text-ink-3')}>{a.correlation_id.slice(0, 8)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        }
      </Loading>
    </SettingsCard>
  );
}

/* Retention ───────────────────────────────────────────────────────── */

function PurgeDialog({ r }: { r: RetentionPolicy }) {
  const purge = useRequestPurge();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  const short = reason.trim().length < 8;
  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        if (v) setReason('');
      }}
    >
      <Button size="sm" variant="danger" onClick={() => setOpen(true)}>
        Request purge
      </Button>
      <DialogContent title={`Request purge · ${r.session_title}`} description="A purge request needs a second administrator to approve. Nothing is deleted now; the audit trail is kept.">
        <div className="space-y-1.5">
          <Label htmlFor={`purge-${r.session_id}`}>
            Reason <span className="font-normal text-ink-2">(required, 8+ characters)</span>
          </Label>
          <Textarea id={`purge-${r.session_id}`} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={300} placeholder="Why should this session be purged?" />
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="secondary">Cancel</Button>
          </DialogClose>
          <Button
            variant="danger"
            disabled={short || purge.isPending}
            onClick={() =>
              purge.mutate(
                { sessionId: r.session_id, reason },
                {
                  onSuccess: () => {
                    toast.success('Purge requested', { description: 'Awaiting second-admin approval.' });
                    setOpen(false);
                  },
                  onError: (e) => fail(e, 'Request failed.'),
                },
              )
            }
          >
            {purge.isPending ? <Loader2 className="animate-spin" /> : <Trash2 />} Request purge
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RetentionPage() {
  return (
    <AdminOnly>
      <RetentionInner />
    </AdminOnly>
  );
}
function RetentionInner() {
  const retention = useRetention();
  return (
    <SettingsCard title="Retention" description="Retention follows the source’s data basis. Purge is a two-step request.">
      <Loading q={retention}>
        {(list) => (
          <ul className="divide-y divide-hairline-soft">
            {list.map((r) => (
              <li key={r.session_id} className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3.5">
                <div className="min-w-[220px] flex-1">
                  <p className="text-[15px] font-medium text-ink">{r.session_title}</p>
                  <p className="mt-0.5 text-[12.5px] text-ink-3">{r.basis}</p>
                </div>
                <CodeChip>{r.source_kind}</CodeChip>
                <span className="w-[110px] text-[13.5px] text-ink-2 tabular">{r.retention_days == null ? 'No limit set' : `${r.retention_days} days`}</span>
                {r.purge_status === 'NONE' ? (
                  <PurgeDialog r={r} />
                ) : (
                  <StatusPill size="sm" meta={{ label: r.purge_status === 'REQUESTED' ? 'Purge requested' : 'Purge approved', tone: 'notice', icon: UserCheck }} />
                )}
              </li>
            ))}
          </ul>
        )}
      </Loading>
    </SettingsCard>
  );
}
