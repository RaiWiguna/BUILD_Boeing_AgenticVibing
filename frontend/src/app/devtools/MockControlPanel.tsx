import { FlaskConical, RotateCcw, X } from 'lucide-react';
import { useState } from 'react';
import { useStore } from 'zustand';
import { useQueryClient } from '@tanstack/react-query';
import { mockControl } from '@/api/adapters/mock';
import type { MockScenarioFlags } from '@/api/adapters/mock/control';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/controls';
import { cn } from '@/lib/utils';

const FLAGS: { key: keyof MockScenarioFlags; label: string; hint: string }[] = [
  { key: 'providerOutage', label: 'Provider outage', hint: 'STT/Gemini unavailable; cached results stay readable' },
  { key: 'connectionLost', label: 'Connection lost', hint: 'Stream drops; mutations pause until resync' },
  { key: 'versionConflictNext', label: 'Conflict on next save', hint: 'Another reviewer saves first' },
  { key: 'audioAccessDenied', label: 'Audio access denied', hint: 'Evidence audio restricted by grant' },
  { key: 'staleTracks', label: 'Stale tracks', hint: 'Track age 38 s → movement NOT_EVALUABLE' },
  { key: 'emptyCatalogue', label: 'Empty catalogue', hint: 'No sessions shared' },
  { key: 'diskHighWater', label: 'Disk at 91 %', hint: 'Imports held above 90 %' },
  { key: 'sessionExpired', label: 'Sign-in expired', hint: 'Next request returns AUTH_REQUIRED' },
];

/** Dev-only panel that simulates server/network conditions. Labelled MOCK; not part of the product. */
export function MockControlPanel() {
  const [open, setOpen] = useState(false);
  const state = useStore(mockControl);
  const qc = useQueryClient();
  const set = (patch: Partial<MockScenarioFlags>) => {
    state.set(patch);
    qc.invalidateQueries();
  };
  const active = FLAGS.filter((f) => state[f.key]).length;
  return (
    <div className="fixed bottom-4 right-4 z-40 print:hidden">
      {open ? (
        <div role="dialog" aria-label="Mock control" className="w-[340px] rounded-[22px] border border-hairline-soft bg-surface p-4 shadow-pop">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="flex items-center gap-2 text-[15px] font-semibold text-ink">
                <FlaskConical className="size-4 text-[#a2470f]" /> Mock control
              </p>
              <p className="text-[12.5px] text-ink-2">Simulates backend conditions. Not part of the product.</p>
            </div>
            <button type="button" aria-label="Close mock control" onClick={() => setOpen(false)} className="inline-flex size-8 items-center justify-center rounded-full text-ink-2 hover:bg-track">
              <X className="size-4" />
            </button>
          </div>
          <ul className="mt-3 divide-y divide-hairline">
            {FLAGS.map((f) => (
              <li key={f.key} className="flex items-center gap-3 py-2.5">
                <label htmlFor={`mock-${f.key}`} className="min-w-0 flex-1 cursor-pointer">
                  <span className="block text-[14px] text-ink">{f.label}</span>
                  <span className="block text-[12px] text-ink-3">{f.hint}</span>
                </label>
                <Switch id={`mock-${f.key}`} checked={state[f.key]} onCheckedChange={(v) => set({ [f.key]: v })} />
              </li>
            ))}
          </ul>
          <div className="mt-3 flex items-center justify-between gap-2 border-t border-hairline pt-3">
            <label className="flex items-center gap-2 text-[12.5px] text-ink-2">
              Latency
              <input type="range" min={0} max={1500} step={50} value={state.latencyMs[1]} onChange={(e) => state.set({ latencyMs: [Math.min(120, Number(e.target.value)), Number(e.target.value)] })} className="w-24 accent-[#2563eb]" aria-label="Maximum mock latency" />
              <span className="tabular">{state.latencyMs[1]} ms</span>
            </label>
            <Button
              size="xs"
              variant="tonal"
              onClick={() => {
                state.reset();
                qc.invalidateQueries();
              }}
            >
              <RotateCcw /> Reset data
            </Button>
          </div>
        </div>
      ) : (
        <button type="button" aria-label="Open mock control" onClick={() => setOpen(true)} className={cn('group flex h-9 items-center gap-1.5 rounded-full border border-[#f3d2bd] bg-[#fff6ef]/95 px-2.5 text-[12px] font-semibold text-[#a2470f] opacity-80 shadow-pop backdrop-blur transition-[opacity,transform] hover:-translate-y-px hover:opacity-100')}>
          <FlaskConical className="size-4" /> <span className="hidden group-hover:inline">MOCK</span>
          {active > 0 && <span className="inline-flex size-5 items-center justify-center rounded-full bg-[#a2470f] text-[11px] text-white">{active}</span>}
        </button>
      )}
    </div>
  );
}
