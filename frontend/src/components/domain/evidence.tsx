import { AudioLines, FileText, Flag, Lightbulb } from 'lucide-react';
import * as React from 'react';
import { useEvidence } from '@/hooks/useEvidence';
import { cn } from '@/lib/utils';

function ChipIcon({ label }: { label: string }) {
  const props = { 'aria-hidden': true, strokeWidth: 2.2 } as const;
  if (label.startsWith('F-')) return <Flag {...props} />;
  if (label.startsWith('Option')) return <Lightbulb {...props} />;
  if (label.startsWith('E-') || label.startsWith('T-')) return <AudioLines {...props} />;
  return <FileText {...props} />;
}

/** Opens the evidence drawer for a scoped evidence/finding ID without changing the replay clock. */
export function EvidenceChip({ id, label, className, size = 'md' }: { id: string; label: string; className?: string; size?: 'sm' | 'md' }) {
  const { open } = useEvidence();
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        open(id);
      }}
      aria-label={`Open evidence ${label}`}
      className={cn(
        'inline-flex shrink-0 items-center gap-1.5 rounded-full bg-data-tint font-semibold text-data-strong transition-colors duration-[140ms] hover:bg-data-soft focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus tabular',
        size === 'sm' ? 'h-6 px-2 text-[12px] [&_svg]:size-3' : 'h-8 px-3 text-[13px] [&_svg]:size-3.5',
        className,
      )}
    >
      <ChipIcon label={label} />
      {label}
    </button>
  );
}

/** Original quote with the critical slot marked. Never truncated (PRD §23.4). */
export function Quote({ text, highlight, tone = 'data', className }: { text: string; highlight?: string | null; tone?: 'data' | 'discrepancy'; className?: string }) {
  const content = React.useMemo(() => {
    if (!highlight) return text;
    const idx = text.toLowerCase().indexOf(highlight.toLowerCase());
    if (idx < 0) return text;
    return (
      <>
        {text.slice(0, idx)}
        <mark className={cn('rounded-[4px] font-semibold', tone === 'discrepancy' ? 'text-discrepancy' : 'text-data')}>
          {text.slice(idx, idx + highlight.length)}
          <span className="sr-only"> (critical slot{tone === 'discrepancy' ? ', differs' : ''})</span>
        </mark>
        {text.slice(idx + highlight.length)}
      </>
    );
  }, [text, highlight, tone]);
  return <q className={cn('break-words text-quote text-ink [quotes:"“"_"”"]', className)}>{content}</q>;
}
