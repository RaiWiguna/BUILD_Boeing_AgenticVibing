import { useMemo } from 'react';
import { cn } from '@/lib/utils';

function seeded(seed: string) {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i += 1) h = Math.imul(h ^ seed.charCodeAt(i), 16777619);
  return () => {
    h = Math.imul(h ^ (h >>> 15), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return ((h ^= h >>> 16) >>> 0) / 4294967296;
  };
}

/** Decorative waveform thumbnail (validation preview). Not audio data. */
export function MiniWave({ seed, bars = 64, className, activeRatio = 0.42 }: { seed: string; bars?: number; className?: string; activeRatio?: number }) {
  const heights = useMemo(() => {
    const r = seeded(seed);
    return Array.from({ length: bars }, (_, i) => {
      const env = 0.35 + 0.65 * Math.abs(Math.sin((i / bars) * Math.PI * 3.2 + r()));
      return Math.max(0.12, env * (0.45 + r() * 0.55));
    });
  }, [seed, bars]);
  return (
    <svg aria-hidden viewBox={`0 0 ${bars * 4} 32`} preserveAspectRatio="none" className={cn('h-8 w-full', className)}>
      {heights.map((h, i) => (
        <rect key={i} x={i * 4 + 0.75} y={16 - h * 14} width="2" height={h * 28} rx="1" fill={i / bars < activeRatio ? '#2563eb' : '#b9c7dd'} />
      ))}
    </svg>
  );
}
