import { CircleDashed, CircleHelp, Radio } from 'lucide-react';
import { useMemo } from 'react';
import type { EntityInfo, EntityStateView, LayoutView, Track, TrackSeries, WorkspaceSnapshot } from '@/api/types';
import { useElementSize } from '@/hooks/useElementSize';
import { formatClock } from '@/lib/time';
import { cn } from '@/lib/utils';

type Pt = [number, number];

const PAD = { l: 34, r: 34, t: 30, b: 30 };
const TRAIL_MS = 120_000;

/** Rounded polyline: corners are replaced with quadratic curves (schematic taxiways). */
function roundedPath(input: Pt[], radius = 22) {
  // A stationary object repeats its position; zero-length segments would divide by zero.
  const points = input.filter((p, i) => i === 0 || p[0] !== input[i - 1]![0] || p[1] !== input[i - 1]![1]);
  if (points.length < 2) return '';
  const [first] = points;
  let d = `M${first![0]},${first![1]}`;
  for (let i = 1; i < points.length - 1; i++) {
    const [px, py] = points[i - 1]!;
    const [cx, cy] = points[i]!;
    const [nx, ny] = points[i + 1]!;
    const d1 = Math.hypot(cx - px, cy - py);
    const d2 = Math.hypot(nx - cx, ny - cy);
    const r = Math.min(radius, d1 / 2, d2 / 2);
    const ax = cx - ((cx - px) / d1) * r;
    const ay = cy - ((cy - py) / d1) * r;
    const bx = cx + ((nx - cx) / d2) * r;
    const by = cy + ((ny - cy) / d2) * r;
    d += ` L${ax},${ay} Q${cx},${cy} ${bx},${by}`;
  }
  const last = points[points.length - 1]!;
  return `${d} L${last[0]},${last[1]}`;
}

/** Top-down aircraft glyph pointing north in a 24×24 box. */
const PLANE = 'M12 1.6c.9 0 1.5 1 1.5 2.4v5.1l7.8 4.5c.4.2.6.6.6 1v1.1l-8.4-2.4v4.6l2.3 1.7v1.4L12 20.1l-3.8 1.1v-1.4l2.3-1.7v-4.6l-8.4 2.4v-1.1c0-.4.2-.8.6-1l7.8-4.5V4c0-1.4.6-2.4 1.5-2.4Z';

function useProjection(layout: LayoutView | null, width: number, height: number) {
  return useMemo(() => {
    if (!layout || !width || !height) return null;
    if (layout.focus) {
      // Airport layout (DEMO): equal scale on both axes, framed on the focus window.
      const f = layout.focus;
      const bw = f.max_x - f.min_x;
      const bh = f.max_y - f.min_y;
      const k = Math.min((width - PAD.l - PAD.r) / bw, (height - PAD.t - PAD.b) / bh);
      const ox = PAD.l + (width - PAD.l - PAD.r - bw * k) / 2;
      const oy = PAD.t + (height - PAD.t - PAD.b - bh * k) / 2;
      const px = (x: number) => ox + (x - f.min_x) * k;
      const py = (y: number) => oy + (f.max_y - y) * k;
      return { px, py, kx: k, ky: k, geo: true, p: (pt: Pt): Pt => [px(pt[0]), py(pt[1])] };
    }
    const b = layout.bounds;
    // Fit vertically to the drawn content (taxiways, hold lines, runway), not the full bounds.
    const ys = [...layout.taxiways.flatMap((t) => t.path.map((p) => p[1])), ...layout.hold_lines.flatMap((h) => h.points.map((p) => p[1])), ...layout.runways.flatMap((r) => r.polygon.map((p) => p[1]))];
    const top = Math.min(b.max_y, Math.max(...ys) + 50);
    const bottom = Math.max(b.min_y, Math.min(...ys) - 40);
    const bw = b.max_x - b.min_x;
    const bh = top - bottom;
    const kx = (width - PAD.l - PAD.r) / bw;
    // Schematic: vertical scale may stretch up to 2× so hold lines read clearly.
    const ky = Math.min((height - PAD.t - PAD.b) / bh, kx * 2);
    const oy = PAD.t + (height - PAD.t - PAD.b - bh * ky) / 2;
    const px = (x: number) => PAD.l + (x - b.min_x) * kx;
    const py = (y: number) => oy + (top - y) * ky;
    return { px, py, kx, ky, geo: false, p: (pt: Pt): Pt => [px(pt[0]), py(pt[1])] };
  }, [layout, width, height]);
}

