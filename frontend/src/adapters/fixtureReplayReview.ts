import type {
  AudioAlignmentReadModel,
  AudioAssetReadModel,
  AnalysisProvenanceReadModel,
  AssistReviewReadModel,
  AssistUpdateReadModel,
  CandidateReadModel,
  EventPageReadModel,
  EventReadModel,
  EvidenceRef,
  EvidenceResolution,
  OperatorAccess,
  OverviewReadModel,
  ReplayFrameReadModel,
  ReplayReviewAdapter,
  ReplaySourceReadModel,
  ReviewOpenResult,
  ReviewControl,
  ReviewReceipt,
  ReviewAnnotationReadModel,
  ReviewSpeed,
  SubscriptionState,
  ScenarioReadModel,
  SessionReadModel,
  SessionViewReadModel,
  SnapshotReadModel,
  TranscriptReadModel,
  ReplaySnapshotReadModel,
} from '../contracts/replayReview'

export const FIXTURE_FRAME_MS = 74_600
export const FIXTURE_EVENT_PAGE_SIZE = 2

const scenario: ScenarioReadModel = {
  id: 'FE-01-FIXTURE',
  title: 'Synthetic runway review display',
  objective: 'Display authored LOCAL_METRES geometry, tracks, predictions and deterministic alert evidence.',
  version: 'fixture-1',
  duration_s: 120,
  domain_review: 'NOT_REVIEWED',
}

const fixtureSession: SessionReadModel = {
  id: 'SYN-FE-01',
  status: 'READY',
  scenario,
  condition: 'synthetic-fixture',
  seed: 1,
  kind: 'training',
  created_utc_ms: null,
}

const fixtureSnapshot: SnapshotReadModel = {
  session_id: fixtureSession.id,
  sim_ms: 0,
  sequence: 0,
  revision: 0,
  status: 'READY',
  speed: 1,
  kind: 'training',
  seed: fixtureSession.seed,
  scenario,
  scenario_title: scenario.title,
  condition: fixtureSession.condition,
  track_count: 2,
  alert_count: 1,
  event_count: 5,
  runway_state: 'OCCUPIED',
  data_quality: 'DEGRADED · SYNTHETIC',
}

const fixtureEvents: EventReadModel[] = [
  {
    id: 'SYN-FE-04:COMM:01',
    ordinal: 1,
    sim_ms: 72_400,
    type: 'COMMUNICATION',
    message: 'Authored synthetic phrase for timeline layout only; not transcribed audio.',
    target: 'TUG-04',
    details: { channel: 'ground', provenance: 'authored-fixture' },
  },
  {
    id: 'SYN-FE-03:CLR:01',
    ordinal: 2,
    sim_ms: 73_020,
    type: 'CLEARANCE',
    message: 'Synthetic HOLD_SHORT clearance recorded for TUG-04.',
    target: 'TUG-04',
    details: { instruction: 'HOLD_SHORT', runway: '27' },
  },
  {
    id: 'SYN-FE-03:TRACK:TUG-04',
    ordinal: 3,
    sim_ms: 74_360,
    type: 'TRACK',
    message: 'Synthetic last-known vehicle position; this sample is stale at the displayed frame.',
    target: 'TUG-04',
    observed_ms: 71_000,
    received_ms: 74_360,
  },
  {
    id: 'SYN-FE-03:TRACK:AC-01',
    ordinal: 4,
    sim_ms: 74_530,
    type: 'TRACK',
    message: 'Synthetic observed aircraft track sample.',
    target: 'AC-01',
    observed_ms: 74_180,
    received_ms: 74_530,
  },
  {
    id: 'SYN-FE-04:ALERT:01',
    ordinal: 5,
    sim_ms: FIXTURE_FRAME_MS,
    type: 'ALERT_OPEN',
    message: 'Authored deterministic alert fixture; no operational inference.',
    evidence_event_ids: ['SYN-FE-03:TRACK:TUG-04'],
  },
]

const fixtureAnalysis: AnalysisProvenanceReadModel = {
  id: 'AN-FE-05-SYN-01', source_session_id: fixtureSession.id, kind: 'assist',
  source_version: 'fixture-1', model_version: 'authored-fixture-not-AI', rule_version: 'authored-fixture-rules-1',
  input_hash: null, transcript_revision_basis: 2, window_start_ms: 72_000, window_end_ms: FIXTURE_FRAME_MS,
  status: 'authored-fixture-only',
}

