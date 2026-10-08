import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Eye, EyeOff, FlaskConical, Loader2, ShieldCheck } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router';
import { DEMO_ACCOUNT_PASSWORD } from '@/app/devtools/demo';
import { useAuth } from '@/app/providers/AuthProvider';
import { isApiError } from '@/api/errors';
import { Wordmark } from '@/components/layout/Logo';
import { Button } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { useApi } from '@/hooks/useApi';
import { ROLE_LABEL } from '@/lib/roles';
import { cn } from '@/lib/utils';

export function LoginPage() {
  const { session, login } = useAuth();
  const api = useApi();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const demo = useQuery({ queryKey: ['demo-accounts'], queryFn: () => api.demoAccounts(), staleTime: Infinity });
  const next = params.get('next');
  const safeNext = next && next.startsWith('/') && !next.startsWith('//') ? next : '/sessions';

  if (session) return <Navigate to={safeNext} replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!email.trim() || !password) {
      setError('Enter your email and password.');
      return;
    }
    setBusy(true);
    try {
      await login(email, password);
      navigate(safeNext, { replace: true });
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Sign-in failed. Try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid grid-cols-1 min-h-dvh bg-canvas lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      <div className="flex flex-col px-6 py-8 sm:px-12 lg:px-16">
        <Wordmark />
        <div className="mx-auto flex w-full max-w-[420px] flex-1 flex-col justify-center py-12">
          <h1 className="text-[40px] font-medium leading-[1.05] tracking-[-0.035em] text-ink">Sign in</h1>
          <p className="mt-3 text-[16px] text-ink-2">Research replay workspace for reviewing communication context and evidence.</p>

          <form onSubmit={submit} noValidate className="mt-9 space-y-5">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} aria-invalid={!!error} placeholder="name@organisation.test" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input id="password" type={show ? 'text' : 'password'} autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={!!error} className="pr-12" />
                <button type="button" onClick={() => setShow((v) => !v)} aria-label={show ? 'Hide password' : 'Show password'} className="absolute right-1.5 top-1/2 inline-flex size-9 -translate-y-1/2 items-center justify-center rounded-[10px] text-ink-2 hover:bg-track">
                  {show ? <EyeOff className="size-[18px]" /> : <Eye className="size-[18px]" />}
                </button>
              </div>
            </div>
            {error && (
              <p role="alert" className="rounded-[12px] bg-discrepancy-tint px-3.5 py-2.5 text-[14px] text-discrepancy">
                {error}
              </p>
            )}
            <Button type="submit" variant="primary" size="lg" className="w-full" disabled={busy}>
              {busy ? <Loader2 className="animate-spin" /> : null}
              {busy ? 'Signing in…' : 'Sign in'}
              {!busy && <ArrowRight />}
            </Button>
            <p className="flex items-center gap-2 text-[13px] text-ink-2">
              <ShieldCheck aria-hidden className="size-4 text-ink-3" /> Individual accounts only. Sessions expire after 60 min idle.
            </p>
          </form>

          <div className="mt-10 rounded-[20px] border border-dashed border-[#f3d2bd] bg-[#fffaf6] p-4">
            <p className="flex items-center gap-2 text-[13px] font-semibold text-[#a2470f]">
              <FlaskConical className="size-4" /> MOCK demo accounts
            </p>
            <p className="mt-1 text-[12.5px] text-ink-2">
              Password for every demo account: <code className="rounded bg-white px-1.5 py-0.5 text-[12px] text-ink">{DEMO_ACCOUNT_PASSWORD}</code>
            </p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {(demo.data ?? []).map((d) => (
                <button
                  key={d.email}
                  type="button"
                  onClick={() => {
                    setEmail(d.email);
                    setPassword(DEMO_ACCOUNT_PASSWORD);
                    setError(null);
                  }}
                  className={cn('rounded-[12px] border border-hairline bg-surface px-3 py-2 text-left transition-colors hover:border-hairline-strong', email === d.email && 'border-data bg-data-tint')}
                >
                  <span className="block text-[13.5px] font-semibold text-ink">{ROLE_LABEL[d.role]}</span>
                  <span className="block truncate text-[12px] text-ink-2">{d.email}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
        <p className="text-[12.5px] text-ink-3">SYNTHETIC data · Replay offline · NOT_DOMAIN_VALIDATED</p>
      </div>

      <div className="relative hidden overflow-hidden p-4 lg:block">
        <div className="relative h-full overflow-hidden rounded-[32px] bg-[#0f2a6b]">
          <div aria-hidden className="absolute inset-0 bg-[radial-gradient(120%_80%_at_0%_0%,#1f4fd6_0%,transparent_60%),radial-gradient(90%_70%_at_100%_100%,#f3a37a_0%,transparent_55%),radial-gradient(70%_60%_at_80%_20%,#7db3ff_0%,transparent_60%),linear-gradient(160deg,#173a8f,#5b74c4_55%,#e9b7a1)]" />
          <svg aria-hidden viewBox="0 0 600 600" className="absolute inset-0 h-full w-full opacity-[0.22]">
            <rect x="40" y="290" width="520" height="34" rx="6" fill="none" stroke="#fff" strokeWidth="1.5" />
            <path d="M60 307H540" stroke="#fff" strokeDasharray="14 12" strokeWidth="1.5" />
            <path d="M120 440C220 440 300 440 420 420 470 410 470 360 470 324" fill="none" stroke="#fff" strokeWidth="1.5" />
            <path d="M200 170C260 170 300 190 320 220 330 240 330 270 330 290" fill="none" stroke="#fff" strokeWidth="1.5" />
            <path d="M452 352H488" stroke="#fff" strokeWidth="3" />
            <circle cx="470" cy="380" r="7" fill="#fff" />
          </svg>
          <div className="relative flex h-full flex-col justify-end p-12 text-white">
            <span className="inline-flex w-fit items-center gap-2 rounded-full bg-white/15 px-3 py-1.5 text-[13px] font-medium backdrop-blur">Said · Heard · Observed</span>
            <p className="mt-5 max-w-[460px] text-[38px] font-medium leading-[1.08] tracking-[-0.03em]">Context you can trace back to evidence.</p>
            <p className="mt-4 max-w-[440px] text-[16px] leading-relaxed text-white/80">FlowLens replays recorded sessions, keeps instructions, readbacks and observations separate, and shows what is still unknown. The controller keeps all authority.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
