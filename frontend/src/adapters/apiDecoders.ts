import { ApiRequestError, type Decoder } from '../api'
import type {
  ApiAssistMessageWire,
  ApiEvidenceRefWire,
  ApiEvidenceResolutionWire,
  ApiEventPageWire,
  ApiEventWire,
  ApiHighlightWire,
  ApiLayoutWire,
  ApiOptionWire,
  ApiPredictionWire,
  ApiReviewAnnotationWire,
  ApiReviewReceiptWire,
  ApiScenarioWire,
  ApiSnapshotWire,
  ApiTrackWire,
  ApiTranscriptPageWire,
  ApiTranscriptSegmentWire,
  ApiTranscriptionJobWire,
  ApiWebSocketMessageWire,
  JsonValue,
} from '../contracts/apiWire'
import type {
  BackendHealth,
  AssistHighlightReadModel,
  CandidateReadModel,
  EventPageReadModel,
  EventReadModel,
  EvidenceResolution,
  OperatorAccess,
  ReplayFrameReadModel,
  ReplaySnapshotReadModel,
  ReviewAnnotationReadModel,
  ScenarioReadModel,
  SessionReadModel,
  SnapshotReadModel,
  TranscriptReadModel,
  TranscriptionJobReadModel,
} from '../contracts/replayReview'

type UnknownRecord = Record<string, unknown>

export const decodeHealth: Decoder<BackendHealth> = (value) => {
  const item = object(value, 'health')
  const mode = string(item.mode, 'health.mode')
  if (string(item.status, 'health.status') !== 'ok') fail('unsupported_profile', 'Backend health is not ok.')
  const singleWriter = boolean(item.single_writer, 'health.single_writer')
  return { state: 'online', version: string(item.version, 'health.version'), mode, single_writer: singleWriter }
}

export function decodeScenario(value: unknown): ScenarioReadModel {
  const item = decodeScenarioWire(value)
  return {
    id: item.id,
    title: item.title,
    objective: item.objective,
    version: item.version,
    duration_s: item.duration_s,
    domain_review: item.domain_review,
    ...(item.aircraft_count === undefined ? {} : { aircraft_count: item.aircraft_count }),
    ...(item.vehicle_count === undefined ? {} : { vehicle_count: item.vehicle_count }),
  }
}

export const decodeScenarioList: Decoder<ScenarioReadModel[]> = (value) => {
  const item = object(value, 'scenario collection')
  return array(item.items, 'scenarios.items').map(decodeScenario)
}

export function decodeOperatorAccess(value: unknown): OperatorAccess {
  const item = object(value, 'operator access')
  return {
    token: string(item.token, 'auth.token'),
    expires_in_s: nonnegativeNumber(item.expires_in_s, 'auth.expires_in_s'),
  }
}

export function decodeSession(value: unknown): SessionReadModel {
  const item = object(value, 'session')
  if (item.scenario === undefined) fail('unsupported_profile', 'Session metadata does not include a public scenario projection.')
  const createdUtc = item.created_utc === undefined || item.created_utc === null
    ? null
    : Math.round(finiteNumber(item.created_utc, 'session.created_utc') * 1000)
  const kind = item.kind === 'training' || item.kind === 'review' ? item.kind : 'unknown'
  return {
    id: string(item.id, 'session.id'),
    status: optionalString(item.status) ?? 'READY',
    scenario: decodeScenario(item.scenario),
    condition: string(item.condition, 'session.condition'),
    seed: nonnegativeNumber(item.seed, 'session.seed'),
    kind,
    created_utc_ms: createdUtc,
  }
}

export const decodeSessionList: Decoder<SessionReadModel[]> = (value) => {
  const item = object(value, 'session collection')
  return array(item.items, 'sessions.items').map(decodeSession)
}

export function decodeApiSnapshot(value: unknown): ApiSnapshotWire {
  const item = object(value, 'snapshot')
  const metadata = object(item.metadata, 'snapshot.metadata')
  const seat = object(item.seat, 'snapshot.seat')
  const kind = literal(item.kind, ['training', 'review'], 'snapshot.kind')
  const role = literal(seat.role, ['instructor', 'tower', 'ground', 'observer'], 'snapshot.seat.role')
  const trackRows = array(item.tracks, 'snapshot.tracks')
  const alertRows = array(item.alerts, 'snapshot.alerts')
  const eventRows = array(item.events, 'snapshot.events')
  const assessmentRows = array(item.assessments, 'snapshot.assessments')
  const parent = metadata.parent === undefined || metadata.parent === null
    ? metadata.parent
    : decodeParent(metadata.parent)
  const sourceSessionId = optionalString(item.source_session_id)
  const reviewAnnotations = item.review_annotations === undefined
    ? undefined
    : array(item.review_annotations, 'snapshot.review_annotations').map((row, index) => jsonObject(row, `snapshot.review_annotations[${index}]`))

  return {
    session_id: string(item.session_id, 'snapshot.session_id'),
    kind,
    sequence: nonnegativeInteger(item.sequence, 'snapshot.sequence'),
    sim_ms: nonnegativeInteger(item.sim_ms, 'snapshot.sim_ms'),
    revision: nonnegativeInteger(item.revision, 'snapshot.revision'),
    status: string(item.status, 'snapshot.status'),
    speed: nonnegativeNumber(item.speed, 'snapshot.speed'),
    metadata: {
      id: string(metadata.id, 'snapshot.metadata.id'),
      scenario: decodeScenarioWire(metadata.scenario),
      condition: string(metadata.condition, 'snapshot.metadata.condition'),
      seed: nonnegativeInteger(metadata.seed, 'snapshot.metadata.seed'),
      config: jsonObject(metadata.config, 'snapshot.metadata.config'),
      engine_version: string(metadata.engine_version, 'snapshot.metadata.engine_version'),
      ...(optionalString(metadata.config_version) === undefined ? {} : { config_version: optionalString(metadata.config_version) }),
      ...(optionalString(metadata.kind) === undefined ? {} : { kind: optionalString(metadata.kind) }),
      ...(parent === undefined ? {} : { parent }),
      ...(metadata.created_utc === undefined ? {} : { created_utc: finiteNumber(metadata.created_utc, 'snapshot.metadata.created_utc') }),
    },
    layout: decodeLayout(item.layout),
    tracks: trackRows.map((row, index) => decodeTrack(row, `snapshot.tracks[${index}]`)),
    clearances: array(item.clearances, 'snapshot.clearances').map((row, index) => decodeClearance(row, `snapshot.clearances[${index}]`)),
    requests: array(item.requests, 'snapshot.requests').map((row, index) => decodeRequest(row, `snapshot.requests[${index}]`)),
    predictions: array(item.predictions, 'snapshot.predictions').map((row, index) => decodePrediction(row, `snapshot.predictions[${index}]`)),
    runway: decodeRunway(item.runway),
    alerts: alertRows.map((row, index) => decodeAlert(row, `snapshot.alerts[${index}]`)),
    events: eventRows.map((row, index) => decodeEvent(row, `snapshot.events[${index}]`)),
    acknowledgements: array(item.acknowledgements, 'snapshot.acknowledgements').map((row, index) => decodeAcknowledgement(row, `snapshot.acknowledgements[${index}]`)),
    assessments: assessmentRows.map((row, index) => decodeEvent(row, `snapshot.assessments[${index}]`)),
    complexity: decodeComplexity(item.complexity),
    error: nullableString(item.error, 'snapshot.error'),
    seat: { role, label: string(seat.label, 'snapshot.seat.label') },
    server_sent_utc_ms: nonnegativeInteger(item.server_sent_utc_ms, 'snapshot.server_sent_utc_ms'),
    ...(sourceSessionId === undefined ? {} : { source_session_id: sourceSessionId }),
    ...(item.review_end_ms === undefined ? {} : { review_end_ms: nonnegativeInteger(item.review_end_ms, 'snapshot.review_end_ms') }),
    ...(item.playback_ms === undefined ? {} : { playback_ms: nonnegativeInteger(item.playback_ms, 'snapshot.playback_ms') }),
    ...(reviewAnnotations === undefined ? {} : { review_annotations: reviewAnnotations }),
  }
}