const initialFixtureTranscript: TranscriptReadModel['items'] = [
  {
    id: 'SEG-FE05-RAW-01', asset_id: 'ASSET-FE05-SYN-01', start_ms: 1_200, end_ms: 2_100,
    timebase: 'audio-relative', alignment_state: 'unknown', channel_id: 'ground', speaker_label: null,
    speaker_source: 'authored-fixture-unknown', speaker_confidence: null,
    text: 'Tug four, cross runway twenty seven.', raw_text: 'Tug four, cross runway twenty seven.',
    language: 'en', asr_confidence: null, model_version: 'authored-fixture-not-ASR',
    correction_status: 'authored-raw-example', revision: 1, session_start_ms: null, session_end_ms: null,
  },
  {
    id: 'SEG-FE05-COR-02', asset_id: 'ASSET-FE05-SYN-01', start_ms: 3_400, end_ms: 4_600,
    timebase: 'audio-relative', alignment_state: 'unknown', channel_id: 'ground', speaker_label: 'Ground · authored label',
    speaker_source: 'authored-fixture', speaker_confidence: null,
    text: 'Tug four, hold short runway twenty seven.', raw_text: 'Tug four, cross runway twenty seven.',
    language: 'en', asr_confidence: null, model_version: 'authored-fixture-not-ASR',
    correction_status: 'corrected · authored fixture', revision: 2, session_start_ms: null, session_end_ms: null,
  },
]

const initialFixtureHighlights: AssistReviewReadModel['highlights'] = [
  {
    id: 'HI-FE05-LINKED-01', revision: 1, category: 'instruction-vs-event-candidate', review_priority: 'review',
    statement: 'Authored example: a transcript candidate is explicitly linked to the recorded HOLD_SHORT event for this fixture.',
    transcript_segment_ids: ['SEG-FE05-COR-02'], session_event_ids: ['SYN-FE-03:CLR:01'],
    uncertainty: 'Synthetic UI example only; the relationship has not been domain reviewed.',
    provider_version: 'authored-fixture-not-provider', rule_version: 'authored-fixture-rules-1', status: 'unreviewed',
    link_status: 'linked',
  },
  {
    id: 'HI-FE05-POSSIBLE-02', revision: 1, category: 'nearby-track-candidate', review_priority: 'review',
    statement: 'Authored example: this nearby track reference is a possible link only; proximity does not establish a relationship.',
    transcript_segment_ids: ['SEG-FE05-RAW-01'], session_event_ids: ['SYN-FE-03:TRACK:TUG-04'],
    uncertainty: 'Audio alignment is unknown and the event is not merged with the transcript segment.',
    provider_version: 'authored-fixture-not-provider', rule_version: 'authored-fixture-rules-1', status: 'unreviewed',
    linked_alert_id: 'ALERT-FE-03-01', link_status: 'possible_link',
  },
]

const initialFixtureCandidates: CandidateReadModel['items'] = [
  {
    id: 'OPT-FE05-SYN-01', replay_analysis_id: fixtureAnalysis.id, revision: 1,
    statement: 'Evaluator option candidate: compare the authored transcript revision with the recorded event in this replay window.',
    rationale: 'The option is linked to one authored transcript reference and one source event reference for review practice.',
    supporting_evidence: [
      { kind: 'transcript_segment', id: 'SEG-FE05-COR-02' },
      { kind: 'session_event', id: 'SYN-FE-03:CLR:01' },
    ],
    preconditions: ['Evaluator view of this synthetic replay only.'],
    unknowns: ['Audio-to-session alignment is unknown.', 'No operational suitability or procedure is asserted.'],
    source_version: fixtureAnalysis.source_version ?? undefined,
    model_version: fixtureAnalysis.model_version ?? undefined,
    rule_version: fixtureAnalysis.rule_version ?? undefined,
    review_status: 'unreviewed',
  },
]

