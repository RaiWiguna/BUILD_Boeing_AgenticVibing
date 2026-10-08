import { Car, ChevronRight, CircleDashed, Plane } from 'lucide-react';
import { Link } from 'react-router';
import { useRunwayMemory } from '@/features/workspace/queries';
import { useReplay } from '@/features/replay/store';
import { EvidenceChip } from '@/components/domain/evidence';
import { LayoutMini } from '@/components/domain/LayoutMini';
import { Card, CardHeader, StatusPill } from '@/components/domain/primitives';
import { Callout, EmptyState, ErrorState, LoadingRows } from '@/components/domain/states';
import { useSessionScope } from '@/hooks/useSessionScope';
import { LOOP_KIND_LABEL, STATUS } from '@/lib/status';
import { formatClock } from '@/lib/time';
import { cn } from '@/lib/utils';

/** Runway memory: what is known about objects related to the runway at as-of. Not a safety indication. */
export function RunwayTab() {
  const { detail, sid, carry, label, asOf } = useSessionScope();
  const runway = detail?.layout?.runways[0] ?? null;
  const rw = useRunwayMemory(runway?.id ?? (detail ? 'audio-only' : null));
  const duration = useReplay((s) => s.duration);
  const link = (p: string) => `/s/${sid}/${p}${carry ? `?${carry}` : ''}`;
  if (!detail) return null;
  if (rw.isError && !rw.data)
    return (
      <Card className="p-6">
        <ErrorState error={rw.error} onRetry={() => rw.refetch()} />
      </Card>
    );
  if (!rw.data)
    return (
      <Card className="p-6">
        <LoadingRows rows={5} />
      </Card>
    );
  const data = rw.data;
  const pct = (ms: number) => (duration ? (ms / duration) * 100 : 0);
  const callsign = (id: string) => detail.entities.find((e) => e.id === id)?.callsign ?? 'Unknown';

  return (
    <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,1fr)]">
      <div className="space-y-5">
        <Card aria-labelledby="rw-layout" className="p-5 sm:p-6">
          <CardHeader
            id="rw-layout"
            title={runway ? `Runway ${runway.ends[0]}/${runway.ends[1]}` : 'Runway'}
            subtitle={`Objects related to this runway at ${formatClock(asOf)}`}
            actions={
              <StatusPill
                meta={
                  data.coverage === 'COMPLETE'
                    ? { label: 'Complete coverage', tone: 'data', icon: CircleDashed }
                    : { label: data.coverage === 'AUDIO_ONLY' ? 'Audio-only coverage' : 'Partial coverage', tone: 'notice', icon: CircleDashed }
                }
              />
            }
          />
          {detail.layout ? (
            <div className="mt-4 overflow-hidden rounded-[18px] ring-1 ring-hairline-soft">
              <LayoutMini layout={detail.layout} className="h-[200px]" />
            </div>
          ) : (
            <Callout className="mt-4" tone="muted" title="No layout imported">
              Runway geometry is not available for this session. Occupancy cannot be evaluated.
            </Callout>
          )}
          <p className="mt-2 text-[12.5px] text-ink-3">{detail.layout?.caption ?? 'Audio-only session'} · Runway status is never shown as “safe” or “clear”.</p>
        </Card>

        <Card aria-labelledby="rw-occupancy" className="p-5 sm:p-6">
          <CardHeader id="rw-occupancy" title="Observed occupancy" subtitle="Intervals where the stored footprint overlaps the runway polygon" />
          <ul className="mt-4 space-y-4">
            {data.occupancy.map((o) => {
              const evaluated = o.status === 'EVALUATED';
              return (
                <li key={o.entity_id} className="grid grid-cols-[88px_minmax(0,1fr)] items-center gap-x-4 gap-y-1">
                  <span className="text-[15px] font-semibold text-ink">{callsign(o.entity_id)}</span>
                  <div className={cn('relative h-7 overflow-hidden rounded-[8px]', evaluated ? 'bg-sunken' : 'hatch-muted')} role="img" aria-label={evaluated ? `${callsign(o.entity_id)} occupancy: ${o.intervals.length ? o.intervals.map((i) => `${formatClock(i.start_ms)} to ${formatClock(i.end_ms)}`).join(', ') : 'no overlap observed'}` : `${callsign(o.entity_id)} occupancy not evaluable: ${o.reason}`}>
                    {data.gaps.map((g) => (
                      <span key={g.start_ms} aria-hidden className="hatch-notice absolute inset-y-0 opacity-70" style={{ left: `${pct(g.start_ms)}%`, width: `${pct(g.end_ms - g.start_ms)}%` }} />
                    ))}
                    {o.intervals.map((i) => (
                      <span key={i.start_ms} aria-hidden className="hatch-data absolute inset-y-1 rounded-[5px]" style={{ left: `${pct(i.start_ms)}%`, width: `${Math.max(0.6, pct(i.end_ms - i.start_ms))}%` }} />
                    ))}
                    <span aria-hidden className="absolute inset-y-0 w-[2px] bg-data" style={{ left: `${pct(asOf)}%` }} />
                    {!evaluated && <span className="absolute inset-0 flex items-center px-3 text-[12px] font-semibold tracking-[0.02em] text-ink-2">NOT_EVALUABLE</span>}
                  </div>
                  <span />
                  <p className="text-[13px] text-ink-2">
                    {evaluated ? (o.intervals.length ? o.intervals.map((i) => `${formatClock(i.start_ms)}–${formatClock(i.end_ms)}`).join(' · ') : 'No overlap observed in stored coverage') : o.reason}
                  </p>
                </li>
              );
            })}
          </ul>
          <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5 text-[12.5px] text-ink-2">
            <span className="flex items-center gap-2"><span aria-hidden className="hatch-data inline-block h-3 w-6 rounded-[3px]" /> Observed overlap</span>
            <span className="flex items-center gap-2"><span aria-hidden className="hatch-muted inline-block h-3 w-6 rounded-[3px]" /> Not evaluable</span>
            <span className="flex items-center gap-2"><span aria-hidden className="hatch-notice inline-block h-3 w-6 rounded-[3px]" /> Audio gap</span>
            <span className="flex items-center gap-2"><span aria-hidden className="inline-block h-3 w-[2px] bg-data" /> As-of</span>
          </div>
        </Card>
      </div>

      <div className="space-y-5">
        <Card aria-labelledby="rw-objects" className="p-5">
          <CardHeader id="rw-objects" title="Objects" subtitle="Said · Heard · Observed kept separate" />
          <ul className="mt-3 divide-y divide-hairline-soft">
            {data.objects.map(({ entity, state }) => (
              <li key={entity.id}>
                <Link to={link(`memory/${entity.id}`)} className="group flex items-center gap-3 py-3">
                  <span aria-hidden className="inline-flex size-10 items-center justify-center rounded-full bg-track text-ink">
                    {entity.kind === 'VEHICLE' ? <Car className="size-5" /> : <Plane className="size-5 -rotate-45" />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[15px] font-semibold text-ink group-hover:text-data">{entity.callsign}</span>
                    <span className="mt-0.5 flex flex-wrap gap-1.5">
                      <StatusPill size="sm" meta={STATUS.instruction[state.instruction.state]} />
                      <StatusPill size="sm" meta={STATUS.readback[state.readback.state]} />
                      <StatusPill size="sm" meta={STATUS.movement[state.movement.state]} />
                    </span>
                  </span>
                  <ChevronRight aria-hidden className="size-[18px] text-ink-2" />
                </Link>
              </li>
            ))}
          </ul>
        </Card>

        <Card aria-labelledby="rw-instr" className="p-5">
          <CardHeader id="rw-instr" title="Active instructions" subtitle="As recorded — not a clearance" />
          {data.active_instructions.length === 0 ? (
            <p className="mt-3 text-[14px] text-ink-2">No active instructions at this as-of.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {data.active_instructions.map((a) => (
                <li key={`${a.entity_id}-${a.t}`} className="flex items-center gap-3 rounded-[14px] bg-sunken px-3.5 py-2.5">
                  <span className="w-12 shrink-0 text-[13.5px] text-ink-2 tabular">{formatClock(a.t)}</span>
                  <span className="min-w-0 flex-1 text-[14.5px] text-ink">
                    <span className="font-semibold">{callsign(a.entity_id)}</span> · {a.summary}
                  </span>
                  {a.evidence_id && <EvidenceChip size="sm" id={a.evidence_id} label={label(a.evidence_id)} />}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card aria-labelledby="rw-loops" className="p-5">
          <CardHeader id="rw-loops" title="Open loops" />
          {data.open_loops.filter((l) => l.status === 'OPEN' || l.status === 'PARTIAL').length === 0 ? (
            <EmptyState className="py-6" title="No open loops">
              Loops close only with evidence.
            </EmptyState>
          ) : (
            <ul className="mt-3 space-y-2">
              {data.open_loops
                .filter((l) => l.status === 'OPEN' || l.status === 'PARTIAL')
                .map((l) => (
                  <li key={l.id} className="flex items-center justify-between gap-3 rounded-[14px] bg-sunken px-3.5 py-2.5">
                    <span className="text-[14.5px] text-ink">
                      <span className="font-semibold">{l.entity_ids.map(callsign).join(', ')}</span> · {LOOP_KIND_LABEL[l.kind] ?? l.kind}
                      <span className="block text-[12.5px] text-ink-2 tabular">since {formatClock(l.started_ms)}</span>
                    </span>
                    <StatusPill size="sm" meta={STATUS.loop[l.status]} />
                  </li>
                ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
