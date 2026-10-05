export type AdapterMode = 'fixture' | 'api'

export type UiState =
  | 'loading'
  | 'empty'
  | 'ready'
  | 'degraded'
  | 'disconnected'
  | 'unauthorized'
  | 'conflict'
  | 'error'

export interface ScenarioReadModel {
  id: string
  title: string
  objective: string
  version: string
  duration_s: number
  domain_review: string
  aircraft_count?: number
  vehicle_count?: number
}

export type BackendHealth =
  | { state: 'fixture'; version: string; mode: 'fixture' }
  | { state: 'online'; version: string; mode: string; single_writer: boolean }

export interface OverviewReadModel {
  health: BackendHealth
  scenarios: ScenarioReadModel[]
  source_label: string
}

export interface SessionReadModel {
  id: string
  status: string
  scenario: ScenarioReadModel
  condition: string
  seed: number
  kind: 'training' | 'review' | 'unknown'
  created_utc_ms: number | null
}

export interface OperatorAccess {
  token: string
  expires_in_s: number
}

export interface SnapshotReadModel {
  session_id: string
  sim_ms: number
  sequence: number
  revision: number
  status: string
  speed: number
  kind: 'training' | 'review' | 'unknown'
  seed: number
  scenario: ScenarioReadModel
  scenario_title: string
  condition: string
  track_count: number
  alert_count: number
  event_count: number
  runway_state: string
  data_quality: string
}

export interface EventReadModel {
  id: string
  ordinal: number
  sim_ms: number
  type: string
  message: string
  target?: string
  actor?: string
  audit_utc_s?: number
  observed_ms?: number
  received_ms?: number
  evidence_event_ids?: string[]
  details?: Record<string, unknown>
}

export interface SessionViewReadModel {
  session: SessionReadModel
  snapshot: SnapshotReadModel
  events: EventReadModel[]
}

export interface DashboardAdapter {
  readonly mode: AdapterMode
  loadOverview(signal?: AbortSignal): Promise<OverviewReadModel>
  authenticateOperator(key: string, signal?: AbortSignal): Promise<OperatorAccess>
  listSessions(token: string, signal?: AbortSignal): Promise<SessionReadModel[]>
  createSession(token: string, scenarioId: string, signal?: AbortSignal): Promise<SessionReadModel>
  loadSession(token: string, sessionId: string, signal?: AbortSignal): Promise<SessionViewReadModel>
}

export interface ReplaySourceReadModel {
  source_session_id: string
  source_kind: 'synthetic' | 'authorized_replay' | 'unknown'
  label: string
  provenance: string
  source_version: string | null
  quality: 'known' | 'degraded' | 'unknown'
}

export interface ReplayTrackReadModel {
  id: string
  callsign: string
  kind: 'aircraft' | 'vehicle'
  x_m: number
  y_m: number
  speed_mps: number
  heading_deg: number
  phase: string
  length_m: number
  width_m: number
  runway: string
  route: Array<[number, number]>
  owner: string
  observed_ms: number
  received_ms: number
  source: string
  event_id: string
  stale: boolean
}

export interface ReplaySnapshotReadModel {
  session_id: string
  source_session_id: string
  kind: 'training' | 'review'
  sequence: number
  sim_ms: number
  playback_ms: number | null
  revision: number
  status: string
  speed: number
  scenario_id: string
  scenario_title: string
  condition: string
  source_version: string
  layout: {
    id: string
    version: string
    name: string
    coordinate_system: string
    physical_runway_id: string
    runway: Array<[number, number]>
    protected_area: Array<[number, number]>
    taxiways: Array<Array<[number, number]>>
    hold_lines: Array<Array<[number, number]>>
    directions: Record<string, string>
    note: string
  }
  tracks: ReplayTrackReadModel[]
  clearances: Array<{ id: string; target: string; instruction: string; runway: string; issued_ms: number; issuer: string; status: string; readback: string; event_id: string }>
  predictions: Array<{ object_id: string; physical_runway_id?: string; direction?: string; interval_index?: number; entry_s: number; exit_s: number; exit_unknown: boolean; threshold_eta_s: number | null; assumed_entry_range_s: number[]; assumed_exit_range_s: number[]; model_version?: string; source_event_id?: string }>
  alerts: Array<{ id: string; rule: string; objects: string[]; severity: string; reason: string; status: string; created_ms: number; calculated_ms: number; updated_ms?: number; data_degraded: boolean; metrics: Record<string, unknown>; evidence_event_ids: string[]; track_ages_ms: Record<string, number>; assumptions: string }>
  runway: { open: boolean; state: string; data_quality: string; observed_occupants: string[]; degraded_ids: string[] }
  events: EventReadModel[]
  event_count: number
  track_count: number
  alert_count: number
}

export interface ReplayFrameReadModel {
  source_session_id: string
  requested_ms: number
  frame_ms: number
  track_count: number
  alert_count: number
  quality: 'known' | 'degraded' | 'unknown'
  state?: 'ready' | 'degraded' | 'disconnected' | 'unavailable'
  connection_message?: string
  snapshot?: ReplaySnapshotReadModel
}

export interface EventPageReadModel {
  items: EventReadModel[]
  next_cursor: number
  state: Exclude<UiState, 'loading' | 'disconnected' | 'unauthorized' | 'conflict' | 'error'>
}

export interface EvidenceRef {
  kind: 'session_event' | 'transcript_segment' | 'detector_alert'
  id: string
}