export function toSnapshotReadModel(snapshot: ApiSnapshotWire): SnapshotReadModel {
  return {
    session_id: snapshot.session_id,
    sim_ms: snapshot.sim_ms,
    sequence: snapshot.sequence,
    revision: snapshot.revision,
    status: snapshot.status,
    speed: snapshot.speed,
    kind: snapshot.kind,
    seed: snapshot.metadata.seed,
    scenario: {
      id: snapshot.metadata.scenario.id,
      title: snapshot.metadata.scenario.title,
      objective: snapshot.metadata.scenario.objective,
      version: snapshot.metadata.scenario.version,
      duration_s: snapshot.metadata.scenario.duration_s,
      domain_review: snapshot.metadata.scenario.domain_review,
      ...(snapshot.metadata.scenario.aircraft_count === undefined ? {} : { aircraft_count: snapshot.metadata.scenario.aircraft_count }),
      ...(snapshot.metadata.scenario.vehicle_count === undefined ? {} : { vehicle_count: snapshot.metadata.scenario.vehicle_count }),
    },
    scenario_title: snapshot.metadata.scenario.title,
    condition: snapshot.metadata.condition,
    track_count: snapshot.tracks.length,
    alert_count: snapshot.alerts.length,
    event_count: snapshot.events.length,
    runway_state: snapshot.runway.state,
    data_quality: snapshot.runway.data_quality,
  }
}

export function toReplaySnapshotReadModel(snapshot: ApiSnapshotWire): ReplaySnapshotReadModel {
  const sourceSessionId = snapshot.source_session_id ?? snapshot.metadata.id
  return {
    session_id: snapshot.session_id,
    source_session_id: sourceSessionId,
    kind: snapshot.kind,
    sequence: snapshot.sequence,
    sim_ms: snapshot.sim_ms,
    playback_ms: snapshot.playback_ms ?? null,
    ...(snapshot.review_end_ms === undefined ? {} : { review_end_ms: snapshot.review_end_ms }),
    revision: snapshot.revision,
    status: snapshot.status,
    speed: snapshot.speed,
    scenario_id: snapshot.metadata.scenario.id,
    scenario_title: snapshot.metadata.scenario.title,
    condition: snapshot.metadata.condition,
    source_version: snapshot.metadata.engine_version,
    config_version: snapshot.metadata.config_version ?? null,
    viewer_role: snapshot.seat.role,
    viewer_label: snapshot.seat.label,
    layout: snapshot.layout,
    tracks: snapshot.tracks,
    clearances: snapshot.clearances,
    predictions: snapshot.predictions,
    alerts: snapshot.alerts.map(({ id, rule, objects, severity, reason, status, created_ms, calculated_ms, updated_ms, data_degraded, metrics, evidence_event_ids, track_ages_ms, assumptions }) => ({
      id, rule, objects, severity, reason, status, created_ms, calculated_ms,
      ...(updated_ms === undefined ? {} : { updated_ms }), data_degraded, metrics, evidence_event_ids, track_ages_ms, assumptions,
    })),
    runway: snapshot.runway,
    acknowledgements: snapshot.acknowledgements,
    review_annotations: (snapshot.review_annotations ?? []).map(toSnapshotReviewAnnotation),
    events: snapshot.events.map(toEventReadModel),
    event_count: snapshot.events.length,
    track_count: snapshot.tracks.length,
    alert_count: snapshot.alerts.length,
  }
}

export const decodeApiEventPage: Decoder<ApiEventPageWire> = (value) => {
  const item = object(value, 'event page')
  const items = array(item.items, 'events.items').map((row, index) => decodeEvent(row, `events.items[${index}]`))
  const nextCursor = nonnegativeInteger(item.next_cursor, 'events.next_cursor')
  for (let index = 1; index < items.length; index += 1) {
    if (items[index].ordinal <= items[index - 1].ordinal) fail('unsupported_profile', 'Event page ordinals are not strictly increasing.')
  }
  if (items.length > 0 && nextCursor < items[items.length - 1].ordinal) fail('unsupported_profile', 'Event cursor precedes an item in its page.')
  return { items, next_cursor: nextCursor }
}

export function toEventPageReadModel(page: ApiEventPageWire): EventPageReadModel {
  const items = page.items.map(toEventReadModel)
  return { items, next_cursor: page.next_cursor, state: items.length ? 'ready' : 'empty' }
}

export function decodeEventReadModel(value: unknown): EventReadModel {
  return toEventReadModel(decodeEvent(value, 'event'))
}

