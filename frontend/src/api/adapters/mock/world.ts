/**
 * MOCK world: pure derivations from a ScenarioSpec into contract-shaped DTOs.
 * This simulates what the backend reducer/rules would return. It lives only in the
 * mock adapter and must be removed when the HTTP adapter is wired (roadmap §1).
 */
import type {
  AnalysisRun,
  Association,
  Evidence,
  EntityInfo,
  EntityStateView,
  Finding,
  GeometryResult,
  Intent,
  MemoryEvent,
  OpenLoop,
  Option,
  ReplayMode,
  RunView,
  SourceEvent,
  SourceManifest,
  TimeRange,
  Track,
  TrackPoint,
  TrackSeries,
  TranscriptSegment,
  WaveformView,
} from '../../types';
import { at, mid, rand, sha } from './ids';
import type { FindingSpec, LoopSpec, OptionSpec, ScenarioSpec, SegmentSpec } from './seed/spec';

export const DEFAULT_LATENCY = 2500;

export interface World {
  spec: ScenarioSpec;
  sessionId: string;
  assetIds: string[];
  entities: (EntityInfo & { initialMovement?: string })[];
  entityByCallsign: Map<string, EntityInfo>;
  runs: RunView[];
  segIds: Map<string, string>;
  evIds: Map<string, string>;
  findingIds: Map<string, string>;
  optionIds: Map<string, string>;
  loopIds: Map<string, string>;
  labels: Record<string, string>;
  manifest: SourceManifest;
}

export function buildWorld(spec: ScenarioSpec): World {
  const sessionId = mid(`session:${spec.key}`);
  const assetIds = spec.channels.map((c) => mid(`${spec.key}:asset:${c.index}`));
  const entities = spec.entities.map((e) => ({ ...e, id: mid(`${spec.key}:entity:${e.callsign}`) }));
  const entityByCallsign = new Map(entities.map((e) => [e.callsign, e]));
  const labels: Record<string, string> = {};
  const segIds = new Map<string, string>();
  const evIds = new Map<string, string>();
  for (const s of spec.segments) {
    const sid = mid(`${spec.key}:seg:${s.key}`);
    const eid = mid(`${spec.key}:ev:${s.key}`);
    segIds.set(s.key, sid);
    evIds.set(s.key, eid);
    labels[sid] = s.key;
    labels[eid] = s.evidence;
  }
  const findingIds = new Map(spec.findings.map((f) => [f.key, mid(`${spec.key}:finding:${f.key}`)]));
  const optionIds = new Map(spec.options.map((o) => [o.key, mid(`${spec.key}:option:${o.key}`)]));
  const loopIds = new Map(spec.loops.map((l) => [l.key, mid(`${spec.key}:loop:${l.key}`)]));
  findingIds.forEach((id, key) => (labels[id] = key));
  optionIds.forEach((id, key) => (labels[id] = key));
  loopIds.forEach((id, key) => (labels[id] = key));
  entities.forEach((e) => (labels[e.id] = e.callsign));

  const runs: RunView[] = spec.runs.map((r, i) => {
    const id = mid(`${spec.key}:run:${r.label}`);
    labels[id] = `Run ${r.label}`;
    const status = r.status === 'NOT_ANALYZED' ? 'QUEUED' : r.status;
    const run: AnalysisRun = {
      id,
      session_id: sessionId,
      analysis_run_id: id,
      revision: r.revision,
      status,
      input_hash: sha(`${spec.key}:input:${r.revision}`),
      config_hash: sha(`${spec.key}:config:${r.label}`),
      model_version: 'MOCK',
      api_version: 'mock-interactions-1',
      sdk_version: 'mock-sdk-1',
      prompt_version: 'prompt-v1',
      reducer_version: 'reducer-v1',
      rule_version: 'lab-1',
      usage: { audio_ms: spec.durationMs, input_tokens: 18_400 + i * 1200, output_tokens: 3_200 + i * 400, latency_ms: 41_000 + i * 3000, cost_microunits: null },
    };
    return {
      run,
      label: r.label,
      input_revision: r.revision,
      created_at: r.createdAt,
      completed_at: r.status === 'COMPLETED' || r.status === 'PARTIAL' ? r.createdAt : null,
      failure: r.status === 'PARTIAL' ? { code: 'PROVIDER_UNAVAILABLE', message: 'Gemini was unavailable after transcription completed.' } : null,
      coverage_note: r.coverageNote ?? null,
    };
  });

  const manifest: SourceManifest = {
    id: mid(`${spec.key}:manifest`),
    session_id: sessionId,
    revision: 1,
    source_kind: 'SYNTHETIC',
    source_label: spec.sourceLabel,
    source_hash: sha(`${spec.key}:manifest`),
    domain_validation: 'NOT_DOMAIN_VALIDATED',
    coordinate_system: spec.hasLayout ? 'FICTIONAL_LOCAL_XY' : 'NONE',
    units: 'm',
    layout_version: spec.hasLayout ? 'fictional-2' : null,
    clock: { offset_ms: 0, timezone: 'UTC', uncertainty_ms: 40, mapping_version: 'clock-1' },
    coverage: {
      audio: true,
      tracks: spec.hasTracks,
      vehicles: spec.hasTracks ? false : null,
      speaker_identity: spec.speakerIdentity,
      quality: spec.gaps.length ? 'AMBIGUOUS' : 'SUPPORTED',
      gaps: spec.gaps,
    },
    permissions: {
      local: spec.permissions.local_read.state === 'ALLOWED',
      cloud: spec.permissions.cloud_audio.state === 'ALLOWED' && spec.permissions.cloud_transcript.state === 'ALLOWED',
      export: spec.permissions.report_export.state === 'ALLOWED',
      audio_export: spec.permissions.audio_export.state === 'ALLOWED',
      basis: 'Synthetic data created for this project (SYNTHETIC).',
      retention_days: spec.retentionDays,
    },
    assets: spec.channels.map((c, i) => ({
      id: assetIds[i]!,
      channels: 1,
      duration_ms: spec.durationMs,
      fixture_path: null,
      media_type: 'audio/flac' as const,
      sample_rate_hz: 16000,
      sha256: sha(`${spec.key}:asset:${c.index}`),
    })),
  };

  return { spec, sessionId, assetIds, entities, entityByCallsign, runs, segIds, evIds, findingIds, optionIds, loopIds, labels, manifest };
}

