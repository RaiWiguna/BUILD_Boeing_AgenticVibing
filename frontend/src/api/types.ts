/**
 * Frontend wire types.
 *
 * - Types re-exported from `./generated/contracts` are the frozen contract 1.0.0.
 * - Types under "PROPOSED_CONTRACT" are view DTOs the UI needs but contract 1.0.0
 *   does not define yet (session catalogue, permission matrix, accounts/grants,
 *   export jobs, display labels, projections). They are inputs for contract
 *   reconciliation before backend integration — not a unilateral contract change.
 */
import type {
  AnalysisRun,
  Association,
  Brief,
  ClockMapping,
  Coverage,
  CriticalSlot,
  Evidence1,
  FactualItem,
  Finding,
  GeometryResult,
  Intent,
  MemoryEvent,
  OpenLoop,
  Option,
  PlaybackState,
  ProviderProfile,
  QueryAnswer,
  Review,
  Snapshot,
  SourceEvent,
  SourceManifest,
  StreamEvent,
  TimeRange,
  Track,
  TranscriptSegment,
} from './generated/contracts';

export type {
  AnalysisRun,
  Association,
  Brief,
  ClockMapping,
  Coverage,
  CriticalSlot,
  FactualItem,
  Finding,
  GeometryResult,
  Intent,
  MemoryEvent,
  OpenLoop,
  Option,
  PlaybackState,
  ProviderProfile,
  QueryAnswer,
  Review,
  Snapshot,
  SourceEvent,
  SourceManifest,
  StreamEvent,
  TimeRange,
  Track,
  TranscriptSegment,
};
export type Evidence = Evidence1;

/* ── Contract enum aliases ─────────────────────────────────────────── */
export type Quality = Finding['quality'];
export type FindingCategory = Finding['category'];
export type FindingPriority = Finding['priority'];
export type FindingStatus = Finding['status'];
export type Applicability = Finding['applicability'];
export type OptionReviewStatus = Option['review_status'];
export type ReviewDecision = Review['decision'];
export type SpeechAct = Intent['speech_act'];
export type RoleCandidate = Intent['role_candidate'];
export type AssociationStatus = Association['status'];
export type AssociationRelationship = Association['relationship'];
export type InstructionState = MemoryEvent['instruction'];
export type InterpretationState = MemoryEvent['interpretation'];
export type ReadbackState = MemoryEvent['readback'];
export type MovementState = MemoryEvent['movement'];
export type ReviewerState = MemoryEvent['reviewer'];
export type OpenLoopKind = OpenLoop['kind'];
export type OpenLoopStatus = OpenLoop['status'];
export type ReplayMode = Snapshot['mode'];
export type RunStatus = AnalysisRun['status'];
export type SourceKind = SourceManifest['source_kind'];
export type DomainValidation = SourceManifest['domain_validation'];
export type QueryStatus = QueryAnswer['status'];
export type ProviderReadiness = ProviderProfile['readiness'];
export type TranscriptOrigin = TranscriptSegment['origin'];
export type StreamEventType = StreamEvent['type'];

/* ── PROPOSED_CONTRACT: identity, roles, grants ────────────────────── */
export type Role = 'EVALUATOR' | 'CONTROLLER_REVIEW' | 'OBSERVER' | 'ADMIN';
export type Capability =
  | 'session.read'
  | 'session.import'
  | 'analysis.create'
  | 'audio.play'
  | 'review.write'
  | 'export.create'
  | 'truth.read'
  | 'admin.manage';

export interface Account {
  id: string;
  name: string;
  email: string;
  role: Role;
  active: boolean;
  last_login_at: string | null;
  must_change_password: boolean;
}

export interface AuthSession {
  account: Account;
  capabilities: Capability[];
  expires_at: string;
  idle_expires_at: string;
}

export interface SessionGrant {
  id: string;
  session_id: string;
  account_id: string;
  capabilities: Capability[];
  granted_by: string;
  granted_at: string;
}

