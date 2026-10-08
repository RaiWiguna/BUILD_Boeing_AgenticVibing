import type { LayoutView } from '@/api/types';
import { cn } from '@/lib/utils';

/** Small schematic of the fictional layout for previews. Illustrative only — no positions. */
export function LayoutMini({ layout, className, highlight = 'HL-A27' }: { layout: LayoutView; className?: string; highlight?: string }) {
  const { min_x, max_x, min_y, max_y } = layout.bounds;
  const w = max_x - min_x;
  const h = max_y - min_y;
  const sx = (x: number) => ((x - min_x) / w) * 400;
  const sy = (y: number) => ((max_y - y) / h) * 120;
  const rwy = layout.runways[0]!;
  const hl = layout.hold_lines.find((l) => l.id === highlight);
  return (
    <svg viewBox="0 0 400 120" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Fictional layout preview" className={cn('h-full w-full', className)}>
      <rect width="400" height="120" fill="#eef1f5" />
      {layout.taxiways.map((t) => (
        <polyline key={t.id} points={t.path.map(([x, y]) => `${sx(x)},${sy(y)}`).join(' ')} fill="none" stroke="#dbe1e8" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
      ))}
      {layout.taxiways.map((t) => (
        <polyline key={`${t.id}-c`} points={t.path.map(([x, y]) => `${sx(x)},${sy(y)}`).join(' ')} fill="none" stroke="#a9b8cc" strokeWidth="1" strokeDasharray="4 4" />
      ))}
      <polygon points={rwy.polygon.map(([x, y]) => `${sx(x)},${sy(y)}`).join(' ')} fill="#6b7280" />
      <line x1={sx(rwy.centerline[0][0]) + 24} y1={sy(0)} x2={sx(rwy.centerline[1][0]) - 24} y2={sy(0)} stroke="#fff" strokeWidth="1" strokeDasharray="7 6" opacity="0.8" />
      <text x={sx(rwy.centerline[1][0]) - 8} y={sy(0) + 3.5} textAnchor="end" fontSize="9" fontWeight="600" fill="#fff">
        RWY {rwy.ends[1]}
      </text>
      {hl && <polyline points={hl.points.map(([x, y]) => `${sx(x)},${sy(y)}`).join(' ')} stroke="#d63384" strokeWidth="2" />}
      {layout.taxiways.map((t) => (
        <text key={`${t.id}-l`} x={sx(t.label_at[0])} y={sy(t.label_at[1]) - 7} fontSize="8.5" fontWeight="600" fill="#64748b" textAnchor="middle">
          {t.label}
        </text>
      ))}
    </svg>
  );
}
