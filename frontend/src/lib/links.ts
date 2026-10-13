/** Sign-in route. The public landing page at `/` never links here; it is reached directly. */
export const LOGIN_PATH = '/login-flow';

/**
 * Single source for links between session screens. Every link keeps the run and
 * the lens the user chose, so neither changes without an explicit action.
 */
export type SessionArea =
  | 'workspace'
  | 'memory'
  | 'memory/runway'
  | `memory/${string}`
  | 'review/transcript'
  | 'review/findings'
  | 'review/options'
  | 'debrief'
  | 'metrics'
  | 'ask';

/** URL value of the lens: `debrief` (full session) or `as-known` (what was known at `t`). */
export type LensParam = 'debrief' | 'as-known';

export interface LinkFocus {
  finding?: string;
  segment?: string;
  option?: string;
  evidence?: string;
  selected?: string;
  brief?: string;
}

export interface LinkScope {
  sid: string;
  run?: string | null;
  lens?: LensParam | null;
  t?: number | null;
  focus?: LinkFocus;
}

/** Areas that read the whole session by default (decision D-1). */
export const FULL_SESSION_AREAS = ['review', 'debrief', 'metrics', 'ask'] as const;
export type LensArea = 'replay' | 'analysis';

export function lensAreaOf(pathname: string): LensArea {
  const area = /^\/s\/[^/]+\/([^/?]+)/.exec(pathname)?.[1] ?? '';
  return (FULL_SESSION_AREAS as readonly string[]).includes(area) ? 'analysis' : 'replay';
}

/** Session area of a `/s/{sid}/...` path; object memory pages collapse to `memory`. */
export function areaFromPath(pathname: string) {
  return /^\/s\/[^/]+\/(.+)$/.exec(pathname)?.[1]?.replace(/^memory\/(?!runway).+/, 'memory') ?? 'workspace';
}

export function parseLens(value: string | null): LensParam | null {
  return value === 'debrief' || value === 'as-known' ? value : null;
}

export function sessionHref(area: SessionArea, { sid, run, lens, t, focus }: LinkScope) {
  const q = new URLSearchParams();
  if (run) q.set('run', run);
  if (lens) q.set('mode', lens);
  if (t != null) q.set('t', String(Math.round(t)));
  for (const [k, v] of Object.entries(focus ?? {})) if (v) q.set(k, v);
  const s = q.toString();
  return `/s/${sid}/${area}${s ? `?${s}` : ''}`;
}

/** Scope (run · lens · t) carried from the current URL — never selection or evidence. */
export function scopeFromParams(params: URLSearchParams): Omit<LinkScope, 'sid' | 'focus'> {
  const t = params.get('t');
  return { run: params.get('run'), lens: parseLens(params.get('mode')), t: t != null && t !== '' && !Number.isNaN(Number(t)) ? Number(t) : null };
}