/* ── Time helpers ──────────────────────────────────────────────────── */

export function segStart(s: SegmentSpec) {
  return at(s.t);
}
export function segEnd(s: SegmentSpec) {
  return at(s.t) + s.dur;
}
export function segAvailable(s: SegmentSpec) {
  return segEnd(s) + (s.latency ?? DEFAULT_LATENCY);
}

/** AS_KNOWN: only information available at as-of. DEBRIEF: events up to as-of, with hindsight. */
export function visible(mode: ReplayMode, asOf: number, eventMs: number, availableMs: number | null) {
  return mode === 'AS_KNOWN' ? (availableMs ?? eventMs) <= asOf : eventMs <= asOf;
}

/* ── Builders ──────────────────────────────────────────────────────── */

export function evidenceFor(w: World, s: SegmentSpec, runId: string | null): Evidence {
  return {
    id: w.evIds.get(s.key)!,
    session_id: w.sessionId,
    analysis_run_id: runId,
    revision: 1,
    kind: 'TRANSCRIPT',
    source_id: w.assetIds[s.ch] ?? w.assetIds[0]!,
    segment_id: w.segIds.get(s.key)!,
    start_ms: segStart(s),
    end_ms: segEnd(s),
    quote: s.text,
    span_start: 0,
    span_end: s.text.length,
    source_hash: w.manifest.assets[s.ch]?.sha256 ?? w.manifest.source_hash,
  };
}

