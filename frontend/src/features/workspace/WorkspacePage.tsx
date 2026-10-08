import { EyeOff, MonitorSmartphone } from 'lucide-react';
import { useEffect, useMemo, useRef } from 'react';
import type { FindingView } from '@/api/types';
import { TimelineBand } from '@/features/replay/TimelineBand';
import { useReplay } from '@/features/replay/store';
import { Card, MoreButton } from '@/components/domain/primitives';
import { ErrorState, LoadingRows } from '@/components/domain/states';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/menu';
import { Button } from '@/components/ui/button';
import { useSessionScope } from '@/hooks/useSessionScope';
import { formatOffset } from '@/lib/time';
import { AttentionRail } from './AttentionRail';
import { MemoryStrip } from './MemoryStrips';
import { useFindings, useSelectedEntity, useSnapshot, useWaveforms } from './queries';
import { ScopeBanners, SessionHeader } from './SessionHeader';
import { SituationCanvas, SituationLegend } from './SituationCanvas';
import { Link } from 'react-router';

function rangeOf(f: FindingView) {
  const starts = f.finding.evidence.map((e) => e.start_ms).filter((v): v is number => v != null);
  const start = starts.length ? Math.min(...starts) : f.finding.event_time_ms - 5000;
  return { start, end: Math.max(f.finding.event_time_ms, start + 1000) };
}

export function WorkspacePage() {
  const { detail, run, sid, carry, mode, asOf, setMode, label } = useSessionScope();
  const snapshot = useSnapshot();
  const findings = useFindings();
  const waves = useWaveforms();
  const [selected, select] = useSelectedEntity();
  const setRange = useReplay((s) => s.setRange);
  const range = useReplay((s) => s.range);

  const entities = useMemo(() => detail?.entities ?? [], [detail?.entities]);
  const selectedId = selected ?? entities[0]?.id ?? null;
  const href = (path: string) => `/s/${sid}/${path}${carry ? `${path.includes('?') ? '&' : '?'}${carry}` : ''}`;

  // Default evidence range: first attention finding (comp: 05:12 – 05:19).
  const seeded = useRef(false);
  useEffect(() => {
    if (seeded.current || range || !findings.data?.length) return;
    const first = findings.data.find((f) => f.finding.priority === 'ATTENTION') ?? findings.data[0]!;
    seeded.current = true;
    setRange(rangeOf(first));
  }, [findings.data, range, setRange]);

  if (!detail) return null;
  if (!run)
    return (
      <>
        <SessionHeader title="Workspace" />
        <Card className="p-8">
          <ErrorState error={new Error('This session has no analysis run yet. Start analysis from the import screen to see memory and findings.')} />
        </Card>
      </>
    );

  const snap = snapshot.data;
  const hidden = snap?.hidden_after_as_of ?? 0;

  return (
    <div className="flex min-h-full flex-col">
      <SessionHeader title="Workspace" />
      <ScopeBanners />
      <p className="mb-4 flex items-center gap-2.5 rounded-[14px] bg-sunken px-3.5 py-3 text-[13.5px] text-ink-2 md:hidden">
        <MonitorSmartphone aria-hidden className="size-4 shrink-0 text-ink-3" /> Open on a larger screen for the full workspace. This view is read-only.
      </p>

      <div className="grid grid-cols-1 flex-1 items-start gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(300px,330px)] 2xl:grid-cols-[minmax(0,1fr)_minmax(330px,380px)]">
        <Card aria-labelledby="situation-heading" className="@container p-5">
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
            <h2 id="situation-heading" className="text-[23px] font-semibold tracking-[-0.025em] text-ink">
              Situation
            </h2>
            <div className="flex items-center gap-4">
              <SituationLegend />
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <MoreButton label="Situation options" />
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-[240px]">
                  {entities.map((e) => (
                    <DropdownMenuItem key={e.id} asChild>
                      <Link to={href(`memory/${e.id}`)}>Open {e.callsign} memory</Link>
                    </DropdownMenuItem>
                  ))}
                  <DropdownMenuItem asChild>
                    <Link to={href('memory/runway')}>Open runway memory</Link>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {snapshot.isError && !snap ? (
            <ErrorState compact className="mt-4" error={snapshot.error} onRetry={() => snapshot.refetch()} />
          ) : (
            <SituationCanvas className="mt-4" layout={detail.layout} snapshot={snap} entities={entities} selected={selectedId} onSelect={select} asOf={asOf} />
          )}

          {!snap && snapshot.isPending ? (
            <LoadingRows rows={3} className="mt-4" />
          ) : (
            <ul className="mt-4 space-y-2.5" aria-label="Memory strips">
              {entities.map((e) => (
                <MemoryStrip key={e.id} entity={e} state={snap?.entities.find((x) => x.entity_id === e.id)} selected={selectedId === e.id} onSelect={() => select(e.id)} memoryHref={href(`memory/${e.id}`)} />
              ))}
            </ul>
          )}

          {mode === 'AS_KNOWN' && hidden > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-[14px] bg-sunken px-4 py-2.5 text-[13.5px] text-ink-2">
              <EyeOff aria-hidden className="size-4 text-ink-3" />
              <span className="flex-1">
                {hidden} {hidden === 1 ? 'item' : 'items'} recorded before {formatOffset(asOf)} became available later and {hidden === 1 ? 'is' : 'are'} hidden in As-known.
              </span>
              <Button size="xs" variant="ghost" onClick={() => setMode('DEBRIEF')}>
                Show in Debrief
              </Button>
            </div>
          )}
        </Card>

        <AttentionRail
          className="xl:sticky xl:top-6"
          findings={findings.data}
          loading={findings.isPending}
          error={findings.isError ? findings.error : null}
          onRetry={() => findings.refetch()}
          loops={snap?.open_loops ?? []}
          entities={entities}
          asOf={asOf}
          reviewBase={href}
          label={label}
          onFocusRange={(f) => setRange(rangeOf(f))}
        />
      </div>

      <div className="z-30 mt-5 md:sticky md:bottom-3">
        <TimelineBand className="shadow-[0_1px_2px_rgba(16,24,40,0.04),0_12px_32px_-12px_rgba(16,24,40,0.18)]" waveforms={waves.data} gaps={snap?.gaps ?? []} markers={snap?.event_markers ?? []} transcriptHref={href('review/transcript')} />
      </div>
    </div>
  );
}