/* ── PROPOSED_CONTRACT: permission matrix (PRD §9.2) ───────────────── */
export type PermissionState = 'ALLOWED' | 'DENIED' | 'UNDETERMINED';
export type PermissionKey =
  | 'local_read'
  | 'cloud_audio'
  | 'cloud_transcript'
  | 'reviewer_access'
  | 'report_export'
  | 'audio_export';
export type PermissionMatrix = Record<PermissionKey, { state: PermissionState; note: string }>;

/* ── PROPOSED_CONTRACT: catalogue / session detail ─────────────────── */
export type AnalysisState = 'NOT_ANALYZED' | RunStatus;
export type SessionLifecycle = 'PREPARING' | 'READY' | 'ARCHIVED';

export interface ChannelInfo {
  index: number;
  label: string; // "Tower", "Ground"
  role: string; // "ATC", "Pilot / vehicle"
}

export interface EntityInfo {
  id: string;
  callsign: string;
  kind: 'AIRCRAFT' | 'VEHICLE';
  type: string; // "A320", "Follow-me"
  role: string; // "Departure", "Ground vehicle"
  aliases: string[];
}

export interface Notice {
  id: string;
  tone: 'notice' | 'discrepancy' | 'muted' | 'data';
  title: string;
  detail: string;
}

export interface SessionSummary {
  id: string;
  title: string;
  context: string; // "Departure · Class B"
  source_kind: SourceKind;
  lifecycle: SessionLifecycle;
  duration_ms: number;
  recorded_at: string;
  updated_at: string;
  source_ready: boolean;
  analysis: AnalysisState;
  domain_validation: DomainValidation;
  channels: ChannelInfo[];
  has_tracks: boolean;
  has_layout: boolean;
  layout_label: string | null;
  latest_run_id: string | null;
  latest_run_label: string | null;
  open_findings: number;
  notices: Notice[];
  /** DEMO track: where the session lives. Absent for in-browser MOCK sessions. */
  origin?: 'MOCK' | 'DEMO_BACKEND';
}

export interface RunView {
  run: AnalysisRun;
  label: string; // "#03"
  input_revision: number;
  created_at: string;
  completed_at: string | null;
  failure: { code: ApiErrorCode; message: string } | null;
  coverage_note: string | null;
}

export interface LayoutView {
  version: string;
  units: 'm';
  caption: string;
  runways: { id: string; ends: [string, string]; polygon: [number, number][]; centerline: [[number, number], [number, number]] }[];
  hold_lines: { id: string; label: string; runway: string; points: [number, number][] }[];
  taxiways: { id: string; label: string; path: [number, number][]; label_at: [number, number] }[];
  bounds: { min_x: number; max_x: number; min_y: number; max_y: number };
  /** Optional initial viewport inside `bounds` (DEMO layouts span whole airports). */
  focus?: { min_x: number; max_x: number; min_y: number; max_y: number };
}

/* ── DEMO track (ADR 0003): real audio + live transcript for backend workspaces ── */
export interface DemoWord {
  text: string;
  start_ms: number;
  end_ms: number;
}

export interface DemoLiveSegment {
  /** Segment key ("T-03"); maps to the transcript segment via `labels`. */
  key: string;
  segment_id: string;
  confidence: number | null;
  speaker: string;
  /** Recogniser chunk ordinal (0-based); the STT ran in fixed-length chunks. */
  chunk: number;
  /** Recording the segment belongs to ("87", "88"). */
  recording: string;
  start_ms: number;
  end_ms: number;
  /** When the final text is shown (segment end + modelled STT latency). */
  final_ms: number;
  words: DemoWord[];
}

export interface DemoPendingFinding {
  finding_id: string;
  key: string;
  title: string;
  priority: 'ATTENTION' | 'NOTICE' | 'INFO';
  pending_ms: number;
  available_ms: number;
}