export function decodeReplayFrame(value: unknown, expectedSourceId?: string, requestedMs?: number): ReplayFrameReadModel {
  const item = object(value, 'replay frame')
  if (item.snapshot !== undefined) {
    const snapshot = decodeApiSnapshot(item.snapshot)
    const sourceId = string(item.source_session_id, 'frame.source_session_id')
    const requestTime = nonnegativeInteger(item.requested_ms, 'frame.requested_ms')
    const frameTime = nonnegativeInteger(item.frame_ms, 'frame.frame_ms')
    if (expectedSourceId !== undefined && sourceId !== expectedSourceId) fail('unsupported_profile', 'Frame source does not match the requested source.')
    if (requestedMs !== undefined && requestTime !== requestedMs) fail('unsupported_profile', 'Frame request time does not match the requested time.')
    if (snapshot.sim_ms !== frameTime) fail('unsupported_profile', 'Frame timestamp does not match its embedded snapshot.')
    if (frameTime > requestTime) fail('unsupported_profile', 'Historical frame is later than its requested time.')
    return {
      source_session_id: sourceId,
      requested_ms: requestTime,
      frame_ms: frameTime,
      track_count: snapshot.tracks.length,
      alert_count: snapshot.alerts.length,
      quality: qualityFromDataQuality(snapshot.runway.data_quality),
      state: 'ready',
      snapshot: toReplaySnapshotReadModel(snapshot),
    }
  }

  // The additive historical-frame DTO is decoded for mocks; the current backend has no route for it.
  const sourceId = string(item.source_session_id, 'frame.source_session_id')
  const requestTime = nonnegativeInteger(item.requested_ms, 'frame.requested_ms')
  const frameTime = nonnegativeInteger(item.frame_ms, 'frame.frame_ms')
  const tracks = array(item.tracks, 'frame.tracks').map((row, index) => decodeTrack(row, `frame.tracks[${index}]`))
  const alerts = array(item.alerts, 'frame.alerts').map((row, index) => decodeAlert(row, `frame.alerts[${index}]`))
  const quality = literal(item.quality, ['known', 'degraded', 'unknown'], 'frame.quality')
  if (expectedSourceId !== undefined && sourceId !== expectedSourceId) fail('unsupported_profile', 'Frame source does not match the requested source.')
  if (requestedMs !== undefined && requestTime !== requestedMs) fail('unsupported_profile', 'Frame request time does not match the requested time.')
  if (frameTime > requestTime) fail('unsupported_profile', 'Historical frame is later than its requested time.')
  return { source_session_id: sourceId, requested_ms: requestTime, frame_ms: frameTime, track_count: tracks.length, alert_count: alerts.length, quality, state: 'ready' }
}

export const decodeTranscriptPage: Decoder<ApiTranscriptPageWire> = (value) => {
  const item = object(value, 'transcript page')
  assertAllowedKeys(item, ['items', 'next_cursor', 'job'], 'transcript page')
  return {
    items: array(item.items, 'transcripts.items').map((row, index) => decodeTranscriptSegment(row, `transcripts.items[${index}]`)),
    next_cursor: nullableString(item.next_cursor, 'transcripts.next_cursor'),
    ...(item.job === undefined ? {} : { job: decodeJob(item.job) }),
  }
}

export function toTranscriptReadModel(page: ApiTranscriptPageWire): TranscriptReadModel {
  const items = page.items.map((item) => ({
    id: item.id,
    asset_id: item.asset_id,
    start_ms: item.start_ms,
    end_ms: item.end_ms,
    timebase: 'audio-relative' as const,
    alignment_state: item.session_start_ms == null ? 'unknown' as const : 'mapped' as const,
    channel_id: item.channel_id,
    speaker_label: item.speaker_label,
    speaker_source: item.speaker_source,
    speaker_confidence: item.speaker_confidence,
    text: item.text,
    ...(item.raw_text === undefined ? {} : { raw_text: item.raw_text }),
    language: item.language,
    asr_confidence: item.asr_confidence,
    model_version: item.model_version,
    correction_status: item.correction_status,
    revision: item.revision ?? null,
    ...(item.session_start_ms === undefined ? {} : { session_start_ms: item.session_start_ms }),
    ...(item.session_start_ms == null ? {} : { session_end_ms: item.session_start_ms + (item.end_ms - item.start_ms) }),
  }))
  return {
    state: items.length ? 'ready' : 'empty',
    items,
    ...(items.some((item) => item.session_start_ms == null)
      ? { message: 'One or more transcript segments have no source-to-session mapping and remain audio-relative.' }
      : {}),
    next_cursor: page.next_cursor,
    ...(page.job === undefined ? {} : { job: toJobReadModel(page.job) }),
  }
}

export function decodeEvidenceResolution(value: unknown): ApiEvidenceResolutionWire {
  const item = object(value, 'evidence resolution')
  assertAllowedKeys(item, ['ref', 'state', 'summary', 'item'], 'evidence resolution')
  const state = literal(item.state, ['resolved', 'unresolved'], 'evidence.state')
  const ref = decodeEvidenceRef(item.ref)
  const result: ApiEvidenceResolutionWire = { ref, state }
  const summary = optionalString(item.summary)
  if (summary !== undefined) result.summary = summary
  if (item.item !== undefined) result.item = jsonValue(item.item, 'evidence.item')
  if (state === 'resolved' && item.item === undefined && summary === undefined) fail('unsupported_profile', 'Resolved evidence has no public item or summary.')
  return result
}

export function toEvidenceResolution(value: ApiEvidenceResolutionWire): EvidenceResolution {
  const context = evidenceContext(value)
  return {
    ref: value.ref,
    state: value.state,
    ...(value.summary === undefined ? {} : { summary: value.summary }),
    ...(context ? { context } : {}),
  }
}

export function decodeEvidenceResolutions(value: unknown): EvidenceResolution[] {
  if (Array.isArray(value)) return value.map((item) => toEvidenceResolution(decodeEvidenceResolution(item)))
  const collection = object(value, 'evidence collection')
  assertAllowedKeys(collection, ['items', 'unresolved'], 'evidence collection')
  const resolvedRows = array(collection.items, 'evidence.items').map((item) => toEvidenceResolution(decodeEvidenceResolution(item)))
  const unresolvedRows = (collection.unresolved === undefined ? [] : array(collection.unresolved, 'evidence.unresolved')).map((item) => {
    if (isRecord(item) && 'state' in item) return toEvidenceResolution(decodeEvidenceResolution(item))
    return { ref: decodeEvidenceRef(item), state: 'unresolved' as const }
  })
  return [...resolvedRows, ...unresolvedRows]
}

function evidenceContext(value: ApiEvidenceResolutionWire): EvidenceResolution['context'] | undefined {
  if (value.item === undefined || value.item === null || Array.isArray(value.item) || typeof value.item !== 'object') return undefined
  const item = value.item as Record<string, JsonValue>
  if (value.ref.kind === 'session_event') {
    const at = typeof item.received_ms === 'number' ? item.received_ms : item.sim_ms
    return typeof at === 'number' && Number.isSafeInteger(at) && at >= 0 ? { timebase: 'session', at_ms: at } : undefined
  }
  if (value.ref.kind === 'detector_alert') {
    const at = typeof item.calculated_ms === 'number' ? item.calculated_ms : item.created_ms
    return typeof at === 'number' && Number.isSafeInteger(at) && at >= 0 ? { timebase: 'session', at_ms: at } : undefined
  }
  if (typeof item.session_start_ms === 'number' && Number.isSafeInteger(item.session_start_ms) && item.session_start_ms >= 0) {
    return { timebase: 'session', at_ms: item.session_start_ms }
  }
  if (typeof item.start_ms === 'number' && Number.isSafeInteger(item.start_ms) && item.start_ms >= 0 && typeof item.asset_id === 'string') {
    return { timebase: 'audio-relative', asset_id: item.asset_id, at_ms: item.start_ms }
  }
  return { timebase: 'unknown', reason: 'Evidence item did not supply a session or audio-relative time.' }
}