const fixtureReplaySnapshot: ReplaySnapshotReadModel = {
  session_id: fixtureSession.id,
  source_session_id: fixtureSession.id,
  kind: 'training',
  sequence: 1,
  sim_ms: FIXTURE_FRAME_MS,
  playback_ms: null,
  revision: 0,
  status: 'READY',
  speed: 1,
  scenario_id: scenario.id,
  scenario_title: scenario.title,
  condition: 'synthetic-fixture',
  source_version: 'fixture-1',
  config_version: 'fixture-display-1',
  viewer_role: 'fixture-reader',
  viewer_label: 'Synthetic fixture viewer',
  layout: {
    id: 'synthetic-lab',
    version: '1.0',
    name: 'FlowLens Research Airfield',
    coordinate_system: 'LOCAL_METRES',
    physical_runway_id: 'RWY-09-27',
    runway: [[0, -22.5], [3000, -22.5], [3000, 22.5], [0, 22.5]],
    protected_area: [[0, -75], [3000, -75], [3000, 75], [0, 75]],
    taxiways: [
      [[0, -160], [3000, -160]],
      [[1500, -260], [1500, 260]],
      [[300, -160], [300, -75]],
      [[2700, -160], [2700, -75]],
    ],
    hold_lines: [[[1470, -95], [1530, -95]], [[1470, 95], [1530, 95]]],
    directions: { '27': 'RWY-09-27', '09': 'RWY-09-27' },
    note: 'Synthetic geometry; protected-area dimensions are experiment assumptions, not airport standards.',
  },
  tracks: [
    {
      id: 'AC-01', callsign: 'SYN101', kind: 'aircraft', x_m: 2350, y_m: 12,
      speed_mps: 16, heading_deg: 180, phase: 'final', length_m: 38, width_m: 12,
      runway: '27', route: [[0, 12]], owner: 'tower', observed_ms: FIXTURE_FRAME_MS - 420,
      received_ms: FIXTURE_FRAME_MS - 70, source: 'authored-synthetic-fixture',
      event_id: 'SYN-FE-03:TRACK:AC-01', stale: false,
    },
    {
      id: 'TUG-04', callsign: 'TUG-04', kind: 'vehicle', x_m: 1500, y_m: -112,
      speed_mps: 0, heading_deg: 90, phase: 'holding', length_m: 12, width_m: 3,
      runway: '27', route: [[1500, 80]], owner: 'ground', observed_ms: FIXTURE_FRAME_MS - 3_600,
      received_ms: FIXTURE_FRAME_MS - 240, source: 'authored-synthetic-fixture',
      event_id: 'SYN-FE-03:TRACK:TUG-04', stale: true,
    },
  ],
  clearances: [
    { id: 'CLR-FE-03-01', target: 'TUG-04', instruction: 'HOLD_SHORT', runway: '27', issued_ms: 73_020, issuer: 'synthetic-scenario', status: 'ISSUED', readback: 'ACKNOWLEDGED', event_id: 'SYN-FE-03:CLR:01' },
  ],
  predictions: [
    {
      object_id: 'AC-01', physical_runway_id: 'RWY-09-27', direction: '27', interval_index: 0,
      entry_s: 0, exit_s: 120, exit_unknown: true, threshold_eta_s: 8.4,
      assumed_entry_range_s: [0, 4.9], assumed_exit_range_s: [105.2, 120],
      model_version: 'fixture-detector-1', source_event_id: 'SYN-FE-03:TRACK:AC-01',
    },
  ],
  alerts: [
    {
      id: 'ALERT-FE-03-01', rule: 'TRACKING_DEGRADED', objects: ['TUG-04'],
      severity: 'DATA_DEGRADED', reason: 'Synthetic stale track; clear state cannot be established.',
      status: 'ACTIVE', created_ms: FIXTURE_FRAME_MS, calculated_ms: FIXTURE_FRAME_MS,
      updated_ms: FIXTURE_FRAME_MS, data_degraded: true,
      metrics: {}, evidence_event_ids: ['SYN-FE-03:TRACK:TUG-04'],
      track_ages_ms: { 'TUG-04': 3_600 },
      assumptions: 'Authored UI fixture only; no operational inference.',
    },
  ],
  runway: {
    open: true, state: 'OCCUPIED', data_quality: 'DEGRADED',
    observed_occupants: ['AC-01'], degraded_ids: ['TUG-04'],
  },
  acknowledgements: [{ alert_id: 'ALERT-FE-03-01', actor: 'synthetic-evaluator', sim_ms: FIXTURE_FRAME_MS }],
  review_annotations: [],
  events: fixtureEvents.filter((event) => event.type !== 'TRACK').slice(-2),
  event_count: fixtureEvents.length,
  track_count: 2,
  alert_count: 1,
}

const fixtureStartFrame: ReplaySnapshotReadModel = {
  ...fixtureReplaySnapshot,
  sim_ms: 0,
  playback_ms: 0,
  tracks: [],
  clearances: [],
  predictions: [],
  alerts: [],
  runway: { open: false, state: 'UNKNOWN', data_quality: 'UNKNOWN', observed_occupants: [], degraded_ids: [] },
  acknowledgements: [],
  review_annotations: [],
  events: [],
  event_count: 0,
  track_count: 0,
  alert_count: 0,
}

