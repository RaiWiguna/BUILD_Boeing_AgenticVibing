import { Check, LogOut, Minus, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router';
import type { Capability } from '@/api/types';
import { useAuth } from '@/app/providers/AuthProvider';
import { CodeChip } from '@/components/domain/primitives';
import { Avatar } from '@/components/layout/UserMenu';
import { Button } from '@/components/ui/button';
import { ROLE_LABEL } from '@/lib/roles';
import { formatDateTimeUtc } from '@/lib/time';
import { cn } from '@/lib/utils';
import { SettingsCard } from './SettingsLayout';

export const CAPABILITY_INFO: Record<Capability, { label: string; detail: string }> = {
  'session.read': { label: 'Read sessions', detail: 'Open replay, memory, review and debrief screens.' },
  'session.import': { label: 'Import sessions', detail: 'Create import drafts and commit sources.' },
  'analysis.create': { label: 'Start analysis', detail: 'Run or re-run analysis on a source revision.' },
  'audio.play': { label: 'Play evidence audio', detail: 'Listen to evidence ranges (visual only in this build).' },
  'review.write': { label: 'Write reviews', detail: 'Append review decisions, pairings and transcript revisions.' },
  'export.create': { label: 'Create exports', detail: 'Create brief revisions and report exports.' },
  'truth.read': { label: 'Read ground truth', detail: 'See evaluation ground truth for synthetic sessions.' },
  'admin.manage': { label: 'Administer workspace', detail: 'Users, grants, providers, jobs, storage, audit, retention.' },
};

export function AccountPage() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();
  if (!session) return null;
  const a = session.account;
  return (
    <div className="space-y-5">
      <SettingsCard title="Profile">
        <div className="flex flex-wrap items-center gap-4">
          <Avatar name={a.name} className="size-16 text-[20px]" />
          <div className="min-w-0 flex-1">
            <p className="text-[22px] font-semibold tracking-[-0.02em] text-ink">{a.name}</p>
            <p className="text-[15px] text-ink-2">{a.email}</p>
          </div>
          <CodeChip tone="data">{ROLE_LABEL[a.role]}</CodeChip>
        </div>
        <dl className="mt-5 grid gap-x-8 gap-y-3 border-t border-hairline-soft pt-4 text-[14.5px] sm:grid-cols-2">
          <div>
            <dt className="text-ink-2">Last sign-in</dt>
            <dd className="text-ink tabular">{a.last_login_at ? formatDateTimeUtc(a.last_login_at) : '—'}</dd>
          </div>
          <div>
            <dt className="text-ink-2">Session expires</dt>
            <dd className="text-ink tabular">
              {formatDateTimeUtc(session.expires_at)}
              <span className="block text-[13px] text-ink-3">Idle timeout {formatDateTimeUtc(session.idle_expires_at)}</span>
            </dd>
          </div>
        </dl>
      </SettingsCard>

      <SettingsCard title="What you can do" description="Capabilities come from your role and per-session grants. The server checks every request.">
        <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {(Object.keys(CAPABILITY_INFO) as Capability[]).map((c) => {
            const has = session.capabilities.includes(c);
            return (
              <li key={c} className={cn('flex gap-3 rounded-[14px] border px-3.5 py-3', has ? 'border-hairline-soft' : 'border-dashed border-hairline bg-sunken/60')}>
                <span aria-hidden className={cn('mt-0.5 inline-flex size-5 shrink-0 items-center justify-center rounded-full', has ? 'bg-data-tint text-data' : 'bg-track text-ink-3')}>
                  {has ? <Check className="size-3.5" strokeWidth={2.6} /> : <Minus className="size-3.5" />}
                </span>
                <div className="min-w-0">
                  <p className={cn('text-[14.5px] font-medium', has ? 'text-ink' : 'text-ink-2')}>
                    {CAPABILITY_INFO[c].label} <span className="sr-only">{has ? '(granted)' : '(not granted)'}</span>
                  </p>
                  <p className="text-[13px] text-ink-3">{CAPABILITY_INFO[c].detail}</p>
                </div>
              </li>
            );
          })}
        </ul>
      </SettingsCard>

      <SettingsCard title="Security" description="Individual accounts only — no shared logins.">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="flex max-w-[60ch] items-start gap-2.5 text-[14px] text-ink-2">
            <ShieldCheck aria-hidden className="mt-0.5 size-[18px] shrink-0 text-ready" />
            {a.must_change_password ? 'An administrator reset your password. You will be asked to choose a new one at next sign-in.' : 'Password changes are handled by an administrator in this MOCK build.'}
          </p>
          <Button
            variant="secondary"
            onClick={async () => {
              await logout();
              navigate('/login', { replace: true });
            }}
          >
            <LogOut /> Sign out
          </Button>
        </div>
      </SettingsCard>
    </div>
  );
}
