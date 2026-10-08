import { FlaskConical, ServerOff } from 'lucide-react';
import { Tooltip } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { CodeChip } from './primitives';

/** Always-visible data labels (G-19): SYNTHETIC · MOCK DATA · Replay offline. */
export function DataLabels({ className, mode, extra }: { className?: string; mode?: 'AS_KNOWN' | 'DEBRIEF'; extra?: React.ReactNode }) {
  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      <CodeChip title="Synthetic data, not validated against operations">SYNTHETIC</CodeChip>
      <Tooltip content="All data on this page is served by the in-browser MOCK adapter. No backend or provider was called.">
        <span tabIndex={0} className="inline-flex h-6 items-center gap-1.5 rounded-full bg-[#fff1e8] px-2.5 text-[11.5px] font-semibold uppercase tracking-[0.045em] text-[#a2470f]">
          <FlaskConical aria-hidden className="size-3" /> Mock data
        </span>
      </Tooltip>
      <span className="inline-flex h-6 items-center gap-1.5 rounded-full bg-track px-2.5 text-[12.5px] font-medium text-ink-2">
        <ServerOff aria-hidden className="size-3" /> Replay offline
      </span>
      {mode && <CodeChip tone={mode === 'AS_KNOWN' ? 'data' : 'neutral'}>{mode === 'AS_KNOWN' ? 'As-known' : 'Debrief'}</CodeChip>}
      {extra}
    </div>
  );
}