export class FixtureReplayReviewAdapter implements ReplayReviewAdapter {
  readonly mode = 'fixture' as const
  readonly supported_speeds: readonly ReviewSpeed[] = [0.5, 1, 2, 4]
  private readonly fixtureView: 'evaluator' | 'training'
  private revision = 0
  private playheadMs = FIXTURE_FRAME_MS
  private speed: 0.5 | 1 | 2 | 4 = 1
  private status: 'READY' | 'RUNNING' | 'PAUSED' = 'READY'
  private readonly commands = new Map<string, { body: string; receipt: ReviewReceipt }>()
  private readonly reviewRequests = new Map<string, { body: string; receipt: ReviewReceipt }>()
  private transcriptItems = initialFixtureTranscript.map((segment) => ({ ...segment }))
  private highlights = initialFixtureHighlights.map((highlight) => ({ ...highlight }))
  private candidates = initialFixtureCandidates.map((candidate) => ({ ...candidate, supporting_evidence: [...candidate.supporting_evidence] }))
  private reviewAnnotations: ReviewAnnotationReadModel[] = []
  private conflictExampleIssued = false

  constructor(options: { view?: 'evaluator' | 'training' } = {}) {
    this.fixtureView = options.view ?? 'evaluator'
  }

  async loadOverview(): Promise<OverviewReadModel> {
    return {
      health: { state: 'fixture', version: 'fixture-1', mode: 'fixture' },
      scenarios: [scenario],
      source_label: 'SYNTHETIC / NOT OPERATIONALLY VALIDATED · INLINE FE-03 FIXTURE',
    }
  }

  async authenticateOperator(): Promise<OperatorAccess> {
    throw new Error('Operator authentication is unavailable in fixture mode.')
  }

  async listSessions(): Promise<SessionReadModel[]> {
    return [fixtureSession]
  }

  async createSession(): Promise<SessionReadModel> {
    throw new Error('Fixture mode is read-only. Select API mode to use the local backend.')
  }

  async openReview(sourceSessionId: string): Promise<ReviewOpenResult> {
    this.assertFixtureId(sourceSessionId)
    return { status: 'unavailable', message: 'Fixture mode is already an explicitly labeled local replay; no server review session is created.' }
  }

  async loadSession(_token: string, sessionId: string): Promise<SessionViewReadModel> {
    if (sessionId !== fixtureSession.id) throw new Error(`Fixture source not found: ${sessionId}`)
    return {
      session: { ...fixtureSession, status: this.status },
      snapshot: {
        ...fixtureSnapshot,
        status: this.status,
        sequence: this.revision,
        revision: this.revision,
        sim_ms: this.playheadMs,
        speed: this.speed,
      },
      events: fixtureEvents,
    }
  }

  async loadSource(sourceSessionId: string): Promise<ReplaySourceReadModel> {
    this.assertFixtureId(sourceSessionId)
    return {
      source_session_id: fixtureSession.id,
      source_kind: 'synthetic',
      label: 'SYNTHETIC / NOT OPERATIONALLY VALIDATED',
      provenance: 'Authored inline fixture for frontend development; no simulator or partner data.',
      source_version: 'fixture-1',
      quality: 'unknown',
    }
  }

  async loadFrame(sourceSessionId: string, atMs: number, _signal?: AbortSignal): Promise<ReplayFrameReadModel> {
    this.assertFixtureId(sourceSessionId)
    if (!Number.isSafeInteger(atMs) || atMs < 0 || atMs > FIXTURE_FRAME_MS) throw new Error('Replay time must be an integer inside the recorded fixture range.')
    return this.makeFrame(atMs)
  }

  async listEvents(sourceSessionId: string, cursor: number, untilMs?: number): Promise<EventPageReadModel> {
    this.assertFixtureId(sourceSessionId)
    const inspected = fixtureEvents.filter((event) => event.ordinal > cursor).slice(0, FIXTURE_EVENT_PAGE_SIZE)
    const rows = inspected.filter((event) => untilMs === undefined || event.sim_ms <= untilMs)
    return { items: rows, next_cursor: inspected.at(-1)?.ordinal ?? cursor, state: rows.length ? 'ready' : 'empty' }
  }

  async listTranscript(sourceSessionId: string, cursor: string | null = null, untilMs?: number): Promise<TranscriptReadModel> {
    this.assertFixtureId(sourceSessionId)
    const visible = untilMs === undefined ? this.transcriptItems : this.transcriptItems.filter((item) => item.session_end_ms !== null && item.session_end_ms !== undefined && item.session_end_ms <= untilMs)
    const offset = cursor === null ? 0 : Number(cursor)
    if (!Number.isSafeInteger(offset) || offset < 0) throw new Error('Fixture transcript cursor is invalid.')
    const items = visible.slice(offset, offset + 1)
    const nextOffset = offset + items.length
    return {
      state: items.length ? 'ready' : 'empty', items,
      next_cursor: nextOffset < visible.length ? String(nextOffset) : null,
      message: untilMs === undefined
        ? 'Authored synthetic transcript examples only; no ASR ran, no partner data is present, and audio-to-session alignment is unknown.'
        : 'Segments without a session mapping are omitted from this precise historical cutoff.',
    }
  }

