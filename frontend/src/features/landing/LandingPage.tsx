import { ArrowDown, AudioLines, Braces, CircleHelp, FileSearch, GitCompareArrows, History, MapPinned, ShieldCheck, UserCheck, type LucideIcon } from 'lucide-react';
import { useEffect, type CSSProperties, type ReactNode } from 'react';
import { LogoMark } from '@/components/layout/Logo';
import { cn } from '@/lib/utils';
import workspaceShot from '@/assets/landing/workspace.jpg';
import { Reveal } from './Reveal';

/**
 * Public product introduction (mobile first). Follows the app's Margin-derived language:
 * pale canvas, white 24px cards, charcoal action, blue data, magenta discrepancy, hatching.
 * It intentionally has no link into the sign-in flow; that lives at /login-flow.
 */
export function LandingPage() {
  useEffect(() => {
    const prev = document.title;
    document.title = 'FlowLens · Said, heard, observed';
    return () => {
      document.title = prev;
    };
  }, []);

  return (
    <div id="top" className="min-h-dvh overflow-x-clip bg-canvas text-ink">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-50 focus:rounded-control focus:bg-surface focus:px-4 focus:py-2 focus:shadow-pop">
        Skip to content
      </a>
      <Header />
      <main id="main">
        <Hero />
        <Pressure />
        <ThreeRecords />
        <Pipeline />
        <Workspace />
        <Compare />
        <Dataset />
        <Principles />
        <Closing />
      </main>
      <Footer />
    </div>
  );
}

/* ------------------------------------------------------------------ chrome */

const NAV = [
  { href: '#records', label: 'Product' },
  { href: '#pipeline', label: 'How it works' },
  { href: '#data', label: 'Data' },
];

function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-hairline-soft/80 bg-canvas/80 backdrop-blur-md supports-[backdrop-filter]:bg-canvas/70">
      <div className="px-4 sm:px-6">
        <div className="mx-auto flex h-16 max-w-[1200px] items-center justify-between">
        <a href="#top" className="flex items-center gap-2.5 rounded-[10px]" aria-label="FlowLens, back to top">
          <LogoMark className="size-8" />
          <span className="text-[19px] font-semibold tracking-[-0.025em]">FlowLens</span>
        </a>
        <nav aria-label="Sections" className="-mr-3.5 hidden items-center gap-1 md:flex">
          {NAV.map((n) => (
            <a key={n.href} href={n.href} className="rounded-[10px] px-3.5 py-2 text-[14.5px] font-medium text-ink-2 transition-colors duration-150 hover:bg-track hover:text-ink">
              {n.label}
            </a>
          ))}
        </nav>
          <span className="rounded-full border border-hairline bg-surface px-3 py-1 text-[12.5px] font-medium text-ink-2 md:hidden">Research prototype</span>
        </div>
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer className="border-t border-hairline-soft">
      <div className="mx-auto grid max-w-[1200px] gap-8 px-4 py-10 sm:px-6 md:grid-cols-[1fr_auto] md:items-end">
        <div>
          <span className="flex items-center gap-2.5">
            <LogoMark className="size-7" />
            <span className="text-[17px] font-semibold tracking-[-0.02em]">FlowLens</span>
          </span>
          <p className="mt-3 max-w-[46ch] text-[14px] leading-relaxed text-ink-2">
            Research prototype for replaying recorded tower sessions. Not certified for operational use and not connected to any live frequency.
          </p>
        </div>
        <div className="text-[13px] leading-relaxed text-ink-2 md:text-right">
          <p>Audio and ADS-B from TartanAviation, Patrikar et al., <span className="whitespace-nowrap">CC BY 4.0</span>.</p>
          <p>© 2026 FlowLens</p>
        </div>
      </div>
    </footer>
  );
}

function Section({ id, className, children }: { id?: string; className?: string; children: ReactNode }) {
  return (
    <section id={id} className={cn('scroll-mt-16 px-4 py-16 sm:px-6 md:py-24', className)}>
      <div className="mx-auto max-w-[1200px]">{children}</div>
    </section>
  );
}