export const decodeHighlightPage: Decoder<AssistHighlightReadModel[]> = (value) => {
  const item = object(value, 'highlight collection')
  assertAllowedKeys(item, ['items'], 'highlight collection')
  return array(item.items, 'highlights.items').map((row) => {
    const highlight = decodeHighlight(row)
    return {
      id: highlight.id,
      revision: highlight.revision ?? null,
      category: highlight.category,
      review_priority: highlight.review_priority,
      statement: highlight.statement,
      transcript_segment_ids: highlight.transcript_segment_ids,
      session_event_ids: highlight.session_event_ids,
      uncertainty: highlight.uncertainty,
      provider_version: highlight.provider_version,
      rule_version: highlight.rule_version,
      status: highlight.status,
      ...(highlight.linked_alert_id === undefined ? {} : { linked_alert_id: highlight.linked_alert_id }),
      ...(highlight.link_status === undefined ? {} : { link_status: highlight.link_status }),
    }
  })
}

export function decodeJob(value: unknown): ApiTranscriptionJobWire {
  const item = object(value, 'transcription job')
  assertAllowedKeys(item, ['id', 'asset_id', 'status', 'provider', 'model', 'version', 'language', 'started_utc', 'finished_utc', 'error', 'chunk_progress'], 'transcription job')
  return {
    id: string(item.id, 'job.id'),
    asset_id: string(item.asset_id, 'job.asset_id'),
    status: literal(item.status, ['queued', 'running', 'needs-review', 'completed', 'failed', 'cancelled'], 'job.status'),
    provider: nullableString(item.provider, 'job.provider'),
    model: nullableString(item.model, 'job.model'),
    version: nullableString(item.version, 'job.version'),
    language: nullableString(item.language, 'job.language'),
    started_utc: nullableFiniteNumber(item.started_utc, 'job.started_utc'),
    finished_utc: nullableFiniteNumber(item.finished_utc, 'job.finished_utc'),
    error: nullableString(item.error, 'job.error'),
    chunk_progress: item.chunk_progress === undefined ? null : jsonValue(item.chunk_progress, 'job.chunk_progress'),
  }
}

export function toJobReadModel(value: ApiTranscriptionJobWire): TranscriptionJobReadModel {
  return { ...value }
}

export const decodeCandidatePage: Decoder<CandidateReadModel> = (value) => {
  const item = object(value, 'option collection')
  assertAllowedKeys(item, ['items'], 'option collection')
  const options = array(item.items, 'options.items').map((row, index) => decodeOption(row, `options.items[${index}]`))
  return {
    state: options.length ? 'ready' : 'empty',
    evaluator_access: 'granted',
    items: options.map((option) => ({
      id: option.id,
      replay_analysis_id: option.replay_analysis_id,
      revision: option.revision ?? null,
      statement: option.option_statement,
      rationale: option.rationale,
      supporting_evidence: option.supporting_evidence_ids,
      preconditions: option.preconditions,
      unknowns: option.unknowns,
      source_version: option.source_version,
      model_version: option.model_version,
      rule_version: option.rule_version,
      review_status: option.review_status,
    })),
  }
}

export function decodeReviewReceipt(value: unknown, fallbackRequestId?: string): ApiReviewReceiptWire {
  const item = object(value, 'review receipt')
  assertAllowedKeys(item, ['request_id', 'revision', 'status', 'message', 'annotation'], 'review receipt')
  const revision = nonnegativeInteger(item.revision, 'receipt.revision')
  const annotation = item.annotation === undefined ? undefined : decodeReviewAnnotation(item.annotation)
  const requestId = item.request_id === undefined ? fallbackRequestId : string(item.request_id, 'receipt.request_id')
  if (!requestId) fail('unsupported_profile', 'Review receipt omits request_id and no submitted request ID was supplied to the decoder.')
  let status: ApiReviewReceiptWire['status']
  if (item.status === undefined && annotation !== undefined) {
    if (annotation.revision !== revision) fail('unsupported_profile', 'Review annotation revision does not match its receipt revision.')
    status = 'accepted'
  } else {
    status = literal(item.status, ['accepted', 'conflict', 'unavailable'], 'receipt.status')
  }
  return {
    request_id: requestId,
    revision,
    status,
    ...(optionalString(item.message) === undefined ? {} : { message: optionalString(item.message) }),
    ...(annotation === undefined ? {} : { annotation }),
  }
}

export function decodeAssistMessage(value: unknown): ApiAssistMessageWire {
  const item = object(value, 'assist message')
  assertAllowedKeys(item, ['schema_version', 'source_session_id', 'sequence', 'type', 'payload'], 'assist message')
  if (item.schema_version !== 'assist-1') fail('unsupported_profile', 'Unsupported assist stream schema version.')
  const base = {
    schema_version: 'assist-1' as const,
    source_session_id: string(item.source_session_id, 'assist.source_session_id'),
    sequence: nonnegativeInteger(item.sequence, 'assist.sequence'),
  }
  const type = string(item.type, 'assist.type')
  const payload = object(item.payload, 'assist.payload')
  switch (type) {
    case 'snapshot':
      assertAllowedKeys(payload, ['jobs', 'transcripts', 'highlights', 'options', 'review_annotations'], 'assist snapshot')
      return {
        ...base,
        type,
        payload: {
          jobs: array(payload.jobs, 'assist.snapshot.jobs').map(decodeJob),
          transcripts: array(payload.transcripts, 'assist.snapshot.transcripts').map((row, index) => decodeTranscriptSegment(row, `assist.snapshot.transcripts[${index}]`)),
          highlights: array(payload.highlights, 'assist.snapshot.highlights').map(decodeHighlight),
          options: array(payload.options, 'assist.snapshot.options').map((row, index) => decodeOption(row, `assist.snapshot.options[${index}]`)),
          review_annotations: array(payload.review_annotations, 'assist.snapshot.review_annotations').map(decodeReviewAnnotation),
        },
      }
    case 'job_progress':
      assertAllowedKeys(payload, ['job'], 'assist job_progress')
      return { ...base, type, payload: { job: decodeJob(payload.job) } }
    case 'segment':
      assertAllowedKeys(payload, ['segment'], 'assist segment')
      return { ...base, type, payload: { segment: decodeTranscriptSegment(payload.segment, 'assist.segment') } }
    case 'highlight':
      assertAllowedKeys(payload, ['highlight'], 'assist highlight')
      return { ...base, type, payload: { highlight: decodeHighlight(payload.highlight) } }
    case 'option':
      assertAllowedKeys(payload, ['option'], 'assist option')
      return { ...base, type, payload: { option: decodeOption(payload.option, 'assist.option') } }
    case 'review_annotation':
      assertAllowedKeys(payload, ['annotation'], 'assist review_annotation')
      return { ...base, type, payload: { annotation: decodeReviewAnnotation(payload.annotation) } }
    case 'error':
      assertAllowedKeys(payload, ['code', 'message'], 'assist error')
      return { ...base, type, payload: { code: string(payload.code, 'assist.error.code'), message: string(payload.message, 'assist.error.message') } }
    default:
      fail('unsupported_profile', `Unsupported assist message type "${type}".`)
  }
}

