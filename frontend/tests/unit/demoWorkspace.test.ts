import { beforeEach, describe, expect, it } from 'vitest';
import type { DemoAnalysis } from '@/api/adapters/demo/client';
import { toExternal } from '@/api/adapters/demo/hybrid';
import { mockControl } from '@/api/adapters/mock/control';
import { MockApiClient } from '@/api/adapters/mock/engine';
import { at } from '@/api/adapters/mock/ids';
import { DEMO_PASSWORD } from '@/api/adapters/mock/seed/accounts';
import { STANDARD_PERMISSIONS, type ScenarioSpec } from '@/api/adapters/mock/seed/spec';
import { useReplay } from '@/features/replay/store';
import { phaseOf, revealedWords, WORD_LAG_MS } from '@/features/workspace/LiveTranscript';

const WID = '0b7e3f8a-4d6c-4e1f-9a2b-1c3d5e7f9a0b';

const SPEC: ScenarioSpec = {
  key: 'demo-fixture',
  title: '',
  context: 'Fixture · ground',
  lifecycle: 'READY',
  analysis: 'COMPLETED',
  durationMs: 60_000,
  recordedAt: '2022-09-10T19:03:13Z',
  updatedAt: '2026-10-11T10:00:00Z',
  sourceLabel: 'Public corpus fixture',
  sourceKind: 'PUBLIC_CORPUS',
  layoutVersion: 'fixture-layout-1',
  channels: [{ index: 0, label: 'Radio', role: 'Mixed' }],
  entities: [{ callsign: 'N1', kind: 'AIRCRAFT', type: 'PA-28', role: 'Taxi', aliases: [] }],
  hasTracks: true,
  hasLayout: true,
  gaps: [],
  permissions: STANDARD_PERMISSIONS,
  retentionDays: 30,
  providerAvailable: false,
  runs: [{ label: '#01', revision: 1, status: 'COMPLETED', createdAt: '2026-10-11T10:00:00Z' }],
  segments: [
    { key: 'T-01', evidence: 'E-01', t: '00:02.0', dur: 2000, ch: 0, text: 'Taxi via Alpha', act: 'INSTRUCTION', role: 'CONTROLLER', entity: 'N1', action: 'TAXI', latency: 900, effects: { instruction: 'ACTIVE' } },
    { key: 'T-02', evidence: 'E-02', t: '00:52.0', dur: 1500, ch: 0, text: 'Via Alpha', act: 'READBACK', role: 'PILOT', entity: 'N1', latency: 900 },
  ],
  movements: [],
  tracks: [
    {
      entity: 'N1',
      footprint: false,
      waypoints: [
        ['00:00.0', 0, 0, 90, 10],
        ['00:20.0', 100, 0, 90, 10],
        ['00:40.0', 200, 0, 0, 5],
      ],
      gaps: [['00:10.0', '00:30.0']],
    },
  ],
  findings: [
    { key: 'F-01', category: 'QUALITY_GAP', priority: 'NOTICE', status: 'OPEN', entity: 'N1', t: '00:04.0', pending: '00:04.0', available: '00:06.0', title: 'Observation is synthetic', statement: 'Fixture.', evidence: ['T-01'], quality: 'AMBIGUOUS', unknowns: [], movement: 'NOT_EVALUABLE' },
  ],
  options: [],
  insufficient: [],
  notices: [],
  speakerIdentity: false,
};

function analysis(cursor = 0): DemoAnalysis {
  return {
    workspace: { id: WID, name: 'My KAGC run', scenario_id: 'demo-fixture', status: 'READY', duration_ms: 60_000, created_at: '', ready_at: '', progress: 1, eta_ms: 0, steps: [], files: [], labels: [], recordings: [], playback_cursor_ms: cursor },
    spec: SPEC,
    live: {
      segments: [
        { key: 'T-01', part: '88', confidence: 0.9, chunk: 'file-chunk-00', chunk_range_ms: [0, 50_000], words: [{ text: 'Taxi', start_ms: 2000, end_ms: 2400 }, { text: 'via', start_ms: 2400, end_ms: 2700 }, { text: 'Alpha', start_ms: 2700, end_ms: 3600 }] },
        { key: 'T-02', part: '88', confidence: 0.8, chunk: 'file-chunk-01', chunk_range_ms: [50_000, 60_000], words: [{ text: 'Via', start_ms: 52_000, end_ms: 52_400 }, { text: 'Alpha', start_ms: 52_400, end_ms: 53_200 }] },
      ],
      speakers: { 'T-01': 'ATC (candidate)' },
      chunk_boundaries_ms: [50_000],
    },
    layout: { version: 'fixture-layout-1', units: 'm', caption: 'Fixture', runways: [], hold_lines: [], taxiways: [], bounds: { min_x: -10, max_x: 300, min_y: -50, max_y: 50 }, focus: { min_x: 0, max_x: 200, min_y: -20, max_y: 20 } },
    peaks: { bucket_ms: 100, values: [0.1, 0.5] },
    labels: ['MOCK', 'PUBLIC_CORPUS audio'],
    attribution: 'Fixture audio',
    stt: { provider: 'cached', run: 'fixture', chunks: 2 },
    adsb: [{ name: 'fixture.csv', label: 'ADS-B', summary: {} }],
    recordings: [{ part: '88', name: '88.wav', offset_ms: 0, duration_ms: 60_000, recorded_at: '2022-09-10T19:03:13Z', audio_url: `/api/demo/workspaces/${WID}/audio/88` }],
    audio_url: `/api/demo/workspaces/${WID}/audio`,
  };
}