export interface CanvasEntity {
  info: EntityInfo;
  state: EntityStateView | undefined;
  series: TrackSeries | undefined;
  track: Track | undefined;
}

/**
 * Situation canvas (comp 03). Fictional layout in metres, observed trail solid,
 * prediction dashed, footprint vs centre-point distinguished, stale tracks faded,
 * missing positions listed — never invented.
 */
export function SituationCanvas({
  layout,
  snapshot,
  entities,
  selected,
  onSelect,
  asOf,
  className,
}: {
  layout: LayoutView | null;
  snapshot: WorkspaceSnapshot | undefined;
  entities: EntityInfo[];
  selected: string | null;
  onSelect: (id: string) => void;
  asOf: number;
  className?: string;
}) {
  const [ref, size] = useElementSize<HTMLDivElement>();
  const proj = useProjection(layout, size.width, size.height);

  const objects: CanvasEntity[] = useMemo(
    () =>
      entities.map((info) => ({
        info,
        state: snapshot?.entities.find((e) => e.entity_id === info.id),
        series: snapshot?.series.find((s) => s.entity_id === info.id),
        track: snapshot?.tracks.find((t) => t.entity_id === info.id),
      })),
    [entities, snapshot],
  );
  const missing = objects.filter((o) => o.state?.track_status === 'MISSING' || (!o.series?.points.length && o.state));
  const inGap = snapshot?.gaps.find((g) => asOf >= g.start_ms && asOf <= g.end_ms);

  if (!layout) {
    return (
      <div className={cn('relative flex min-h-[260px] flex-col items-center justify-center overflow-hidden rounded-[18px] bg-sunken px-6 text-center', className)}>
        <div aria-hidden className="absolute inset-0 opacity-60 [background:repeating-linear-gradient(135deg,transparent_0_9px,rgba(120,130,145,0.08)_9px_10px)]" />
        <span className="relative inline-flex size-12 items-center justify-center rounded-full bg-surface text-ink-2 shadow-control">
          <Radio aria-hidden className="size-[22px]" />
        </span>
        <p className="relative mt-4 text-[16px] font-semibold text-ink">Audio-only session</p>
        <p className="relative mt-1 max-w-[440px] text-[14px] text-ink-2">No layout or position data was imported. The situation is limited to what was said and heard; movement stays NOT_EVALUABLE.</p>
      </div>
    );
  }

  return (
    <div ref={ref} className={cn('relative h-[300px] overflow-hidden rounded-[18px] bg-[#f2f4f7] 2xl:h-[330px]', className)}>
      {proj && (
        <svg width={size.width} height={size.height} className="absolute inset-0 select-none" role="img" aria-labelledby="situation-title situation-desc">
          <title id="situation-title">Situation at {formatClock(asOf)}</title>
          <desc id="situation-desc">
            {objects
              .map((o) => {
                const st = o.state?.track_status;
                return `${o.info.callsign}: ${st === 'MISSING' || !st ? 'position not available' : st === 'POINT_ONLY' ? 'centre point only, footprint not available' : st === 'STALE' ? 'stale position' : 'observed position with footprint'}`;
              })
              .join('. ')}
          </desc>
          <defs>
            <pattern id="sit-dots" width="18" height="18" patternUnits="userSpaceOnUse">
              <circle cx="1.5" cy="1.5" r="1" fill="#dde2e8" />
            </pattern>
            <pattern id="sit-hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="8" height="8" fill="#f6f1e6" />
              <line x1="0" y1="0" x2="0" y2="8" stroke="#e8d9b8" strokeWidth="3" />
            </pattern>
            <linearGradient id="sit-rwy" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor="#7b818b" />
              <stop offset="1" stopColor="#686e78" />
            </linearGradient>
          </defs>
          <rect width={size.width} height={size.height} fill="url(#sit-dots)" />
          {proj.geo ? <AirportLayout layout={layout} proj={proj} /> : <Layout layout={layout} proj={proj} />}
          {objects.map((o) => (
            <Trail key={`trail-${o.info.id}`} o={o} proj={proj} asOf={asOf} selected={o.info.id === selected} />
          ))}
          {objects.map((o) => (
            <Marker key={`m-${o.info.id}`} o={o} proj={proj} width={size.width} selected={o.info.id === selected} onSelect={onSelect} />
          ))}
        </svg>
      )}

      {missing.length > 0 && (
        <div className="absolute right-3 top-3 flex max-w-[60%] flex-col items-end gap-1.5">
          {missing.map((o) => (
            <button
              key={o.info.id}
              type="button"
              onClick={() => onSelect(o.info.id)}
              className={cn('inline-flex items-center gap-1.5 rounded-[10px] border border-hairline bg-surface/95 px-2.5 py-1.5 text-[12.5px] text-ink-2 shadow-control backdrop-blur transition-colors hover:text-ink', selected === o.info.id && 'border-data/40 ring-2 ring-data/15')}
            >
              <CircleHelp aria-hidden className="size-3.5 text-ink-3" />
              <span className="font-semibold text-ink">{o.info.callsign}</span>· Position not available
            </button>
          ))}
        </div>
      )}
      {inGap && (
        <div role="status" className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded-[10px] border border-notice-soft bg-notice-tint px-2.5 py-1.5 text-[12.5px] font-medium text-notice">
          <CircleDashed aria-hidden className="size-3.5" /> Audio gap {formatClock(inGap.start_ms)}–{formatClock(inGap.end_ms)} · no source coverage
        </div>
      )}
      <p className={cn('pointer-events-none absolute bottom-2.5 right-3.5 text-[12px] text-ink-3', layout.focus && 'max-w-[55%] truncate text-right')} title={layout.caption}>
        {layout.caption}
      </p>
    </div>
  );
}

