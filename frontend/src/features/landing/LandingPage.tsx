import {
  ArrowDown,
  ArrowUp,
  AudioLines,
  Braces,
  CircleHelp,
  FileSearch,
  FlaskConical,
  GitCompareArrows,
  History,
  LayoutPanelLeft,
  ListChecks,
  MapPinned,
  Plane,
  RadioTower,
  ShieldCheck,
  SlidersHorizontal,
  UserCheck,
  type LucideIcon,
} from 'lucide-react';
import { useEffect, useState, type CSSProperties, type ReactNode } from 'react';
import { LogoMark } from '@/components/layout/Logo';
import { cn } from '@/lib/utils';
import workspaceShot from '@/assets/landing/workspace.jpg';
import { Reveal } from './Reveal';

/**
 * Public product introduction (mobile first). Follows the app's Margin-derived language:
 * one pale canvas, white 24px cards, charcoal action, blue data, magenta discrepancy, hatching.
 * It intentionally has no link into the sign-in flow; that lives at /login-flow.
 *
 * Radius scale: 28px feature containers, 24px cards, 16px inner rows, 8px chips, 12px controls.
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
    <div className="min-h-dvh overflow-x-clip bg-canvas text-ink">
      <span id="top" aria-hidden className="absolute top-0 h-px w-px" />
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

const delay = (ms: number) => ({ '--enter-delay': `${ms}ms` }) as CSSProperties;

/* ------------------------------------------------------------------ chrome */

const NAV = [
  { id: 'records', label: 'Product' },
  { id: 'pipeline', label: 'How it works' },
  { id: 'data', label: 'Data' },
];

/** Which nav section is under the header. IntersectionObserver only; no scroll listeners. */
function useActiveSection(ids: string[]) {
  const [active, setActive] = useState<string | null>(null);
  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return;
    const visible = new Map<string, boolean>();
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) visible.set(e.target.id, e.isIntersecting);
        setActive(ids.find((id) => visible.get(id)) ?? null);
      },
      { rootMargin: '-35% 0px -60% 0px' },
    );
    for (const id of ids) {
      const el = document.getElementById(id);
      if (el) io.observe(el);
    }
    return () => io.disconnect();
  }, [ids]);
  return active;
}

/** True once the page has scrolled past the very top (sentinel at #top). */
function useScrolled() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const el = document.getElementById('top');
    if (!el || typeof IntersectionObserver === 'undefined') return;
    const io = new IntersectionObserver(([e]) => setScrolled(!e?.isIntersecting));
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return scrolled;
}

const NAV_IDS = NAV.map((n) => n.id);

function Header() {
  const active = useActiveSection(NAV_IDS);
  const scrolled = useScrolled();
  return (
    <header
      className={cn(
        'sticky top-0 z-40 border-b transition-[background-color,border-color,box-shadow] duration-300',
        scrolled ? 'border-[color:var(--hairline-soft)] bg-canvas/80 shadow-[0_1px_12px_rgba(25,27,32,0.04)] backdrop-blur-md' : 'border-transparent bg-canvas',
      )}
    >
      <div className="px-4 sm:px-6">
        <div className="mx-auto flex h-16 max-w-[1200px] items-center justify-between">
          <a href="#top" className="-ml-1 flex items-center gap-2.5 rounded-[10px] p-1" aria-label="FlowLens, back to top">
            <LogoMark className="size-8" />
            <span className="text-[19px] font-semibold tracking-[-0.025em]">FlowLens</span>
          </a>
          <nav aria-label="Sections" className="hidden items-center gap-0.5 rounded-[14px] border border-[color:var(--hairline-soft)] bg-surface/70 p-1 shadow-control md:flex">
            {NAV.map((n) => (
              <a
                key={n.id}
                href={`#${n.id}`}
                aria-current={active === n.id ? 'true' : undefined}
                className={cn(
                  'rounded-[10px] px-3.5 py-1.5 text-[14px] font-medium transition-colors duration-150',
                  active === n.id ? 'bg-action text-on-action' : 'text-ink-2 hover:bg-track hover:text-ink',
                )}
              >
                {n.label}
              </a>
            ))}
          </nav>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-hairline bg-surface px-2.5 py-1 text-[12.5px] font-medium text-ink-2 md:hidden">
            <FlaskConical aria-hidden className="size-3.5 text-ink-3" />
            Research prototype
          </span>
        </div>
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer className="px-4 pb-10 sm:px-6">
      <div className="mx-auto max-w-[1200px] border-t border-hairline-strong/70 pt-8">
        <div className="grid gap-8 md:grid-cols-[minmax(0,1fr)_auto] md:items-start">
          <div>
            <span className="flex items-center gap-2.5">
              <LogoMark className="size-7" />
              <span className="text-[17px] font-semibold tracking-[-0.02em]">FlowLens</span>
            </span>
            <p className="mt-3 max-w-[46ch] text-[14px] leading-relaxed text-ink-2 text-pretty">
              Research prototype for replaying recorded tower sessions. Not certified for operational use and not connected to any live frequency.
            </p>
          </div>
          <nav aria-label="Footer" className="flex flex-wrap gap-x-6 gap-y-2 text-[14px] font-medium text-ink-2">
            {NAV.map((n) => (
              <a key={n.id} href={`#${n.id}`} className="rounded-[6px] hover:text-ink">
                {n.label}
              </a>
            ))}
            <a href="#top" className="inline-flex items-center gap-1 rounded-[6px] hover:text-ink">
              Top <ArrowUp aria-hidden className="size-3.5" />
            </a>
          </nav>
        </div>
        <div className="mt-8 flex flex-col gap-1 text-[13px] text-ink-3 sm:flex-row sm:justify-between">
          <p>
            Audio and ADS‑B: TartanAviation, Patrikar et al., <span className="whitespace-nowrap">CC BY 4.0</span>
          </p>
          <p>© 2026 FlowLens</p>
        </div>
      </div>
    </footer>
  );
}