async function client() {
  const api = new MockApiClient();
  await api.login('evaluator@flowlens.test', DEMO_PASSWORD);
  return api;
}

describe('DEMO workspace bridge (ADR 0003)', () => {
  beforeEach(() => {
    mockControl.getState().reset();
    mockControl.getState().set({ latencyMs: [0, 0] });
  });

  it('maps backend analysis to live timing: chunk ordinal, final after latency, pending defaults', () => {
    const { spec, extras } = toExternal(analysis(12_000));
    expect(spec.key).toBe(`demo-fixture:${WID}`);
    expect(spec.title).toBe('My KAGC run');
    const [t1, t2] = extras.media.segments;
    expect(t1!.chunk).toBe(0);
    expect(t2!.chunk).toBe(1);
    expect(t1!.final_ms).toBe(at('00:02.0') + 2000 + 900);
    expect(t2!.speaker).toBe('Unknown speaker');
    expect(extras.media.findings[0]).toMatchObject({ key: 'F-01', pending_ms: 4000, available_ms: 6000 });
    expect(extras.media.playback_cursor_ms).toBe(12_000);
  });

  it('registers as a session under the backend UUID with media, layout and real peaks', async () => {
    const api = await client();
    const { spec, extras } = toExternal(analysis());
    api.registerExternal(spec, extras);
    const list = await api.listSessions();
    const row = list.find((s) => s.id === WID)!;
    expect(row).toMatchObject({ origin: 'DEMO_BACKEND', source_kind: 'PUBLIC_CORPUS', title: 'My KAGC run' });
    const detail = await api.getSession(WID);
    expect(detail.media?.audio_url).toContain(WID);
    expect(detail.layout?.focus).toBeDefined();
    expect(detail.manifest.layout_version).toBe('fixture-layout-1');
    const waves = await api.getWaveforms(WID);
    expect(waves[0]!.peaks).toEqual([0.1, 0.5]);
  });

  it('findings stay hidden until available (As-known) — the live view never shows them early', async () => {
    const api = await client();
    const { spec, extras } = toExternal(analysis());
    api.registerExternal(spec, extras);
    const runId = (await api.getSession(WID)).latest_run_id!;
    const scope = { sessionId: WID, runId };
    expect(await api.listFindings(scope, { mode: 'AS_KNOWN', asOfMs: 5000 })).toHaveLength(0);
    expect(await api.listFindings(scope, { mode: 'AS_KNOWN', asOfMs: 6000 })).toHaveLength(1);
  });

  it('a feed coverage gap makes the track stale and freezes it at the last fix; heading comes from data', async () => {
    const api = await client();
    const { spec, extras } = toExternal(analysis());
    api.registerExternal(spec, extras);
    const runId = (await api.getSession(WID)).latest_run_id!;
    const scope = { sessionId: WID, runId };
    const before = await api.getSnapshot(scope, { mode: 'AS_KNOWN', asOfMs: 8000 });
    expect(before.entities[0]!.track_status).toBe('POINT_ONLY');
    expect(before.tracks[0]!.heading_deg).toBe(90);
    const inGap = await api.getSnapshot(scope, { mode: 'AS_KNOWN', asOfMs: 20_000 });
    expect(inGap.entities[0]!.track_status).toBe('STALE');
    expect(inGap.tracks[0]!.x_m).toBe(50); // last reported fix at 10 s
    expect(inGap.tracks[0]!.age_ms).toBe(10_000);
  });

  it('survives a MOCK data reset (external sessions are re-registered)', async () => {
    const api = await client();
    const { spec, extras } = toExternal(analysis());
    api.registerExternal(spec, extras);
    mockControl.getState().set({ resetDataNonce: mockControl.getState().resetDataNonce + 1 });
    expect((await api.listSessions()).some((s) => s.id === WID)).toBe(true);
  });
});

describe('live transcript timing', () => {
  const seg = toExternal(analysis()).extras.media.segments[0]!;

  it('reveals each word shortly after it is spoken, then turns final after the STT latency', () => {
    expect(phaseOf(seg, 1999)).toBe('HIDDEN');
    expect(phaseOf(seg, 2100)).toBe('LISTENING');
    expect(revealedWords(seg, 2400 + WORD_LAG_MS).map((w) => w.text)).toEqual(['Taxi']);
    expect(phaseOf(seg, 2400 + WORD_LAG_MS)).toBe('INTERIM');
    expect(phaseOf(seg, seg.final_ms - 1)).toBe('INTERIM');
    expect(phaseOf(seg, seg.final_ms)).toBe('FINAL');
  });
});

describe('replay clock · listen to a range', () => {
  it('plays from the range start and pauses at its end', () => {
    const r = useReplay.getState();
    r.init('fixture-session', 60_000, 30_000);
    useReplay.getState().playRange({ start: 4000, end: 6000 });
    expect(useReplay.getState()).toMatchObject({ cursor: 4000, status: 'PLAYING', stopAt: 6000 });
    useReplay.getState().tick(1500);
    expect(useReplay.getState().status).toBe('PLAYING');
    useReplay.getState().tick(1000);
    expect(useReplay.getState()).toMatchObject({ cursor: 6000, status: 'PAUSED', stopAt: null });
  });
});