type Projection = NonNullable<ReturnType<typeof useProjection>>;

function Layout({ layout, proj }: { layout: LayoutView; proj: Projection }) {
  const rwy = layout.runways[0]!;
  const x0 = proj.px(rwy.centerline[0][0]);
  const x1 = proj.px(rwy.centerline[1][0]);
  const cy = proj.py(rwy.centerline[0][1]);
  const half = Math.max(15, ((rwy.polygon[2]![1] - rwy.polygon[0]![1]) / 2) * proj.ky);
  return (
    <g>
      {/* taxiways: edge, surface, centreline */}
      {layout.taxiways.map((t) => {
        const d = roundedPath(t.path.map(proj.p), 28);
        return (
          <g key={t.id}>
            <path d={d} fill="none" stroke="#d9dee5" strokeWidth={22} strokeLinecap="round" strokeLinejoin="round" />
            <path d={d} fill="none" stroke="#e8ebf0" strokeWidth={19} strokeLinecap="round" strokeLinejoin="round" />
            <path d={d} fill="none" stroke="#c9b67a" strokeOpacity={0.55} strokeWidth={1} strokeDasharray="6 6" />
          </g>
        );
      })}
      {/* runway */}
      <rect x={x0} y={cy - half} width={x1 - x0} height={half * 2} rx={4} fill="url(#sit-rwy)" />
      <line x1={x0 + 58} x2={x1 - 58} y1={cy} y2={cy} stroke="#fff" strokeOpacity={0.85} strokeWidth={1.6} strokeDasharray="14 10" />
      {[0, 1].map((i) => (
        <g key={i}>
          {Array.from({ length: 4 }, (_, k) => (
            <rect key={k} x={i === 0 ? x0 + 6 : x1 - 14} y={cy - half + 4 + k * ((half * 2 - 8) / 4)} width={8} height={(half * 2 - 8) / 4 - 3} rx={1} fill="#fff" opacity={0.75} />
          ))}
          <text x={i === 0 ? x0 + 22 : x1 - 22} y={cy + 6} textAnchor={i === 0 ? 'start' : 'end'} fontSize={17} fontWeight={600} fill="#fff" letterSpacing="0.02em">
            {rwy.ends[i]}
          </text>
        </g>
      ))}
      {/* hold lines */}
      {layout.hold_lines.map((h) => {
        const pts = h.points.map(proj.p);
        const [a, b] = [pts[0]!, pts[pts.length - 1]!];
        const highlight = h.runway === rwy.id && h.id.endsWith('27');
        const stroke = highlight ? '#d63384' : '#e0a21a';
        const mid = (a[0] + b[0]) / 2;
        // The relevant hold line gets a callout above the runway (comp 03); others a side label.
        const above = cy - half - 34;
        return (
          <g key={h.id}>
            {highlight && <line x1={mid} x2={mid} y1={above + 8} y2={cy + half} stroke={stroke} strokeWidth={1.4} strokeDasharray="3 3" />}
            <line x1={a[0] - 4} y1={a[1]} x2={b[0] + 4} y2={b[1]} stroke={stroke} strokeWidth={2.6} strokeLinecap="round" />
            {highlight && <circle cx={mid} cy={cy} r={3.2} fill={stroke} stroke="#fff" strokeWidth={1.2} />}
            {highlight ? (
              <text x={mid} y={above - 12} textAnchor="middle" fontSize={12} fontWeight={600} fill="#191b20">
                <tspan x={mid}>Hold line</tspan>
                <tspan x={mid} dy={14}>
                  RWY {h.label.replace(/.*RWY\s*/, '')}
                </tspan>
              </text>
            ) : (
              <text x={b[0] + 10} y={a[1] + 4} fontSize={11.5} fontWeight={600} fill="#96610b">
                {h.label}
              </text>
            )}
          </g>
        );
      })}
      {layout.taxiways.map((t) => (
        <text key={`${t.id}-l`} x={proj.px(t.label_at[0])} y={proj.py(t.label_at[1]) + 22} textAnchor="middle" fontSize={11.5} fontWeight={600} fill="#7a8494" letterSpacing="0.04em">
          {t.label}
        </text>
      ))}
    </g>
  );
}

