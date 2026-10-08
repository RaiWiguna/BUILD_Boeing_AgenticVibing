/**
 * Single vocabulary for every contract enum shown in the UI: label + tone + icon.
 * Status is never colour-only (PRD §23.4): every entry carries text and an icon.
 */
import {
  AlertTriangle,
  Ban,
  CheckCircle2,
  CircleDashed,
  CircleDot,
  CircleHelp,
  CircleSlash,
  Clock3,
  EyeOff,
  GitMerge,
  Info,
  Link2,
  Loader2,
  MinusCircle,
  RefreshCcw,
  ShieldAlert,
  XCircle,
  type LucideIcon,
} from 'lucide-react';

export type Tone = 'data' | 'discrepancy' | 'notice' | 'ready' | 'muted' | 'neutral';

export interface StatusMeta {
  label: string;
  tone: Tone;
  icon: LucideIcon;
  code?: string;
}

const m = (label: string, tone: Tone, icon: LucideIcon, code?: string): StatusMeta => ({ label, tone, icon, code });

export const STATUS = {
  priority: {
    ATTENTION: m('Attention', 'discrepancy', AlertTriangle, 'ATTENTION'),
    NOTICE: m('Notice', 'notice', AlertTriangle, 'NOTICE'),
    INFO: m('Info', 'data', Info, 'INFO'),
  },
  findingStatus: {
    OPEN: m('Open', 'neutral', CircleDot, 'OPEN'),
    UNDER_REVIEW: m('Under review', 'data', Clock3, 'UNDER_REVIEW'),
    CONFIRMED: m('Confirmed', 'ready', CheckCircle2, 'CONFIRMED'),
    DISMISSED: m('Dismissed', 'muted', XCircle, 'DISMISSED'),
    UNRESOLVED: m('Cannot be determined yet', 'notice', CircleHelp, 'UNRESOLVED'),
    SUPERSEDED: m('Superseded', 'muted', RefreshCcw, 'SUPERSEDED'),
  },
  instruction: {
    ACTIVE: m('Active', 'data', CircleDot, 'ACTIVE'),
    SUPERSEDED: m('Superseded', 'muted', RefreshCcw, 'SUPERSEDED'),
    CANCELLED: m('Cancelled', 'muted', Ban, 'CANCELLED'),
    COMPLETED_REPORTED: m('Completed (reported)', 'ready', CheckCircle2, 'COMPLETED_REPORTED'),
    UNKNOWN: m('Unknown', 'muted', CircleHelp, 'UNKNOWN'),
  },
  readback: {
    NOT_OBSERVED: m('Not observed', 'muted', EyeOff, 'NOT_OBSERVED'),
    MATCHED: m('Matched', 'ready', CheckCircle2, 'MATCHED'),
    PARTIAL: m('Partial', 'notice', MinusCircle, 'PARTIAL'),
    MISMATCH: m('Mismatch', 'discrepancy', AlertTriangle, 'MISMATCH'),
    AMBIGUOUS: m('Ambiguous', 'notice', CircleHelp, 'AMBIGUOUS'),
    CORRECTED: m('Corrected', 'data', RefreshCcw, 'CORRECTED'),
  },
  movement: {
    NOT_EVALUABLE: m('Not evaluable', 'muted', CircleSlash, 'NOT_EVALUABLE'),
    CONSISTENT: m('Consistent', 'data', CheckCircle2, 'CONSISTENT'),
    DIVERGENCE_CANDIDATE: m('Divergence candidate', 'discrepancy', AlertTriangle, 'DIVERGENCE_CANDIDATE'),
    UNKNOWN: m('Unknown', 'muted', CircleHelp, 'UNKNOWN'),
  },
  interpretation: {
    CANDIDATE: m('Candidate', 'muted', CircleDashed, 'CANDIDATE'),
    SUPPORTED: m('Supported', 'data', CheckCircle2, 'SUPPORTED'),
    AMBIGUOUS: m('Ambiguous', 'notice', CircleHelp, 'AMBIGUOUS'),
    REVIEWED: m('Reviewed', 'ready', CheckCircle2, 'REVIEWED'),
    REJECTED: m('Rejected', 'muted', XCircle, 'REJECTED'),
  },
  reviewer: {
    UNREVIEWED: m('Unreviewed', 'muted', CircleDashed, 'UNREVIEWED'),
    CONFIRMED: m('Confirmed', 'ready', CheckCircle2, 'CONFIRMED'),
    DISMISSED: m('Dismissed', 'muted', XCircle, 'DISMISSED'),
    UNRESOLVED: m('Unresolved', 'notice', CircleHelp, 'UNRESOLVED'),
  },
  quality: {
    SUPPORTED: m('Supported', 'data', CheckCircle2, 'SUPPORTED'),
    AMBIGUOUS: m('Ambiguous', 'notice', CircleHelp, 'AMBIGUOUS'),
    MISSING: m('Missing', 'muted', CircleSlash, 'MISSING'),
    CONFLICTING: m('Conflicting', 'discrepancy', AlertTriangle, 'CONFLICTING'),
  },
  association: {
    PROPOSED: m('Proposed', 'muted', CircleDashed, 'PROPOSED'),
    ACCEPTED_BY_VALIDATION: m('Supported', 'data', Link2, 'ACCEPTED_BY_VALIDATION'),
    CONFIRMED_BY_REVIEW: m('Confirmed by review', 'ready', CheckCircle2, 'CONFIRMED_BY_REVIEW'),
    AMBIGUOUS: m('Ambiguous', 'notice', CircleHelp, 'AMBIGUOUS'),
    REJECTED: m('Rejected', 'muted', XCircle, 'REJECTED'),
    SUPERSEDED: m('Superseded', 'muted', RefreshCcw, 'SUPERSEDED'),
  },
  loop: {
    OPEN: m('Open', 'notice', Clock3, 'OPEN'),
    PARTIAL: m('Partial', 'notice', MinusCircle, 'PARTIAL'),
    CLOSED_WITH_EVIDENCE: m('Closed with evidence', 'ready', CheckCircle2, 'CLOSED_WITH_EVIDENCE'),
    CANCELLED: m('Cancelled', 'muted', Ban, 'CANCELLED'),
    SUPERSEDED: m('Superseded', 'muted', RefreshCcw, 'SUPERSEDED'),
    UNKNOWN: m('Unknown', 'muted', CircleHelp, 'UNKNOWN'),
  },
  optionReview: {
    UNREVIEWED: m('Unreviewed', 'muted', CircleDashed, 'UNREVIEWED'),
    RELEVANT: m('Relevant', 'ready', CheckCircle2, 'RELEVANT'),
    NOT_RELEVANT: m('Not relevant', 'muted', XCircle, 'NOT_RELEVANT'),
    UNSUPPORTED: m('Unsupported by evidence', 'discrepancy', ShieldAlert, 'UNSUPPORTED'),
    UNRESOLVED: m('Cannot be determined yet', 'notice', CircleHelp, 'UNRESOLVED'),
  },
  analysis: {
    NOT_ANALYZED: m('Not analysed', 'muted', CircleDashed),
    QUEUED: m('Queued', 'data', Clock3),
    RUNNING: m('Running', 'data', Loader2),
    COMPLETED: m('Completed', 'ready', CheckCircle2),
    PARTIAL: m('Partial', 'discrepancy', MinusCircle),
    FAILED: m('Failed', 'discrepancy', XCircle),
    CANCELLED: m('Cancelled', 'muted', Ban),
  },
  permission: {
    ALLOWED: m('Allowed', 'ready', CheckCircle2),
    DENIED: m('Denied', 'discrepancy', Ban),
    UNDETERMINED: m('Undetermined', 'notice', Clock3),
  },
  speechAct: {
    REQUEST: m('Request', 'neutral', CircleDot),
    INSTRUCTION: m('Instruction', 'data', CircleDot),
    READBACK: m('Readback', 'data', GitMerge),
    REPORT: m('Report', 'neutral', CircleDot),
    CORRECTION: m('Correction', 'discrepancy', RefreshCcw),
    CANCELLATION: m('Cancellation', 'muted', Ban),
    COORDINATION: m('Coordination', 'neutral', CircleDot),
    HANDOFF: m('Handoff', 'neutral', CircleDot),
    INFORMATION: m('Information', 'neutral', Info),
    UNKNOWN: m('Not analysed', 'muted', CircleHelp),
  },
} as const;

