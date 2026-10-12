/**
 * DEMO track (ADR 0003): HTTP client for the local demo backend (`/api/demo`,
 * proxied by Vite to the Compose API). It is not the G-BE contract adapter: it
 * stores named workspaces, runs the processing schedule and serves the prepared
 * scenario. Session screens keep reading through the MOCK engine.
 */
import { ApiError } from '../../errors';
import type { DemoHealth, DemoPort, DemoScenarios, DemoWorkspace, PlacedFile } from '../../demo';
import type { LayoutView } from '../../types';
import type { ScenarioSpec } from '../mock/seed/spec';

export const DEMO_BASE = '/api/demo';

export interface DemoAnalysis {
  workspace: DemoWorkspace;
  spec: ScenarioSpec;
  live: {
    segments: { key: string; part: string; confidence: number | null; words: { text: string; start_ms: number; end_ms: number }[]; chunk: string; chunk_range_ms: [number, number] }[];
    speakers: Record<string, string>;
    chunk_boundaries_ms: number[];
  };
  layout: LayoutView | null;
  peaks: { bucket_ms: number; values: number[] } | null;
  labels: string[];
  attribution: string;
  stt: { provider: string; run: string; chunks: number };
  adsb: { name: string; label: string; summary: Record<string, unknown> }[];
  recordings: { part: string; name: string; offset_ms: number; duration_ms: number; recorded_at: string; audio_url: string }[];
  audio_url: string;
}


interface ErrorBody {
  code?: string;
  message?: string;
  recovery?: string | null;
  details?: Record<string, unknown>;
}

/** Map a demo backend error body onto the app's typed ApiError. */
function toApiError(status: number, body: ErrorBody | null): ApiError {
  const message = body?.message ?? `Server returned HTTP ${status}.`;
  const details = { ...(body?.details ?? {}), demo_code: body?.code ?? null, http_status: status };
  const opts = { recovery: body?.recovery ?? undefined, details };
  if (status === 404) return new ApiError('NOT_FOUND', message, opts);
  if (status === 409) return new ApiError('VERSION_CONFLICT', message, opts);
  if (status === 413 || status === 422 || status === 400) return new ApiError('INVALID_IMPORT', message, opts);
  return new ApiError('PROVIDER_UNAVAILABLE', message, { ...opts, recovery: opts.recovery ?? 'Try again.' });
}

function offline(): ApiError {
  return new ApiError('PROVIDER_UNAVAILABLE', 'Server not reachable.', {
    recovery: 'Start the server, then retry.',
    details: { demo_code: 'OFFLINE' },
  });
}

function parseJson(text: string): unknown {
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return null;
  }
}

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = 4000): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${DEMO_BASE}${path}`, { ...init, signal: ctrl.signal, headers: { Accept: 'application/json', ...(init.headers ?? {}) } });
  } catch {
    throw offline();
  } finally {
    clearTimeout(timer);
  }
  const text = await res.text();
  const body = parseJson(text);
  // The Vite proxy answers 502/504 with HTML when the API container is down.
  if (res.status === 502 || res.status === 503 || res.status === 504) throw offline();
  if (!res.ok) throw toApiError(res.status, body as ErrorBody | null);
  return body as T;
}

export const demoApi: Omit<DemoPort, 'registerWorkspace' | 'rememberPlayback'> & { getAnalysis(id: string): Promise<DemoAnalysis> } = {
  health: () => request<DemoHealth>('/health', {}, 1500),
  scenarios: () => request<DemoScenarios>('/scenarios', {}, 2500),
  listWorkspaces: () => request<DemoWorkspace[]>('/workspaces', {}, 2500),
  getWorkspace: (id: string) => request<DemoWorkspace>(`/workspaces/${encodeURIComponent(id)}`),
  getAnalysis: (id: string) => request<DemoAnalysis>(`/workspaces/${encodeURIComponent(id)}/analysis`, {}, 8000),
  savePlayback: (id: string, cursorMs: number) =>
    request<{ cursor_ms: number }>(`/workspaces/${encodeURIComponent(id)}/playback`, {
      method: 'PUT',
      body: JSON.stringify({ cursor_ms: Math.max(0, Math.round(cursorMs)) }),
      headers: { 'Content-Type': 'application/json' },
    }),

  createWorkspace: (name: string, files: PlacedFile[], onProgress: (loaded: number, total: number) => void, signal?: AbortSignal) => send('/workspaces', 201, { name }, files, onProgress, signal),
};

/** Multipart upload with byte progress (fetch cannot report upload progress). */
function send(path: string, ok: number, fields: Record<string, string>, files: PlacedFile[], onProgress: (loaded: number, total: number) => void, signal?: AbortSignal): Promise<DemoWorkspace> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    for (const [k, v] of Object.entries(fields)) form.append(k, v);
    form.append('positions', JSON.stringify(Object.fromEntries(files.map((f) => [f.file.name, f.position]))));
    for (const f of files) form.append('files', f.file, f.file.name);
    xhr.open('POST', `${DEMO_BASE}${path}`);
    xhr.setRequestHeader('Accept', 'application/json');
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded, e.total);
    };
    xhr.onerror = () => reject(offline());
    xhr.onabort = () => reject(new ApiError('VERSION_CONFLICT', 'Upload cancelled.', { details: { demo_code: 'CANCELLED' } }));
    xhr.onload = () => {
      const body = parseJson(xhr.responseText);
      if (xhr.status === ok) resolve(body as DemoWorkspace);
      else if (xhr.status >= 502 && xhr.status <= 504) reject(offline());
      else reject(toApiError(xhr.status, body as ErrorBody | null));
    };
    signal?.addEventListener('abort', () => xhr.abort());
    xhr.send(form);
  });
}