/** True-geometry airport layout (DEMO): every runway as its polygon, taxiways to scale. */
function AirportLayout({ layout, proj }: { layout: LayoutView; proj: Projection }) {
  const taxiW = Math.max(7, 18 * proj.kx);
  return (
    <g>
      {layout.taxiways.map((t) => {
        const d = roundedPath(t.path.map(proj.p), 14);
        return (
          <g key={t.id}>
            <path d={d} fill="none" stroke="#d9dee5" strokeWidth={taxiW + 3} strokeLinecap="round" strokeLinejoin="round" />
            <path d={d} fill="none" stroke="#e8ebf0" strokeWidth={taxiW} strokeLinecap="round" strokeLinejoin="round" />
            <path d={d} fill="none" stroke="#c9b67a" strokeOpacity={0.6} strokeWidth={1} strokeDasharray="6 6" />
          </g>
        );
      })}
      {layout.runways.map((r) => {
        const poly = r.polygon.map(proj.p);
        const [a, b] = r.centerline.map(proj.p) as [Pt, Pt];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
        const ux = (b[0] - a[0]) / len;
        const uy = (b[1] - a[1]) / len;
        const angle = (Math.atan2(uy, ux) * 180) / Math.PI;
        const inset = Math.min(46, len / 6);
        return (
          <g key={r.id}>
            <polygon points={poly.map((pt) => pt.join(',')).join(' ')} fill="url(#sit-rwy)" stroke="#5d636c" strokeWidth={0.6} />
            <line x1={a[0] + ux * inset} y1={a[1] + uy * inset} x2={b[0] - ux * inset} y2={b[1] - uy * inset} stroke="#fff" strokeOpacity={0.85} strokeWidth={1.2} strokeDasharray="10 8" />
            {[0, 1].map((i) => {
              const [x, y] = i === 0 ? [a[0] + ux * 18, a[1] + uy * 18] : [b[0] - ux * 18, b[1] - uy * 18];
              const rot = i === 0 ? angle + 90 : angle - 90;
              return (
                <text key={i} x={x} y={y} transform={`rotate(${rot} ${x} ${y})`} textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={700} fill="#fff">
                  {r.ends[i]}
                </text>
              );
            })}
          </g>
        );
      })}
      {layout.taxiways.map((t) => (
        <text key={`${t.id}-l`} x={proj.px(t.label_at[0])} y={proj.py(t.label_at[1])} textAnchor="middle" fontSize={11} fontWeight={600} fill="#7a8494" letterSpacing="0.04em">
          {t.label}
        </text>
      ))}
    </g>
  );
}

