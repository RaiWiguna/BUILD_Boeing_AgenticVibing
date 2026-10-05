import type {
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
  ReviewControl,
  ReviewReceipt,
  ScenarioReadModel,
  SessionReadModel,
  SessionViewReadModel,
  SnapshotReadModel,
  TranscriptReadModel,
  ReplaySnapshotReadModel,
} from '../contracts/replayReview'

export const FIXTURE_FRAME_MS = 74_600

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
  event_count: 2,
  runway_state: 'OCCUPIED',
  data_quality: 'DEGRADED · SYNTHETIC',
}

const fixtureEvents: EventReadModel[] = [
  {
    id: 'SYN-FE-03:TRACK:AC-01',
    ordinal: 1,
    sim_ms: FIXTURE_FRAME_MS - 70,
    type: 'TRACK',
    message: 'Synthetic observed aircraft track sample.',
    target: 'AC-01',
    observed_ms: FIXTURE_FRAME_MS - 420,
    received_ms: FIXTURE_FRAME_MS - 70,
  },
  {
    id: 'SYN-FE-03:TRACK:TUG-04',
    ordinal: 2,
    sim_ms: FIXTURE_FRAME_MS - 240,
    type: 'TRACK',
    message: 'Synthetic last-known vehicle position; this sample is stale at the displayed frame.',
    target: 'TUG-04',
    observed_ms: FIXTURE_FRAME_MS - 3_600,
    received_ms: FIXTURE_FRAME_MS - 240,
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
    { id: 'CLR-FE-03-01', target: 'TUG-04', instruction: 'HOLD_SHORT', runway: '27', issued_ms: FIXTURE_FRAME_MS - 4_000, issuer: 'synthetic-scenario', status: 'ISSUED', readback: 'ACKNOWLEDGED', event_id: 'SYN-FE-03:CLR:01' },
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
  events: fixtureEvents,
  event_count: fixtureEvents.length,
  track_count: 2,
  alert_count: 1,
}

function makeFrame(requestedMs: number): ReplayFrameReadModel {
  return {
    source_session_id: fixtureSession.id,
    requested_ms: requestedMs,
    frame_ms: FIXTURE_FRAME_MS,
    track_count: fixtureReplaySnapshot.tracks.length,
    alert_count: fixtureReplaySnapshot.alerts.length,
    quality: 'degraded',
    state: 'degraded',
    snapshot: fixtureReplaySnapshot,
  }
}

export class FixtureReplayReviewAdapter implements ReplayReviewAdapter {
  readonly mode = 'fixture' as const
  private revision = 0
  private playheadMs = FIXTURE_FRAME_MS
  private speed: 0.5 | 1 | 2 | 4 = 1
  private status: 'READY' | 'RUNNING' | 'PAUSED' = 'READY'

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
    if (!Number.isFinite(atMs) || atMs < 0) throw new Error('Replay time must be a nonnegative finite number.')
    if (atMs < FIXTURE_FRAME_MS) throw new Error('The fixture has no archived frame at or before this replay time.')
    return makeFrame(atMs)
  }

  async listEvents(sourceSessionId: string, cursor: number, untilMs?: number): Promise<EventPageReadModel> {
    this.assertFixtureId(sourceSessionId)
    const rows = fixtureEvents.filter((event) => event.ordinal > cursor && (untilMs === undefined || event.sim_ms <= untilMs))
    return { items: rows, next_cursor: rows.at(-1)?.ordinal ?? cursor, state: rows.length ? 'ready' : 'empty' }
  }

  async listTranscript(sourceSessionId: string): Promise<TranscriptReadModel> {
    this.assertFixtureId(sourceSessionId)
    return { state: 'unavailable', items: [] }
  }

  async resolveEvidence(sourceSessionId: string, refs: EvidenceRef[], untilMs?: number): Promise<EvidenceResolution[]> {
    this.assertFixtureId(sourceSessionId)
    const eventsById = new Map(fixtureEvents.map((event) => [event.id, event]))
    return refs.map((ref) => {
      if (ref.kind !== 'session_event') return { ref, state: 'unavailable' }
      const event = eventsById.get(ref.id)
      return event && (untilMs === undefined || event.sim_ms <= untilMs)
        ? { ref, state: 'resolved', summary: `${event.type}: ${event.message}` }
        : { ref, state: 'unresolved' }
    })
  }

  async listCandidates(sourceSessionId: string): Promise<CandidateReadModel> {
    this.assertFixtureId(sourceSessionId)
    return { state: 'unavailable', items: [] }
  }

  subscribeSource(sourceSessionId: string): () => void {
    this.assertFixtureId(sourceSessionId)
    return () => undefined
  }

  subscribeAssist(sourceSessionId: string, _listener: (state: AssistUpdateReadModel) => void): () => void {
    this.assertFixtureId(sourceSessionId)
    return () => undefined
  }

  async controlReview(sourceSessionId: string, control: ReviewControl): Promise<ReviewReceipt> {
    this.assertFixtureId(sourceSessionId)
    if (control.expected_revision !== this.revision) {
      return { request_id: `fixture-${this.revision}`, revision: this.revision, status: 'conflict', message: 'Fixture revision changed.' }
    }
    if (control.type === 'START') this.status = 'RUNNING'
    if (control.type === 'PAUSE') this.status = 'PAUSED'
    if (control.type === 'SEEK') {
      if (!Number.isFinite(control.at_ms) || control.at_ms < 0) throw new Error('Seek time must be nonnegative.')
      this.playheadMs = control.at_ms
    }
    if (control.type === 'SET_SPEED') this.speed = control.speed
    this.revision += 1
    return { request_id: `fixture-${this.revision}`, revision: this.revision, status: 'accepted' }
  }

  async correctTranscript(sourceSessionId: string, _segmentId: string, expectedRevision: number, _text: string): Promise<ReviewReceipt> {
    this.assertFixtureId(sourceSessionId)
    return {
      request_id: `fixture-${this.revision}`,
      revision: this.revision,
      status: expectedRevision === this.revision ? 'unavailable' : 'conflict',
      message: 'No transcript fixture is loaded.',
    }
  }

  async reviewCandidate(sourceSessionId: string, _candidateId: string, expectedRevision: number, _decision: 'confirmed' | 'dismissed' | 'unresolved'): Promise<ReviewReceipt> {
    this.assertFixtureId(sourceSessionId)
    return {
      request_id: `fixture-${this.revision}`,
      revision: this.revision,
      status: expectedRevision === this.revision ? 'unavailable' : 'conflict',
      message: 'No evaluator candidate fixture is loaded.',
    }
  }

  private assertFixtureId(sourceSessionId: string): void {
    if (sourceSessionId !== fixtureSession.id) throw new Error(`Fixture source not found: ${sourceSessionId}`)
  }
}