export function decodeWebSocketMessage(value: unknown): ApiWebSocketMessageWire {
  const item = object(value, 'WebSocket message')
  if (item.schema_version !== undefined || item.type === 'snapshot' && item.payload !== undefined) {
    return { profile: 'assist', message: decodeAssistMessage(item) }
  }
  return { profile: 'source', snapshot: decodeApiSnapshot(item) }
}

export function decodeControlReceipt(value: unknown, expectedSessionId: string, requestId: string): { request_id: string; revision: number; status: 'accepted' } {
  const item = object(value, 'review control receipt')
  if (string(item.session_id, 'control.session_id') !== expectedSessionId) fail('unsupported_profile', 'Review command receipt belongs to a different session.')
  const status = string(item.status, 'control.status')
  if (!['READY', 'RUNNING', 'PAUSED', 'ENDED', 'INTERRUPTED'].includes(status)) fail('unsupported_profile', 'Review command returned an unsupported status.')
  return { request_id: requestId, revision: nonnegativeInteger(item.revision, 'control.revision'), status: 'accepted' }
}

export function toEventReadModel(item: ApiEventWire): EventReadModel {
  const extra: Record<string, unknown> = {}
  const known = new Set(['id', 'ordinal', 'sim_ms', 'type', 'message', 'target', 'actor', 'audit_utc', 'observed_ms', 'received_ms', 'evidence_event_ids'])
  for (const [key, value] of Object.entries(item)) if (!known.has(key)) extra[key] = value
  const result: EventReadModel = {
    id: item.id,
    ordinal: item.ordinal,
    sim_ms: item.sim_ms,
    type: item.type,
    message: item.message,
    ...(typeof item.target === 'string' ? { target: item.target } : {}),
    ...(typeof item.actor === 'string' ? { actor: item.actor } : {}),
    ...(typeof item.audit_utc === 'number' ? { audit_utc_s: item.audit_utc } : {}),
    ...(typeof item.observed_ms === 'number' ? { observed_ms: item.observed_ms } : {}),
    ...(typeof item.received_ms === 'number' ? { received_ms: item.received_ms } : {}),
    ...(Array.isArray(item.evidence_event_ids) ? { evidence_event_ids: item.evidence_event_ids.map((entry, index) => string(entry, `event.evidence_event_ids[${index}]`)) } : {}),
    ...(Object.keys(extra).length ? { details: extra } : {}),
  }
  return result
}

function decodeScenarioWire(value: unknown): ApiScenarioWire {
  const item = object(value, 'scenario')
  return {
    id: string(item.id, 'scenario.id'),
    title: string(item.title, 'scenario.title'),
    objective: string(item.objective, 'scenario.objective'),
    version: string(item.version, 'scenario.version'),
    duration_s: nonnegativeNumber(item.duration_s, 'scenario.duration_s'),
    domain_review: string(item.domain_review, 'scenario.domain_review'),
    ...(item.aircraft_count === undefined ? {} : { aircraft_count: nonnegativeInteger(item.aircraft_count, 'scenario.aircraft_count') }),
    ...(item.vehicle_count === undefined ? {} : { vehicle_count: nonnegativeInteger(item.vehicle_count, 'scenario.vehicle_count') }),
  }
}

function decodeParent(value: unknown): { session_id: string; frame_ms: number } {
  const item = object(value, 'snapshot.metadata.parent')
  return { session_id: string(item.session_id, 'snapshot.metadata.parent.session_id'), frame_ms: nonnegativeInteger(item.frame_ms, 'snapshot.metadata.parent.frame_ms') }
}

function decodeLayout(value: unknown): ApiLayoutWire {
  const item = object(value, 'snapshot.layout')
  const coordinateSystem = string(item.coordinate_system, 'layout.coordinate_system')
  if (coordinateSystem !== 'LOCAL_METRES') fail('unsupported_profile', `Unsupported layout coordinate system "${coordinateSystem}".`)
  return {
    id: string(item.id, 'layout.id'),
    version: string(item.version, 'layout.version'),
    name: string(item.name, 'layout.name'),
    coordinate_system: coordinateSystem,
    physical_runway_id: string(item.physical_runway_id, 'layout.physical_runway_id'),
    runway: pointList(item.runway, 'layout.runway'),
    protected_area: pointList(item.protected_area, 'layout.protected_area'),
    taxiways: lineList(item.taxiways, 'layout.taxiways'),
    hold_lines: lineList(item.hold_lines, 'layout.hold_lines'),
    directions: stringRecord(item.directions, 'layout.directions'),
    note: string(item.note, 'layout.note'),
  }
}

function decodeTrack(value: unknown, label: string): ApiTrackWire {
  const item = object(value, label)
  return {
    id: string(item.id, `${label}.id`),
    callsign: string(item.callsign, `${label}.callsign`),
    kind: literal(item.kind, ['aircraft', 'vehicle'], `${label}.kind`),
    x_m: finiteNumber(item.x_m, `${label}.x_m`),
    y_m: finiteNumber(item.y_m, `${label}.y_m`),
    speed_mps: nonnegativeNumber(item.speed_mps, `${label}.speed_mps`),
    heading_deg: finiteNumber(item.heading_deg, `${label}.heading_deg`),
    phase: string(item.phase, `${label}.phase`),
    length_m: positiveNumber(item.length_m, `${label}.length_m`),
    width_m: positiveNumber(item.width_m, `${label}.width_m`),
    runway: literal(item.runway, ['09', '27'], `${label}.runway`),
    route: pointList(item.route, `${label}.route`),
    owner: literal(item.owner, ['tower', 'ground'], `${label}.owner`),
    observed_ms: nonnegativeInteger(item.observed_ms, `${label}.observed_ms`),
    received_ms: nonnegativeInteger(item.received_ms, `${label}.received_ms`),
    source: string(item.source, `${label}.source`),
    event_id: string(item.event_id, `${label}.event_id`),
    stale: boolean(item.stale, `${label}.stale`),
  }
}

function decodeClearance(value: unknown, label: string): ApiSnapshotWire['clearances'][number] {
  const item = object(value, label)
  return {
    id: string(item.id, `${label}.id`),
    target: string(item.target, `${label}.target`),
    instruction: string(item.instruction, `${label}.instruction`),
    runway: literal(item.runway, ['09', '27'], `${label}.runway`),
    issued_ms: nonnegativeInteger(item.issued_ms, `${label}.issued_ms`),
    issuer: string(item.issuer, `${label}.issuer`),
    status: string(item.status, `${label}.status`),
    readback: string(item.readback, `${label}.readback`),
    event_id: string(item.event_id, `${label}.event_id`),
  }
}

