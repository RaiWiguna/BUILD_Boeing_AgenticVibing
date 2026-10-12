/**
 * Replay time helpers. Session time is relative milliseconds on the replay clock
 * (`session_time_ms`). Wall-clock values are always rendered with an explicit zone.
 */

/** 322000 → "05:22.0" (tenths shown by default). */
export function formatOffset(ms: number, opts: { tenths?: boolean } = {}) {
  const tenths = opts.tenths ?? true;
  const safe = Math.max(0, ms);
  const totalSeconds = Math.floor(safe / 1000);
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  const base = `${h > 0 ? `${h}:` : ''}${String(m).padStart(h > 0 ? 2 : 2, '0')}:${String(s).padStart(2, '0')}`;
  if (!tenths) return base;
  return `${base}.${Math.floor((safe % 1000) / 100)}`;
}

/** 322000 → "05:22" */
export function formatClock(ms: number) {
  return formatOffset(ms, { tenths: false });
}

/** Duration in mm:ss (e.g. 1120000 → "18:40"). */
export function formatDuration(ms: number) {
  return formatOffset(ms, { tenths: false });
}

/** "05:22.0", "5:22", "322", "05:22" → ms. Returns null when not parseable. */
export function parseOffset(input: string): number | null {
  const value = input.trim();
  if (!value) return null;
  const match = /^(?:(\d+):)?(\d{1,2}):(\d{1,2})(?:\.(\d))?$/.exec(value);
  if (match) {
    const [, h, m, s, t] = match;
    const seconds = Number(h ?? 0) * 3600 + Number(m) * 60 + Number(s);
    if (Number(s) > 59) return null;
    return seconds * 1000 + Number(t ?? 0) * 100;
  }
  if (/^\d+(\.\d)?$/.test(value)) return Math.round(Number(value) * 1000);
  return null;
}

/** Relative age "2 s ago", "12 s ago", "3 min ago". */
export function formatAge(ms: number | null | undefined) {
  if (ms == null) return '—';
  if (ms < 1000) return 'now';
  if (ms < 60_000) return `${Math.round(ms / 1000)} s ago`;
  return `${Math.round(ms / 60_000)} min ago`;
}

const dateFmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
const timeFmt = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC', hour12: false });

export function formatDate(iso: string) {
  return dateFmt.format(new Date(iso));
}

export function formatTimeUtc(iso: string) {
  return `${timeFmt.format(new Date(iso))} UTC`;
}

/** Wall-clock UTC of an offset into a recording that started at `startIso`: "19:02:10Z". */
export function formatUtcAt(startIso: string, ms: number) {
  return `${new Date(Date.parse(startIso) + ms).toISOString().slice(11, 19)}Z`;
}

export function formatDateTimeUtc(iso: string) {
  return `${formatDate(iso)}, ${formatTimeUtc(iso)}`;
}

export function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = bytes / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value >= 10 ? value.toFixed(0) : value.toFixed(1)} ${units[i]}`;
}

export function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}
