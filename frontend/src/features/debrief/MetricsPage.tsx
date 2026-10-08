import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { ArrowLeftRight, AudioLines, CircleDot, FlaskConical, Info } from 'lucide-react';
import { Link } from 'react-router';
import { qk } from '@/api/queryKeys';
import type { MetricsView } from '@/api/types';
import { useReplay } from '@/features/replay/store';
import { ScopeBanners } from '@/features/workspace/SessionHeader';
import { SessionPageHeader } from '@/features/workspace/SessionPageHeader';
import { CodeChip, DeltaPill, IconTile } from '@/components/domain/primitives';
import { ErrorState, LoadingRows } from '@/components/domain/states';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { useApi } from '@/hooks/useApi';
import { useSessionScope } from '@/hooks/useSessionScope';
import { formatClock } from '@/lib/time';
import { cn } from '@/lib/utils';

function useMetrics() {
  const api = useApi();
  const { sid, runId, asOf, scope } = useSessionScope();
  return useQuery({ queryKey: qk.metrics(sid, runId ?? '-', asOf), queryFn: () => api.getMetrics(scope!, asOf), enabled: !!scope, placeholderData: keepPreviousData });
}

const secs = (ms: number) => Math.round(ms / 1000);

function Kpi({ icon, label, value, unit, delta, deltaUnit, hint }: { icon: typeof AudioLines; label: string; value: number | string; unit?: string; delta: number | null; deltaUnit?: string; hint: string }) {
  return (
    <section className="card flex flex-col p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[15px] font-medium text-ink-2">{label}</p>
        <IconTile icon={icon} size="sm" />
      </div>
      <p className="mt-4 text-[56px] font-medium leading-none tracking-[-0.045em] text-ink tabular">
        {value}
        {unit && <span className="ml-1 text-[22px] font-medium tracking-[-0.02em] text-ink-2">{unit}</span>}
      </p>
      <div className="mt-4 flex min-h-7 items-center">
        {delta == null ? <span className="text-[13px] text-ink-3">No earlier run to compare</span> : <DeltaPill value={delta} unit={deltaUnit} goodWhen="neutral" label="vs previous run" />}
      </div>
      <p className="mt-3 border-t border-hairline-soft pt-3 text-[12.5px] leading-snug text-ink-3">{hint}</p>
    </section>
  );
}

