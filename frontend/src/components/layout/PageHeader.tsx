import { ChevronRight } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router';
import { cn } from '@/lib/utils';

export function Breadcrumb({ items }: { items: { label: string; to?: string }[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-1.5">
      <ol className="flex flex-wrap items-center gap-1.5 text-[14px] text-ink-2">
        {items.map((it, i) => (
          <li key={i} className="flex items-center gap-1.5">
            {it.to ? (
              <Link to={it.to} className="rounded-[6px] hover:text-ink hover:underline underline-offset-4">
                {it.label}
              </Link>
            ) : (
              <span aria-current="page">{it.label}</span>
            )}
            {i < items.length - 1 && <ChevronRight aria-hidden className="size-3.5 text-ink-3" />}
          </li>
        ))}
      </ol>
    </nav>
  );
}

/** Large page title (Margin style) with subtitle row and right-aligned controls. */
export function PageHeader({ title, subtitle, breadcrumb, actions, labels, className }: { title: ReactNode; subtitle?: ReactNode; breadcrumb?: { label: string; to?: string }[]; actions?: ReactNode; labels?: ReactNode; className?: string }) {
  return (
    <header className={cn('mb-6 flex flex-wrap items-start justify-between gap-x-6 gap-y-4', className)}>
      <div className="min-w-0">
        {breadcrumb && <Breadcrumb items={breadcrumb} />}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <h1 className="text-[32px] font-medium leading-[1.08] tracking-[-0.035em] text-ink xl:text-title">{title}</h1>
          {labels}
        </div>
        {subtitle && <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[16px] text-ink-2">{subtitle}</div>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2.5">{actions}</div>}
    </header>
  );
}

export function MetaSep() {
  return <span aria-hidden className="text-ink-3">·</span>;
}