function decodeRequest(value: unknown, label: string): ApiSnapshotWire['requests'][number] {
  const item = object(value, label)
  return { target: string(item.target, `${label}.target`), completed: boolean(item.completed, `${label}.completed`), requested_ms: nonnegativeInteger(item.requested_ms, `${label}.requested_ms`) }
}

function decodePrediction(value: unknown, label: string): ApiPredictionWire {
  const item = object(value, label)
  const result: ApiPredictionWire = {
    object_id: string(item.object_id, `${label}.object_id`),
    entry_s: finiteNumber(item.entry_s, `${label}.entry_s`),
    exit_s: finiteNumber(item.exit_s, `${label}.exit_s`),
    exit_unknown: boolean(item.exit_unknown, `${label}.exit_unknown`),
    threshold_eta_s: item.threshold_eta_s === null ? null : finiteNumber(item.threshold_eta_s, `${label}.threshold_eta_s`),
    assumed_entry_range_s: numberList(item.assumed_entry_range_s, `${label}.assumed_entry_range_s`),
    assumed_exit_range_s: numberList(item.assumed_exit_range_s, `${label}.assumed_exit_range_s`),
  }
  const physicalRunwayId = optionalString(item.physical_runway_id)
  const direction = optionalString(item.direction)
  const modelVersion = optionalString(item.model_version)
  const sourceEventId = optionalString(item.source_event_id)
  if (physicalRunwayId !== undefined) result.physical_runway_id = physicalRunwayId
  if (direction !== undefined) result.direction = direction
  if (item.interval_index !== undefined) result.interval_index = nonnegativeInteger(item.interval_index, `${label}.interval_index`)
  if (modelVersion !== undefined) result.model_version = modelVersion
  if (sourceEventId !== undefined) result.source_event_id = sourceEventId
  return result
}

function decodeRunway(value: unknown): ApiSnapshotWire['runway'] {
  const item = object(value, 'snapshot.runway')
  return {
    open: boolean(item.open, 'snapshot.runway.open'),
    state: string(item.state, 'snapshot.runway.state'),
    data_quality: string(item.data_quality, 'snapshot.runway.data_quality'),
    observed_occupants: stringList(item.observed_occupants, 'snapshot.runway.observed_occupants'),
    degraded_ids: stringList(item.degraded_ids, 'snapshot.runway.degraded_ids'),
  }
}

function decodeAlert(value: unknown, label: string): ApiSnapshotWire['alerts'][number] {
  const item = object(value, label)
  const metrics = jsonObject(item.metrics, `${label}.metrics`)
  for (const [key, metric] of Object.entries(metrics)) {
    if (key === 'intervals') {
      array(metric, `${label}.metrics.intervals`).forEach((row, index) => decodePrediction(row, `${label}.metrics.intervals[${index}]`))
    } else if (typeof metric !== 'number' || !Number.isFinite(metric)) {
      fail('invalid_payload', `${label}.metrics.${key} must be a finite number.`)
    }
  }
  return {
    id: string(item.id, `${label}.id`),
    rule: string(item.rule, `${label}.rule`),
    objects: stringList(item.objects, `${label}.objects`),
    severity: string(item.severity, `${label}.severity`),
    reason: string(item.reason, `${label}.reason`),
    status: string(item.status, `${label}.status`),
    created_ms: nonnegativeInteger(item.created_ms, `${label}.created_ms`),
    calculated_ms: nonnegativeInteger(item.calculated_ms, `${label}.calculated_ms`),
    ...(item.updated_ms === undefined ? {} : { updated_ms: nonnegativeInteger(item.updated_ms, `${label}.updated_ms`) }),
    data_degraded: boolean(item.data_degraded, `${label}.data_degraded`),
    metrics,
    evidence_event_ids: stringList(item.evidence_event_ids, `${label}.evidence_event_ids`),
    track_ages_ms: numberRecord(item.track_ages_ms, `${label}.track_ages_ms`),
    assumptions: string(item.assumptions, `${label}.assumptions`),
  }
}

function decodeEvent(value: unknown, label: string): ApiEventWire {
  const item = object(value, label)
  const details: Record<string, JsonValue> = {}
  for (const [key, raw] of Object.entries(item)) {
    if (!['id', 'ordinal', 'sim_ms', 'type', 'message'].includes(key)) details[key] = jsonValue(raw, `${label}.${key}`)
  }
  if (details.track !== undefined) details.track = decodeEventTrack(details.track, `${label}.track`)
  if (details.evidence_event_ids !== undefined) details.evidence_event_ids = stringList(details.evidence_event_ids, `${label}.evidence_event_ids`)
  if (details.audit_utc !== undefined) details.audit_utc = finiteNumber(details.audit_utc, `${label}.audit_utc`)
  if (details.observed_ms !== undefined) details.observed_ms = nonnegativeInteger(details.observed_ms, `${label}.observed_ms`)
  if (details.received_ms !== undefined) details.received_ms = nonnegativeInteger(details.received_ms, `${label}.received_ms`)
  return {
    id: string(item.id, `${label}.id`),
    ordinal: nonnegativeInteger(item.ordinal, `${label}.ordinal`),
    sim_ms: nonnegativeInteger(item.sim_ms, `${label}.sim_ms`),
    type: string(item.type, `${label}.type`),
    message: string(item.message, `${label}.message`),
    ...details,
  }
}

function decodeEventTrack(value: JsonValue, label: string): JsonValue {
  const item = object(value, label)
  return {
    id: string(item.id, `${label}.id`),
    callsign: string(item.callsign, `${label}.callsign`),
    kind: literal(item.kind, ['aircraft', 'vehicle'], `${label}.kind`),
    x_m: finiteNumber(item.x_m, `${label}.x_m`),
    y_m: finiteNumber(item.y_m, `${label}.y_m`),
    speed_mps: nonnegativeNumber(item.speed_mps, `${label}.speed_mps`),
    heading_deg: finiteNumber(item.heading_deg, `${label}.heading_deg`),
    phase: string(item.phase, `${label}.phase`),
    length_m: positiveNumber(item.length_m, `${label}.length_m`),
    width_m: positiveNumber(item.width_m, `${label}.width_m`),
    runway: literal(item.runway, ['09', '27'], `${label}.runway`),
    route: pointList(item.route, `${label}.route`),
    owner: literal(item.owner, ['tower', 'ground'], `${label}.owner`),
    observed_ms: nonnegativeInteger(item.observed_ms, `${label}.observed_ms`),
    received_ms: nonnegativeInteger(item.received_ms, `${label}.received_ms`),
    source: string(item.source, `${label}.source`),
    event_id: string(item.event_id, `${label}.event_id`),
  }
}

function decodeAcknowledgement(value: unknown, label: string): ApiSnapshotWire['acknowledgements'][number] {
  const item = object(value, label)
  return { alert_id: string(item.alert_id, `${label}.alert_id`), actor: string(item.actor, `${label}.actor`), sim_ms: nonnegativeInteger(item.sim_ms, `${label}.sim_ms`) }
}