function Heading({ children, className }: { children: ReactNode; className?: string }) {
  return <h2 className={cn('max-w-[18ch] text-[32px] font-medium leading-[1.08] tracking-[-0.035em] text-balance md:text-[44px]', className)}>{children}</h2>;
}

function Lead({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn('mt-4 max-w-[56ch] text-[16px] leading-relaxed text-ink-2 md:text-[17px]', className)}>{children}</p>;
}

/* -------------------------------------------------------------------- hero */

function Hero() {
  return (
    <section className="px-4 pb-16 pt-8 sm:px-6 md:pb-24 md:pt-16">
      <div className="mx-auto grid max-w-[1200px] items-center gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.02fr)] lg:gap-14">
        <div>
          <span className="enter inline-flex items-center gap-2 rounded-full border border-hairline bg-surface px-3 py-1.5 text-[13px] font-medium text-ink-2 shadow-control">
            <AudioLines aria-hidden className="size-4 text-data" />
            Tower radio meets ADS-B
          </span>
          <h1 className="enter mt-5 text-[44px] font-medium leading-[1.02] tracking-[-0.045em] text-balance sm:text-[56px] lg:text-[68px]" style={{ '--enter-delay': '80ms' } as CSSProperties}>
            Said, heard, observed. On one timeline.
          </h1>
          <p className="enter mt-5 max-w-[42ch] text-[17px] leading-relaxed text-ink-2 md:text-[18px]" style={{ '--enter-delay': '160ms' } as CSSProperties}>
            FlowLens replays tower radio beside <span className="whitespace-nowrap">ADS-B</span> tracks, so each readback is checked against where the aircraft actually went.
          </p>
          <div className="enter mt-8" style={{ '--enter-delay': '240ms' } as CSSProperties}>
            <a href="#pipeline" className="group inline-flex h-12 items-center gap-2 rounded-control bg-action px-6 text-[15px] font-medium text-on-action shadow-action transition-[background-color,transform] duration-150 hover:bg-action-hover active:scale-[0.98]">
              See how it works
              <ArrowDown aria-hidden className="size-[18px] transition-transform duration-200 group-hover:translate-y-0.5" />
            </a>
          </div>
        </div>
        <HeroVisual />
      </div>
    </section>
  );
}

function Wave({ tone = 'data', bars = 18 }: { tone?: 'data' | 'discrepancy'; bars?: number }) {
  const heights = [5, 9, 14, 8, 17, 11, 6, 13, 18, 10, 7, 15, 12, 6, 9, 16, 8, 5, 11, 14];
  return (
    <span aria-hidden className="flex h-5 items-center gap-[2.5px]">
      {heights.slice(0, bars).map((h, i) => (
        <span key={i} className={cn('wave-bar w-[2.5px] rounded-full', tone === 'data' ? 'bg-data/70' : 'bg-discrepancy/70')} style={{ height: h, '--i': i } as CSSProperties} />
      ))}
    </span>
  );
}