/** Split a trail where the feed reported nothing for more than 5 s (coverage gap). */
function splitOnGaps<T extends { t: number }>(points: T[], maxGapMs = 5000) {
  const out: T[][] = [];
  for (const p of points) {
    const cur = out[out.length - 1];
    if (cur && p.t - cur[cur.length - 1]!.t <= maxGapMs) cur.push(p);
    else out.push([p]);
  }
  return out;
}

function Trail({ o, proj, asOf, selected }: { o: CanvasEntity; proj: Projection; asOf: number; selected: boolean }) {
  const s = o.series;
  if (!s || !s.points.length) return null;
  const stale = o.state?.track_status === 'STALE';
  const pts = s.points.filter((p) => p.t >= asOf - TRAIL_MS && p.t <= asOf);
  const color = selected ? '#2563eb' : '#5b84e0';
  const runs = splitOnGaps(pts).map((run) => run.map((p) => proj.p([p.x, p.y])));
  const predicted = s.predicted.map((p) => proj.p([p.x, p.y]));
  const beads = pts.filter((p, i) => i > 0 && i < pts.length - 1 && Math.round(p.t / 1000) % 30 === 0);
  return (
    <g opacity={stale ? 0.4 : selected ? 1 : 0.75}>
      {runs.map((observed, i) => observed.length > 1 && <path key={i} d={roundedPath(observed, 10)} fill="none" stroke={color} strokeWidth={selected ? 2.6 : 2} strokeLinecap="round" strokeLinejoin="round" />)}
      {!stale && predicted.length > 1 && <path d={roundedPath(predicted, 10)} fill="none" stroke={color} strokeWidth={1.6} strokeDasharray="5 5" strokeLinecap="round" />}
      {!stale && predicted.length > 1 && <circle cx={predicted[predicted.length - 1]![0]} cy={predicted[predicted.length - 1]![1]} r={4} fill="#fff" stroke={color} strokeWidth={1.6} />}
      {beads.map((p) => {
        const [x, y] = proj.p([p.x, p.y]);
        return <circle key={p.t} cx={x} cy={y} r={3.2} fill={color} stroke="#fff" strokeWidth={1.4} />;
      })}
    </g>
  );
}