  async loadAssistReview(sourceSessionId: string, analysisId?: string): Promise<AssistReviewReadModel> {
    this.assertFixtureId(sourceSessionId)
    if (this.fixtureView === 'training') {
      return {
        state: 'unavailable',
        message: 'This authored fixture uses a training-seat projection; evaluator-only highlights and options are not supplied.',
        provider_availability: 'unavailable', evaluator_access: 'denied', highlights: [],
        candidates: { state: 'unavailable', evaluator_access: 'denied', message: 'Evaluator-only options are hidden for this fixture training view.', items: [] },
        review_annotations: [], jobs: [], analysis: null,
      }
    }
    if (analysisId && analysisId !== fixtureAnalysis.id) {
      return {
        state: 'unavailable', message: 'The requested analysis ID is outside this authored fixture.',
        provider_availability: 'unavailable', evaluator_access: 'granted', highlights: [],
        candidates: { state: 'unavailable', evaluator_access: 'granted', message: 'No matching analysis fixture exists.', items: [] },
        review_annotations: [...this.reviewAnnotations], jobs: [], analysis: null,
      }
    }
    const candidates: CandidateReadModel = {
      state: this.candidates.length ? 'ready' : 'empty', evaluator_access: 'granted', analysis: fixtureAnalysis,
      message: 'Authored evaluator fixture only. The text was not generated by an AI provider.',
      items: this.candidates.map((candidate) => ({ ...candidate, supporting_evidence: [...candidate.supporting_evidence] })),
    }
    return {
      state: this.transcriptItems.length || this.highlights.length || this.candidates.length ? 'ready' : 'empty',
      message: 'All transcript, highlight, option and review examples in this panel are authored synthetic fixtures. No provider or partner source was used.',
      provider_availability: 'unavailable', evaluator_access: 'granted',
      highlights: this.highlights.map((highlight) => ({ ...highlight })), candidates,
      review_annotations: [...this.reviewAnnotations], jobs: [], analysis: fixtureAnalysis,
    }
  }

  async loadAudioAsset(sourceSessionId: string, assetId?: string): Promise<AudioAssetReadModel> {
    this.assertFixtureId(sourceSessionId)
    return { state: 'unavailable', ...(assetId ? { asset_id: assetId } : {}), message: 'Fixture mode contains no audio bytes; playback is unavailable.' }
  }

  sessionMsToAudioSeconds(alignment: AudioAlignmentReadModel, sessionMs: number): number | null {
    if (alignment.state !== 'mapped' || !Number.isFinite(sessionMs) || sessionMs < 0) return null
    const audioMs = sessionMs - alignment.offset_ms
    return audioMs < 0 ? null : audioMs / 1000
  }

  audioSecondsToSessionMs(alignment: AudioAlignmentReadModel, audioSeconds: number): number | null {
    if (alignment.state !== 'mapped' || !Number.isFinite(audioSeconds) || audioSeconds < 0) return null
    const sessionMs = Math.round(audioSeconds * 1000 + alignment.offset_ms)
    return Number.isSafeInteger(sessionMs) && sessionMs >= 0 ? sessionMs : null
  }

  async resolveEvidence(sourceSessionId: string, refs: EvidenceRef[], untilMs?: number, _signal?: AbortSignal, _analysisId?: string): Promise<EvidenceResolution[]> {
    this.assertFixtureId(sourceSessionId)
    const eventsById = new Map(fixtureEvents.map((event) => [event.id, event]))
    return refs.map((ref) => {
      if (ref.kind === 'session_event') {
        const event = eventsById.get(ref.id)
        return event && (untilMs === undefined || event.sim_ms <= untilMs)
          ? { ref, state: 'resolved', summary: `${event.type}: ${event.message}`, context: { timebase: 'session', at_ms: event.received_ms ?? event.sim_ms } }
          : { ref, state: 'unresolved' }
      }
      if (ref.kind === 'detector_alert') {
        const alert = fixtureReplaySnapshot.alerts.find((item) => item.id === ref.id)
        return alert && (untilMs === undefined || alert.calculated_ms <= untilMs)
          ? { ref, state: 'resolved', summary: `${alert.rule}: ${alert.reason}`, context: { timebase: 'session', at_ms: alert.calculated_ms } }
          : { ref, state: 'unresolved' }
      }
      const segment = this.transcriptItems.find((item) => item.id === ref.id)
      if (!segment) return { ref, state: 'unresolved' }
      if (untilMs !== undefined && (segment.session_end_ms === null || segment.session_end_ms === undefined || segment.session_end_ms > untilMs)) return { ref, state: 'unresolved' }
      return segment.session_start_ms === null || segment.session_start_ms === undefined
        ? { ref, state: 'resolved', summary: 'Authored transcript fixture segment; session alignment remains unknown.', context: { timebase: 'audio-relative', asset_id: segment.asset_id ?? '', at_ms: segment.start_ms } }
        : { ref, state: 'resolved', summary: 'Authored transcript fixture segment with explicit session alignment.', context: { timebase: 'session', at_ms: segment.session_start_ms } }
    })
  }

