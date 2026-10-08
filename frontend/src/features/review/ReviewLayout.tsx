import { ExternalLink } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router';
import { ModeToggle, ScopeBanners, SessionLabels } from '@/features/workspace/SessionHeader';
import { CodeChip } from '@/components/domain/primitives';
import { MetaSep } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { useSessionScope } from '@/hooks/useSessionScope';
import { formatOffset } from '@/lib/time';
import { cn } from '@/lib/utils';

const TABS = [
  { to: 'transcript', label: 'Transcript', title: 'Transcript review', note: 'Original STT stays read-only; corrections are new revisions.' },
  { to: 'findings', label: 'Findings', title: 'Findings', note: 'AI findings and source alerts are recorded separately.' },
  { to: 'options', label: 'Options', title: 'Option candidates', note: 'Hypothetical alternatives for evaluator review.' },
] as const;

/** Shared header + tab bar for Transcript / Findings / Options (comps 05–07). */
export function ReviewLayout() {
  const { detail, run, mode, asOf, sid, carry } = useSessionScope();
  const { pathname } = useLocation();
  const active = TABS.find((t) => pathname.includes(`/review/${t.to}`)) ?? TABS[0];
  if (!detail) return null;
  const q = carry ? `?${carry}` : '';
  const runway = detail.layout?.runways[0];
  return (
    <div className="flex min-h-full flex-col">
      <header className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <h1 className="text-[36px] font-medium leading-[1.05] tracking-[-0.04em] text-ink xl:text-[46px]">{active.title}</h1>
          <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-2">
            <p className="flex flex-wrap items-center gap-x-2 text-[17px] text-ink-2 tabular">
              {runway ? `Runway ${runway.ends[1]}` : detail.title}
              <MetaSep />
              {formatOffset(asOf)}
              <MetaSep />
              {run ? `Run ${run.label}` : 'No run'}
              <MetaSep />
              {mode === 'DEBRIEF' ? 'Debrief' : 'As-known'}
            </p>
            <SessionLabels />
            {active.to === 'options' && <CodeChip tone="discrepancy">LAB_RULE</CodeChip>}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2.5 lg:shrink-0">
          <ModeToggle />
          <Button asChild variant="secondary">
            <Link to={`/s/${sid}/workspace${q}`}>
              <ExternalLink /> Open workspace
            </Link>
          </Button>
        </div>
      </header>
      <nav aria-label="Review sections" className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-[20px] border border-hairline-soft bg-surface px-3 shadow-card">
        <div className="flex">
          {TABS.map((t) => (
            <NavLink
              key={t.to}
              to={`/s/${sid}/review/${t.to}${q}`}
              className={({ isActive }) =>
                cn(
                  'relative inline-flex h-[54px] items-center px-5 text-[16px] font-medium transition-colors after:absolute after:inset-x-3 after:bottom-0 after:h-[2.5px] after:rounded-full',
                  isActive ? 'text-data after:bg-data' : 'text-ink-2 hover:text-ink after:bg-transparent',
                )
              }
            >
              {t.label}
            </NavLink>
          ))}
        </div>
        <p className="hidden pr-3 text-[14px] text-ink-2 lg:block">{active.note}</p>
      </nav>
      <ScopeBanners />
      <Outlet />
    </div>
  );
}

export function ColumnCard({ children, className, label }: { children: ReactNode; className?: string; label?: string }) {
  return (
    <section aria-label={label} className={cn('card min-w-0 p-5', className)}>
      {children}
    </section>
  );
}