/** One audio file placed on the session timeline. Gaps between recordings are silent. */
export interface DemoRecording {
  part: string;
  name: string;
  url: string;
  offset_ms: number;
  duration_ms: number;
  recorded_at: string;
}

export interface DemoMedia {
  workspace_id: string;
  audio_url: string;
  audio_media_type: string;
  recordings: DemoRecording[];
  /** Provenance labels shown wherever the media is shown. */
  labels: string[];
  attribution: string;
  stt_label: string;
  segments: DemoLiveSegment[];
  chunk_boundaries_ms: number[];
  findings: DemoPendingFinding[];
  playback_cursor_ms: number;
}

export interface SessionDetail extends SessionSummary {
  manifest: SourceManifest;
  permissions: PermissionMatrix;
  runs: RunView[];
  entities: EntityInfo[];
  layout: LayoutView | null;
  provider_profile_ids: string[];
  /** Suggested replay start (first attention item becomes available). */
  default_as_of_ms: number;
  /** Display labels for contract UUIDs (e.g. evidence "E-12"). */
  labels: Record<string, string>;
  /** DEMO track only: playable audio and live transcript timing. */
  media?: DemoMedia | null;
}

/* ── PROPOSED_CONTRACT: imports ────────────────────────────────────── */
export type ImportStatus = 'DRAFT' | 'VALIDATING' | 'NEEDS_REMEDIATION' | 'READY' | 'COMMITTED' | 'FAILED';

export interface ImportFileInput {
  name: string;
  size: number;
  type: string;
}

export interface ImportIssue {
  code: string;
  file: string;
  field: string | null;
  row: number | null;
  message: string;
  blocking: boolean;
  recovery: string;
}

export interface ImportFileView {
  id: string;
  name: string;
  detected_type: 'WAV' | 'FLAC' | 'JSON' | 'JSONL' | 'CSV' | 'UNKNOWN';
  kind: 'AUDIO' | 'EVENTS' | 'TRACK' | 'LAYOUT' | 'UNKNOWN';
  size_bytes: number;
  channels: number | null;
  duration_ms: number | null;
  channel_label: string | null;
  sha256: string | null;
  status: 'VALIDATING' | 'VALID' | 'INVALID';
}

export interface ImportDraft {
  id: string;
  version: number;
  status: ImportStatus;
  title: string;
  source_kind: SourceKind;
  files: ImportFileView[];
  issues: ImportIssue[];
  clock: ClockMapping & { source_start_utc: string | null };
  layout_version: string | null;
  checksum_verified: boolean;
  permissions: PermissionMatrix;
  retention_days: number | null;
  coverage: Coverage;
  committed_session_id: string | null;
}

export interface AnalysisEstimate {
  stt_requests: number;
  gemini_requests: number;
  audio_minutes: number;
  budget_label: string;
  blockers: string[];
}

/* ── PROPOSED_CONTRACT: workspace projections ──────────────────────── */
export interface EntityStateView {
  entity_id: string;
  instruction: { state: InstructionState; summary: string | null; quote: string | null; evidence_id: string | null };
  readback: { state: ReadbackState; summary: string | null; quote: string | null; evidence_id: string | null };
  movement: { state: MovementState; summary: string | null; reason: string | null };
  interpretation: InterpretationState;
  reviewer: ReviewerState;
  source_age_ms: number | null;
  track_status: 'FRESH' | 'STALE' | 'POINT_ONLY' | 'MISSING';
}

export interface TrackPoint {
  t: number;
  x: number;
  y: number;
}

export interface TrackSeries {
  entity_id: string;
  footprint: boolean;
  stale_after_ms: number | null;
  points: TrackPoint[];
  predicted: TrackPoint[];
}

/** One fact row on a live highlight (position, distance, what was said). */
export interface LiveFact {
  label: string;
  value: string;
  tone?: 'attention' | 'notice';
}