  async listCandidates(sourceSessionId: string, analysisId?: string): Promise<CandidateReadModel> {
    this.assertFixtureId(sourceSessionId)
    if (this.fixtureView === 'training') return { state: 'unavailable', evaluator_access: 'denied', message: 'Evaluator-only options are hidden for this fixture training view.', items: [] }
    if (analysisId && analysisId !== fixtureAnalysis.id) return { state: 'unavailable', evaluator_access: 'granted', message: 'No matching analysis fixture exists.', items: [] }
    return { state: this.candidates.length ? 'ready' : 'empty', evaluator_access: 'granted', analysis: fixtureAnalysis, items: this.candidates.map((candidate) => ({ ...candidate, supporting_evidence: [...candidate.supporting_evidence] })) }
  }

  subscribeSource(
    sourceSessionId: string,
    listener: (frame: ReplayFrameReadModel | null) => void,
    stateListener?: (state: SubscriptionState, message?: string) => void,
  ): () => void {
    this.assertFixtureId(sourceSessionId)
    let active = true
    stateListener?.('connected', 'Local authored fixture clock is connected.')
    const timer = setInterval(() => {
      if (active && this.status === 'RUNNING') listener(this.advancePlayback())
    }, 100)
    return () => {
      if (!active) return
      active = false
      clearInterval(timer)
      stateListener?.('disconnected', 'Fixture replay subscription closed.')
    }
  }

  subscribeAssist(sourceSessionId: string, listener: (state: AssistUpdateReadModel) => void): () => void {
    this.assertFixtureId(sourceSessionId)
    if (this.fixtureView === 'training') {
      listener({ type: 'unavailable', message: 'Evaluator-only assist content is hidden for this authored fixture training view.' })
      return () => undefined
    }
    const transcript: TranscriptReadModel = { state: this.transcriptItems.length ? 'ready' : 'empty', items: this.transcriptItems.map((segment) => ({ ...segment })), next_cursor: null }
    const candidates = this.listCandidates(sourceSessionId)
    void candidates.then((candidateReadModel) => listener({
      type: 'snapshot', transcripts: transcript, candidates: candidateReadModel,
      highlights: this.highlights.map((highlight) => ({ ...highlight })),
      review_annotations: [...this.reviewAnnotations], jobs: [],
    }))
    return () => undefined
  }

  async controlReview(sourceSessionId: string, control: ReviewControl): Promise<ReviewReceipt> {
    this.assertFixtureId(sourceSessionId)
    const requestId = control.request_id ?? `fixture-review-${Date.now()}-${this.commands.size + 1}`
    const body = JSON.stringify(control)
    const previous = this.commands.get(requestId)
    if (previous) {
      return previous.body === body
        ? previous.receipt
        : { request_id: requestId, revision: this.revision, status: 'conflict', message: 'Fixture request identity was reused with a different control.' }
    }
    if (control.expected_revision !== this.revision) {
      return { request_id: requestId, revision: this.revision, status: 'conflict', message: 'Fixture revision changed.' }
    }
    if (control.type === 'START') this.status = 'RUNNING'
    if (control.type === 'PAUSE') this.status = 'PAUSED'
    if (control.type === 'SEEK') {
      if (!Number.isSafeInteger(control.at_ms) || control.at_ms < 0 || control.at_ms > FIXTURE_FRAME_MS) throw new Error('Seek time must be inside the recorded fixture range.')
      this.playheadMs = control.at_ms
    }
    if (control.type === 'SET_SPEED') this.speed = control.speed
    this.revision += 1
    const receipt: ReviewReceipt = { request_id: requestId, revision: this.revision, status: 'accepted' }
    this.commands.set(requestId, { body, receipt })
    return receipt
  }

