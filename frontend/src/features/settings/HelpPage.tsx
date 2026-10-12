import { Ear, Eye, Keyboard, Layers, MessageSquareQuote } from 'lucide-react';
import { useEffect } from 'react';
import { useLocation } from 'react-router';
import { StatusPill } from '@/components/domain/primitives';
import { PageHeader } from '@/components/layout/PageHeader';
import { Kbd } from '@/components/ui/input';
import { CATEGORY_LABEL, STATUS } from '@/lib/status';
import { SettingsCard } from './SettingsLayout';

const CATEGORY_DETAIL: Record<string, string> = {
  CRITICAL_SLOT_UNCERTAIN: 'A critical value (runway, callsign, hold point) could not be heard or read with confidence.',
  READBACK_DISCREPANCY: 'The readback candidate names a different value than the instruction it is paired with.',
  SPEECH_RECORD_DISCREPANCY: 'What was said differs from a recorded system entry for the same object.',
  MOVEMENT_DIVERGENCE: 'Observed movement differs from the active instruction. Needs position data with a footprint.',
  QUALITY_GAP: 'Audio, track or clock coverage is missing; the interval is unknown, never assumed normal.',
};

const GLOSSARY: [string, string][] = [
  ['As-known', 'What was available at the replay time — nothing from later is shown.'],
  ['Debrief', 'Post-hoc view with everything recorded, including information that arrived later.'],
  ['Evidence', 'A time range of audio, transcript, track or event that supports a statement. Labelled E-nn.'],
  ['Finding', 'A candidate issue for a reviewer to assess. Labelled F-nn. Not a fact until reviewed.'],
  ['NOT_EVALUABLE', 'Not enough data to assess. Shown grey — never as consistent or safe.'],
  ['Run', 'One analysis pass over a source revision. Runs are never switched automatically.'],
  ['Revision', 'Reviews, corrections and briefs append new revisions; earlier ones stay in the record.'],
];

const SHORTCUTS: [string, string][] = [
  ['Space', 'Play / pause replay'],
  ['← / →', 'Seek 5 s (Shift: 1 s)'],
  ['[ / ]', 'Previous / next event'],
  ['F', 'Follow leader'],
  ['Home / End', 'Start / end of session'],
  ['⌘K', 'Search'],
  ['J / K', 'Review: next / previous finding'],
  ['1 / 2 / 3', 'Review: choose confirm / dismiss / cannot be determined (never saves)'],
  ['⌘↵ / Ctrl+↵', 'Review: save when decision and reason are filled'],
];

