export type Role = 'instructor' | 'tower' | 'ground' | 'observer'
export type Instruction = 'HOLD_SHORT' | 'CROSS_RUNWAY' | 'LAND' | 'LINE_UP_AND_WAIT' | 'TAKEOFF' | 'GO_AROUND'
export interface Scenario { id: string; title: string; objective: string; version: string; duration_s: number; domain_review: string }
export interface Track { id: string; callsign: string; kind: 'aircraft' | 'vehicle'; x_m: number; y_m: number; speed_mps: number; heading_deg: number; phase: string; length_m: number; width_m: number; runway: string; owner: string; observed_ms: number; event_id: string; stale: boolean }
export interface Clearance { id: string; target: string; instruction: Instruction; runway: string; issued_ms: number; issuer: string; status: string; readback: string; event_id: string }
export interface Prediction { object_id: string; entry_s: number; exit_s: number; exit_unknown: boolean; threshold_eta_s: number | null; assumed_entry_range_s: number[]; assumed_exit_range_s: number[] }
export interface Alert { id: string; rule: string; objects: string[]; severity: string; reason: string; status: string; created_ms: number; calculated_ms: number; data_degraded: boolean; metrics: { overlap_s?: number; start_s?: number; margin_s?: number; intervals?: Prediction[] }; evidence_event_ids: string[]; track_ages_ms: Record<string, number>; assumptions: string }
export interface Event { id: string; ordinal: number; sim_ms: number; type: string; message: string; actor?: string; target?: string; assessment?: { type: string; text: string; values: Record<string, number> } }
export interface Complexity { score: number; level: string; components: Record<string, number>; weights: Record<string, number>; label: string }
export interface Metadata { id: string; scenario: Scenario; condition: 'flowlens' | 'baseline'; seed: number; status?: string; config: { low_visibility: boolean; emergency: boolean; delay_ms: number; noise_m: number; buffer_s: number }; engine_version: string; parent?: { session_id: string; frame_ms: number } }
export interface Snapshot {
  session_id: string; kind: 'training' | 'review'; sequence: number; sim_ms: number; revision: number; status: string; speed: number;
  metadata: Metadata; tracks: Track[]; clearances: Clearance[]; predictions: Prediction[]; alerts: Alert[]; events: Event[];
  requests: { target: string; completed: boolean; requested_ms: number }[];
  runway: { open: boolean; state: string; data_quality: string; observed_occupants: string[]; degraded_ids: string[] };
  complexity: Record<string, Complexity>; acknowledgements: { alert_id: string; actor: string; sim_ms: number }[];
  assessments: Event[]; error?: string; seat: { role: Role; label: string }; source_session_id?: string;
  review_end_ms?: number; playback_ms?: number; server_sent_utc_ms: number;
  review_annotations?: { sim_ms: number; text: string; actor: string; type: string }[];
}
