/**
 * DEMO track (ADR 0003): the hybrid client. Seeded MOCK sessions stay in-browser;
 * workspaces stored by the demo backend are fetched once READY and registered
 * into the MOCK engine under their backend UUID, so Workspace / Memory / Review /
 * Debrief read them through the same port. Workspaces still PROCESSING are listed
 * as preparing. When the backend is offline the MOCK catalogue still works.
 */
import type { ApiClient } from '../../client';
import { useDemoBackend, type DemoWorkspace } from '../../demo';
import { isApiError } from '../../errors';
import type { DemoMedia, SessionDetail, SessionSummary } from '../../types';
import type { ExternalSession, MockApiClient } from '../mock/engine';
import { at, mid } from '../mock/ids';
import type { ScenarioSpec } from '../mock/seed/spec';
import { DEFAULT_LATENCY } from '../mock/world';
import { demoApi, type DemoAnalysis } from './client';

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Backend analysis → ScenarioSpec + media for the engine. Keys are made unique per workspace. */
export function toExternal(a: DemoAnalysis): { spec: ScenarioSpec; extras: ExternalSession } {
  const key = `${a.spec.key}:${a.workspace.id}`;
  const spec: ScenarioSpec = { ...a.spec, key, title: a.workspace.name };
  const segments: DemoMedia['segments'] = a.live.segments.flatMap((live) => {
    const seg = spec.segments.find((s) => s.key === live.key);
    if (!seg) return [];
    const start = at(seg.t);
    const end = start + seg.dur;
    return [
      {
        key: live.key,
        segment_id: mid(`${key}:seg:${live.key}`),
        confidence: live.confidence,
        speaker: a.live.speakers[live.key] ?? 'Unknown speaker',
        // Recogniser chunk ordinal (0-based), from the chunk's start offset.
        chunk: a.live.chunk_boundaries_ms.filter((b) => b <= live.chunk_range_ms[0]).length,
        recording: live.part ?? a.recordings?.[0]?.part ?? '',
        start_ms: start,
        end_ms: end,
        final_ms: end + (seg.latency ?? DEFAULT_LATENCY),
        words: live.words,
      },
    ];
  });
  const findings: DemoMedia['findings'] = spec.findings.map((f) => ({
    finding_id: mid(`${key}:finding:${f.key}`),
    key: f.key,
    title: f.title,
    priority: f.priority,
    pending_ms: at(f.pending ?? f.available),
    available_ms: at(f.available),
  }));
  return {
    spec,
    extras: {
      sessionId: a.workspace.id,
      layout: a.layout,
      peaks: a.peaks,
      media: {
        workspace_id: a.workspace.id,
        audio_url: a.audio_url,
        audio_media_type: 'audio/wav',
        recordings: (a.recordings ?? []).map((r) => ({ part: r.part, name: r.name, url: r.audio_url, offset_ms: r.offset_ms, duration_ms: r.duration_ms, recorded_at: r.recorded_at })),
        labels: a.labels,
        attribution: a.attribution,
        stt_label: `${a.stt.provider} · ${a.stt.run}`,
        segments,
        chunk_boundaries_ms: a.live.chunk_boundaries_ms,
        findings,
        playback_cursor_ms: a.workspace.playback_cursor_ms,
      },
    },
  };
}

/** A workspace still processing on the backend, shown as a preparing session. */
function processingSummary(w: DemoWorkspace): SessionSummary {
  const step = w.steps.find((s) => s.status === 'RUNNING') ?? w.steps.find((s) => s.status === 'PENDING');
  return {
    id: w.id,
    title: w.name,
    context: 'Processing',
    source_kind: 'PUBLIC_CORPUS',
    lifecycle: 'PREPARING',
    duration_ms: w.duration_ms,
    recorded_at: w.created_at,
    updated_at: w.created_at,
    source_ready: false,
    analysis: 'RUNNING',
    domain_validation: 'NOT_DOMAIN_VALIDATED',
    channels: [{ index: 0, label: 'Radio', role: 'Mixed' }],
    has_tracks: true,
    has_layout: true,
    layout_label: null,
    latest_run_id: null,
    latest_run_label: null,
    open_findings: 0,
    notices: [{ id: `${w.id}:processing`, tone: 'data', title: `Processing ${Math.round(w.progress * 100)}%`, detail: step ? step.label : 'Saving session' }],
    origin: 'DEMO_BACKEND',
  };
}

export function createHybridClient(mock: MockApiClient): ApiClient {
  const inflight = new Map<string, Promise<void>>();
  /** ready_at of the analysis registered per workspace; a newer one means it was reprocessed. */
  const registered = new Map<string, string | null>();

  function register(id: string) {
    let p = inflight.get(id);
    if (!p) {
      p = demoApi
        .getAnalysis(id)
        .then((a) => {
          const { spec, extras } = toExternal(a);
          mock.registerExternal(spec, extras);
          registered.set(id, a.workspace.ready_at);
        })
        .finally(() => inflight.delete(id));
      inflight.set(id, p);
    }
    return p;
  }

  async function sync(): Promise<DemoWorkspace[]> {
    try {
      const list = await demoApi.listWorkspaces();
      const processing = list.filter((w) => w.status === 'PROCESSING');
      for (const w of processing) {
        mock.unregisterExternal(w.id);
        registered.delete(w.id);
      }
      await Promise.all(list.filter((w) => w.status === 'READY' && (!mock.hasExternal(w.id) || registered.get(w.id) !== w.ready_at)).map((w) => register(w.id).catch(() => undefined)));
      useDemoBackend.setState({ status: 'ONLINE', processing });
      return processing;
    } catch {
      useDemoBackend.setState({ status: 'OFFLINE', processing: [] });
      return [];
    }
  }

  const overrides: Pick<ApiClient, 'listSessions' | 'getSession'> = {
    async listSessions() {
      const processing = await sync();
      const sessions = await mock.listSessions();
      return [...processing.map(processingSummary), ...sessions];
    },
    async getSession(sessionId: string): Promise<SessionDetail> {
      if (UUID.test(sessionId) && !mock.hasSession(sessionId)) {
        try {
          await register(sessionId);
          useDemoBackend.setState({ status: 'ONLINE' });
        } catch (e) {
          // Unknown to the backend too → fall through to the engine's NOT_FOUND.
          if (!(isApiError(e) && e.code === 'NOT_FOUND')) {
            if (isApiError(e) && e.details.demo_code === 'OFFLINE') useDemoBackend.setState({ status: 'OFFLINE' });
            throw e;
          }
        }
      } else if (mock.hasExternal(sessionId)) {
        // Refresh the saved playback position (best effort).
        try {
          const w = await demoApi.getWorkspace(sessionId);
          if (w.status === 'READY' && registered.has(sessionId) && registered.get(sessionId) !== w.ready_at) await register(sessionId);
          else mock.setExternalCursor(sessionId, w.playback_cursor_ms);
        } catch {
          /* keep the last known position */
        }
      }
      return mock.getSession(sessionId);
    },
  };

  return new Proxy(mock, {
    get(target, prop, receiver) {
      if (prop in overrides) return overrides[prop as keyof typeof overrides];
      const value = Reflect.get(target, prop, receiver);
      return typeof value === 'function' ? value.bind(target) : value;
    },
  }) as unknown as ApiClient;
}

/** Ensure a READY backend workspace is registered (used right after processing finishes). */
export async function registerDemoWorkspace(mock: MockApiClient, id: string) {
  const a = await demoApi.getAnalysis(id);
  const { spec, extras } = toExternal(a);
  mock.registerExternal(spec, extras);
  return a;
}