export function segmentFor(w: World, s: SegmentSpec, runId: string | null): TranscriptSegment {
  return {
    id: w.segIds.get(s.key)!,
    session_id: w.sessionId,
    analysis_run_id: runId,
    revision: 1,
    source_id: w.assetIds[s.ch] ?? w.assetIds[0]!,
    channel: s.ch,
    start_ms: segStart(s),
    end_ms: segEnd(s),
    event_time_ms: segStart(s),
    available_time_ms: segAvailable(s),
    recorded_at: w.spec.updatedAt,
    text: s.text,
    origin: 'MOCK',
    confidence: null,
    quality: s.quality ?? 'SUPPORTED',
    provider_profile_version: 'stt-mock-1',
    speaker_id: null,
    supersedes_id: null,
    reason: null,
    evidence: [evidenceFor(w, s, runId)],
  };
}

export function intentFor(w: World, s: SegmentSpec, runId: string | null): Intent {
  const entity = s.entity ? w.entityByCallsign.get(s.entity) : null;
  const ev = w.evIds.get(s.key)!;
  return {
    id: mid(`${w.spec.key}:intent:${s.key}`),
    session_id: w.sessionId,
    analysis_run_id: runId,
    revision: 1,
    segment_ids: [w.segIds.get(s.key)!],
    speech_act: s.act,
    role_candidate: s.role,
    entity_candidates: entity ? [entity.id] : [],
    actions: s.action ? [s.action] : [],
    callsign: { value: s.entity, quality: s.callsignQuality ?? (s.entity ? 'SUPPORTED' : 'MISSING'), evidence_ids: [ev], alternatives: s.assoc?.alternatives?.map((a) => a.split(' · ')[0]!) ?? [], unknowns: s.entity ? [] : ['callsign'] },
    runway: { value: s.runway ?? null, quality: s.runway ? (s.runwayQuality ?? 'SUPPORTED') : 'MISSING', evidence_ids: [ev], alternatives: [], unknowns: s.runway ? [] : ['runway'] },
    condition: null,
    negation: false,
    quality: s.quality ?? 'SUPPORTED',
    unknowns: s.unknowns ?? [],
    alternatives: s.assoc?.alternatives ?? [],
    evidence: [evidenceFor(w, s, runId)],
    event_time_ms: segStart(s),
    available_time_ms: segAvailable(s),
    recorded_at: w.spec.updatedAt,
  };
}

export function associationFor(w: World, s: SegmentSpec, runId: string | null): Association | null {
  if (!s.assoc) return null;
  const entityIds = s.entity ? [w.entityByCallsign.get(s.entity)!.id] : [];
  return {
    id: mid(`${w.spec.key}:assoc:${s.key}`),
    session_id: w.sessionId,
    analysis_run_id: runId,
    revision: 1,
    source_intent_id: mid(`${w.spec.key}:intent:${s.key}`),
    target_intent_id: s.assoc.target ? mid(`${w.spec.key}:intent:${s.assoc.target}`) : null,
    relationship: s.assoc.relationship,
    status: s.assoc.status,
    entity_candidates: entityIds,
    alternatives: s.assoc.alternatives ?? [],
    unknowns: s.assoc.unknowns ?? [],
    evidence: [evidenceFor(w, s, runId)],
    event_time_ms: segStart(s),
    available_time_ms: segAvailable(s),
    recorded_at: w.spec.updatedAt,
  };
}

export function findingFor(w: World, f: FindingSpec, runId: string | null, stale: boolean): Finding {
  const segs = f.evidence.map((k) => w.spec.segments.find((s) => s.key === k)).filter((s): s is SegmentSpec => !!s);
  const evidence = segs.map((s) => evidenceFor(w, s, runId));
  return {
    id: w.findingIds.get(f.key)!,
    session_id: w.sessionId,
    analysis_run_id: runId,
    revision: 1,
    category: f.category,
    statement: f.statement,
    priority: f.priority,
    status: f.status,
    entity_ids: [w.entityByCallsign.get(f.entity)?.id ?? mid(`${w.spec.key}:entity:${f.entity}`)],
    rule_version: 'lab-1',
    model_version: 'MOCK',
    quality: f.quality,
    applicability: 'LAB_ONLY',
    unknowns: f.unknowns,
    stale,
    evidence: evidence.length ? (evidence as [Evidence, ...Evidence[]]) : [evidenceFor(w, w.spec.segments[0]!, runId)],
    event_time_ms: at(f.t),
    available_time_ms: at(f.available),
    recorded_at: w.spec.updatedAt,
  };
}