function decodeComplexity(value: unknown): ApiSnapshotWire['complexity'] {
  const item = object(value, 'snapshot.complexity')
  const result: ApiSnapshotWire['complexity'] = {}
  for (const [role, raw] of Object.entries(item)) {
    const row = object(raw, `snapshot.complexity.${role}`)
    result[role] = {
      score: finiteNumber(row.score, `snapshot.complexity.${role}.score`),
      level: string(row.level, `snapshot.complexity.${role}.level`),
      components: numberRecord(row.components, `snapshot.complexity.${role}.components`),
      weights: numberRecord(row.weights, `snapshot.complexity.${role}.weights`),
      label: string(row.label, `snapshot.complexity.${role}.label`),
    }
  }
  return result
}

function decodeTranscriptSegment(value: unknown, label: string): ApiTranscriptSegmentWire {
  const item = object(value, label)
  assertAllowedKeys(item, ['id', 'asset_id', 'start_ms', 'end_ms', 'channel_id', 'speaker_label', 'speaker_source', 'speaker_confidence', 'text', 'language', 'asr_confidence', 'model_version', 'correction_status', 'revision', 'raw_text', 'session_start_ms'], label)
  const startMs = nonnegativeInteger(item.start_ms, `${label}.start_ms`)
  const endMs = nonnegativeInteger(item.end_ms, `${label}.end_ms`)
  if (endMs < startMs) fail('invalid_payload', `${label}.end_ms precedes start_ms.`)
  return {
    id: string(item.id, `${label}.id`),
    asset_id: string(item.asset_id, `${label}.asset_id`),
    start_ms: startMs,
    end_ms: endMs,
    channel_id: string(item.channel_id, `${label}.channel_id`),
    speaker_label: nullableString(item.speaker_label, `${label}.speaker_label`),
    speaker_source: nullableString(item.speaker_source, `${label}.speaker_source`),
    speaker_confidence: nullableConfidence(item.speaker_confidence, `${label}.speaker_confidence`),
    text: string(item.text, `${label}.text`),
    language: nullableString(item.language, `${label}.language`),
    asr_confidence: nullableConfidence(item.asr_confidence, `${label}.asr_confidence`),
    model_version: nullableString(item.model_version, `${label}.model_version`),
    correction_status: string(item.correction_status, `${label}.correction_status`),
    ...(item.revision === undefined ? {} : { revision: nonnegativeInteger(item.revision, `${label}.revision`) }),
    ...(item.raw_text === undefined ? {} : { raw_text: string(item.raw_text, `${label}.raw_text`) }),
    ...(item.session_start_ms === undefined ? {} : { session_start_ms: item.session_start_ms === null ? null : nonnegativeInteger(item.session_start_ms, `${label}.session_start_ms`) }),
  }
}

function decodeEvidenceRef(value: unknown): ApiEvidenceRefWire {
  const item = object(value, 'evidence reference')
  assertAllowedKeys(item, ['kind', 'id'], 'evidence reference')
  return { kind: literal(item.kind, ['session_event', 'transcript_segment', 'detector_alert'], 'evidence.kind'), id: string(item.id, 'evidence.id') }
}

function decodeHighlight(value: unknown): ApiHighlightWire {
  const item = object(value, 'assist highlight')
  assertAllowedKeys(item, ['id', 'revision', 'category', 'review_priority', 'statement', 'transcript_segment_ids', 'session_event_ids', 'uncertainty', 'provider_version', 'rule_version', 'status', 'linked_alert_id', 'link_status'], 'assist highlight')
  const linkStatus = item.link_status === undefined || item.link_status === null
    ? item.link_status
    : literal(item.link_status, ['linked', 'possible_link'], 'highlight.link_status')
  return {
    id: string(item.id, 'highlight.id'),
    ...(item.revision === undefined ? {} : { revision: nonnegativeInteger(item.revision, 'highlight.revision') }),
    category: string(item.category, 'highlight.category'),
    review_priority: string(item.review_priority, 'highlight.review_priority'),
    statement: string(item.statement, 'highlight.statement'),
    transcript_segment_ids: stringList(item.transcript_segment_ids, 'highlight.transcript_segment_ids'),
    session_event_ids: stringList(item.session_event_ids, 'highlight.session_event_ids'),
    uncertainty: string(item.uncertainty, 'highlight.uncertainty'),
    provider_version: string(item.provider_version, 'highlight.provider_version'),
    rule_version: string(item.rule_version, 'highlight.rule_version'),
    status: string(item.status, 'highlight.status'),
    ...(item.linked_alert_id === undefined ? {} : { linked_alert_id: nullableString(item.linked_alert_id, 'highlight.linked_alert_id') }),
    ...(linkStatus === undefined ? {} : { link_status: linkStatus }),
  }
}

function decodeOption(value: unknown, label: string): ApiOptionWire {
  const item = object(value, label)
  assertAllowedKeys(item, ['id', 'replay_analysis_id', 'revision', 'option_statement', 'rationale', 'supporting_evidence_ids', 'preconditions', 'unknowns', 'source_version', 'model_version', 'rule_version', 'review_status'], label)
  return {
    id: string(item.id, `${label}.id`),
    replay_analysis_id: string(item.replay_analysis_id, `${label}.replay_analysis_id`),
    ...(item.revision === undefined ? {} : { revision: nonnegativeInteger(item.revision, `${label}.revision`) }),
    option_statement: string(item.option_statement, `${label}.option_statement`),
    rationale: string(item.rationale, `${label}.rationale`),
    supporting_evidence_ids: array(item.supporting_evidence_ids, `${label}.supporting_evidence_ids`).map(decodeEvidenceRef),
    preconditions: stringList(item.preconditions, `${label}.preconditions`),
    unknowns: stringList(item.unknowns, `${label}.unknowns`),
    source_version: string(item.source_version, `${label}.source_version`),
    model_version: string(item.model_version, `${label}.model_version`),
    rule_version: string(item.rule_version, `${label}.rule_version`),
    review_status: string(item.review_status, `${label}.review_status`),
  }
}

function decodeReviewAnnotation(value: unknown): ApiReviewAnnotationWire {
  const item = object(value, 'review annotation')
  assertAllowedKeys(item, ['id', 'target_id', 'decision', 'reviewer', 'timestamp', 'revision', 'correction', 'reason'], 'review annotation')
  const timestamp = item.timestamp
  if (typeof timestamp !== 'number' && (typeof timestamp !== 'string' || !/^\d{4}-\d\d-\d\dT.*(?:Z|[+-]\d\d:\d\d)$/.test(timestamp) || !Number.isFinite(Date.parse(timestamp)))) {
    fail('invalid_payload', 'annotation.timestamp must be a finite epoch value or an ISO-8601 timestamp with timezone.')
  }
  return {
    ...(optionalString(item.id) === undefined ? {} : { id: optionalString(item.id) }),
    target_id: string(item.target_id, 'annotation.target_id'),
    decision: literal(item.decision, ['corrected', 'confirmed', 'dismissed', 'unresolved'], 'annotation.decision'),
    reviewer: string(item.reviewer, 'annotation.reviewer'),
    timestamp: typeof timestamp === 'number' ? finiteNumber(timestamp, 'annotation.timestamp') : timestamp,
    ...(item.revision === undefined ? {} : { revision: nonnegativeInteger(item.revision, 'annotation.revision') }),
    ...(item.correction === undefined ? {} : { correction: nullableString(item.correction, 'annotation.correction') }),
    ...(item.reason === undefined ? {} : { reason: nullableString(item.reason, 'annotation.reason') }),
  }
}