  async correctTranscript(sourceSessionId: string, segmentId: string, expectedRevision: number, text: string, reason = 'Fixture correction example', requestId = createFixtureRequestId('transcript')): Promise<ReviewReceipt> {
    this.assertFixtureId(sourceSessionId)
    if (this.fixtureView !== 'evaluator') return fixtureUnavailable(requestId, 'Transcript correction is hidden in the fixture training view.')
    const segment = this.transcriptItems.find((item) => item.id === segmentId)
    if (!segment) return fixtureUnavailable(requestId, 'The transcript segment is not in this fixture.')
    if (segment.revision === null) return fixtureUnavailable(requestId, 'The transcript fixture supplied no expected revision.')
    const body = JSON.stringify({ segmentId, expectedRevision, text, reason })
    const previous = this.reviewRequests.get(requestId)
    if (previous) return previous.body === body ? previous.receipt : fixtureConflict(requestId, segment.revision, 'Fixture request ID was reused with a different body.')

    if (!this.conflictExampleIssued && segment.id === 'SEG-FE05-COR-02') {
      this.conflictExampleIssued = true
      const remoteRevision = segment.revision + 1
      this.transcriptItems = this.transcriptItems.map((item) => item.id === segmentId
        ? { ...item, text: 'Authored concurrent revision: hold short at runway 27.', correction_status: 'corrected · authored reconciliation example', revision: remoteRevision }
        : item)
      const receipt = fixtureConflict(requestId, remoteRevision, 'Authored fixture conflict: a newer revision arrived. Draft retained; refresh/reconcile, then retry explicitly with a new request ID.')
      this.reviewRequests.set(requestId, { body, receipt })
      this.reviewAnnotations = [...this.reviewAnnotations, fixtureAnnotation(segmentId, 'corrected', remoteRevision, 'Authored concurrent revision arrived in the fixture.')]
      return receipt
    }
    if (expectedRevision !== segment.revision) {
      const receipt = fixtureConflict(requestId, segment.revision, 'Expected revision is stale. Refresh/reconcile and retry explicitly with a new request ID.')
      this.reviewRequests.set(requestId, { body, receipt })
      return receipt
    }

    const nextRevision = segment.revision + 1
    this.transcriptItems = this.transcriptItems.map((item) => item.id === segmentId
      ? { ...item, text, correction_status: 'corrected · authored fixture revision', revision: nextRevision }
      : item)
    const annotation = fixtureAnnotation(segmentId, 'corrected', nextRevision, reason, text)
    const receipt: ReviewReceipt = { request_id: requestId, revision: nextRevision, status: 'accepted', authority: 'fixture', message: 'Accepted in local fixture memory only; no server persistence.', annotation }
    this.reviewRequests.set(requestId, { body, receipt })
    this.reviewAnnotations = [...this.reviewAnnotations, annotation]
    return receipt
  }

  async reviewCandidate(sourceSessionId: string, candidateId: string, expectedRevision: number, decision: 'confirmed' | 'dismissed' | 'unresolved', reason = 'Fixture review example', analysisId?: string, requestId = createFixtureRequestId('candidate')): Promise<ReviewReceipt> {
    this.assertFixtureId(sourceSessionId)
    if (this.fixtureView !== 'evaluator') return fixtureUnavailable(requestId, 'Candidate review is hidden in the fixture training view.')
    if (analysisId && analysisId !== fixtureAnalysis.id) return fixtureUnavailable(requestId, 'The analysis ID is outside this fixture.')
    const index = this.candidates.findIndex((item) => item.id === candidateId)
    const candidate = this.candidates[index]
    if (!candidate) return fixtureUnavailable(requestId, 'The candidate is not in this fixture.')
    const body = JSON.stringify({ candidateId, expectedRevision, decision, reason, analysisId })
    const previous = this.reviewRequests.get(requestId)
    if (previous) return previous.body === body ? previous.receipt : fixtureConflict(requestId, candidate.revision ?? 0, 'Fixture request ID was reused with a different body.')
    if (candidate.revision !== expectedRevision) {
      const receipt = fixtureConflict(requestId, candidate.revision ?? 0, 'Expected revision is stale. Refresh/reconcile and retry explicitly with a new request ID.')
      this.reviewRequests.set(requestId, { body, receipt })
      return receipt
    }
    const nextRevision = expectedRevision + 1
    this.candidates[index] = { ...candidate, revision: nextRevision, review_status: decision }
    const annotation = fixtureAnnotation(candidateId, decision, nextRevision, reason)
    const receipt: ReviewReceipt = { request_id: requestId, revision: nextRevision, status: 'accepted', authority: 'fixture', message: 'Accepted in local fixture memory only; no server persistence.', annotation }
    this.reviewRequests.set(requestId, { body, receipt })
    this.reviewAnnotations = [...this.reviewAnnotations, annotation]
    return receipt
  }

