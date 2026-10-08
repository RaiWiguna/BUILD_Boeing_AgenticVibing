import { cn } from '@/lib/utils';

/** FlowLens mark: a lens ring with a communication path crossing it. Exploratory, not an official logo. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 36 36" aria-hidden className={cn('size-9', className)}>
      <defs>
        <linearGradient id="fl-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#3b7bff" />
          <stop offset="1" stopColor="#1d4fd7" />
        </linearGradient>
      </defs>
      <rect width="36" height="36" rx="11" fill="url(#fl-g)" />
      <circle cx="18" cy="18" r="8.2" fill="none" stroke="#fff" strokeWidth="2.3" opacity="0.95" />
      <path d="M6.5 22.5c6-0.6 10.6-4 14.8-9.8l8.4-3.4" fill="none" stroke="#fff" strokeWidth="2.3" strokeLinecap="round" />
      <circle cx="21.3" cy="12.7" r="1.9" fill="#fff" />
    </svg>
  );
}

export function Wordmark({ collapsed }: { collapsed?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      {!collapsed && <span className="text-[21px] font-semibold tracking-[-0.025em] text-ink">FlowLens</span>}
    </span>
  );
}