function toSnapshotReviewAnnotation(value: Record<string, JsonValue>): ReviewAnnotationReadModel {
  const item = object(value, 'snapshot review annotation')
  if ('decision' in item || 'target_id' in item) {
    return {
      kind: 'review_annotation',
      ...decodeReviewAnnotation(item),
      // Additive annotations carry audit time; no session-time mapping is supplied by this snapshot.
      session_ms: null,
    }
  }

  // CURRENT_SOURCE Review annotations are existing Assessment records. Preserve their own
  // type/text/values and explicit review playhead without coercing them into C-05 decisions.
  assertAllowedKeys(item, ['sim_ms', 'actor', 'type', 'text', 'values'], 'snapshot assessment annotation')
  const assessmentType = literal(item.type, ['bookmark', 'recognition', 'answer', 'tlx', 'trainer_review'], 'annotation.type')
  return {
    kind: 'assessment',
    assessment_type: assessmentType,
    reviewer: string(item.actor, 'annotation.actor'),
    session_ms: nonnegativeInteger(item.sim_ms, 'annotation.sim_ms'),
    text: string(item.text, 'annotation.text'),
    values: item.values === undefined ? {} : numberRecord(item.values, 'annotation.values'),
  }
}

function pointList(value: unknown, label: string): Array<[number, number]> {
  return array(value, label).map((point, index) => {
    const coordinates = array(point, `${label}[${index}]`)
    if (coordinates.length !== 2) fail('invalid_payload', `${label}[${index}] must have exactly two coordinates.`)
    return [finiteNumber(coordinates[0], `${label}[${index}][0]`), finiteNumber(coordinates[1], `${label}[${index}][1]`)]
  })
}

function lineList(value: unknown, label: string): Array<Array<[number, number]>> {
  return array(value, label).map((line, index) => pointList(line, `${label}[${index}]`))
}

function qualityFromDataQuality(value: string): 'known' | 'degraded' | 'unknown' {
  const normalized = value.toLowerCase()
  if (['nominal', 'good', 'ok'].includes(normalized)) return 'known'
  return normalized === 'unknown' ? 'unknown' : 'degraded'
}

function numberList(value: unknown, label: string): number[] {
  return array(value, label).map((item, index) => finiteNumber(item, `${label}[${index}]`))
}

function stringList(value: unknown, label: string): string[] {
  return array(value, label).map((item, index) => string(item, `${label}[${index}]`))
}

function stringRecord(value: unknown, label: string): Record<string, string> {
  const item = object(value, label)
  const result: Record<string, string> = {}
  for (const [key, raw] of Object.entries(item)) result[key] = string(raw, `${label}.${key}`)
  return result
}

function numberRecord(value: unknown, label: string): Record<string, number> {
  const item = object(value, label)
  const result: Record<string, number> = {}
  for (const [key, raw] of Object.entries(item)) result[key] = finiteNumber(raw, `${label}.${key}`)
  return result
}

function jsonObject(value: unknown, label: string): Record<string, JsonValue> {
  const item = object(value, label)
  const result: Record<string, JsonValue> = {}
  for (const [key, raw] of Object.entries(item)) result[key] = jsonValue(raw, `${label}.${key}`)
  return result
}

function jsonValue(value: unknown, label: string): JsonValue {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value
  if (typeof value === 'number') return finiteNumber(value, label)
  if (Array.isArray(value)) return value.map((entry, index) => jsonValue(entry, `${label}[${index}]`))
  if (typeof value === 'object') return jsonObject(value, label)
  fail('invalid_payload', `${label} is not a JSON value.`)
}

function assertAllowedKeys(item: UnknownRecord, allowed: string[], label: string): void {
  const unknown = Object.keys(item).filter((key) => !allowed.includes(key))
  if (unknown.length) fail('unsupported_profile', `${label} contains unsupported field(s): ${unknown.join(', ')}.`)
}

function object(value: unknown, label: string): UnknownRecord {
  if (!isRecord(value)) fail('invalid_payload', `${label} must be an object.`)
  return value
}

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function array(value: unknown, label: string): unknown[] {
  if (!Array.isArray(value)) fail('invalid_payload', `${label} must be an array.`)
  return value
}

function string(value: unknown, label: string): string {
  if (typeof value !== 'string') fail('invalid_payload', `${label} must be a string.`)
  return value
}

function optionalString(value: unknown): string | undefined {
  return value === undefined ? undefined : string(value, 'optional string field')
}

function nullableString(value: unknown, label: string): string | null {
  if (value === null) return null
  return string(value, label)
}

function finiteNumber(value: unknown, label: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) fail('invalid_payload', `${label} must be a finite number.`)
  return value
}

function nonnegativeNumber(value: unknown, label: string): number {
  const result = finiteNumber(value, label)
  if (result < 0) fail('invalid_payload', `${label} must be nonnegative.`)
  return result
}

function positiveNumber(value: unknown, label: string): number {
  const result = finiteNumber(value, label)
  if (result <= 0) fail('invalid_payload', `${label} must be positive.`)
  return result
}

function nonnegativeInteger(value: unknown, label: string): number {
  const result = nonnegativeNumber(value, label)
  if (!Number.isInteger(result)) fail('invalid_payload', `${label} must be an integer.`)
  return result
}

function nullableFiniteNumber(value: unknown, label: string): number | null {
  return value === null ? null : finiteNumber(value, label)
}

function nullableConfidence(value: unknown, label: string): number | null {
  const result = nullableFiniteNumber(value, label)
  if (result !== null && (result < 0 || result > 1)) fail('invalid_payload', `${label} must be between 0 and 1 or null.`)
  return result
}

function boolean(value: unknown, label: string): boolean {
  if (typeof value !== 'boolean') fail('invalid_payload', `${label} must be a boolean.`)
  return value
}

function literal<const T extends readonly string[]>(value: unknown, choices: T, label: string): T[number] {
  if (typeof value !== 'string' || !choices.includes(value)) fail('unsupported_profile', `${label} has unsupported value "${String(value)}".`)
  return value
}

function fail(reason: ApiRequestError['reason'], message: string): never {
  throw new ApiRequestError('error', message, null, reason)
}
