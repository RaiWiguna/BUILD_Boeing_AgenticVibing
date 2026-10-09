import type { ReactNode } from 'react';
import { Breadcrumb, MetaSep } from '@/components/layout/PageHeader';
import { useSessionScope } from '@/hooks/useSessionScope';
import { LensSummary, ModeToggle, RunSelector, SessionLabels } from './SessionHeader';

export interface Crumb {
  label: string;
  to?: string;
}

/**
 * One header for every session screen except the Workspace (comp 03):
 * `Sessions › {session} › {area}` breadcrumb, title, a context strip
 * (run · lens · labels) and actions on the right. The lens toggle always sits
 * first in the actions so it is in the same place on every screen.
 */
export function SessionPageHeader({ title, area, crumbs, chips, actions, lens = true }: { title: ReactNode; area: string; crumbs?: Crumb[]; chips?: ReactNode; actions?: ReactNode; lens?: boolean }) {
  const { detail, run, href } = useSessionScope();
  if (!detail) return null;
  const trail: Crumb[] = [{ label: 'Sessions', to: `/sessions?selected=${detail.id}` }, { label: detail.title, to: href('workspace') }, ...(crumbs ?? [{ label: area }])];
  return (
    <header className="mb-5 short:mb-3">
      <div className="fit:short:sr-only">
        <Breadcrumb items={trail} />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
        <h1 className="text-[34px] font-medium leading-[1.05] tracking-[-0.04em] text-ink xl:text-[42px] short:xl:text-[34px]">{title}</h1>
        {(lens || actions) && (
          <div className="flex flex-wrap items-center gap-2.5">
            {lens && <ModeToggle />}
            {actions}
          </div>
        )}
      </div>
      {/* Context strip spans the full width so labels never wrap under the actions. */}
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2 short:mt-1">
        <p className="flex flex-wrap items-center gap-x-2 text-[16px] text-ink-2 tabular">
          {run ? <RunSelector /> : 'No run'}
          <MetaSep />
          <LensSummary />
        </p>
        <SessionLabels />
        {chips}
      </div>
    </header>
  );
}
