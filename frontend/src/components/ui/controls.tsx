import { RadioGroup as R, Select as S, Switch as Sw, ToggleGroup as T, Progress as Pr } from 'radix-ui';
import { Check, ChevronDown } from 'lucide-react';
import * as React from 'react';
import { cn } from '@/lib/utils';

/* Radio */
export const RadioGroup = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<typeof R.Root>>(({ className, ...props }, ref) => <R.Root ref={ref} className={cn('grid gap-1', className)} {...props} />);
RadioGroup.displayName = 'RadioGroup';

export function RadioRow({ value, label, description, disabled, className }: { value: string; label: React.ReactNode; description?: React.ReactNode; disabled?: boolean; className?: string }) {
  const id = React.useId();
  return (
    <label htmlFor={id} className={cn('group flex cursor-pointer items-start gap-3 rounded-[12px] px-3 py-2.5 transition-colors duration-[140ms] hover:bg-sunken has-[[data-state=checked]]:bg-data-tint has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-60', className)}>
      <R.Item id={id} value={value} disabled={disabled} aria-labelledby={`${id}-label`} aria-describedby={description ? `${id}-desc` : undefined} className="mt-[2px] flex size-[20px] shrink-0 items-center justify-center rounded-full border-[1.5px] border-boundary bg-surface transition-colors data-[state=checked]:border-data focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus">
        <R.Indicator className="size-[10px] rounded-full bg-data" />
      </R.Item>
      <span className="min-w-0">
        <span id={`${id}-label`} className="block text-[15px] text-ink">{label}</span>
        {description && <span id={`${id}-desc`} className="mt-0.5 block text-caption text-ink-2">{description}</span>}
      </span>
    </label>
  );
}

/* Switch */
export const Switch = React.forwardRef<HTMLButtonElement, React.ComponentPropsWithoutRef<typeof Sw.Root>>(({ className, ...props }, ref) => (
  <Sw.Root
    ref={ref}
    className={cn('relative inline-flex h-[28px] w-[48px] shrink-0 items-center rounded-full bg-[#dfe3e8] p-[3px] transition-colors duration-[160ms] data-[state=checked]:bg-data disabled:cursor-not-allowed disabled:opacity-55 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus', className)}
    {...props}
  >
    <Sw.Thumb className="block size-[22px] rounded-full bg-white shadow-[0_1px_3px_rgba(25,27,32,0.25)] transition-transform duration-[160ms] data-[state=checked]:translate-x-[20px]" />
  </Sw.Root>
));
Switch.displayName = 'Switch';

/* Select */
export function Select({ value, onValueChange, options, label, className, icon, size = 'default' }: { value: string; onValueChange: (v: string) => void; options: { value: string; label: string }[]; label: string; className?: string; icon?: React.ReactNode; size?: 'default' | 'sm' }) {
  return (
    <S.Root value={value} onValueChange={onValueChange}>
      <S.Trigger aria-label={label} className={cn('inline-flex items-center gap-2 whitespace-nowrap rounded-control border border-hairline bg-surface pl-3.5 pr-3 text-[14px] font-medium text-ink shadow-control transition-colors hover:bg-sunken focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus [&_svg]:size-4', size === 'sm' ? 'h-9' : 'h-11', className)}>
        {icon}
        <S.Value />
        <S.Icon asChild>
          <ChevronDown className="ml-auto text-ink-2" />
        </S.Icon>
      </S.Trigger>
      <S.Portal>
        <S.Content position="popper" sideOffset={6} className="z-50 min-w-[var(--radix-select-trigger-width)] rounded-[16px] border border-hairline-soft bg-surface p-1.5 shadow-pop data-[state=open]:animate-in data-[state=open]:fade-in-0">
          <S.Viewport>
            {options.map((o) => (
              <S.Item key={o.value} value={o.value} className="relative flex h-9 cursor-pointer select-none items-center rounded-[10px] pl-3 pr-9 text-[14px] text-ink outline-none data-[highlighted]:bg-track">
                <S.ItemText>{o.label}</S.ItemText>
                <S.ItemIndicator className="absolute right-3">
                  <Check className="size-4 text-data" />
                </S.ItemIndicator>
              </S.Item>
            ))}
          </S.Viewport>
        </S.Content>
      </S.Portal>
    </S.Root>
  );
}

/* Segmented control (As-known / Debrief, 0.5× / 1× / 2×, HTML / CSV / JSON) */
export function Segmented<V extends string>({ value, onChange, options, label, className, size = 'default', tone = 'neutral' }: { value: V; onChange: (v: V) => void; options: { value: V; label: React.ReactNode; disabled?: boolean }[]; label: string; className?: string; size?: 'default' | 'sm'; tone?: 'neutral' | 'data' }) {
  return (
    <T.Root type="single" value={value} onValueChange={(v) => v && onChange(v as V)} aria-label={label} className={cn('inline-flex items-center gap-1 rounded-[14px] bg-track p-1', className)}>
      {options.map((o) => (
        <T.Item
          key={o.value}
          value={o.value}
          disabled={o.disabled}
          className={cn(
            'inline-flex flex-1 items-center justify-center gap-1.5 whitespace-nowrap rounded-[10px] px-3.5 font-medium text-ink-2 transition-[background-color,color,box-shadow] duration-[140ms] hover:text-ink disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus',
            size === 'sm' ? 'h-8 text-[13px]' : 'h-9 text-[14px]',
            tone === 'data' ? 'data-[state=on]:bg-data-tint data-[state=on]:text-data-strong data-[state=on]:shadow-[inset_0_0_0_1px_rgba(37,99,235,0.18)]' : 'data-[state=on]:bg-surface data-[state=on]:text-ink data-[state=on]:shadow-control',
          )}
        >
          {o.label}
        </T.Item>
      ))}
    </T.Root>
  );
}

/* Progress */
export function Progress({ value, className, tone = 'data', label }: { value: number; className?: string; tone?: 'data' | 'notice' | 'discrepancy' | 'ready'; label: string }) {
  const color = { data: 'bg-data', notice: 'bg-notice', discrepancy: 'bg-discrepancy', ready: 'bg-ready' }[tone];
  return (
    <Pr.Root value={value} aria-label={label} className={cn('relative h-2 w-full overflow-hidden rounded-full bg-track', className)}>
      <Pr.Indicator className={cn('h-full rounded-full transition-[width] duration-300', color)} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </Pr.Root>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn('animate-pulse rounded-[10px] bg-track', className)} />;
}

export function Separator({ className, vertical }: { className?: string; vertical?: boolean }) {
  return <div role="separator" aria-orientation={vertical ? 'vertical' : 'horizontal'} className={cn(vertical ? 'w-px self-stretch bg-hairline' : 'h-px w-full bg-hairline', className)} />;
}
