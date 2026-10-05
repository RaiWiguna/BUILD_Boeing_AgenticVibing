export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }

export interface ApiScenarioWire {
  id: string
  title: string
  objective: string
  version: string
  duration_s: number
  domain_review: string
  aircraft_count?: number
  vehicle_count?: number
}

export interface ApiLayoutWire {
  id: string
  version: string
  name: string
  coordinate_system: 'LOCAL_METRES'
  physical_runway_id: string
  runway: Array<[number, number]>
  protected_area: Array<[number, number]>
  taxiways: Array<Array<[number, number]>>
  hold_lines: Array<Array<[number, number]>>
  directions: Record<string, string>
  note: string
}

export interface ApiTrackWire {
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
  runway: '09' | '27'
  route: Array<[number, number]>
  owner: 'tower' | 'ground'
  observed_ms: number
  received_ms: number
  source: string
  event_id: string
  stale: boolean
}

export interface ApiPredictionWire {
  object_id: string
  physical_runway_id?: string
  direction?: string
  interval_index?: number
  entry_s: number
  exit_s: number
  exit_unknown: boolean
  threshold_eta_s: number | null
  assumed_entry_range_s: number[]
  assumed_exit_range_s: number[]
  model_version?: string
  source_event_id?: string
}

export interface ApiEventWire {
  id: string
  ordinal: number
  sim_ms: number
  type: string
  message: string
  [key: string]: JsonValue
}

export interface ApiSnapshotWire {
  session_id: string
  kind: 'training' | 'review'
  sequence: number
  sim_ms: number
  revision: number
  status: string
  speed: number
  metadata: {
    id: string
    scenario: ApiScenarioWire
    condition: string
    seed: number
    config: Record<string, JsonValue>
    engine_version: string
    config_version?: string
    kind?: string
    parent?: { session_id: string; frame_ms: number } | null
    created_utc?: number
  }
  layout: ApiLayoutWire
  tracks: ApiTrackWire[]
  clearances: Array<{
    id: string
    target: string
    instruction: string
    runway: '09' | '27'
    issued_ms: number
    issuer: string
    status: string
    readback: string
    event_id: string
  }>
  requests: Array<{ target: string; completed: boolean; requested_ms: number }>
  predictions: ApiPredictionWire[]
  runway: { open: boolean; state: string; data_quality: string; observed_occupants: string[]; degraded_ids: string[] }
  alerts: Array<{
    id: string
    rule: string
    objects: string[]
    severity: string
    reason: string
    status: string
    created_ms: number
    calculated_ms: number
    updated_ms?: number
    data_degraded: boolean
    metrics: Record<string, JsonValue>
    evidence_event_ids: string[]
    track_ages_ms: Record<string, number>
    assumptions: string
  }>
  events: ApiEventWire[]
  acknowledgements: Array<{ alert_id: string; actor: string; sim_ms: number }>
  assessments: ApiEventWire[]
  complexity: Record<string, { score: number; level: string; components: Record<string, number>; weights: Record<string, number>; label: string }>
  error: string | null
  seat: { role: 'instructor' | 'tower' | 'ground' | 'observer'; label: string }
  server_sent_utc_ms: number
  source_session_id?: string
  review_end_ms?: number
  playback_ms?: number
  review_annotations?: Array<Record<string, JsonValue>>
}

export interface ApiEventPageWire {
  items: ApiEventWire[]
  next_cursor: number
}

export interface ApiTranscriptSegmentWire {
  id: string
  asset_id: string
  start_ms: number
  end_ms: number
  channel_id: string
  speaker_label: string | null
  speaker_source: string | null
  speaker_confidence: number | null
  text: string
  language: string | null
  asr_confidence: number | null
  model_version: string | null
  correction_status: string
  revision?: number
  raw_text?: string
  session_start_ms?: number | null
}

export interface ApiTranscriptPageWire {
  items: ApiTranscriptSegmentWire[]
  next_cursor: string | null
  job?: ApiTranscriptionJobWire
}

export interface ApiTranscriptionJobWire {
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
  chunk_progress: JsonValue | null
}

export interface ApiEvidenceRefWire {
  kind: 'session_event' | 'transcript_segment' | 'detector_alert'
  id: string
}

export interface ApiEvidenceResolutionWire {
  ref: ApiEvidenceRefWire
  state: 'resolved' | 'unresolved'
  summary?: string
  item?: JsonValue
}

export interface ApiHighlightWire {
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

export interface ApiOptionWire {
  id: string
  replay_analysis_id: string
  option_statement: string
  rationale: string
  supporting_evidence_ids: ApiEvidenceRefWire[]
  preconditions: string[]
  unknowns: string[]
  source_version: string
  model_version: string
  rule_version: string
  review_status: string
}

export interface ApiReviewAnnotationWire {
  id?: string
  target_id: string
  decision: 'corrected' | 'confirmed' | 'dismissed' | 'unresolved'
  reviewer: string
  timestamp: number
  revision?: number
  correction?: string | null
  reason?: string | null
}

export interface ApiReviewReceiptWire {
  request_id: string
  revision: number
  status: 'accepted' | 'conflict' | 'unavailable'
  message?: string
  annotation?: ApiReviewAnnotationWire
}

interface ApiAssistMessageBase {
  schema_version: 'assist-1'
  source_session_id: string
  sequence: number
}

export type ApiAssistMessageWire = ApiAssistMessageBase & (
  | { type: 'snapshot'; payload: { jobs: ApiTranscriptionJobWire[]; transcripts: ApiTranscriptSegmentWire[]; highlights: ApiHighlightWire[]; options: ApiOptionWire[]; review_annotations: ApiReviewAnnotationWire[] } }
  | { type: 'job_progress'; payload: { job: ApiTranscriptionJobWire } }
  | { type: 'segment'; payload: { segment: ApiTranscriptSegmentWire } }
  | { type: 'highlight'; payload: { highlight: ApiHighlightWire } }
  | { type: 'option'; payload: { option: ApiOptionWire } }
  | { type: 'review_annotation'; payload: { annotation: ApiReviewAnnotationWire } }
  | { type: 'error'; payload: { code: string; message: string } }
)

export type ApiWebSocketMessageWire =
  | { profile: 'source'; snapshot: ApiSnapshotWire }
  | { profile: 'assist'; message: ApiAssistMessageWire }