/** Live highlight wording: what the controller needs to know, times in UTC. */
export interface LiveHighlight {
  title: string;
  text: string;
  /** false: shown in the transcript and timeline only. */
  attention?: boolean;
  /** The situation ends here (ms); the card then shows `resolved`. */
  until_ms?: number;
  resolved?: string;
  facts?: LiveFact[];
}

/** A standing item to keep in mind: a clearance limit, traffic advised, or a stated intention. */
export interface ReminderView {
  id: string;
  entity_label: string;
  kind: 'LIMIT' | 'TRAFFIC' | 'INTENT';
  source: 'ATC' | 'PILOT' | null;
  title: string;
  text: string;
  event_time_ms: number;
  /** The step this one replaced (e.g. the previous clearance limit). */
  previous: { title: string; event_time_ms: number } | null;
  state: 'ACTIVE' | 'DONE';
  done_time_ms: number | null;
  done_text: string | null;
  evidence: string[];
}

export interface WorkspaceSnapshot {
  snapshot: Snapshot;
  as_of_ms: number;
  mode: ReplayMode;
  entities: EntityStateView[];
  tracks: Track[];
  series: TrackSeries[];
  geometry: GeometryResult[];
  gaps: TimeRange[];
  event_markers: { id: string; t: number; kind: 'INSTRUCTION' | 'READBACK' | 'REPORT' | 'CORRECTION' | 'FINDING'; label: string }[];
  hidden_after_as_of: number;
  /** DEMO: standing items at the as-of (absent when the session has none). */
  reminders?: ReminderView[];
}

export interface WaveformView {
  channel: number;
  label: string;
  bucket_ms: number;
  peaks: number[];
}

/* ── PROPOSED_CONTRACT: transcript ─────────────────────────────────── */
export interface TranscriptRow {
  segment: TranscriptSegment;
  original: TranscriptSegment; // raw STT, never edited
  revisions: TranscriptSegment[];
  label: string; // "T-13"
  evidence_label: string; // "E-13"
  intent: Intent | null;
  association: Association | null;
  association_targets: { id: string; label: string; entity: string | null }[];
  stale_dependents: number;
}

export interface TranscriptView {
  rows: TranscriptRow[];
  channels: ChannelInfo[];
  hidden_after_as_of: number;
}

/* ── PROPOSED_CONTRACT: memory ─────────────────────────────────────── */
export interface HistoryItem {
  id: string;
  t: number;
  title: string;
  detail: string;
  tone: 'data' | 'discrepancy' | 'muted' | 'notice' | 'ready';
  evidence_id: string | null;
  available_ms: number | null;
  debrief_only: boolean;
}

export interface EntityMemoryView {
  entity: EntityInfo;
  state: EntityStateView;
  said: { quote: string | null; evidence_id: string | null; lifecycle: InstructionState; interpretation: InterpretationState; reviewer: ReviewerState; highlight: string | null } | null;
  heard: { quote: string | null; evidence_id: string | null; readback: ReadbackState; interpretation: InterpretationState; reviewer: ReviewerState; highlight: string | null; speaker: string } | null;
  observed: { movement: MovementState; statement: string; reason: string | null; interpretation: InterpretationState; reviewer: ReviewerState };
  history: HistoryItem[];
  provenance: { input_revision: number; reducer_version: string; rule_version: string; evidence_ids: string[]; updated_at: string };
  hidden_after_as_of: number;
}

export interface RunwayMemoryView {
  runway_id: string;
  coverage: 'COMPLETE' | 'PARTIAL' | 'AUDIO_ONLY';
  objects: { entity: EntityInfo; state: EntityStateView }[];
  active_instructions: { entity_id: string; summary: string; evidence_id: string | null; t: number }[];
  occupancy: { entity_id: string; intervals: TimeRange[]; status: GeometryResult['status']; reason: string | null }[];
  gaps: TimeRange[];
}

