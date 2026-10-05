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
} from '../contracts/replayReview'

const scenario: ScenarioReadModel = {
  id: 'FE-01-FIXTURE',
  title: 'Frontend scaffold fixture',
  objective: 'Exercise the typed UI adapter with authored, non-operational fixture metadata.',
  version: 'fixture-1',
  duration_s: 60,
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
  track_count: 0,
  alert_count: 0,
  event_count: 1,
  runway_state: 'unknown',
  data_quality: 'fixture-only',
}

const fixtureEvents: EventReadModel[] = [
  {
    id: 'SYN-FE-01:1',
    ordinal: 1,
    sim_ms: 0,
    type: 'FIXTURE_READY',
    message: 'Authored FE-01 UI fixture; not a simulator run or operational evidence.',
  },
]

function makeFrame(requestedMs: number): ReplayFrameReadModel {
  return {
    source_session_id: fixtureSession.id,
    requested_ms: requestedMs,
    frame_ms: 0,
    track_count: 0,
    alert_count: 0,
    quality: 'unknown',
  }
}

export class FixtureReplayReviewAdapter implements ReplayReviewAdapter {
  readonly mode = 'fixture' as const
  private revision = 0
  private playheadMs = 0
  private speed: 0.5 | 1 | 2 | 4 = 1
  private status: 'READY' | 'RUNNING' | 'PAUSED' = 'READY'

  async loadOverview(): Promise<OverviewReadModel> {
    return {
      health: { state: 'fixture', version: 'fixture-1', mode: 'fixture' },
      scenarios: [scenario],
      source_label: 'SYNTHETIC / NOT OPERATIONALLY VALIDATED · INLINE FE-01 FIXTURE',
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

  async loadFrame(sourceSessionId: string, atMs: number): Promise<ReplayFrameReadModel> {
    this.assertFixtureId(sourceSessionId)
    if (!Number.isFinite(atMs) || atMs < 0) throw new Error('Replay time must be a nonnegative finite number.')
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

  async resolveEvidence(sourceSessionId: string, refs: EvidenceRef[]): Promise<EvidenceResolution[]> {
    this.assertFixtureId(sourceSessionId)
    return refs.map((ref) => ({ ref, state: 'unresolved' }))
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