export function optionFor(w: World, o: OptionSpec, runId: string | null): Option {
  const segs = o.evidence.map((k) => w.spec.segments.find((s) => s.key === k)).filter((s): s is SegmentSpec => !!s);
  return {
    id: w.optionIds.get(o.key)!,
    session_id: w.sessionId,
    analysis_run_id: runId,
    revision: 1,
    as_of_ms: at(o.asOf),
    statement: o.statement,
    rationale: o.rationale,
    preconditions: o.preconditions,
    unknowns: o.unknowns,
    consequences: o.consequences,
    applicability: 'LAB_ONLY',
    review_status: 'UNREVIEWED',
    model_version: 'MOCK',
    prompt_version: 'prompt-v1',
    input_hash: sha(`${w.spec.key}:input:2`),
    evidence: segs.map((s) => evidenceFor(w, s, runId)) as [Evidence, ...Evidence[]],
    event_time_ms: at(o.asOf),
    available_time_ms: at(o.available),
    recorded_at: w.spec.updatedAt,
  };
}

export function loopFor(w: World, l: LoopSpec, runId: string | null, mode: ReplayMode, asOf: number): OpenLoop | null {
  const origin = w.spec.segments.find((s) => s.key === l.origin)!;
  if (!visible(mode, asOf, segStart(origin), segAvailable(origin))) return null;
  const closing = l.closing ? w.spec.segments.find((s) => s.key === l.closing) : undefined;
  const closed = closing && visible(mode, asOf, segStart(closing), segAvailable(closing));
  return {
    id: w.loopIds.get(l.key)!,
    session_id: w.sessionId,
    analysis_run_id: runId,
    revision: 1,
    originating_id: w.segIds.get(l.origin)!,
    entity_ids: [w.entityByCallsign.get(l.entity)!.id],
    kind: l.kind,
    status: closed ? l.status : 'OPEN',
    started_ms: segStart(origin),
    expected_window_ms: l.windowMs,
    coverage_known: l.coverageKnown,
    closing_evidence_ids: closed && closing ? [w.evIds.get(closing.key)!] : [],
    timer_profile_version: 'lab-timer-v1',
    evidence: [evidenceFor(w, origin, runId)],
    event_time_ms: segStart(origin),
    available_time_ms: segAvailable(origin),
    recorded_at: w.spec.updatedAt,
  };
}

/* ── Projections ───────────────────────────────────────────────────── */

export function movementAt(w: World, callsign: string, asOf: number) {
  const list = w.spec.movements.filter((m) => m.entity === callsign && at(m.from) <= asOf);
  return list[list.length - 1] ?? null;
}

function interp(points: [string, number, number][], t: number): { x: number; y: number; moving: boolean } | null {
  if (!points.length) return null;
  const first = points[0]!;
  if (t < at(first[0])) return null;
  for (let i = 0; i < points.length - 1; i += 1) {
    const a = points[i]!;
    const b = points[i + 1]!;
    const ta = at(a[0]);
    const tb = at(b[0]);
    if (t >= ta && t <= tb) {
      const k = tb === ta ? 0 : (t - ta) / (tb - ta);
      return { x: a[1] + (b[1] - a[1]) * k, y: a[2] + (b[2] - a[2]) * k, moving: a[1] !== b[1] || a[2] !== b[2] };
    }
  }
  const last = points[points.length - 1]!;
  return { x: last[1], y: last[2], moving: false };
}

export function trackStatus(w: World, callsign: string, asOf: number, forceStale: boolean): EntityStateView['track_status'] {
  const spec = w.spec.tracks.find((t) => t.entity === callsign);
  if (!spec) return 'MISSING';
  if (forceStale) return 'STALE';
  const first = at(spec.waypoints[0]![0]);
  if (asOf < first) return 'MISSING';
  if (spec.staleAfter && asOf > at(spec.staleAfter)) return 'STALE';
  return spec.footprint ? 'FRESH' : 'POINT_ONLY';
}