/* ── PROPOSED_CONTRACT: evidence ───────────────────────────────────── */
export interface SlotComparisonRow {
  slot: 'CALLSIGN' | 'RUNWAY' | 'ACTION' | 'CONDITION' | 'NEGATION';
  said: string | null;
  heard: string | null;
  status: 'MATCHED' | 'MISMATCH' | 'MISSING' | 'AMBIGUOUS';
}

export interface EvidenceItemView {
  evidence: Evidence;
  label: string;
  role: 'SAID' | 'HEARD' | 'OBSERVED' | 'EVENT' | 'POLICY';
  channel: string | null;
  speaker: string; // "ATC · Tower" / "Candidate · FLN214"
  highlight: string | null;
  available_ms: number | null;
}

export interface EvidenceBundle {
  id: string;
  label: string; // "F-03" or "E-12"
  title: string;
  as_of_ms: number;
  items: EvidenceItemView[];
  slots: SlotComparisonRow[];
  range: TimeRange | null;
  association: { status: AssociationStatus; note: string } | null;
  source_events: SourceEvent[];
  track_note: string | null;
  provenance: { model_version: string; prompt_version: string; rule_version: string; input_revision: number; source_quality: Quality; applicability: Applicability | null };
  alternatives: string[];
  audio_access: 'ALLOWED' | 'DENIED';
}

/* ── PROPOSED_CONTRACT: findings & options ─────────────────────────── */
export interface FindingView {
  finding: Finding;
  label: string;
  title: string;
  entity_label: string;
  source_alert: { status: 'NOT_AVAILABLE' | 'PRESENT'; severity: string | null; note: string };
  movement: MovementState;
  reviews: Review[];
  correction_note: string | null;
  /** Operational wording for the live highlight; falls back to title/statement. */
  live: LiveHighlight;
  slots: SlotComparisonRow[];
}

export interface OptionView {
  option: Option;
  label: string;
  title: string;
  evaluation_question: string;
  evidence_labels: Record<string, string>;
  reviews: Review[];
  review_allowed: boolean;
}

export interface OptionSetView {
  options: OptionView[];
  insufficient: { entity_id: string; entity_label: string; needed: string[]; reason: string }[];
  provider_available: boolean;
}

/* ── PROPOSED_CONTRACT: debrief / brief / export ───────────────────── */
export type BriefSection = 'KNOWN_SITUATION' | 'ACTIVE_RESTRICTIONS' | 'CONTEXT_CHANGES' | 'FINDINGS' | 'REVIEW_STATUS' | 'UNKNOWN_COVERAGE';

export interface BriefView {
  brief: Brief;
  label: string; // "Brief revision 2"
  stale: boolean;
  stale_reason: string | null;
  sections: { section: BriefSection; title: string; items: (FactualItem & { detail: string | null; evidence_labels: string[] })[] }[];
  spotlight: { finding_id: string; title: string; detail: string; metric: string; metric_label: string } | null;
}

export interface JournalEntry {
  id: string;
  t: number;
  kind: 'INSTRUCTION' | 'READBACK' | 'FINDING' | 'CORRECTION' | 'REVIEW' | 'REPORT';
  title: string;
  detail: string;
  label: string;
  tone: 'data' | 'discrepancy' | 'muted';
}

export type ExportFormat = 'HTML' | 'CSV' | 'JSON';
export type ExportStatus = 'PREPARING' | 'READY' | 'FAILED' | 'EXPIRED' | 'REVOKED';

export interface ExportJob {
  id: string;
  session_id: string;
  run_id: string;
  brief_id: string | null;
  format: ExportFormat;
  status: ExportStatus;
  include_journal: boolean;
  redacted: boolean;
  created_at: string;
  expires_at: string;
  size_bytes: number | null;
  failure: string | null;
}

export interface ExportPolicy {
  report_allowed: boolean;
  audio_allowed: boolean;
  redaction_required: boolean;
  expiry_hours: number;
  reason: string | null;
}