function Section({ id, className, children }: { id?: string; className?: string; children: ReactNode }) {
  return (
    <section id={id} className={cn('scroll-mt-16 px-4 py-14 sm:px-6 md:py-20', className)}>
      <div className="mx-auto max-w-[1200px]">{children}</div>
    </section>
  );
}

function Heading({ children, className }: { children: ReactNode; className?: string }) {
  return <h2 className={cn('max-w-[18ch] text-[32px] font-medium leading-[1.06] tracking-[-0.035em] text-balance md:text-[46px]', className)}>{children}</h2>;
}

function Lead({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn('mt-4 max-w-[54ch] text-[16px] leading-relaxed text-ink-2 text-pretty md:text-[17px]', className)}>{children}</p>;
}

/* -------------------------------------------------------------------- hero */

function Hero() {
  return (
    <section className="px-4 pb-14 pt-6 sm:px-6 md:pb-24 md:pt-14">
      <div className="mx-auto grid max-w-[1200px] items-center gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.04fr)] lg:gap-16">
        <div className="lg:pb-6">
          <span className="enter inline-flex items-center gap-2 rounded-full border border-hairline bg-surface py-1 pl-1 pr-3 text-[13px] font-medium text-ink-2 shadow-control">
            <span className="flex size-6 items-center justify-center rounded-full bg-data-tint">
              <AudioLines aria-hidden className="size-3.5 text-data" />
            </span>
            Tower radio meets ADS‑B
          </span>
          <h1 className="enter mt-6 text-[44px] font-medium leading-[1.02] tracking-[-0.045em] text-balance sm:text-[58px] lg:text-[66px]" style={delay(80)}>
            Said, heard, observed. <span className="text-ink-3">On one timeline.</span>
          </h1>
          <p className="enter mt-5 max-w-[40ch] text-[17px] leading-relaxed text-ink-2 text-pretty md:text-[18px]" style={delay(160)}>
            FlowLens replays tower radio beside ADS‑B tracks, so each readback is checked against where the aircraft actually went.
          </p>
          <div className="enter mt-8" style={delay(240)}>
            <a
              href="#pipeline"
              className="group inline-flex h-12 items-center gap-2.5 rounded-control bg-action pl-6 pr-2 text-[15px] font-medium text-on-action shadow-action transition-[background-color,transform] duration-150 hover:bg-action-hover active:scale-[0.98]"
            >
              See how it works
              <span className="flex size-8 items-center justify-center rounded-[9px] bg-white/12 transition-transform duration-200 group-hover:translate-y-0.5">
                <ArrowDown aria-hidden className="size-4" />
              </span>
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
        <span key={i} className={cn('wave-bar w-[2.5px] rounded-full', tone === 'data' ? 'bg-data/60' : 'bg-discrepancy/60')} style={{ height: h, '--i': i } as CSSProperties} />
      ))}
    </span>
  );
}