export function sourceAge(w: World, callsign: string, asOf: number, forceStale: boolean) {
  const spec = w.spec.tracks.find((t) => t.entity === callsign);
  if (!spec || asOf < at(spec.waypoints[0]![0])) return null;
  if (forceStale) return 38_000;
  const last = at(spec.waypoints[spec.waypoints.length - 1]![0]);
  if (asOf > last + 10_000) return 12_000;
  return 1000 + Math.floor(rand(`${callsign}:${Math.floor(asOf / 1000)}`) * 2) * 1000;
}

export function seriesFor(w: World, asOf: number, forceStale: boolean): TrackSeries[] {
  return w.spec.tracks.flatMap((spec) => {
    const entity = w.entityByCallsign.get(spec.entity);
    if (!entity) return [];
    const points: TrackPoint[] = [];
    const end = forceStale ? Math.min(asOf, asOf - 38_000) : asOf;
    for (let t = at(spec.waypoints[0]![0]); t <= end; t += 2000) {
      const p = interp(spec.waypoints, t);
      if (p) points.push({ t, x: p.x, y: p.y });
    }
    const cur = interp(spec.waypoints, end);
    if (cur && points.length && points[points.length - 1]!.t !== end) points.push({ t: end, x: cur.x, y: cur.y });
    const predicted: TrackPoint[] = (spec.predicted ?? [])
      .filter(([c]) => Math.abs(at(c) - asOf) < 40_000 || at(c) > asOf)
      .filter(() => !forceStale)
      .map(([c, x, y]) => ({ t: at(c), x, y }));
    const keepPredicted = cur && predicted.length && asOf >= at(spec.predicted![0]![0]) - 6000 && asOf <= at(spec.predicted![spec.predicted!.length - 1]![0]);
    return [{ entity_id: entity.id, footprint: spec.footprint, stale_after_ms: forceStale ? asOf - 38_000 : spec.staleAfter ? at(spec.staleAfter) : null, points, predicted: keepPredicted && cur ? [{ t: asOf, x: cur.x, y: cur.y }, ...predicted.slice(1)] : [] }];
  });
}

export function tracksFor(w: World, runId: string | null, asOf: number, forceStale: boolean): Track[] {
  return w.spec.tracks.flatMap((spec) => {
    const entity = w.entityByCallsign.get(spec.entity);
    const t = forceStale ? asOf - 38_000 : asOf;
    const p = interp(spec.waypoints, t);
    if (!entity || !p) return [];
    return [
      {
        id: mid(`${w.spec.key}:track:${spec.entity}:${Math.floor(t / 1000)}`),
        session_id: w.sessionId,
        analysis_run_id: runId,
        revision: 1,
        entity_id: entity.id,
        source_id: w.assetIds[0]!,
        source_event_id: `trk-${spec.entity}-${Math.floor(t / 1000)}`,
        source_hash: sha(`${w.spec.key}:tracks`),
        kind: 'TRACK',
        x_m: Math.round(p.x),
        y_m: Math.round(p.y),
        heading_deg: 270,
        speed_mps: p.moving ? 8 : 0,
        length_m: entity.kind === 'VEHICLE' ? 5 : 38,
        width_m: entity.kind === 'VEHICLE' ? 2 : 35,
        age_ms: forceStale ? 38_000 : 1000,
        layout_version: 'fictional-2',
        quality: spec.footprint ? 'SUPPORTED' : 'AMBIGUOUS',
        statement: spec.footprint ? 'Observed position with footprint' : 'Observed centre point only; footprint not available',
        event_time_ms: t,
        available_time_ms: t + 400,
        recorded_at: w.spec.updatedAt,
      },
    ];
  });
}