export function HelpPage() {
  const { hash } = useLocation();
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'start' });
  }, [hash]);
  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader title="Help" subtitle="How to read FlowLens — a research replay tool. It does not issue instructions or clearances." />
      <div className="space-y-5">
        <SettingsCard title="Said · Heard · Observed" description="Three sources are always kept apart, so a gap in one is never filled by another.">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {[
              { icon: MessageSquareQuote, t: 'Said', d: 'Transmissions from the transcript and audio — instructions, readbacks, reports.' },
              { icon: Ear, t: 'Heard', d: 'The readback candidate and how it pairs with an instruction. Pairing can be ambiguous.' },
              { icon: Eye, t: 'Observed', d: 'Track positions and events. Missing coverage is shown as unknown.' },
            ].map(({ icon: Icon, t, d }) => (
              <div key={t} className="rounded-[16px] bg-sunken p-4">
                <Icon aria-hidden className="size-5 text-data" />
                <p className="mt-2 text-[16px] font-semibold text-ink">{t}</p>
                <p className="mt-1 text-[14px] leading-snug text-ink-2">{d}</p>
              </div>
            ))}
          </div>
        </SettingsCard>

        <section id="finding-categories" className="scroll-mt-6">
          <SettingsCard title="Finding categories" description="Findings are hypotheses for review, ranked by priority. They never say an action was unsafe.">
            <ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {Object.entries(CATEGORY_LABEL).map(([k, label]) => (
                <li key={k} className="rounded-[14px] border border-hairline-soft px-4 py-3">
                  <p className="text-[15px] font-medium text-ink">{label}</p>
                  <p className="mt-0.5 text-[13.5px] leading-snug text-ink-2">{CATEGORY_DETAIL[k]}</p>
                  <p className="mt-1.5 font-mono text-[11.5px] text-ink-3">{k}</p>
                </li>
              ))}
            </ul>
            <div className="mt-4 flex flex-wrap gap-2">
              {Object.values(STATUS.priority).map((p) => (
                <StatusPill key={p.label} size="sm" meta={p} showCode />
              ))}
            </div>
          </SettingsCard>
        </section>

        <SettingsCard title="Status legend" description="Colour carries meaning, always paired with an icon and a label. Unknown is grey — never green.">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            {(
              [
                ['Readback', STATUS.readback],
                ['Movement', STATUS.movement],
                ['Instruction', STATUS.instruction],
                ['Finding status', STATUS.findingStatus],
              ] as const
            ).map(([title, map]) => (
              <div key={title}>
                <p className="text-[13px] font-medium uppercase tracking-[0.06em] text-ink-3">{title}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {Object.values(map).map((s) => (
                    <StatusPill key={s.label} size="sm" meta={s} />
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-5 grid gap-3 border-t border-hairline-soft pt-4 text-[13.5px] text-ink-2 sm:grid-cols-3">
            <span className="flex items-center gap-2.5">
              <span aria-hidden className="hatch-data h-3.5 w-10 rounded-full bg-data-tint" /> Predicted / derived
            </span>
            <span className="flex items-center gap-2.5">
              <span aria-hidden className="hatch-muted h-3.5 w-10 rounded-full bg-sunken" /> Gap · unknown
            </span>
            <span className="flex items-center gap-2.5">
              <span aria-hidden className="hatch-discrepancy h-3.5 w-10 rounded-full bg-discrepancy-tint" /> Discrepancy
            </span>
          </div>
        </SettingsCard>

        <section id="provenance" className="scroll-mt-6">
          <SettingsCard title="Provenance" description="Every derived item carries where it came from, so it can be checked and reproduced.">
            <ul className="grid grid-cols-1 gap-2 text-[14px] text-ink-2 md:grid-cols-2">
              {[
                ['Source revision', 'Which import revision the run analysed.'],
                ['Run', 'Analysis pass label (e.g. #03) and input revision.'],
                ['Model · prompt · rule · schema', 'Versions used to produce the item.'],
                ['Event vs available time', 'When it happened vs when it was known — As-known uses the latter.'],
                ['Revisions', 'Corrections and reviews supersede, never overwrite.'],
              ].map(([k, v]) => (
                <li key={k} className="flex gap-3 rounded-[14px] bg-sunken px-4 py-3">
                  <Layers aria-hidden className="mt-0.5 size-4 shrink-0 text-ink-3" />
                  <span>
                    <span className="block font-medium text-ink">{k}</span>
                    {v}
                  </span>
                </li>
              ))}
            </ul>
          </SettingsCard>
        </section>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <SettingsCard title="Glossary">
            <dl className="divide-y divide-hairline-soft">
              {GLOSSARY.map(([k, v]) => (
                <div key={k} className="grid grid-cols-[130px_1fr] gap-3 py-2.5 text-[14px]">
                  <dt className="font-medium text-ink">{k}</dt>
                  <dd className="text-ink-2">{v}</dd>
                </div>
              ))}
            </dl>
          </SettingsCard>
          <div className="space-y-5">
            <SettingsCard title="Keyboard" description="Single-key shortcuts work when focus is not in a text field.">
              <ul className="divide-y divide-hairline-soft">
                {SHORTCUTS.map(([k, v]) => (
                  <li key={k} className="flex items-center justify-between gap-3 py-2.5 text-[14px] text-ink-2">
                    {v}
                    <Kbd>{k}</Kbd>
                  </li>
                ))}
              </ul>
              <p className="mt-3 flex items-center gap-2 text-[12.5px] text-ink-3">
                <Keyboard aria-hidden className="size-4" /> All controls are reachable by keyboard.
              </p>
            </SettingsCard>
          </div>
        </div>
      </div>
    </div>
  );
}