function Marker({ o, proj, width, selected, onSelect }: { o: CanvasEntity; proj: Projection; width: number; selected: boolean; onSelect: (id: string) => void }) {
  const last = o.series?.points[o.series.points.length - 1];
  if (!last) return null;
  const [x, y] = proj.p([last.x, last.y]);
  const status = o.state?.track_status ?? 'FRESH';
  const stale = status === 'STALE';
  const pointOnly = status === 'POINT_ONLY' || !o.series?.footprint;
  const heading = o.track?.heading_deg ?? 0;
  const color = selected ? '#2563eb' : '#1f2937';
  const label = o.info.callsign;
  const tagW = label.length * 7.6 + 22 + (stale ? 44 : 0);
  const flip = x + 18 + tagW > width - 12;
  const tx = flip ? x - 18 - tagW : x + 18;
  const ty = y + 8;
  const describe = `${label}, ${pointOnly ? 'centre point only — footprint not available' : 'observed position with footprint'}${stale ? ', stale' : ''}. Select to show its memory.`;
  const len = Math.max(20, (o.track?.length_m ?? 38) * proj.kx * 1.4);
  const wid = Math.max(18, (o.track?.width_m ?? 35) * proj.ky * 1.1);
  return (
    <g
      role="button"
      tabIndex={0}
      aria-label={describe}
      aria-pressed={selected}
      className="cursor-pointer outline-none [&:focus-visible_.focus-ring]:opacity-100"
      onClick={() => onSelect(o.info.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(o.info.id);
        }
      }}
      opacity={stale ? 0.5 : 1}
    >
      <circle className="focus-ring opacity-0" cx={x} cy={y} r={22} fill="none" stroke="#2563eb" strokeWidth={2} />
      {pointOnly ? (
        <>
          <circle cx={x} cy={y} r={13} fill="#2563eb" fillOpacity={0.06} stroke={color} strokeOpacity={0.55} strokeWidth={1.2} strokeDasharray="3 3" />
          <g transform={`translate(${x - 9} ${y - 9}) rotate(${heading} 9 9) scale(${18 / 24})`}>
            <path d={PLANE} fill="#fff" stroke={color} strokeWidth={1.5} strokeLinejoin="round" />
          </g>
          <circle cx={x} cy={y} r={1.8} fill={color} />
        </>
      ) : (
        <>
          <rect x={x - len / 2} y={y - wid / 2} width={len} height={wid} rx={5} transform={`rotate(${heading + 90} ${x} ${y})`} fill="#2563eb" fillOpacity={selected ? 0.14 : 0.08} stroke="#2563eb" strokeOpacity={0.35} strokeWidth={1} />
          <g transform={`translate(${x - 12} ${y - 12}) rotate(${heading} 12 12)`}>
            <path d={o.info.kind === 'VEHICLE' ? 'M6 4h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z' : PLANE} fill={color} />
          </g>
        </>
      )}
      <g>
        <rect x={tx} y={ty - 12} width={tagW} height={24} rx={7} fill={selected ? '#2563eb' : '#fff'} stroke={selected ? '#2563eb' : '#dfe3e8'} />
        <text x={tx + 11} y={ty + 4.5} fontSize={12.5} fontWeight={650} fill={selected ? '#fff' : '#191b20'} letterSpacing="0.01em">
          {label}
          {stale && (
            <tspan fontWeight={500} fill={selected ? '#dbe6ff' : '#96610b'}>
              {' '}
              · stale
            </tspan>
          )}
        </text>
      </g>
    </g>
  );
}

/** Legend for the canvas header. */
export function SituationLegend() {
  return (
    <ul className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-[13px] text-ink-2" aria-label="Legend">
      <li className="flex items-center gap-2">
        <svg aria-hidden width="26" height="6">
          <line x1="1" y1="3" x2="25" y2="3" stroke="#2563eb" strokeWidth="2.4" strokeLinecap="round" />
        </svg>
        Observed
      </li>
      <li className="flex items-center gap-2">
        <svg aria-hidden width="26" height="6">
          <line x1="1" y1="3" x2="25" y2="3" stroke="#2563eb" strokeWidth="1.8" strokeDasharray="5 4" />
        </svg>
        Predicted
      </li>
      <li className="flex items-center gap-2">
        <svg aria-hidden width="16" height="16">
          <circle cx="8" cy="8" r="6.5" fill="none" stroke="#596273" strokeWidth="1.2" strokeDasharray="2.5 2.5" />
          <circle cx="8" cy="8" r="1.6" fill="#596273" />
        </svg>
        Centre point
      </li>
      <li className="flex items-center gap-2">
        <CircleHelp aria-hidden className="size-4 text-ink-3" />
        Missing
      </li>
    </ul>
  );
}
