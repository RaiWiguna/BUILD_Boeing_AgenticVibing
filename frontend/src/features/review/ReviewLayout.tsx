import { ExternalLink } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router';
import { ScopeBanners } from '@/features/workspace/SessionHeader';
import { SessionPageHeader } from '@/features/workspace/SessionPageHeader';
import { CodeChip } from '@/components/domain/primitives';
import { Button } from '@/components/ui/button';
import { useSessionScope } from '@/hooks/useSessionScope';
import { cn } from '@/lib/utils';

const TABS = [
  { to: 'transcript', label: 'Transcript', title: 'Transcript review', note: 'Original STT stays read-only; corrections are new revisions.' },
  { to: 'findings', label: 'Findings', title: 'Findings', note: 'Review each finding against its evidence; decisions are append-only.' },
  { to: 'options', label: 'Options', title: 'Option candidates', note: 'Hypothetical alternatives for evaluator review.' },
] as const;

/** Shared header + tab bar for Transcript / Findings / Options (comps 05–07). */
export function ReviewLayout() {
  const { detail, sid, carry, href } = useSessionScope();
  const { pathname } = useLocation();
  const active = TABS.find((t) => pathname.includes(`/review/${t.to}`)) ?? TABS[0];
  if (!detail) return null;
  const q = carry ? `?${carry}` : '';
  return (
    // Findings fits the viewport on large screens (columns scroll inside); the others scroll the page.
    <div className={cn('flex min-h-full flex-col', active.to === 'findings' && 'fit:h-[calc(100dvh-60px)]')}>
      <SessionPageHeader
        title={active.title}
        area="Review"
        crumbs={[{ label: 'Review', to: href('review/findings') }, { label: active.label }]}
        chips={active.to === 'options' && <CodeChip tone="discrepancy">LAB_RULE</CodeChip>}
        actions={
          <Button asChild variant="secondary">
            <Link to={href('workspace')}>
              <ExternalLink /> Open workspace
            </Link>
          </Button>
        }
      />
      <nav aria-label="Review sections" className="mb-5 flex flex-wrap items-center justify-between gap-3 short:mb-3 rounded-[20px] border border-hairline-soft bg-surface px-3 shadow-card">
        <div className="flex">
          {TABS.map((t) => (
            <NavLink
              key={t.to}
              to={`/s/${sid}/review/${t.to}${q}`}
              className={({ isActive }) =>
                cn(
                  'relative inline-flex h-[54px] short:h-11 items-center px-5 text-[16px] font-medium transition-colors after:absolute after:inset-x-3 after:bottom-0 after:h-[2.5px] after:rounded-full',
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