export const TONE_TEXT: Record<Tone, string> = {
  data: 'text-data-strong',
  discrepancy: 'text-discrepancy',
  notice: 'text-notice',
  ready: 'text-ready',
  muted: 'text-muted',
  neutral: 'text-ink-2',
};

export const TONE_PILL: Record<Tone, string> = {
  data: 'bg-data-tint text-data-strong',
  discrepancy: 'bg-discrepancy-tint text-discrepancy',
  notice: 'bg-notice-tint text-notice',
  ready: 'bg-ready-tint text-ready',
  muted: 'bg-muted-tint text-muted',
  neutral: 'bg-track text-ink-2',
};

export const TONE_DOT: Record<Tone, string> = {
  data: 'bg-data',
  discrepancy: 'bg-[#d63384]',
  notice: 'bg-[#e0a21a]',
  ready: 'bg-[#22a35f]',
  muted: 'bg-[#a3aab5]',
  neutral: 'bg-[#a3aab5]',
};

export const TONE_TILE: Record<Tone, string> = {
  data: 'bg-data-tint text-data',
  discrepancy: 'bg-discrepancy-tint text-discrepancy',
  notice: 'bg-notice-tint text-notice',
  ready: 'bg-ready-tint text-ready',
  muted: 'bg-muted-tint text-muted',
  neutral: 'bg-track text-ink-2',
};

export const CATEGORY_LABEL: Record<string, string> = {
  CRITICAL_SLOT_UNCERTAIN: 'Critical slot uncertain',
  READBACK_DISCREPANCY: 'Readback discrepancy',
  OPEN_LOOP: 'Open loop',
  SPEECH_RECORD_DISCREPANCY: 'Speech–record discrepancy',
  MOVEMENT_DIVERGENCE: 'Instruction–movement divergence',
  QUALITY_GAP: 'Source / quality gap',
};

export const LOOP_KIND_LABEL: Record<string, string> = {
  REQUEST_RESPONSE: 'Response to request',
  REPORT_EXPECTED: 'Report expected',
  COORDINATION_PENDING: 'Coordination pending',
  READBACK_EXPECTED: 'Readback expected',
};