/** Occupied audio per minute — solid up to as-of, hatched after; gaps are hatched grey, never zero. */
function MinuteChart({ m, asOf }: { m: MetricsView; asOf: number }) {
  const seek = useReplay((s) => s.seek);
  const max = Math.ceil(Math.max(60_000, ...m.per_minute.map((x) => x.occupied_ms)) / 30_000) * 30_000;
  const H = 200;
  const refY = H - (m.reference_ms / max) * H;
  return (
    <section aria-labelledby="minute-title" className="card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="minute-title" className="text-[20px] font-semibold tracking-[-0.02em] text-ink">
            Occupied audio time per minute
          </h2>
          <p className="mt-1 text-[14px] text-ink-2">Voice activity on all channels · click a bar to move the replay as-of</p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-[12.5px] text-ink-2">
          <span className="flex items-center gap-1.5">
            <span aria-hidden className="h-3 w-3 rounded-[3px] bg-data" /> Up to as-of
          </span>
          <span className="flex items-center gap-1.5">
            <span aria-hidden className="hatch-data-soft h-3 w-3 rounded-[3px] bg-data-tint" /> After as-of
          </span>
          <span className="flex items-center gap-1.5">
            <span aria-hidden className="hatch-muted h-3 w-3 rounded-[3px] bg-sunken" /> Audio gap (unknown)
          </span>
          <span className="flex items-center gap-1.5">
            <span aria-hidden className="w-4 border-t-2 border-dashed border-discrepancy" /> {m.reference_label}
          </span>
        </div>
      </div>
      <div className="relative mt-6 pl-9">
        <div className="pointer-events-none absolute inset-y-0 left-0 flex w-8 flex-col justify-between text-right text-[11.5px] text-ink-3 tabular" style={{ height: H }}>
          <span>{secs(max)}s</span>
          <span>{secs(max / 2)}s</span>
          <span>0s</span>
        </div>
        <div className="relative" style={{ height: H }}>
          {[0, 0.5, 1].map((f) => (
            <div key={f} aria-hidden className="absolute inset-x-0 border-t border-hairline-soft" style={{ top: f * H }} />
          ))}
          <div aria-hidden className="absolute inset-x-0 z-10 border-t-2 border-dashed border-discrepancy/70" style={{ top: refY }}>
            <span className="absolute -top-[22px] right-0 rounded-full bg-surface px-2 text-[11.5px] font-medium text-discrepancy shadow-control">LAB_RULE {secs(m.reference_ms)} s</span>
          </div>
          <ol className="absolute inset-0 flex items-end gap-[3px]" aria-label="Occupied audio per minute">
            {m.per_minute.map((x) => {
              const start = x.minute * 60_000;
              const past = start + 60_000 <= asOf;
              const current = start <= asOf && asOf < start + 60_000;
              const h = x.gap && x.occupied_ms === 0 ? H * 0.32 : Math.max(3, (x.occupied_ms / max) * H);
              const label = `Minute ${formatClock(start)}: ${x.gap ? 'audio gap, ' : ''}${secs(x.occupied_ms)} s occupied`;
              return (
                <li key={x.minute} className="relative flex h-full flex-1 items-end">
                  <Tooltip content={label}>
                    <button
                      type="button"
                      aria-label={label}
                      onClick={() => seek(start + 59_000)}
                      className={cn(
                        'w-full rounded-t-[6px] transition-[filter] hover:brightness-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
                        x.gap ? 'hatch-muted bg-sunken' : past || current ? 'bg-data' : 'hatch-data-soft bg-data-tint',
                        current && !x.gap && 'bg-gradient-to-t from-data to-[#5b8cf0]',
                      )}
                      style={{ height: h }}
                    />
                  </Tooltip>
                </li>
              );
            })}
          </ol>
          <div aria-hidden className="absolute inset-y-0 z-20 w-0 border-l-2 border-ink" style={{ left: `${(asOf / (m.per_minute.length * 60_000)) * 100}%` }}>
            <span className="absolute -top-6 -translate-x-1/2 whitespace-nowrap rounded-full bg-ink px-2 py-0.5 text-[11px] font-medium text-white tabular">as-of {formatClock(asOf)}</span>
          </div>
        </div>
        <div className="relative mt-2 h-4 text-[11.5px] text-ink-3 tabular">
          {[...m.per_minute.filter((x) => x.minute % 3 === 0 && x.minute <= m.per_minute.length - 2).map((x) => x.minute), m.per_minute.length].map((min) => (
            <span key={min} className="absolute -translate-x-1/2 first:translate-x-0 last:-translate-x-full" style={{ left: `${(min / m.per_minute.length) * 100}%` }}>
              {formatClock(min * 60_000)}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

/** Margin "why" waterfall, re-used as: where attention items came from (counts, not scores). */
function Breakdown({ m }: { m: MetricsView }) {
  const { sid, carry } = useSessionScope();
  const total = m.breakdown.reduce((s, b) => s + b.count, 0);
  const offsets = m.breakdown.map((_, i) => m.breakdown.slice(0, i).reduce((s, b) => s + b.count, 0));
  return (
    <section aria-labelledby="breakdown-title" className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 id="breakdown-title" className="text-[20px] font-semibold tracking-[-0.02em] text-ink">
            Where attention items came from
          </h2>
          <p className="mt-1 text-[14px] text-ink-2">Findings by category in this run · counts only, not a safety score</p>
        </div>
        <p className="text-[40px] font-medium leading-none tracking-[-0.04em] text-ink tabular">{total}</p>
      </div>
      <ol className="mt-5 space-y-1">
        {m.breakdown.map((b, i) => {
          const left = (offsets[i]! / total) * 100;
          const width = (b.count / total) * 100;
          return (
            <li key={b.category} className="grid grid-cols-[minmax(150px,200px)_minmax(0,1fr)_64px] items-center gap-4 py-1.5">
              <span className="truncate text-[14px] text-ink">{b.label}</span>
              <span className="relative h-7">
                {i > 0 && <span aria-hidden className="absolute -top-3 h-3 border-l border-dashed border-hairline-strong" style={{ left: `${left}%` }} />}
                <span className={cn('absolute inset-y-0 rounded-[7px]', b.category.endsWith('DISCREPANCY') ? 'hatch-discrepancy bg-discrepancy-tint' : b.category === 'QUALITY_GAP' ? 'hatch-muted bg-sunken' : 'hatch-data bg-data-tint')} style={{ left: `${left}%`, width: `max(${width}%, 10px)` }} />
              </span>
              <span className="text-right text-[13.5px] font-medium text-ink-2 tabular">
                {b.count} {b.count === 1 ? 'item' : 'items'}
              </span>
            </li>
          );
        })}
        <li className="grid grid-cols-[minmax(150px,200px)_minmax(0,1fr)_64px] items-center gap-4 border-t border-hairline-soft pt-2.5">
          <span className="text-[14px] font-semibold text-ink">Total</span>
          <span className="h-7 rounded-[7px] bg-ink/85" />
          <span className="text-right text-[13.5px] font-semibold text-ink tabular">{total}</span>
        </li>
      </ol>
      <div className="mt-4 flex justify-end">
        <Button asChild size="sm" variant="tonal">
          <Link to={`/s/${sid}/review/findings${carry ? `?${carry}` : ''}`}>Open findings</Link>
        </Button>
      </div>
    </section>
  );
}

export function MetricsPage() {
  const metrics = useMetrics();
  const { asOf } = useSessionScope();
  const m = metrics.data;
  return (
    <div className="flex min-h-full flex-col">
      <SessionPageHeader
        title="Communication metrics"
        chips={
          <span className="inline-flex h-[30px] items-center gap-1.5 rounded-full bg-[#f3eefe] px-3 text-[13.5px] font-medium text-[#6941c6]">
            <FlaskConical aria-hidden className="size-[15px]" /> P1 · Experimental
          </span>
        }
        actions={
          <span className="inline-flex h-11 items-center gap-2 rounded-control border border-hairline bg-surface px-3.5 text-[14px] font-medium text-ink shadow-control tabular">
            As of {formatClock(asOf)} <CodeChip>Replay</CodeChip>
          </span>
        }
      />
      <ScopeBanners />
      <div role="note" className="mb-5 flex items-start gap-3 rounded-[16px] border border-hairline-soft bg-surface px-4 py-3 text-[14px] text-ink-2 shadow-card">
        <Info aria-hidden className="mt-0.5 size-[18px] shrink-0 text-data" />
        <p>
          <span className="font-medium text-ink">Indicators are experimental</span> — not a workload, performance or fitness assessment. Voice activity detection is not validated; audio gaps are shown as unknown, never as zero.
        </p>
      </div>
      {metrics.isError && !m ? (
        <div className="card p-6">
          <ErrorState error={metrics.error} onRetry={() => metrics.refetch()} />
        </div>
      ) : !m ? (
        <div className="card p-6">
          <LoadingRows rows={6} />
        </div>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            <Kpi icon={AudioLines} label="Measured active audio" value={formatClock(m.active_audio_ms)} delta={m.previous_active_audio_ms == null ? null : secs(m.active_audio_ms - m.previous_active_audio_ms)} deltaUnit=" s" hint="Sum of voice segments up to as-of across channels." />
            <Kpi icon={CircleDot} label="Open loops at as-of" value={m.open_loops_at_as_of} delta={m.previous_open_loops == null ? null : m.open_loops_at_as_of - m.previous_open_loops} hint="Expected follow-ups not yet observed in stored coverage." />
            <Kpi icon={ArrowLeftRight} label="Object switches" value={m.object_switches} delta={m.previous_object_switches == null ? null : m.object_switches - m.previous_object_switches} hint="Times consecutive transmissions addressed a different object." />
          </div>
          <div className="grid grid-cols-1 items-start gap-5 2xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
            <MinuteChart m={m} asOf={asOf} />
            <Breakdown m={m} />
          </div>
        </div>
      )}
    </div>
  );
}