export function geometryFor(w: World, runId: string | null, asOf: number, forceStale: boolean): GeometryResult[] {
  return w.entities.map((e) => {
    const status = trackStatus(w, e.callsign, asOf, forceStale);
    const mv = movementAt(w, e.callsign, asOf);
    const evaluable = status === 'FRESH';
    const reason = evaluable
      ? null
      : status === 'POINT_ONLY'
        ? 'Footprint not available (centre point only)'
        : status === 'STALE'
          ? 'Track stale (age 38 s); last movement status is not carried forward'
          : (mv?.reason ?? 'No position data');
    return {
      session_id: w.sessionId,
      analysis_run_id: runId,
      revision: 1,
      entity_id: e.id,
      status: evaluable ? 'EVALUATED' : 'NOT_EVALUABLE',
      occupied: evaluable ? false : null,
      intervals: [],
      layout_version: w.spec.hasLayout ? 'fictional-2' : null,
      rule_version: 'lab-1',
      reason,
      uncertainty_ms: evaluable ? 400 : null,
      evidence: [],
    };
  });
}

export function entityStates(w: World, mode: ReplayMode, asOf: number, forceStale: boolean, reviewerOf: (callsign: string) => EntityStateView['reviewer']): EntityStateView[] {
  return w.entities.map((e) => {
    const segs = w.spec.segments.filter((s) => s.entity === e.callsign && s.effects && visible(mode, asOf, segStart(s), segAvailable(s)));
    let instruction: EntityStateView['instruction'] = { state: 'UNKNOWN', summary: null, quote: null, evidence_id: null };
    let readback: EntityStateView['readback'] = { state: 'NOT_OBSERVED', summary: null, quote: null, evidence_id: null };
    let interpretation: EntityStateView['interpretation'] = 'CANDIDATE';
    for (const s of segs) {
      const fx = s.effects!;
      if (fx.instruction) instruction = { state: fx.instruction, summary: fx.instructionSummary ?? instruction.summary, quote: s.act === 'INSTRUCTION' ? s.text : instruction.quote, evidence_id: s.act === 'INSTRUCTION' ? w.evIds.get(s.key)! : instruction.evidence_id };
      if (fx.readback) readback = { state: fx.readback, summary: fx.readbackSummary ?? null, quote: s.act === 'INSTRUCTION' ? null : s.text, evidence_id: s.act === 'INSTRUCTION' ? null : w.evIds.get(s.key)! };
      interpretation = fx.interpretation ?? (s.quality === 'AMBIGUOUS' ? 'AMBIGUOUS' : 'SUPPORTED');
    }
    const status = trackStatus(w, e.callsign, asOf, forceStale);
    const mv = movementAt(w, e.callsign, asOf);
    let movement: EntityStateView['movement'] = mv ? { state: mv.state, summary: mv.summary, reason: mv.reason } : { state: 'UNKNOWN', summary: 'Unknown', reason: null };
    if (status === 'STALE') movement = { state: 'NOT_EVALUABLE', summary: 'NOT_EVALUABLE', reason: 'Track stale (age 38 s)' };
    if (status === 'MISSING' && w.spec.hasTracks && w.spec.tracks.some((t) => t.entity === e.callsign)) movement = { state: 'NOT_EVALUABLE', summary: 'NOT_EVALUABLE', reason: 'No position yet at this as-of' };
    return {
      entity_id: e.id,
      instruction,
      readback,
      movement,
      interpretation: segs.length ? interpretation : 'CANDIDATE',
      reviewer: reviewerOf(e.callsign),
      source_age_ms: sourceAge(w, e.callsign, asOf, forceStale),
      track_status: status,
    };
  });
}