function Speaker({ icon: Icon, tone }: { icon: LucideIcon; tone: 'data' | 'discrepancy' }) {
  return (
    <span className={cn('flex size-7 shrink-0 items-center justify-center rounded-full', tone === 'data' ? 'bg-data-tint text-data-strong' : 'bg-discrepancy-tint text-discrepancy')}>
      <Icon aria-hidden className="size-3.5" />
    </span>
  );
}

function HeroVisual() {
  return (
    <div className="enter relative lg:pl-2" style={delay(200)}>
      <figure aria-label="Example finding: a readback that differs from the clearance" className="relative overflow-hidden rounded-[28px] spotlight-mesh p-6 pb-28 text-white shadow-pop sm:p-8 sm:pb-32">
        <svg aria-hidden viewBox="0 0 400 400" className="pointer-events-none absolute -bottom-28 -right-20 size-[340px] opacity-30">
          <circle cx="200" cy="200" r="150" fill="none" stroke="#fff" strokeWidth="1" />
          <circle cx="200" cy="200" r="100" fill="none" stroke="#fff" strokeWidth="1" strokeDasharray="3 6" />
          <path d="M40 260 C140 250 220 210 300 120" fill="none" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <div className="relative flex items-center justify-between gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/16 px-3 py-1.5 text-[13px] font-medium ring-1 ring-inset ring-white/25 backdrop-blur">
            <GitCompareArrows aria-hidden className="size-4" />
            Readback differs
          </span>
          <span className="text-[13px] font-medium text-white/80 tabular">KAGC Ground</span>
        </div>
        <p className="relative mt-8 text-[56px] font-medium leading-none tracking-[-0.045em] tabular sm:text-[72px]">N147G</p>
        <p className="relative mt-4 max-w-[24ch] text-[20px] font-medium leading-snug tracking-[-0.015em] text-balance sm:text-[24px]">Hold short of runway 28 was read back as runway 13.</p>
        <p className="relative mt-3 max-w-[38ch] text-[14.5px] leading-relaxed text-white/80 text-pretty">The readback came five seconds later. Nobody corrected it on frequency.</p>
      </figure>

      <div className="relative -mt-20 ml-3 mr-3 rounded-[24px] border border-white/70 bg-surface/95 p-3 shadow-pop backdrop-blur sm:ml-10 sm:mr-6 sm:p-4">
        <div className="flex items-center justify-between px-1 pb-2.5 pt-0.5">
          <p className="text-[13px] font-semibold text-ink">On frequency</p>
          <p className="text-[12.5px] text-ink-2 tabular">121.9 MHz</p>
        </div>
        <ol className="space-y-2">
          <li className="enter rounded-[16px] bg-sunken p-3" style={delay(650)}>
            <div className="flex items-center gap-2.5">
              <Speaker icon={RadioTower} tone="data" />
              <span className="text-[12.5px] font-semibold text-data-strong">Said · Ground</span>
              <span className="ml-auto text-[12px] text-ink-3 tabular">00:41</span>
            </div>
            <p className="mt-2 text-[14.5px] leading-snug text-ink">
              …taxi runway one three via Bravo, <mark className="rounded-[5px] bg-data-tint px-1 text-data-strong">hold short runway two eight.</mark>
            </p>
          </li>
          <li className="enter rounded-[16px] bg-sunken p-3" style={delay(1150)}>
            <div className="flex items-center gap-2.5">
              <Speaker icon={Plane} tone="discrepancy" />
              <span className="text-[12.5px] font-semibold text-discrepancy">Heard · N147G</span>
              <span className="ml-auto flex items-center gap-2">
                <Wave tone="discrepancy" bars={12} />
                <span className="text-[12px] text-ink-3 tabular">00:46</span>
              </span>
            </div>
            <p className="mt-2 text-[14.5px] leading-snug text-ink">
              Via Bravo, <mark className="mark-flag rounded-[5px] px-1 text-discrepancy">hold short one three</mark>, four seven golf.
            </p>
          </li>
        </ol>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- pressure */

function Pictogram({ total, filled, tone }: { total: number; filled: number; tone: 'ink' | 'discrepancy' }) {
  return (
    <span aria-hidden className="grid shrink-0 grid-cols-5 gap-1.5 pt-1.5">
      {Array.from({ length: total }, (_, i) => (
        <span
          key={i}
          className={cn(
            'size-3 rounded-full sm:size-3.5',
            i < filled ? (tone === 'ink' ? 'bg-action' : 'bg-discrepancy') : 'border border-hairline-strong hatch-muted',
          )}
        />
      ))}
    </span>
  );
}

function Pressure() {
  return (
    <Section className="pt-6 md:pt-10">
      <Reveal>
        <Heading>Traffic keeps growing. Towers do not.</Heading>
        <Lead>Controllers hold every clearance in working memory while the next call is already on frequency.</Lead>
      </Reveal>

      <div className="mt-10 grid grid-cols-1 gap-3 md:grid-cols-6 md:gap-4">
        <Reveal className="card p-6 md:col-span-4 md:p-8">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
            <div>
              <p className="text-[16px] font-semibold tracking-[-0.01em]">Demand vs people</p>
              <p className="mt-0.5 text-[13.5px] text-ink-2">Reported growth</p>
            </div>
            <span className="flex items-center gap-3 text-[12.5px] text-ink-2">
              <span className="inline-flex items-center gap-1.5">
                <span aria-hidden className="h-2.5 w-4 rounded-[3px] hatch-data" /> Flights
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span aria-hidden className="h-2.5 w-4 rounded-[3px] bg-action" /> Controllers
              </span>
            </span>
          </div>
          <div className="mt-8 space-y-7">
            <div>
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-[14.5px] text-ink-2">Global flight demand, by 2030</p>
                <p className="text-[26px] font-medium tracking-[-0.03em] text-data-strong tabular">+12%</p>
              </div>
              <div className="mt-2.5 h-5 rounded-[7px] hatch-data grow-x" />
            </div>
            <div>
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-[14.5px] text-ink-2">Controller headcount, 2022 to 2025</p>
                <p className="text-[26px] font-medium tracking-[-0.03em] tabular">+0.5%</p>
              </div>
              <div className="relative mt-2.5 h-5">
                <div aria-hidden className="absolute inset-0 rounded-[7px] border border-dashed border-hairline-strong" />
                <div className="relative h-full w-[4.2%] min-w-3.5 rounded-[7px] bg-action grow-x" />
              </div>
              <p className="mt-2 text-[12.5px] text-ink-3">Dashed outline: the growth in flights, for scale.</p>
            </div>
          </div>
        </Reveal>

        <Reveal delay={80} className="relative flex min-h-[220px] flex-col justify-between overflow-hidden rounded-[24px] bg-data p-6 text-white shadow-card md:col-span-2 md:p-8">
          <div aria-hidden className="absolute -right-10 -top-10 size-44 rounded-full border border-white/20" />
          <div aria-hidden className="absolute -right-2 -top-2 size-28 rounded-full border border-dashed border-white/20" />
          <p className="relative text-[15px] font-semibold text-white/85">LAX tower, average day</p>
          <div className="relative">
            <p className="text-[60px] font-medium leading-none tracking-[-0.05em] tabular">1,592</p>
            <p className="mt-3 text-[14.5px] leading-relaxed text-white/85">flights handled. About 66 every hour, more than one a minute.</p>
          </div>
        </Reveal>

        <Reveal className="card flex flex-col p-6 md:col-span-3 md:p-8">
          <div className="flex items-start justify-between gap-4">
            <p className="text-[52px] font-medium leading-none tracking-[-0.05em] tabular">90.3%</p>
            <Pictogram total={10} filled={9} tone="ink" />
          </div>
          <p className="mt-4 max-w-[44ch] text-[15px] leading-relaxed text-ink-2 text-pretty">of controllers in a published study reported high to very high mental workload. Roughly nine in ten.</p>
          <p className="mt-auto pt-5 text-[13px] text-ink-3">Senjaya et al., 2020</p>
        </Reveal>

        <Reveal delay={80} className="card flex flex-col p-6 md:col-span-3 md:p-8">
          <div className="flex items-start justify-between gap-4">
            <p className="text-[52px] font-medium leading-none tracking-[-0.05em] text-discrepancy tabular">≈20%</p>
            <Pictogram total={5} filled={1} tone="discrepancy" />
          </div>
          <p className="mt-4 max-w-[44ch] text-[15px] leading-relaxed text-ink-2 text-pretty">of US runway incursions trace back to an ATC action or inaction. About one in five.</p>
          <p className="mt-auto pt-5 text-[13px] text-ink-3">FAA, fiscal year 2023</p>
        </Reveal>
      </div>
    </Section>
  );
}

/* ----------------------------------------------------------- three records */

interface Slot {
  label: string;
  tone?: 'mismatch' | 'ok';
  note?: string;
}

interface RecordRow {
  layer: string;
  source: string;
  icon: LucideIcon;
  time: string;
  gap?: string;
  text: string;
  slots: Slot[];
  tone: 'data' | 'discrepancy' | 'ready';
}

const RECORDS: RecordRow[] = [
  {
    layer: 'Said',
    source: 'Ground controller',
    icon: RadioTower,
    time: '00:41.2',
    tone: 'data',
    text: 'Skyhawk one four seven golf, taxi runway one three via Bravo, hold short runway two eight.',
    slots: [{ label: 'N147G' }, { label: 'Taxi' }, { label: 'RWY 13' }, { label: 'via B' }, { label: 'Hold short 28' }],
  },
  {
    layer: 'Heard',
    source: 'Pilot readback',
    icon: Plane,
    time: '00:46.8',
    gap: '+5.6 s',
    tone: 'discrepancy',
    text: 'Runway one three via Bravo, hold short one three, four seven golf.',
    slots: [{ label: 'N147G' }, { label: 'RWY 13' }, { label: 'via B' }, { label: 'Hold short 13', tone: 'mismatch', note: 'expected 28' }],
  },
  {
    layer: 'Observed',
    source: 'ADS‑B track',
    icon: MapPinned,
    time: '01:12.0',
    gap: '+25.2 s',
    tone: 'ready',
    text: 'Track slows on Bravo and stops before the runway 28 hold line.',
    slots: [{ label: 'Stopped at B / 28', tone: 'ok' }, { label: '3 kt to 0 kt' }],
  },
];

const LAYER_TONE = {
  data: { node: 'bg-data text-white', text: 'text-data-strong' },
  discrepancy: { node: 'bg-discrepancy text-white', text: 'text-discrepancy' },
  ready: { node: 'bg-ready text-white', text: 'text-ready' },
} as const;

function ThreeRecords() {
  return (
    <Section id="records">
      <div className="grid gap-10 lg:grid-cols-[minmax(0,0.82fr)_minmax(0,1.18fr)] lg:gap-16">
        <Reveal className="lg:sticky lg:top-28 lg:self-start">
          <Heading>Three records. Never merged.</Heading>
          <Lead>A correct readback does not prove the aircraft moved as cleared. FlowLens keeps what was said, what was heard and what the track shows apart, then points to where they disagree.</Lead>
          <dl className="mt-8 grid max-w-[420px] grid-cols-3 gap-2">
            {(['data', 'discrepancy', 'ready'] as const).map((tone, i) => (
              <div key={tone} className="rounded-[16px] border border-[color:var(--hairline-soft)] bg-surface px-3 py-3 shadow-card">
                <dt className={cn('text-[13px] font-semibold', LAYER_TONE[tone].text)}>{RECORDS[i]!.layer}</dt>
                <dd className="mt-0.5 text-[12.5px] leading-snug text-ink-2">{['Controller audio', 'Pilot audio', 'ADS‑B track'][i]}</dd>
              </div>
            ))}
          </dl>
        </Reveal>

        <Reveal delay={100} className="card p-3 sm:p-4">
          <div className="flex items-center justify-between px-2 pb-3 pt-1.5">
            <p className="text-[15px] font-semibold">Example session</p>
            <p className="text-[13px] text-ink-2">Ground, runway 13 flow</p>
          </div>
          <ol className="relative">
            {RECORDS.map((r, i) => {
              const t = LAYER_TONE[r.tone];
              return (
                <li key={r.layer} className="relative grid grid-cols-[32px_minmax(0,1fr)] gap-3 pb-3 last:pb-0 sm:grid-cols-[36px_minmax(0,1fr)]">
                  {/* Time rail connecting the three records */}
                  {i < RECORDS.length - 1 && <span aria-hidden className="absolute bottom-0 left-[15.5px] top-10 w-px bg-hairline-strong sm:left-[17.5px]" />}
                  <div className="relative flex flex-col items-center pt-4">
                    <span className={cn('flex size-8 items-center justify-center rounded-full ring-4 ring-surface sm:size-9', t.node)}>
                      <r.icon aria-hidden className="size-4" />
                    </span>
                  </div>
                  <div className="rounded-[16px] bg-sunken p-4 sm:p-5">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className={cn('text-[17px] font-semibold tracking-[-0.01em]', t.text)}>{r.layer}</p>
                        <p className="text-[13px] text-ink-2">{r.source}</p>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-1">
                        <span className="rounded-full bg-surface px-2.5 py-1 text-[12.5px] font-medium text-ink-2 shadow-control tabular">{r.time}</span>
                        {r.gap && <span className="text-[12px] text-ink-3 tabular">{r.gap}</span>}
                      </div>
                    </div>
                    <p className="mt-3 text-[15.5px] leading-relaxed text-ink text-pretty">“{r.text}”</p>
                    <ul aria-label={`${r.layer} slots`} className="mt-4 flex flex-wrap gap-1.5">
                      {r.slots.map((s) => (
                        <li
                          key={s.label}
                          className={cn(
                            'inline-flex items-center gap-1.5 rounded-[8px] px-2.5 py-1 text-[12.5px] font-medium',
                            s.tone === 'mismatch' ? 'bg-discrepancy-tint text-discrepancy ring-1 ring-inset ring-discrepancy/25' : s.tone === 'ok' ? 'bg-ready-tint text-ready' : 'bg-surface text-ink-2 ring-1 ring-inset ring-hairline',
                          )}
                        >
                          {s.tone === 'mismatch' && <span className="sr-only">Mismatch: </span>}
                          {s.label}
                          {s.note && <span className="font-normal text-discrepancy/75">· {s.note}</span>}
                        </li>
                      ))}
                    </ul>
                  </div>
                </li>
              );
            })}
          </ol>
          <p className="mx-2 mb-1 mt-4 rounded-[14px] border border-dashed border-hairline-strong px-4 py-3 text-[13.5px] leading-relaxed text-ink-2 text-pretty">
            The readback was wrong, yet the aircraft stopped where it was cleared to. Both facts stay visible, side by side.
          </p>
        </Reveal>
      </div>
    </Section>
  );
}

/* ---------------------------------------------------------------- pipeline */

const STEPS: { icon: LucideIcon; title: string; body: string; output: ReactNode }[] = [
  { icon: AudioLines, title: 'Transcribe', body: 'Speech-to-text tuned for ATC phraseology turns each transmission into timed words.', output: <>00:46.8 “hold short one three”</> },
  { icon: Braces, title: 'Extract', body: 'Callsign, runway, taxiway, hold short and conditions become validated slots, each with its quote.', output: <>HOLD_SHORT · RWY 13</> },
  { icon: GitCompareArrows, title: 'Pair', body: 'Each clearance is matched with its readback, so a missing or wrong element stands out.', output: <span className="text-discrepancy">28 said, 13 read back</span> },
  { icon: MapPinned, title: 'Check', body: 'Deterministic geometry tests the instruction against ADS‑B and the airport layout.', output: <span className="text-ready">Held at B / 28</span> },
  { icon: UserCheck, title: 'Review', body: 'An evaluator accepts or rejects each finding, with the audio one click away.', output: <>Accepted, with note</> },
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
        <ol className="relative grid gap-7 md:grid-cols-5 md:gap-6">
          <span aria-hidden className="grow-y absolute bottom-6 left-[19.5px] top-6 w-px bg-hairline-strong md:hidden" />
          <span aria-hidden className="grow-x absolute left-5 right-[calc((100%_-_96px)/5_-_20px)] top-[19.5px] hidden h-px bg-hairline-strong md:block" />
          {STEPS.map((s, i) => (
            <li key={s.title} className="relative grid grid-cols-[40px_minmax(0,1fr)] gap-4 md:flex md:flex-col md:gap-0">
              <span className={cn('relative z-[1] flex size-10 items-center justify-center rounded-full ring-[5px] ring-canvas', i === STEPS.length - 1 ? 'bg-action text-on-action' : 'bg-data text-white')}>
                <s.icon aria-hidden className="size-[18px]" />
              </span>
              <div className="md:mt-5 md:flex md:flex-1 md:flex-col">
                <p className="text-[18px] font-semibold tracking-[-0.015em]">{s.title}</p>
                <p className="mb-3 mt-1.5 text-[15px] leading-relaxed text-ink-2 text-pretty md:mb-4">{s.body}</p>
                <p className="inline-flex max-w-full self-start rounded-[8px] md:mt-auto bg-surface px-2.5 py-1.5 text-[12.5px] font-medium text-ink-2 shadow-control ring-1 ring-inset ring-[color:var(--hairline-soft)] tabular">
                  <span className="truncate">{s.output}</span>
                </p>
              </div>
            </li>
          ))}
        </ol>
      </Reveal>
    </Section>
  );
}

/* --------------------------------------------------------------- workspace */

const CALLOUTS: { icon: LucideIcon; title: string; body: string }[] = [
  { icon: LayoutPanelLeft, title: 'Situation', body: 'Aircraft on the airport layout, with missing tracks shown as missing.' },
  { icon: ListChecks, title: 'Needs attention', body: 'Findings appear the moment their evidence is complete.' },
  { icon: SlidersHorizontal, title: 'Timeline', body: 'Every frequency on one scrubber, as known at the time or in full.' },
];

function Workspace() {
  return (
    <Section className="pt-0 md:pt-0">
      <Reveal className="rounded-[28px] bg-canvas-outer p-2 sm:p-3">
        <div className="px-3 pb-5 pt-5 sm:px-5 sm:pt-7 md:pb-8">
          <Heading className="max-w-[22ch]">One screen for the whole session.</Heading>
          <Lead className="mt-3">Audio, transcript, airport map and findings move together. Scrub to any second and see only what was known at that moment.</Lead>
        </div>
        <figure className="overflow-hidden rounded-[22px] border border-hairline bg-surface shadow-pop">
          <div aria-hidden className="flex h-10 items-center gap-3 border-b border-[color:var(--hairline-soft)] bg-sunken px-4">
            <span className="flex gap-1.5">
              <span className="size-2.5 rounded-full bg-hairline-strong" />
              <span className="size-2.5 rounded-full bg-hairline-strong" />
              <span className="size-2.5 rounded-full bg-hairline-strong" />
            </span>
            <span className="mx-auto truncate rounded-[8px] bg-surface px-3 py-1 text-[12px] text-ink-3 ring-1 ring-inset ring-[color:var(--hairline-soft)]">flowlens.site/s/runway-27/workspace</span>
            <span className="w-[42px]" />
          </div>
          <div className="bg-sunken">
            <img
              src={workspaceShot}
              width={2000}
              height={1250}
              loading="lazy"
              decoding="async"
              alt="FlowLens workspace replaying a recorded session: airport map with aircraft positions, findings that need attention, and the audio timeline."
              className="aspect-[4/5] w-full object-cover object-[36%_50%] sm:aspect-[16/10]"
            />
          </div>
        </figure>
        <ul className="grid gap-2 px-1 pb-1 pt-3 sm:grid-cols-3 sm:gap-3 sm:px-0 sm:pb-0">
          {CALLOUTS.map((c) => (
            <li key={c.title} className="flex gap-3 rounded-[18px] bg-surface/70 p-4">
              <c.icon aria-hidden className="mt-0.5 size-[18px] shrink-0 text-data" />
              <div>
                <p className="text-[14.5px] font-semibold">{c.title}</p>
                <p className="mt-0.5 text-[13.5px] leading-relaxed text-ink-2 text-pretty">{c.body}</p>
              </div>
            </li>
          ))}
        </ul>
      </Reveal>
    </Section>
  );
}

/* ----------------------------------------------------------------- compare */

const COMPARE: { label: string; radar: string; lens: string }[] = [
  { label: 'Listens to', radar: 'Surface radar, multilateration and ADS‑B', lens: 'Tower radio, ADS‑B and the airport layout' },
  { label: 'Knows', radar: 'Where each aircraft is', lens: 'What it was told, and whether the readback and the movement matched' },
  { label: 'Speaks up', radar: 'Seconds before two paths conflict', lens: 'At the transmission where the mismatch began' },
  { label: 'Shows proof as', radar: 'Positions on a display', lens: 'The audio span, transcript words and track points' },
];

function Compare() {
  return (
    <Section>
      <Reveal>
        <Heading className="max-w-[20ch]">Surface radar sees position. FlowLens adds intent.</Heading>
        <Lead>ASDE-X and A-SMGCS stay in charge of surveillance. FlowLens is the layer that remembers the conversation.</Lead>
      </Reveal>

      <Reveal delay={80} className="card mt-10 overflow-hidden">
        <div className="relative">
          {/* Desktop: the FlowLens column carries a tinted band from header to last row. */}
          <span aria-hidden className="absolute inset-y-0 right-0 hidden w-[calc((100%_-_180px)/2)] bg-data-tint/45 md:block" />
          <div className="relative hidden grid-cols-[180px_1fr_1fr] border-b border-[color:var(--hairline-soft)] text-[13px] font-semibold md:grid">
            <span className="px-6 py-4" />
            <span className="px-6 py-4 text-ink-2">Surface surveillance</span>
            <span className="flex items-center gap-2 px-6 py-4 text-data-strong">
              <LogoMark className="size-5" /> FlowLens
            </span>
          </div>
          <dl className="relative">
            {COMPARE.map((c, i) => (
              <div key={c.label} className={cn('grid gap-3 px-5 py-5 md:grid-cols-[180px_1fr_1fr] md:gap-0 md:p-0', i > 0 && 'border-t border-[color:var(--hairline-soft)]')}>
                <dt className="text-[14px] font-semibold md:px-6 md:py-5">{c.label}</dt>
                <dd className="grid grid-cols-1 gap-2 min-[480px]:grid-cols-2 md:contents">
                  <span className="rounded-[12px] bg-sunken p-3 text-[14.5px] leading-relaxed text-ink-2 md:rounded-none md:bg-transparent md:px-6 md:py-5">
                    <span className="mb-1 block text-[12px] font-medium text-ink-3 md:hidden">Surveillance</span>
                    {c.radar}
                  </span>
                  <span className="rounded-[12px] bg-data-tint/60 p-3 text-[14.5px] leading-relaxed text-ink md:rounded-none md:bg-transparent md:px-6 md:py-5">
                    <span className="mb-1 block text-[12px] font-medium text-data-strong md:hidden">FlowLens</span>
                    {c.lens}
                  </span>
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </Reveal>
    </Section>
  );
}

/* ----------------------------------------------------------------- dataset */

const DATA_STATS = [
  { value: '3,374 h', label: 'of tower radio audio, timestamped in UTC' },
  { value: '63M', label: 'ADS‑B position reports' },
  { value: '661', label: 'days of recorded traffic' },
  { value: 'KAGC', label: 'Allegheny County Airport, Pittsburgh' },
];

function Dataset() {
  return (
    <Section id="data">
      <Reveal className="relative overflow-hidden rounded-[28px] bg-[#0f2a6b] p-6 text-white shadow-pop sm:p-10 md:p-14">
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
          <span className="text-[12.5px] font-semibold uppercase tracking-[0.14em] text-white/75">Dataset</span>
          <h2 className="mt-4 max-w-[16ch] text-[34px] font-medium leading-[1.05] tracking-[-0.035em] text-balance md:text-[50px]">Built on real tower recordings.</h2>
          <p className="mt-4 max-w-[50ch] text-[16px] leading-relaxed text-white/85 text-pretty">
            Real static, clipped transmissions and real traffic from the TartanAviation multimodal dataset. When the track is missing, FlowLens says so instead of guessing.
          </p>
          <dl className="mt-10 grid grid-cols-2 gap-x-6 gap-y-8 border-t border-white/20 pt-8 md:grid-cols-4">
            {DATA_STATS.map((s) => (
              <div key={s.value} className="flex flex-col-reverse">
                <dt className="mt-2 text-[14px] leading-snug text-white/80">{s.label}</dt>
                <dd className="text-[32px] font-medium leading-none tracking-[-0.04em] tabular md:text-[42px]">{s.value}</dd>
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
        <Reveal className="lg:sticky lg:top-28 lg:self-start">
          <Heading>Advisory by design.</Heading>
          <Lead>Built for people who are accountable for every word on frequency.</Lead>
        </Reveal>
        <Reveal delay={80} className="card px-5 py-1.5 sm:px-6">
          <ul>
            {PRINCIPLES.map((p, i) => (
              <li key={p.title} className={cn('flex gap-4 py-5', i > 0 && 'border-t border-[color:var(--hairline-soft)]')}>
                <span className={cn('flex size-11 shrink-0 items-center justify-center rounded-full', p.tint)}>
                  <p.icon aria-hidden className="size-5" />
                </span>
                <div>
                  <p className="text-[16.5px] font-semibold tracking-[-0.01em]">{p.title}</p>
                  <p className="mt-1 text-[15px] leading-relaxed text-ink-2 text-pretty">{p.body}</p>
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
    <Section className="pb-16 pt-6 md:pb-24 md:pt-10">
      <Reveal className="relative overflow-hidden rounded-[28px] border border-[color:var(--hairline-soft)] bg-surface p-6 shadow-card sm:p-10 md:p-14">
        <div aria-hidden className="absolute inset-y-0 right-0 hidden w-2/5 hatch-data-soft opacity-60 [mask-image:linear-gradient(to_left,black,transparent)] md:block" />
        <LogoMark className="relative size-12" />
        <p className="relative mt-8 max-w-[17ch] text-[38px] font-medium leading-[1.04] tracking-[-0.045em] text-balance md:text-[64px]">
          The controller decides. <span className="text-data">FlowLens remembers.</span>
        </p>
      </Reveal>
    </Section>
  );
}
