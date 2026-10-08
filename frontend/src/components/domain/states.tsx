import { AlertTriangle, Inbox, Lock, MonitorSmartphone, RefreshCw, Sparkles, WifiOff, type LucideIcon } from 'lucide-react';
import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/controls';
import { errorTitle, isApiError } from '@/api/errors';
import { cn } from '@/lib/utils';
import { TONE_PILL, type Tone } from '@/lib/status';
import { IconTile } from './primitives';

export function EmptyState({ icon = Inbox, title, children, action, className, tone = 'neutral' }: { icon?: LucideIcon; title: string; children?: React.ReactNode; action?: React.ReactNode; className?: string; tone?: Tone }) {
  return (
    <div className={cn('flex flex-col items-center justify-center px-6 py-12 text-center', className)}>
      <IconTile icon={icon} tone={tone} size="lg" />
      <h3 className="mt-4 text-[17px] font-semibold text-ink">{title}</h3>
      {children && <div className="mt-1.5 max-w-[420px] text-[14px] leading-relaxed text-ink-2">{children}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/** Typed error with code, safe message, recovery hint and request ID. Never rendered as an empty success. */
export function ErrorState({ error, onRetry, className, compact }: { error: unknown; onRetry?: () => void; className?: string; compact?: boolean }) {
  if (isApiError(error) && error.code === 'ACCESS_DENIED') return <AccessDenied message={error.message} recovery={error.recovery} className={className} compact={compact} />;
  const message = error instanceof Error ? error.message : 'An unexpected error occurred.';
  const recovery = isApiError(error) ? error.recovery : null;
  const Icon = isApiError(error) && error.code === 'CONNECTION_LOST' ? WifiOff : AlertTriangle;
  return (
    <div role="alert" className={cn(compact ? 'flex items-start gap-3 rounded-[16px] bg-discrepancy-tint/60 p-4 text-left' : 'flex flex-col items-center px-6 py-12 text-center', className)}>
      <IconTile icon={Icon} tone="discrepancy" size={compact ? 'sm' : 'lg'} />
      <div className={compact ? 'min-w-0' : 'mt-4'}>
        <h3 className="text-[16px] font-semibold text-ink">{errorTitle(error)}</h3>
        <p className="mt-1 max-w-[440px] text-[14px] text-ink-2">{message}</p>
        {recovery && <p className="mt-1 max-w-[440px] text-[14px] text-ink">{recovery}</p>}
        {isApiError(error) && <p className="mt-2 text-[12px] text-ink-3 tabular">Code {error.code} · Request {error.requestId}</p>}
        {onRetry && (
          <Button size="sm" variant="secondary" className={compact ? 'mt-3' : 'mt-4'} onClick={onRetry}>
            <RefreshCw /> Try again
          </Button>
        )}
      </div>
    </div>
  );
}

export function AccessDenied({ message, recovery, className, compact, title = 'Access restricted' }: { message?: string; recovery?: string | null; className?: string; compact?: boolean; title?: string }) {
  return (
    <div role="status" className={cn(compact ? 'flex items-start gap-3 rounded-[16px] border border-dashed border-hairline-strong bg-sunken p-4' : 'flex flex-col items-center px-6 py-12 text-center', className)}>
      <IconTile icon={Lock} tone="muted" size={compact ? 'sm' : 'lg'} />
      <div className={compact ? 'min-w-0' : 'mt-4'}>
        <h3 className="text-[16px] font-semibold text-ink">{title}</h3>
        <p className="mt-1 max-w-[440px] text-[14px] text-ink-2">{message ?? 'Your grant does not include this capability. Content is not loaded.'}</p>
        {recovery && <p className="mt-1 max-w-[440px] text-[13px] text-ink-2">{recovery}</p>}
      </div>
    </div>
  );
}

/** Tinted callout — "Margin noticed" pattern: icon, title, body, optional action. */
export function Callout({ tone = 'notice', icon: Icon = AlertTriangle, title, children, action, className }: { tone?: Tone; icon?: LucideIcon; title: React.ReactNode; children?: React.ReactNode; action?: React.ReactNode; className?: string }) {
  const bg: Record<Tone, string> = { notice: 'bg-notice-tint', discrepancy: 'bg-discrepancy-tint', data: 'bg-data-tint', ready: 'bg-ready-tint', muted: 'bg-muted-tint', neutral: 'bg-sunken' };
  const text: Record<Tone, string> = { notice: 'text-notice', discrepancy: 'text-discrepancy', data: 'text-data-strong', ready: 'text-ready', muted: 'text-muted', neutral: 'text-ink' };
  return (
    <div className={cn('rounded-[18px] p-4', bg[tone], className)}>
      <div className="flex items-start gap-3">
        <Icon aria-hidden className={cn('mt-0.5 size-[18px] shrink-0', text[tone])} />
        <div className="min-w-0 flex-1">
          <p className={cn('text-[15px] font-semibold', text[tone])}>{title}</p>
          {children && <div className="mt-1 text-[14px] leading-relaxed text-ink">{children}</div>}
          {action && <div className="mt-3">{action}</div>}
        </div>
      </div>
    </div>
  );
}

export function InlineNote({ children, icon: Icon = Sparkles, tone = 'neutral', className }: { children: React.ReactNode; icon?: LucideIcon; tone?: Tone; className?: string }) {
  return (
    <p className={cn('inline-flex items-center gap-2 rounded-full px-3 py-1 text-[13px]', TONE_PILL[tone], className)}>
      <Icon aria-hidden className="size-3.5 shrink-0" />
      {children}
    </p>
  );
}

export function LoadingRows({ rows = 4, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn('space-y-3', className)} aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}

/** Mobile is read-only (plan §responsive): write controls render from md up; below, a short note. */
export function DesktopOnly({ children, what = 'Reviewing' }: { children: React.ReactNode; what?: string }) {
  return (
    <>
      <div className="hidden md:contents">{children}</div>
      <p className="flex items-center gap-2.5 rounded-[14px] bg-sunken px-3.5 py-3 text-[13.5px] text-ink-2 md:hidden">
        <MonitorSmartphone aria-hidden className="size-4 shrink-0 text-ink-3" /> {what} is available on tablet and desktop. This view is read-only.
      </p>
    </>
  );
}