  async reviewHighlight(sourceSessionId: string, highlightId: string, expectedRevision: number, decision: 'confirmed' | 'dismissed' | 'unresolved', reason = 'Fixture review example', requestId = createFixtureRequestId('highlight')): Promise<ReviewReceipt> {
    this.assertFixtureId(sourceSessionId)
    if (this.fixtureView !== 'evaluator') return fixtureUnavailable(requestId, 'Highlight review is hidden in the fixture training view.')
    const index = this.highlights.findIndex((item) => item.id === highlightId)
    const highlight = this.highlights[index]
    if (!highlight) return fixtureUnavailable(requestId, 'The highlight is not in this fixture.')
    const body = JSON.stringify({ highlightId, expectedRevision, decision, reason })
    const previous = this.reviewRequests.get(requestId)
    if (previous) return previous.body === body ? previous.receipt : fixtureConflict(requestId, highlight.revision ?? 0, 'Fixture request ID was reused with a different body.')
    if (highlight.revision !== expectedRevision) {
      const receipt = fixtureConflict(requestId, highlight.revision ?? 0, 'Expected revision is stale. Refresh/reconcile and retry explicitly with a new request ID.')
      this.reviewRequests.set(requestId, { body, receipt })
      return receipt
    }
    const nextRevision = expectedRevision + 1
    this.highlights[index] = { ...highlight, revision: nextRevision, status: decision }
    const annotation = fixtureAnnotation(highlightId, decision, nextRevision, reason)
    const receipt: ReviewReceipt = { request_id: requestId, revision: nextRevision, status: 'accepted', authority: 'fixture', message: 'Accepted in local fixture memory only; no server persistence.', annotation }
    this.reviewRequests.set(requestId, { body, receipt })
    this.reviewAnnotations = [...this.reviewAnnotations, annotation]
    return receipt
  }

  private makeFrame(requestedMs: number): ReplayFrameReadModel {
    const archived = requestedMs >= FIXTURE_FRAME_MS ? fixtureReplaySnapshot : fixtureStartFrame
    const snapshot: ReplaySnapshotReadModel = {
      ...archived,
      viewer_role: this.fixtureView === 'evaluator' ? 'fixture-evaluator' : 'fixture-training',
      viewer_label: this.fixtureView === 'evaluator' ? 'Authored fixture evaluator view' : 'Authored fixture training view',
      playback_ms: this.playheadMs,
      review_end_ms: FIXTURE_FRAME_MS,
      revision: this.revision,
      status: this.status,
      speed: this.speed,
      review_annotations: [...this.reviewAnnotations],
    }
    return {
      source_session_id: fixtureSession.id,
      requested_ms: requestedMs,
      frame_ms: snapshot.sim_ms,
      track_count: snapshot.tracks.length,
      alert_count: snapshot.alerts.length,
      quality: snapshot.runway.data_quality === 'UNKNOWN' ? 'unknown' : 'degraded',
      state: snapshot.runway.data_quality === 'UNKNOWN' ? 'degraded' : 'degraded',
      snapshot,
    }
  }

  private advancePlayback(): ReplayFrameReadModel {
    if (this.status === 'RUNNING') {
      this.playheadMs = Math.min(FIXTURE_FRAME_MS, this.playheadMs + Math.max(1, Math.round(100 * this.speed)))
      if (this.playheadMs >= FIXTURE_FRAME_MS) this.status = 'PAUSED'
    }
    return this.makeFrame(this.playheadMs)
  }

  private assertFixtureId(sourceSessionId: string): void {
    if (sourceSessionId !== fixtureSession.id) throw new Error(`Fixture source not found: ${sourceSessionId}`)
  }
}

function createFixtureRequestId(prefix: string): string {
  return `fixture-${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

function fixtureConflict(requestId: string, revision: number, message: string): ReviewReceipt {
  return { request_id: requestId, revision, status: 'conflict', authority: 'fixture', message }
}

function fixtureUnavailable(requestId: string, message: string): ReviewReceipt {
  return { request_id: requestId, revision: 0, status: 'unavailable', authority: 'fixture', message }
}

function fixtureAnnotation(targetId: string, decision: ReviewAnnotationReadModel['decision'], revision: number, reason: string, correction?: string): ReviewAnnotationReadModel {
  return {
    kind: 'review_annotation', id: `FIXTURE-ANNOTATION-${targetId}-${revision}`, target_id: targetId, decision,
    reviewer: 'Authored fixture evaluator', timestamp: 'authored-fixture-time-not-audit-time', session_ms: null, revision,
    reason, ...(correction === undefined ? {} : { correction }),
  }
}
