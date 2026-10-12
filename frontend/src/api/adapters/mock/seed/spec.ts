/**
 * MOCK scenario DSL. Each synthetic session is declared once here; the mock engine
 * derives contract-shaped DTOs (transcript, memory, findings, evidence, snapshots…)
 * from it. All content is SYNTHETIC and illustrative — never evaluation truth.
 */
import type {
  AnalysisState,
  AssociationStatus,
  ChannelInfo,
  EntityInfo,
  FindingCategory,
  FindingPriority,
  FindingStatus,
  InstructionState,
  InterpretationState,
  LiveFact,
  MovementState,
  Notice,
  PermissionMatrix,
  Quality,
  ReadbackState,
  RoleCandidate,
  SessionLifecycle,
  SourceKind,
  SlotComparisonRow,
  SpeechAct,
  TimeRange,
} from '../../../types';

export type ActionVerb = 'HOLD_SHORT' | 'CROSS_RUNWAY' | 'LINE_UP_WAIT' | 'TAKEOFF' | 'LAND' | 'TAXI' | 'VACATE' | 'CONTACT' | 'REPORT' | 'UNKNOWN';

export interface Effects {
  instruction?: InstructionState;
  instructionSummary?: string;
  readback?: ReadbackState;
  readbackSummary?: string;
  interpretation?: InterpretationState;
}

export interface SegmentSpec {
  key: string; // "T-09"
  evidence: string; // "E-12"
  t: string; // "05:12"
  dur: number; // ms
  ch: number;
  text: string;
  act: SpeechAct;
  role: RoleCandidate;
  entity: string | null; // callsign
  action?: ActionVerb;
  runway?: string | null;
  callsignQuality?: Quality;
  runwayQuality?: Quality;
  quality?: Quality;
  /** Association to an earlier segment key (readback/report/correction). */
  assoc?: { target: string | null; relationship: 'READBACK_OF' | 'REPORT_FOR' | 'CORRECTION_OF' | 'CANCELS' | 'POSSIBLE_LINK'; status: AssociationStatus; alternatives?: string[]; unknowns?: string[] };
  highlight?: string; // substring highlighted as the critical slot
  effects?: Effects;
  latency?: number; // available delay after segment end (default 2500 ms)
  unknowns?: string[];
}

export interface MovementSpec {
  entity: string;
  from: string; // clock
  state: MovementState;
  summary: string;
  reason: string | null;
}

export interface TrackSpec {
  entity: string;
  footprint: boolean;
  staleAfter?: string; // clock after which no updates arrive
  /** [clock, x, y] or, from real/synthetic feeds, [clock, x, y, heading_deg, speed_kt]. */
  waypoints: Waypoint[];
  predicted?: [string, number, number][];
  /** Coverage gaps ([from, to] clocks): no position is reported inside them. */
  gaps?: [string, string][];
}

export type Waypoint = [string, number, number] | [string, number, number, number, number];

export interface FindingSpec {
  key: string; // "F-03"
  category: FindingCategory;
  priority: FindingPriority;
  status: FindingStatus;
  entity: string;
  t: string;
  available: string;
  /** When analysis of this finding visibly starts (DEMO live view); defaults to `available`. */
  pending?: string;
  title: string;
  statement: string;
  /** Live highlight wording: what the controller needs to know, times in UTC. */
  live?: { title: string; text: string; attention?: boolean; until?: string; resolved?: string; facts?: LiveFact[] };
  evidence: string[]; // segment keys
  quality: Quality;
  unknowns: string[];
  movement: MovementState;
  slots?: SlotComparisonRow[];
  sourceAlert?: { status: 'NOT_AVAILABLE' | 'PRESENT'; severity: string | null; note: string };
  trackNote?: string;
  correctionNote?: string;
}

export interface ReminderStepSpec {
  t: string;
  available: string;
  title: string;
  text: string;
  source: 'ATC' | 'PILOT' | null;
}

/** A standing item to keep in mind; each step replaces the previous one. */
export interface ReminderSpec {
  key: string;
  entity: string;
  kind: 'LIMIT' | 'TRAFFIC' | 'INTENT';
  steps: ReminderStepSpec[];
  until?: string;
  done?: string;
  evidence: string[]; // segment keys
}

export interface OptionSpec {
  key: string; // "Option 1"
  title: string;
  question: string;
  statement: string;
  rationale: string;
  evidence: string[]; // segment or finding keys
  preconditions: string[];
  unknowns: string[];
  consequences: string[];
  asOf: string;
  available: string;
}

export interface ScenarioSpec {
  key: string;
  title: string;
  context: string;
  lifecycle: SessionLifecycle;
  analysis: AnalysisState;
  durationMs: number;
  recordedAt: string;
  updatedAt: string;
  sourceLabel: string;
  /** Defaults to SYNTHETIC. */
  sourceKind?: SourceKind;
  /** Defaults to the fictional layout version. */
  layoutVersion?: string;
  channels: ChannelInfo[];
  entities: (Omit<EntityInfo, 'id'> & { initialMovement?: MovementState })[];
  hasTracks: boolean;
  hasLayout: boolean;
  gaps: TimeRange[];
  permissions: PermissionMatrix;
  retentionDays: number;
  providerAvailable: boolean;
  runs: { label: string; revision: number; status: AnalysisState; createdAt: string; coverageNote?: string }[];
  segments: SegmentSpec[];
  movements: MovementSpec[];
  tracks: TrackSpec[];
  findings: FindingSpec[];
  reminders?: ReminderSpec[];
  options: OptionSpec[];
  insufficient: { entity: string; needed: string[]; reason: string }[];
  notices: Omit<Notice, 'id'>[];
  speakerIdentity: boolean | null;
}

export const ALLOWED = (note: string) => ({ state: 'ALLOWED' as const, note });
export const DENIED = (note: string) => ({ state: 'DENIED' as const, note });
export const UNDETERMINED = (note: string) => ({ state: 'UNDETERMINED' as const, note });

export const STANDARD_PERMISSIONS: PermissionMatrix = {
  local_read: ALLOWED('Files are stored on this deployment.'),
  cloud_audio: ALLOWED('Synthetic audio may be sent for transcription.'),
  cloud_transcript: ALLOWED('Transcript text may be sent for analysis.'),
  reviewer_access: ALLOWED('Granted reviewers may open evidence.'),
  report_export: ALLOWED('Reports may be exported from analysis results.'),
  audio_export: DENIED('Audio cannot be exported outside the deployment.'),
};

export const TOWER_GROUND: ChannelInfo[] = [
  { index: 0, label: 'Tower', role: 'ATC' },
  { index: 1, label: 'Ground', role: 'Pilot / vehicle' },
];
