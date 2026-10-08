import { MoreHorizontal, TrendingDown, TrendingUp, type LucideIcon } from 'lucide-react';
import * as React from 'react';
import { cn } from '@/lib/utils';
import { TONE_PILL, TONE_TILE, type StatusMeta, type Tone } from '@/lib/status';

/* Card ─────────────────────────────────────────────────────────────── */
export function Card({ className, as: As = 'section', ...props }: React.HTMLAttributes<HTMLElement> & { as?: 'section' | 'div' | 'article' | 'aside' }) {
  return <As className={cn('card', className)} {...props} />;
}

export function CardHeader({ title, subtitle, actions, className, titleAs: H = 'h2', id }: { title: React.ReactNode; subtitle?: React.ReactNode; actions?: React.ReactNode; className?: string; titleAs?: 'h2' | 'h3'; id?: string }) {
  return (
    <div className={cn('flex items-start justify-between gap-4', className)}>
      <div className="min-w-0">
        <H id={id} className="text-section font-semibold text-ink">{title}</H>
        {subtitle && <p className="mt-1 text-[14px] text-ink-2">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export const MoreButton = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & { label: string }>(({ label, className, ...props }, ref) => (
  <button ref={ref} type="button" aria-label={label} className={cn('inline-flex size-10 shrink-0 items-center justify-center rounded-full border border-hairline bg-surface text-ink-2 transition-colors duration-[140ms] hover:bg-sunken hover:text-ink', className)} {...props}>
    <MoreHorizontal className="size-[18px]" />
  </button>
));
MoreButton.displayName = 'MoreButton';

/* Pills ────────────────────────────────────────────────────────────── */
export function Pill({ tone = 'neutral', icon: Icon, children, className, size = 'md' }: { tone?: Tone; icon?: LucideIcon; children: React.ReactNode; className?: string; size?: 'sm' | 'md' }) {
  return (
    <span className={cn('inline-flex max-w-full items-center gap-1.5 rounded-full font-medium', size === 'sm' ? 'h-6 px-2 text-[12px]' : 'h-7 px-2.5 text-[13px]', TONE_PILL[tone], className)}>
      {Icon && <Icon aria-hidden className={size === 'sm' ? 'size-3.5' : 'size-[14px]'} />}
      <span className="truncate">{children}</span>
    </span>
  );
}

/** Enum status: readable label with icon, optional raw code (e.g. NOT_EVALUABLE). */
export function StatusPill({ meta, showCode = false, size = 'md', className }: { meta: StatusMeta; showCode?: boolean; size?: 'sm' | 'md'; className?: string }) {
  return (
    <Pill tone={meta.tone} icon={meta.icon} size={size} className={className}>
      {showCode && meta.code ? <span className="tracking-[0.02em]">{meta.code}</span> : meta.label}
    </Pill>
  );
}

/** Uppercase code chip — SYNTHETIC, LAB_ONLY, ATTENTION · OPEN (matches the reference comps). */
export function CodeChip({ children, tone = 'neutral', className, title }: { children: React.ReactNode; tone?: Tone; className?: string; title?: string }) {
  return (
    <span title={title} className={cn('inline-flex h-6 shrink-0 items-center rounded-full px-2.5 text-[11.5px] font-semibold uppercase tracking-[0.045em]', tone === 'neutral' ? 'bg-[#eceef1] text-[#4b5260]' : TONE_PILL[tone], className)}>
      {children}
    </span>
  );
}

export function Dot({ tone, className }: { tone: Tone; className?: string }) {
  const map: Record<Tone, string> = { data: 'bg-data', discrepancy: 'bg-[#d63384]', notice: 'bg-[#e0a21a]', ready: 'bg-[#22a35f]', muted: 'bg-[#a3aab5]', neutral: 'bg-[#a3aab5]' };
  return <span aria-hidden className={cn('inline-block size-2 shrink-0 rounded-full', map[tone], className)} />;
}

export function IconTile({ icon: Icon, tone = 'neutral', size = 'md', className }: { icon: LucideIcon; tone?: Tone; size?: 'sm' | 'md' | 'lg'; className?: string }) {
  const s = { sm: 'size-8 [&_svg]:size-4', md: 'size-10 [&_svg]:size-[19px]', lg: 'size-12 [&_svg]:size-[22px]' }[size];
  return (
    <span aria-hidden className={cn('inline-flex shrink-0 items-center justify-center rounded-full', TONE_TILE[tone], s, className)}>
      <Icon strokeWidth={1.9} />
    </span>
  );
}

/** White pill with a coloured triangle — "▼ 1.2 pts vs last week". */
export function DeltaPill({ value, unit = '', goodWhen = 'down', label }: { value: number; unit?: string; goodWhen?: 'up' | 'down' | 'neutral'; label: string }) {
  const up = value > 0;
  const tone = value === 0 || goodWhen === 'neutral' ? 'text-ink-2' : (up && goodWhen === 'up') || (!up && goodWhen === 'down') ? 'text-ready' : 'text-discrepancy';
  const Icon = up ? TrendingUp : TrendingDown;
  return (
    <span className="inline-flex items-center gap-2">
      <span className={cn('inline-flex h-7 items-center gap-1 rounded-full bg-surface px-2.5 text-[13px] font-semibold shadow-pop tabular', tone)}>
        <Icon aria-hidden className="size-3.5" />
        {value === 0 ? '0' : `${up ? '+' : '−'}${Math.abs(value)}`}
        {unit}
      </span>
      <span className="text-[13px] text-ink-2">{label}</span>
    </span>
  );
}

/* Hatched bars (Margin data language) ─────────────────────────────── */
export function HatchedBar({ value, max, variant = 'data', className, height = 10, label }: { value: number; max: number; variant?: 'data' | 'data-solid' | 'discrepancy' | 'muted' | 'notice'; className?: string; height?: number; label?: string }) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  const fill = { data: 'hatch-data', 'data-solid': 'bg-data', discrepancy: 'hatch-discrepancy', muted: 'hatch-muted', notice: 'hatch-notice' }[variant];
  return (
    <div role={label ? 'img' : undefined} aria-label={label} className={cn('w-full overflow-hidden rounded-full bg-sunken', className)} style={{ height }}>
      <div className={cn('h-full rounded-full', fill)} style={{ width: `${pct}%` }} />
    </div>
  );
}

/* Key/value row ────────────────────────────────────────────────────── */
export function KeyValue({ label, children, className }: { label: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('grid grid-cols-[minmax(110px,40%)_1fr] items-center gap-4 py-2.5', className)}>
      <dt className="text-[14px] text-ink-2">{label}</dt>
      <dd className="min-w-0 text-[15px] text-ink">{children}</dd>
    </div>
  );
}

export function SectionLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return <p className={cn('text-[12px] font-medium uppercase tracking-[0.06em] text-ink-3', className)}>{children}</p>;
}