export function memoryEvents(w: World, runId: string | null, mode: ReplayMode, asOf: number, forceStale: boolean): MemoryEvent[] {
  const out: MemoryEvent[] = [];
  const running = new Map<string, { instruction: MemoryEvent['instruction']; readback: MemoryEvent['readback'] }>();
  for (const s of w.spec.segments) {
    if (!s.entity || !s.effects || !visible(mode, asOf, segStart(s), segAvailable(s))) continue;
    const entity = w.entityByCallsign.get(s.entity)!;
    const prev = running.get(s.entity) ?? { instruction: 'UNKNOWN', readback: 'NOT_OBSERVED' };
    const next = { instruction: s.effects.instruction ?? prev.instruction, readback: s.effects.readback ?? prev.readback };
    running.set(s.entity, next);
    const status = trackStatus(w, s.entity, segStart(s), forceStale);
    const mv = movementAt(w, s.entity, segStart(s));
    out.push({
      id: mid(`${w.spec.key}:mem:${s.key}`),
      session_id: w.sessionId,
      analysis_run_id: runId,
      revision: 1,
      entity_id: entity.id,
      intent_id: mid(`${w.spec.key}:intent:${s.key}`),
      interpretation: s.quality === 'AMBIGUOUS' ? 'AMBIGUOUS' : 'SUPPORTED',
      instruction: next.instruction,
      readback: next.readback,
      movement: status === 'STALE' ? 'NOT_EVALUABLE' : (mv?.state ?? 'UNKNOWN'),
      reviewer: 'UNREVIEWED',
      dependency_hashes: [sha(`${w.spec.key}:dep:${s.key}`)],
      reducer_version: 'reducer-v1',
      evidence: [evidenceFor(w, s, runId)],
      event_time_ms: segStart(s),
      available_time_ms: segAvailable(s),
      recorded_at: w.spec.updatedAt,
    });
  }
  return out;
}

export function sourceEvents(w: World, runId: string | null, mode: ReplayMode, asOf: number): SourceEvent[] {
  const events: SourceEvent[] = w.spec.gaps.map((g, i) => ({
    id: mid(`${w.spec.key}:srcev:gap:${i}`),
    session_id: w.sessionId,
    analysis_run_id: runId,
    revision: 1,
    source_id: w.assetIds[0]!,
    source_event_id: `gap-${i + 1}`,
    source_hash: w.manifest.source_hash,
    kind: 'QUALITY',
    entity_id: null,
    statement: `Audio gap ${Math.round((g.end_ms - g.start_ms) / 1000)} s on all channels`,
    quality: 'MISSING',
    event_time_ms: g.start_ms,
    available_time_ms: g.end_ms,
    recorded_at: w.spec.updatedAt,
  }));
  for (const f of w.spec.findings) {
    if (f.sourceAlert?.status === 'PRESENT') {
      events.push({
        id: mid(`${w.spec.key}:srcev:alert:${f.key}`),
        session_id: w.sessionId,
        analysis_run_id: runId,
        revision: 1,
        source_id: w.assetIds[0]!,
        source_event_id: `alert-${f.key}`,
        source_hash: w.manifest.source_hash,
        kind: 'ALERT',
        entity_id: w.entityByCallsign.get(f.entity)?.id ?? null,
        statement: f.sourceAlert.severity ?? 'Source alert',
        quality: 'SUPPORTED',
        event_time_ms: at(f.t),
        available_time_ms: at(f.t) + 500,
        recorded_at: w.spec.updatedAt,
      });
    }
  }
  return events.filter((e) => visible(mode, asOf, e.event_time_ms, e.available_time_ms));
}

/** Deterministic waveform peaks (visual-only replay; no audio is loaded). */
export function waveformsFor(w: World): WaveformView[] {
  const bucket = 250;
  const n = Math.ceil(w.spec.durationMs / bucket);
  return w.spec.channels.map((c) => {
    const peaks: number[] = [];
    for (let i = 0; i < n; i += 1) {
      const t = i * bucket;
      const inGap = w.spec.gaps.some((g) => t >= g.start_ms && t < g.end_ms);
      if (inGap) {
        peaks.push(0);
        continue;
      }
      const seg = w.spec.segments.find((s) => s.ch === c.index && t >= segStart(s) && t < segEnd(s));
      const r = rand(`${w.spec.key}:${c.index}:${i}`);
      if (seg) {
        const phase = (t - segStart(seg)) / seg.dur;
        const env = Math.sin(Math.PI * Math.min(1, Math.max(0, phase))) ** 0.6;
        peaks.push(0.35 + env * (0.45 + r * 0.2));
      } else {
        peaks.push(0.04 + r * 0.07);
      }
    }
    return { channel: c.index, label: c.label, bucket_ms: bucket, peaks };
  });
}

export function gapsFor(w: World): TimeRange[] {
  return w.spec.gaps;
}
