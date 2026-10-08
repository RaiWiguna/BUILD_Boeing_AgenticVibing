import type { ReactNode } from 'react';
import { MetaSep } from '@/components/layout/PageHeader';
import { useSessionScope } from '@/hooks/useSessionScope';
import { SessionLabels } from './SessionHeader';

/**
 * Big-title header for session sub-pages (Review, Debrief, Metrics, Ask):
 * title + "Runway 27 · … · Run #03" meta + session labels, actions on the right.
 */
export function SessionPageHeader({ title, meta, chips, actions }: { title: ReactNode; meta?: ReactNode[]; chips?: ReactNode; actions?: ReactNode }) {
  const { detail, run } = useSessionScope();
  if (!detail) return null;
  const runway = detail.layout?.runways[0];
  const parts = meta ?? [runway ? `Runway ${runway.ends[1]}` : detail.title, detail.context, run ? `Run ${run.label}` : 'No run'];
  return (
    <header className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div className="min-w-0 flex-1">
        <h1 className="text-[36px] font-medium leading-[1.05] tracking-[-0.04em] text-ink xl:text-[46px]">{title}</h1>
        <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-2">
          <p className="flex flex-wrap items-center gap-x-2 text-[17px] text-ink-2 tabular">
            {parts.map((p, i) => (
              <span key={i} className="contents">
                {i > 0 && <MetaSep />}
                {p}
              </span>
            ))}
          </p>
          <SessionLabels />
          {chips}
        </div>
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2.5">{actions}</div>}
    </header>
  );
}