export interface EvidenceResolution {
  ref: EvidenceRef
  state: 'resolved' | 'unresolved' | 'unavailable'
  summary?: string
}

export interface TranscriptionJobReadModel {
  id: string
  asset_id: string
  status: 'queued' | 'running' | 'needs-review' | 'completed' | 'failed' | 'cancelled'
  provider: string | null
  model: string | null
  version: string | null
  language: string | null
  started_utc: number | null
  finished_utc: number | null
  error: string | null
  chunk_progress: unknown
}

export interface TranscriptReadModel {
  state: 'ready' | 'empty' | 'unavailable'
  items: Array<{
    id: string
    asset_id?: string
    start_ms: number
    end_ms: number
    channel_id?: string
    speaker_label?: string | null
    speaker_source?: string | null
    speaker_confidence?: number | null
    text: string
    raw_text?: string
    language?: string | null
    asr_confidence?: number | null
    model_version?: string | null
    correction_status?: string
    revision: number
    session_start_ms?: number | null
  }>
  next_cursor?: string | null
  job?: TranscriptionJobReadModel
}

export interface CandidateReadModel {
  state: 'ready' | 'empty' | 'unavailable'
  items: Array<{
    id: string
    replay_analysis_id?: string
    statement: string
    rationale?: string
    supporting_evidence: EvidenceRef[]
    preconditions?: string[]
    unknowns?: string[]
    source_version?: string
    model_version?: string
    rule_version?: string
    review_status: string
  }>
}

export interface AssistHighlightReadModel {
  id: string
  category: string
  review_priority: string
  statement: string
  transcript_segment_ids: string[]
  session_event_ids: string[]
  uncertainty: string
  provider_version: string
  rule_version: string
  status: string
  linked_alert_id?: string | null
  link_status?: 'linked' | 'possible_link' | null
}

export interface ReviewAnnotationReadModel {
  id?: string
  target_id: string
  decision: 'corrected' | 'confirmed' | 'dismissed' | 'unresolved'
  reviewer: string
  timestamp: number
  revision?: number
  correction?: string | null
  reason?: string | null
}

export type AssistUpdateReadModel =
  | { type: 'snapshot'; transcripts: TranscriptReadModel; candidates: CandidateReadModel; highlights: AssistHighlightReadModel[]; review_annotations: ReviewAnnotationReadModel[]; jobs: TranscriptionJobReadModel[] }
  | { type: 'transcript'; data: TranscriptReadModel }
  | { type: 'candidate'; data: CandidateReadModel }
  | { type: 'highlight'; data: AssistHighlightReadModel }
  | { type: 'review_annotation'; data: ReviewAnnotationReadModel }
  | { type: 'job'; data: TranscriptionJobReadModel }
  | { type: 'state'; state: SubscriptionState; message?: string }
  | { type: 'unavailable'; message: string }
  | { type: 'error'; message: string }

export type SubscriptionState = 'loading' | 'connected' | 'disconnected' | 'unauthorized' | 'error' | 'unavailable'

export type ReviewControl =
  | { type: 'START' | 'PAUSE'; expected_revision: number; request_id?: string }
  | { type: 'SEEK'; at_ms: number; expected_revision: number; request_id?: string }
  | { type: 'SET_SPEED'; speed: 0.5 | 1 | 2 | 4; expected_revision: number; request_id?: string }

export interface ReviewReceipt {
  request_id: string
  revision: number
  status: 'accepted' | 'conflict' | 'unavailable'
  message?: string
}

export interface ReplayReviewAdapter extends DashboardAdapter {
  loadSource(sourceSessionId: string, signal?: AbortSignal): Promise<ReplaySourceReadModel>
  loadFrame(sourceSessionId: string, at_ms: number, signal?: AbortSignal): Promise<ReplayFrameReadModel>
  listEvents(sourceSessionId: string, cursor: number, until_ms?: number, signal?: AbortSignal): Promise<EventPageReadModel>
  listTranscript(sourceSessionId: string, cursor: string | null, until_ms?: number, signal?: AbortSignal): Promise<TranscriptReadModel>
  resolveEvidence(sourceSessionId: string, refs: EvidenceRef[], until_ms?: number, signal?: AbortSignal): Promise<EvidenceResolution[]>
  listCandidates(sourceSessionId: string, analysisId: string, signal?: AbortSignal): Promise<CandidateReadModel>
  subscribeSource(sourceSessionId: string, listener: (frame: ReplayFrameReadModel | null) => void, stateListener?: (state: SubscriptionState, message?: string) => void): () => void
  subscribeAssist(sourceSessionId: string, listener: (state: AssistUpdateReadModel) => void, stateListener?: (state: SubscriptionState, message?: string) => void): () => void
  controlReview(sourceSessionId: string, control: ReviewControl): Promise<ReviewReceipt>
  correctTranscript(sourceSessionId: string, segmentId: string, expected_revision: number, text: string, reason?: string, request_id?: string): Promise<ReviewReceipt>
  reviewCandidate(sourceSessionId: string, candidateId: string, expected_revision: number, decision: 'confirmed' | 'dismissed' | 'unresolved', reason?: string, analysisId?: string, request_id?: string): Promise<ReviewReceipt>
}

export type AsyncState<T> =
  | { state: 'loading' }
  | { state: 'empty' }
  | { state: 'ready'; data: T }
  | { state: 'degraded'; data: T; message: string }
  | { state: 'disconnected' | 'unauthorized' | 'conflict' | 'error'; message: string }