/* ── PROPOSED_CONTRACT: metrics (P1) ───────────────────────────────── */
export interface MetricsView {
  experimental: true;
  active_audio_ms: number;
  previous_active_audio_ms: number | null;
  object_switches: number;
  previous_object_switches: number | null;
  per_minute: { minute: number; occupied_ms: number; gap: boolean }[];
  reference_ms: number;
  reference_label: string;
  breakdown: { category: FindingCategory; label: string; count: number }[];
}

/* ── PROPOSED_CONTRACT: contextual query (P1) ──────────────────────
 * Contract QueryAnswer requires >= 1 evidence item, which cannot represent a valid
 * "unknown / not covered" answer. This view keeps unknown answers evidence-free. */
export interface QueryResultView {
  id: string;
  question: string;
  status: QueryStatus;
  as_of_ms: number;
  mode: ReplayMode;
  context_range: TimeRange;
  items: { statement: string; evidence_ids: string[]; evidence_labels: string[]; unknowns: string[] }[];
  note: string | null;
  model_version: string;
  asked_at: string;
}

/* ── PROPOSED_CONTRACT: operations ─────────────────────────────────── */
export interface JobView {
  id: string;
  session_id: string;
  session_title: string;
  run_label: string;
  stage: 'STT' | 'INTENT' | 'ASSOCIATION' | 'FINDINGS' | 'OPTIONS' | 'BRIEF' | 'EXPORT';
  status: 'QUEUED' | 'LEASED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCELLED' | 'RETRY_WAIT';
  attempt: number;
  completed_units: number;
  total_units: number | null;
  updated_at: string;
  failure: string | null;
}

export interface BudgetView {
  period: string;
  spent_microunits: number;
  limit_microunits: number;
  stt_audio_ms: number;
  gemini_tokens: number;
}

export interface StorageView {
  capacity_bytes: number;
  used_bytes: number;
  warning_ratio: number;
  hold_ratio: number;
  breakdown: { key: 'raw' | 'derived' | 'exports' | 'scratch' | 'database' | 'backup'; label: string; bytes: number }[];
  imports_held: boolean;
}

export interface AuditEntry {
  id: string;
  at: string;
  actor: string;
  capability: string;
  action: string;
  object: string;
  session_title: string | null;
  result: 'OK' | 'DENIED' | 'CONFLICT';
  correlation_id: string;
}

export interface RetentionPolicy {
  session_id: string;
  session_title: string;
  source_kind: SourceKind;
  retention_days: number | null;
  basis: string;
  purge_status: 'NONE' | 'REQUESTED' | 'APPROVED';
}

export interface NotificationItem {
  id: string;
  at: string;
  title: string;
  detail: string;
  tone: 'data' | 'notice' | 'discrepancy' | 'ready';
  href: string | null;
  read: boolean;
}

export interface ProviderCheckResult {
  profile_id: string;
  readiness: ProviderReadiness;
  checked_at: string;
  message: string;
}

/* ── Errors (PRD §22.3) ────────────────────────────────────────────── */
export type ApiErrorCode =
  | 'AUTH_REQUIRED'
  | 'ACCESS_DENIED'
  | 'INVALID_IMPORT'
  | 'SOURCE_PERMISSION_REQUIRED'
  | 'CLOUD_TRANSFER_BLOCKED'
  | 'ALIGNMENT_REQUIRED'
  | 'NOT_EVALUABLE'
  | 'VERSION_CONFLICT'
  | 'IDEMPOTENCY_CONFLICT'
  | 'PROVIDER_UNAVAILABLE'
  | 'PROVIDER_QUOTA_EXCEEDED'
  | 'BUDGET_EXCEEDED'
  | 'INVALID_AI_OUTPUT'
  | 'SOURCE_REVISION_CHANGED'
  | 'EVIDENCE_UNAVAILABLE'
  | 'NOT_FOUND'
  | 'CONNECTION_LOST';

export interface MutationOptions {
  idempotencyKey: string;
  expectedVersion?: number;
}
