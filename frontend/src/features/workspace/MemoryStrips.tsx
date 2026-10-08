import { Car, ChevronRight, Plane } from 'lucide-react';
import { Link } from 'react-router';
import type { EntityInfo, EntityStateView } from '@/api/types';
import { useEvidence } from '@/hooks/useEvidence';
import { STATUS, TONE_TEXT } from '@/lib/status';
import { formatAge } from '@/lib/time';
import { cn } from '@/lib/utils';

function Field({ label, children, sub, className }: { label: string; children: React.ReactNode; sub?: React.ReactNode; className?: string }) {
  return (
    <div className={cn('min-w-0', className)}>
      <p className="text-[12.5px] text-ink-3">{label}</p>
      <div className="mt-1 line-clamp-2 break-words text-[13.5px] font-medium leading-snug text-ink">{children}</div>
      {sub && <p className="mt-0.5 line-clamp-2 text-[12px] leading-snug text-ink-3">{sub}</p>}
    </div>
  );
}

/**
 * One memory strip per object: instruction · readback · movement · source age.
 * Said, Heard and Observed stay in separate columns (G-03); unknown is never green.
 */
export function MemoryStrip({ entity, state, selected, onSelect, memoryHref }: { entity: EntityInfo; state: EntityStateView | undefined; selected: boolean; onSelect: () => void; memoryHref: string }) {
  const { open } = useEvidence();
  const Icon = entity.kind === 'VEHICLE' ? Car : Plane;
  const ins = state?.instruction;
  const rb = state?.readback;
  const mv = state?.movement;
  const rbMeta = rb ? STATUS.readback[rb.state] : null;
  const mvMeta = mv ? STATUS.movement[mv.state] : null;
  const insActive = ins && ins.state !== 'UNKNOWN' && ins.summary;
  const rbKnown = rb && rb.state !== 'NOT_OBSERVED';
  const evidenceId = rb?.evidence_id ?? ins?.evidence_id ?? null;
  const trackMissing = state?.track_status === 'MISSING';
  const stale = state?.track_status === 'STALE';
  const notEvaluable = mv?.state === 'NOT_EVALUABLE';

  return (
    <li
      className={cn(
        'group relative grid cursor-pointer grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-3 rounded-[18px] border px-3.5 py-3 transition-[background-color,border-color,box-shadow] duration-[140ms] @[700px]:grid-cols-[minmax(118px,0.9fr)_minmax(0,1.05fr)_minmax(0,1fr)_minmax(0,1.15fr)_minmax(64px,0.55fr)_auto]',
        selected ? 'border-data/25 bg-data-tint/70 shadow-[inset_3px_0_0_0_#2563eb]' : 'border-hairline-soft bg-surface hover:border-hairline hover:bg-sunken/50',
      )}
      onClick={onSelect}
    >
      <div className="flex min-w-0 items-center gap-2.5">
        <button
          type="button"
          aria-pressed={selected}
          aria-label={`${selected ? 'Selected' : 'Select'} ${entity.callsign} on the situation canvas`}
          onClick={(e) => {
            e.stopPropagation();
            onSelect();
          }}
          className={cn('-ml-1 inline-flex size-9 shrink-0 items-center justify-center rounded-full transition-colors', selected ? 'text-data' : 'text-ink hover:bg-track')}
        >
          <Icon aria-hidden className={cn('size-[22px]', entity.kind === 'AIRCRAFT' && '-rotate-45')} strokeWidth={1.8} />
        </button>
        <div className="min-w-0">
          <Link
            to={memoryHref}
            onClick={(e) => e.stopPropagation()}
            title={`Open ${entity.callsign} memory`}
            className={cn('block truncate rounded-[6px] text-[17.5px] font-semibold tracking-[-0.02em] underline-offset-4 hover:underline', selected ? 'text-data' : 'text-ink')}
          >
            {entity.callsign}
          </Link>
          <p className="truncate text-[12.5px] text-ink-2" title={`${entity.type} · ${entity.role}`}>
            {entity.type} · {entity.role}
          </p>
        </div>
      </div>

      <div className="col-span-2 grid grid-cols-2 gap-x-4 gap-y-3 @[560px]:grid-cols-4 @[700px]:contents">
        <Field label="Instruction" className="@[700px]:border-l @[700px]:border-hairline @[700px]:pl-3">
          {insActive ? ins.summary : <span className="text-ink-3">—</span>}
        </Field>
        <Field label="Readback" className="@[700px]:border-l @[700px]:border-hairline @[700px]:pl-3">
          {rbKnown && rbMeta ? (
            <span className={cn('inline-flex items-center gap-1', rbMeta.tone === 'ready' ? 'text-ink' : TONE_TEXT[rbMeta.tone])}>
              {rb.state === 'MATCHED' ? 'Matches' : (rb.summary ?? rbMeta.label)}
            </span>
          ) : rb?.state === 'NOT_OBSERVED' && insActive ? (
            <span className="text-ink-2">Not observed</span>
          ) : (
            <span className="text-ink-3">—</span>
          )}
        </Field>
        <Field
          label="Movement"
          className="@[700px]:border-l @[700px]:border-hairline @[700px]:pl-3"
          sub={notEvaluable && !trackMissing ? (mv?.reason ?? undefined) : stale ? 'Track stale' : undefined}
        >
          {trackMissing ? (
            <span className="text-ink-2">Track not available</span>
          ) : notEvaluable ? (
            <span className="whitespace-nowrap text-[12px] font-semibold tracking-[0.01em] text-ink">NOT_EVALUABLE</span>
          ) : mvMeta && mv ? (
            <span className={mv.state === 'DIVERGENCE_CANDIDATE' ? TONE_TEXT.discrepancy : 'text-ink'}>{mv.state === 'CONSISTENT' ? (mv.summary ?? 'Consistent') : mvMeta.label}</span>
          ) : (
            <span className="text-ink-3">—</span>
          )}
        </Field>
        <Field label="Source" className="@[700px]:border-l @[700px]:border-hairline @[700px]:pl-3">
          {state?.source_age_ms == null ? <span className="text-ink-3">—</span> : <span className={stale ? 'text-notice' : 'text-ink'}>{formatAge(state.source_age_ms)}</span>}
        </Field>
      </div>

      <div className="col-start-2 row-start-1 flex items-center gap-1.5 @[700px]:col-start-auto @[700px]:row-start-auto">
        <button
          type="button"
          disabled={!evidenceId}
          onClick={(e) => {
            e.stopPropagation();
            if (evidenceId) open(evidenceId);
          }}
          className="inline-flex h-9 items-center gap-1 whitespace-nowrap rounded-[11px] border border-hairline bg-surface pl-3 pr-2 text-[13.5px] font-medium text-ink shadow-control transition-colors hover:bg-sunken disabled:cursor-not-allowed disabled:text-ink-3 disabled:shadow-none"
          aria-label={evidenceId ? `View evidence for ${entity.callsign}` : `No evidence for ${entity.callsign} yet`}
        >
          View evidence <ChevronRight aria-hidden className="size-4 text-ink-2" />
        </button>
      </div>
    </li>
  );
}