function HeroVisual() {
  return (
    <div className="enter relative" style={{ '--enter-delay': '200ms' } as CSSProperties}>
      <figure aria-label="Example finding: a readback that differs from the clearance" className="relative overflow-hidden rounded-[28px] spotlight-mesh p-6 pb-24 text-white shadow-pop sm:p-8 sm:pb-28">
        <div aria-hidden className="pointer-events-none absolute -bottom-24 -right-16 size-72 rounded-full border border-white/25" />
        <div aria-hidden className="pointer-events-none absolute -bottom-10 right-10 size-40 rounded-full bg-white/10 blur-2xl" />
        <div className="relative flex items-center justify-between gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/18 px-3 py-1.5 text-[13px] font-medium ring-1 ring-white/25 backdrop-blur">
            <GitCompareArrows aria-hidden className="size-4" />
            Readback differs
          </span>
          <span className="text-[13px] font-medium text-white/80 tabular">00:46</span>
        </div>
        <p className="relative mt-7 text-[56px] font-medium leading-none tracking-[-0.04em] tabular sm:text-[68px]">N147G</p>
        <p className="relative mt-4 max-w-[26ch] text-[20px] font-medium leading-snug tracking-[-0.015em] sm:text-[24px]">Hold short of runway 28 was read back as runway 13.</p>
        <p className="relative mt-3 max-w-[40ch] text-[14.5px] leading-relaxed text-white/80">Clearance at 00:41, readback five seconds later. Nobody corrected it on frequency.</p>
      </figure>

      <div className="relative -mt-16 ml-3 mr-3 rounded-[24px] border border-hairline-soft bg-surface p-4 shadow-pop sm:ml-10 sm:mr-6 sm:p-5">
        <div className="flex items-center justify-between">
          <p className="text-[13px] font-semibold text-ink">On frequency</p>
          <p className="text-[12.5px] text-ink-2">Ground 121.9</p>
        </div>
        <ol className="mt-3 space-y-3">
          <li className="rounded-[14px] bg-sunken p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-[12.5px] font-semibold text-data-strong">Said · Ground</span>
              <Wave />
            </div>
            <p className="mt-1.5 text-[14.5px] leading-snug text-ink">
              …taxi runway one three via Bravo, <mark className="rounded bg-data-tint px-0.5 text-data-strong">hold short runway two eight.</mark>
            </p>
          </li>
          <li className="rounded-[14px] bg-sunken p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-[12.5px] font-semibold text-discrepancy">Heard · N147G</span>
              <Wave tone="discrepancy" bars={14} />
            </div>
            <p className="mt-1.5 text-[14.5px] leading-snug text-ink">
              Via Bravo, <mark className="rounded bg-discrepancy-tint px-1 text-discrepancy">hold short one three</mark>, four seven golf.
            </p>
          </li>
        </ol>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- pressure */

function Pressure() {
  return (
    <Section className="pt-4 md:pt-8">
      <Reveal>
        <Heading>Traffic keeps growing. Towers do not.</Heading>
        <Lead>Controllers hold every clearance in working memory while the next call is already on frequency.</Lead>
      </Reveal>

      <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-6">
        <Reveal className="card p-6 md:col-span-4 md:p-8">
          <p className="text-[15px] font-semibold">Demand vs people</p>
          <p className="text-[13.5px] text-ink-2">Growth, 2022 to 2030 outlook</p>
          <div className="mt-8 space-y-6">
            <div>
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-[14.5px] text-ink-2">Global flight demand by 2030</span>
                <span className="text-[22px] font-medium tracking-[-0.02em] text-data-strong tabular">+12%</span>
              </div>
              <div className="mt-2 h-4 rounded-[6px] hatch-data grow-x" />
            </div>
            <div>
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-[14.5px] text-ink-2">Controller headcount, 2022 to 2025</span>
                <span className="text-[22px] font-medium tracking-[-0.02em] tabular">+0.5%</span>
              </div>
              <div className="mt-2 h-4 w-[4.2%] min-w-3 rounded-[6px] bg-action grow-x" />
            </div>
          </div>
        </Reveal>

        <Reveal delay={80} className="flex flex-col justify-between rounded-[24px] bg-data p-6 text-white shadow-card md:col-span-2 md:p-8">
          <p className="text-[15px] font-semibold text-white/85">LAX tower, average day</p>
          <div>
            <p className="mt-8 text-[56px] font-medium leading-none tracking-[-0.045em] tabular">1,592</p>
            <p className="mt-3 text-[14.5px] leading-relaxed text-white/85">flights. More than one movement every minute.</p>
          </div>
        </Reveal>

        <Reveal className="card p-6 md:col-span-3 md:p-8">
          <p className="text-[48px] font-medium leading-none tracking-[-0.045em] tabular">90.3%</p>
          <p className="mt-3 max-w-[34ch] text-[15px] leading-relaxed text-ink-2">of controllers in a published study reported high to very high mental workload.</p>
          <p className="mt-4 text-[13px] text-ink-3">Senjaya et al., 2020</p>
        </Reveal>

        <Reveal delay={80} className="card relative overflow-hidden p-6 md:col-span-3 md:p-8">
          <div aria-hidden className="absolute inset-y-0 right-0 w-1/3 hatch-discrepancy opacity-40 [mask-image:linear-gradient(to_left,black,transparent)]" />
          <p className="relative text-[48px] font-medium leading-none tracking-[-0.045em] text-discrepancy tabular">≈20%</p>
          <p className="relative mt-3 max-w-[34ch] text-[15px] leading-relaxed text-ink-2">of US runway incursions trace back to an ATC action or inaction.</p>
          <p className="relative mt-4 text-[13px] text-ink-3">FAA, fiscal year 2023</p>
        </Reveal>
      </div>
    </Section>
  );
}

/* ----------------------------------------------------------- three records */

interface RecordRow {
  layer: string;
  source: string;
  time: string;
  text: ReactNode;
  slots: { label: string; tone?: 'mismatch' | 'ok' }[];
  tone: 'data' | 'discrepancy' | 'ready';
}

const RECORDS: RecordRow[] = [
  {
    layer: 'Said',
    source: 'Ground controller',
    time: '00:41.2',
    tone: 'data',
    text: 'Skyhawk one four seven golf, taxi runway one three via Bravo, hold short runway two eight.',
    slots: [{ label: 'N147G' }, { label: 'Taxi' }, { label: 'RWY 13' }, { label: 'via B' }, { label: 'Hold short 28' }],
  },
  {
    layer: 'Heard',
    source: 'Pilot readback',
    time: '00:46.8',
    tone: 'discrepancy',
    text: 'Runway one three via Bravo, hold short one three, four seven golf.',
    slots: [{ label: 'N147G' }, { label: 'RWY 13' }, { label: 'via B' }, { label: 'Hold short 13', tone: 'mismatch' }],
  },
  {
    layer: 'Observed',
    source: 'ADS-B track',
    time: '01:12.0',
    tone: 'ready',
    text: 'Track slows on Bravo and stops before the runway 28 hold line.',
    slots: [{ label: 'Stopped at B / 28', tone: 'ok' }, { label: '3 kt to 0 kt' }],
  },
];

const LAYER_TONE = {
  data: { dot: 'bg-data', text: 'text-data-strong', bar: 'hatch-data' },
  discrepancy: { dot: 'bg-discrepancy', text: 'text-discrepancy', bar: 'hatch-discrepancy' },
  ready: { dot: 'bg-ready', text: 'text-ready', bar: 'bg-ready/70' },
} as const;

function ThreeRecords() {
  return (
    <Section id="records" className="bg-surface">
      <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-16">
        <Reveal className="lg:sticky lg:top-24 lg:self-start">
          <Heading>Three records. Never merged.</Heading>
          <Lead>A correct readback does not prove the aircraft moved as cleared. FlowLens keeps what was said, what was heard and what the track shows apart, then points to where they disagree.</Lead>
          <div className="mt-8 flex flex-wrap gap-x-5 gap-y-2 text-[13.5px] text-ink-2">
            <span className="inline-flex items-center gap-2">
              <span aria-hidden className="h-2.5 w-5 rounded-[3px] hatch-data" /> Matches the clearance
            </span>
            <span className="inline-flex items-center gap-2">
              <span aria-hidden className="h-2.5 w-5 rounded-[3px] hatch-discrepancy" /> Differs from it
            </span>
          </div>
        </Reveal>

        <Reveal delay={100} className="rounded-[24px] border border-hairline-soft bg-canvas p-3 sm:p-4">
          <div className="flex items-center justify-between px-2 pb-3 pt-1">
            <p className="text-[14px] font-semibold">Example session</p>
            <p className="text-[13px] text-ink-2">Ground, runway 13 flow</p>
          </div>
          <ol className="space-y-3">
            {RECORDS.map((r) => {
              const t = LAYER_TONE[r.tone];
              return (
                <li key={r.layer} className="rounded-[18px] border border-hairline-soft bg-surface p-4 shadow-card sm:p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className={cn('text-[17px] font-semibold tracking-[-0.01em]', t.text)}>{r.layer}</p>
                      <p className="text-[13px] text-ink-2">{r.source}</p>
                    </div>
                    <span className="rounded-full bg-track px-2.5 py-1 text-[12.5px] font-medium text-ink-2 tabular">{r.time}</span>
                  </div>
                  <p className="mt-3 text-[15.5px] leading-relaxed text-ink">“{r.text}”</p>
                  <ul aria-label={`${r.layer} slots`} className="mt-4 flex flex-wrap gap-1.5">
                    {r.slots.map((s) => (
                      <li
                        key={s.label}
                        className={cn(
                          'rounded-[8px] px-2.5 py-1 text-[12.5px] font-medium',
                          s.tone === 'mismatch' ? 'bg-discrepancy-tint text-discrepancy ring-1 ring-discrepancy/25' : s.tone === 'ok' ? 'bg-ready-tint text-ready' : 'bg-track text-ink-2',
                        )}
                      >
                        {s.tone === 'mismatch' && <span className="sr-only">Mismatch: </span>}
                        {s.label}
                      </li>
                    ))}
                  </ul>
                </li>
              );
            })}
          </ol>
          <p className="px-2 pb-1 pt-4 text-[13.5px] leading-relaxed text-ink-2">
            Here the readback was wrong but the aircraft still stopped where cleared. Both facts stay visible, side by side.
          </p>
        </Reveal>
      </div>
    </Section>
  );
}

/* ---------------------------------------------------------------- pipeline */

const STEPS: { icon: LucideIcon; title: string; body: string }[] = [
  { icon: AudioLines, title: 'Transcribe', body: 'Speech-to-text tuned for ATC phraseology turns each transmission into timed words.' },
  { icon: Braces, title: 'Extract', body: 'Callsign, runway, taxiway, hold short and conditions become validated slots with their quotes.' },
  { icon: GitCompareArrows, title: 'Pair', body: 'Each clearance is matched with its readback, so a missing or wrong element stands out.' },
  { icon: MapPinned, title: 'Check', body: 'Deterministic geometry tests the instruction against ADS-B and the airport layout.' },
  { icon: UserCheck, title: 'Review', body: 'An evaluator accepts or rejects each finding, with the audio one click away.' },
];

function Pipeline() {
  return (
    <Section id="pipeline">
      <Reveal>
        <Heading>From radio call to reviewable evidence.</Heading>
        <Lead>Two real data streams, one pipeline. Language models read the words; fixed rules decide what counts as a finding.</Lead>
      </Reveal>

      <Reveal delay={80} className="mt-12">
        {/* Mobile: vertical rail. Desktop: horizontal timeline like the app's "What happened" strip. */}
        <ol className="relative grid gap-8 md:grid-cols-5 md:gap-6">
          <span aria-hidden className="grow-y absolute bottom-3 left-[19px] top-3 w-px bg-hairline-strong md:hidden" />
          <span aria-hidden className="grow-x absolute left-5 right-[calc((100%_-_96px)/5_-_20px)] top-[19px] hidden h-px bg-hairline-strong md:block" />
          {STEPS.map((s, i) => (
            <li key={s.title} className="relative grid grid-cols-[40px_1fr] gap-4 md:block">
              <span
                className={cn(
                  'relative z-[1] flex size-10 items-center justify-center rounded-full border-4 border-canvas',
                  i === STEPS.length - 1 ? 'bg-action text-on-action' : 'bg-data text-white',
                )}
              >
                <s.icon aria-hidden className="size-[18px]" />
              </span>
              <div className="md:mt-5">
                <p className="text-[18px] font-semibold tracking-[-0.015em]">{s.title}</p>
                <p className="mt-1.5 text-[15px] leading-relaxed text-ink-2">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </Reveal>
    </Section>
  );
}

/* --------------------------------------------------------------- workspace */

function Workspace() {
  return (
    <Section className="pt-0 md:pt-0">
      <Reveal className="rounded-[28px] bg-canvas-outer p-2 sm:p-3">
        <div className="px-3 pb-5 pt-5 sm:px-5 sm:pt-6 md:pb-7">
          <Heading className="max-w-[22ch]">One screen for the whole session.</Heading>
          <Lead className="mt-3">Audio, transcript, airport map and findings move together. Scrub to any second and see only what was known at that moment.</Lead>
        </div>
        <figure className="overflow-hidden rounded-[22px] border border-hairline bg-surface shadow-pop">
          <img
            src={workspaceShot}
            width={1600}
            height={1000}
            loading="lazy"
            decoding="async"
            alt="FlowLens workspace replaying a recorded session: airport map with aircraft positions, live transcript, and findings waiting for review."
            className="aspect-square w-full object-cover object-[42%_50%] sm:aspect-[16/10]"
          />
        </figure>
      </Reveal>
    </Section>
  );
}

/* ----------------------------------------------------------------- compare */

const COMPARE: { label: string; radar: string; lens: string }[] = [
  { label: 'Listens to', radar: 'Surface radar, multilateration and ADS-B', lens: 'Tower radio, ADS-B and the airport layout' },
  { label: 'Knows', radar: 'Where each aircraft is', lens: 'What it was told, and whether the readback and the movement matched' },
  { label: 'Speaks up', radar: 'Seconds before two paths conflict', lens: 'At the transmission where the mismatch began' },
  { label: 'Shows proof as', radar: 'Positions on a display', lens: 'The audio span, transcript words and track points' },
];

function Compare() {
  return (
    <Section className="bg-surface">
      <Reveal>
        <Heading className="max-w-[20ch]">Surface radar sees position. FlowLens adds intent.</Heading>
        <Lead>ASDE-X and A-SMGCS stay in charge of surveillance. FlowLens is the layer that remembers the conversation.</Lead>
      </Reveal>

      <Reveal delay={80} className="mt-10 overflow-hidden rounded-[24px] border border-hairline-soft">
        <div className="hidden grid-cols-[180px_1fr_1fr] bg-sunken px-6 py-3 text-[13px] font-semibold text-ink-2 md:grid">
          <span />
          <span>Surface surveillance</span>
          <span className="text-data-strong">FlowLens</span>
        </div>
        <dl>
          {COMPARE.map((c, i) => (
            <div key={c.label} className={cn('grid gap-3 px-5 py-5 md:grid-cols-[180px_1fr_1fr] md:gap-6 md:px-6', i > 0 && 'border-t border-hairline-soft')}>
              <dt className="text-[14px] font-semibold">{c.label}</dt>
              <dd className="grid grid-cols-2 gap-4 md:contents">
                <span className="text-[14.5px] leading-relaxed text-ink-2">
                  <span className="mb-1 block text-[12px] font-medium text-ink-3 md:hidden">Surveillance</span>
                  {c.radar}
                </span>
                <span className="text-[14.5px] leading-relaxed text-ink">
                  <span className="mb-1 block text-[12px] font-medium text-data-strong md:hidden">FlowLens</span>
                  {c.lens}
                </span>
              </dd>
            </div>
          ))}
        </dl>
      </Reveal>
    </Section>
  );
}

/* ----------------------------------------------------------------- dataset */

const DATA_STATS = [
  { value: '3,374 h', label: 'of tower radio audio, timestamped in UTC' },
  { value: '63M', label: 'ADS-B position reports' },
  { value: '661', label: 'days of recorded traffic' },
  { value: 'KAGC', label: 'Allegheny County Airport, Pittsburgh' },
];

function Dataset() {
  return (
    <Section id="data">
      <Reveal className="relative overflow-hidden rounded-[28px] bg-[#0f2a6b] p-6 text-white sm:p-10 md:p-14">
        <div
          aria-hidden
          className="absolute inset-0 bg-[radial-gradient(120%_80%_at_0%_0%,#1f4fd6_0%,transparent_60%),radial-gradient(90%_70%_at_100%_100%,#f3a37a_0%,transparent_55%),radial-gradient(70%_60%_at_80%_20%,#7db3ff_0%,transparent_60%),linear-gradient(160deg,#173a8f,#5b74c4_55%,#e9b7a1)]"
        />
        <svg aria-hidden viewBox="0 0 600 600" preserveAspectRatio="xMaxYMid meet" className="absolute inset-y-0 right-0 h-full w-full opacity-[0.14] md:w-3/5">
          <rect x="40" y="290" width="520" height="34" rx="6" fill="none" stroke="#fff" strokeWidth="1.5" />
          <path d="M60 307H540" stroke="#fff" strokeDasharray="14 12" strokeWidth="1.5" />
          <path d="M120 440C220 440 300 440 420 420 470 410 470 360 470 324" fill="none" stroke="#fff" strokeWidth="1.5" />
          <path d="M200 170C260 170 300 190 320 220 330 240 330 270 330 290" fill="none" stroke="#fff" strokeWidth="1.5" />
        </svg>
        <div className="relative">
          <span className="text-[13px] font-semibold uppercase tracking-[0.14em] text-white/75">Dataset</span>
          <h2 className="mt-4 max-w-[16ch] text-[34px] font-medium leading-[1.06] tracking-[-0.035em] text-balance md:text-[48px]">Built on real tower recordings.</h2>
          <p className="mt-4 max-w-[52ch] text-[16px] leading-relaxed text-white/85">
            Real static, clipped transmissions and real traffic from the TartanAviation multimodal dataset. When the track is missing, FlowLens says so instead of guessing.
          </p>
          <dl className="mt-10 grid grid-cols-2 gap-x-6 gap-y-8 border-t border-white/20 pt-8 md:grid-cols-4">
            {DATA_STATS.map((s) => (
              <div key={s.value}>
                <dt className="sr-only">{s.label}</dt>
                <dd>
                  <span className="block text-[32px] font-medium leading-none tracking-[-0.035em] tabular md:text-[40px]">{s.value}</span>
                  <span className="mt-2 block text-[14px] leading-snug text-white/80">{s.label}</span>
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </Reveal>
    </Section>
  );
}

/* -------------------------------------------------------------- principles */

const PRINCIPLES: { icon: LucideIcon; tint: string; title: string; body: string }[] = [
  { icon: ShieldCheck, tint: 'bg-data-tint text-data-strong', title: 'The controller keeps authority', body: 'FlowLens never issues, edits or transmits an instruction. It only points at evidence.' },
  { icon: CircleHelp, tint: 'bg-notice-tint text-notice', title: 'Unknown stays unknown', body: 'Unclear audio or a missing track is marked not evaluable, never read as all good.' },
  { icon: FileSearch, tint: 'bg-discrepancy-tint text-discrepancy', title: 'Every finding has a source', body: 'Each one links to the exact audio span, transcript words and track points behind it.' },
  { icon: History, tint: 'bg-muted-tint text-muted', title: 'Replay first', body: 'Today it reviews recorded sessions. Live use waits for ANSP approval and safety assurance.' },
];

function Principles() {
  return (
    <Section>
      <div className="grid gap-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-16">
        <Reveal>
          <Heading>Advisory by design.</Heading>
          <Lead>Built for people who are accountable for every word on frequency.</Lead>
        </Reveal>
        <Reveal delay={80} className="card px-5 py-2 sm:px-6">
          <ul>
            {PRINCIPLES.map((p, i) => (
              <li key={p.title} className={cn('flex gap-4 py-5', i > 0 && 'border-t border-hairline-soft')}>
                <span className={cn('flex size-11 shrink-0 items-center justify-center rounded-full', p.tint)}>
                  <p.icon aria-hidden className="size-5" />
                </span>
                <div>
                  <p className="text-[16.5px] font-semibold tracking-[-0.01em]">{p.title}</p>
                  <p className="mt-1 text-[15px] leading-relaxed text-ink-2">{p.body}</p>
                </div>
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </Section>
  );
}

/* ----------------------------------------------------------------- closing */

function Closing() {
  return (
    <Section className="pb-20 pt-4 md:pb-28 md:pt-8">
      <Reveal className="border-t border-hairline-strong pt-10 md:pt-14">
        <p className="max-w-[18ch] text-[40px] font-medium leading-[1.04] tracking-[-0.04em] text-balance md:text-[64px]">
          The controller decides. <span className="text-data">FlowLens remembers.</span>
        </p>
      </Reveal>
    </Section>
  );
}
