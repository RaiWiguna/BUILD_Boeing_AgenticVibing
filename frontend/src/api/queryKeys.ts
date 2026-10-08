import type { ReplayMode } from './types';

/** As-of is bucketed to 100 ms so scrubbing does not create unbounded cache entries. */
export const asOfBucket = (ms: number) => Math.floor(ms / 100) * 100;

/**
 * Query keys always carry the scope that changes the answer: session, run, revision
 * (via run), mode and as-of (rules §4.6). Account switches clear the whole cache.
 */
export const qk = {
  auth: ['auth'] as const,
  sessions: ['sessions'] as const,
  session: (sid: string) => ['session', sid] as const,
  waveforms: (sid: string) => ['session', sid, 'waveforms'] as const,
  import: (id: string) => ['import', id] as const,
  estimate: (sid: string, profile: string) => ['session', sid, 'estimate', profile] as const,
  scoped: (sid: string, rid: string) => ['session', sid, 'run', rid] as const,
  snapshot: (sid: string, rid: string, mode: ReplayMode, asOf: number) => ['session', sid, 'run', rid, 'snapshot', mode, asOfBucket(asOf)] as const,
  entityMemory: (sid: string, rid: string, eid: string, mode: ReplayMode, asOf: number) => ['session', sid, 'run', rid, 'entity', eid, mode, asOfBucket(asOf)] as const,
  runwayMemory: (sid: string, rid: string, rwy: string, mode: ReplayMode, asOf: number) => ['session', sid, 'run', rid, 'runway', rwy, mode, asOfBucket(asOf)] as const,
  transcript: (sid: string, rid: string, mode: ReplayMode, asOf: number) => ['session', sid, 'run', rid, 'transcript', mode, mode === 'DEBRIEF' ? 'all' : asOfBucket(asOf)] as const,
  findings: (sid: string, rid: string, mode: ReplayMode, asOf: number) => ['session', sid, 'run', rid, 'findings', mode, asOfBucket(asOf)] as const,
  options: (sid: string, rid: string, mode: ReplayMode, asOf: number) => ['session', sid, 'run', rid, 'options', mode, asOfBucket(asOf)] as const,
  evidence: (sid: string, rid: string, id: string, mode: ReplayMode, asOf: number) => ['session', sid, 'run', rid, 'evidence', id, mode, asOfBucket(asOf)] as const,
  journal: (sid: string, rid: string, mode: ReplayMode, asOf: number) => ['session', sid, 'run', rid, 'journal', mode, asOfBucket(asOf)] as const,
  briefs: (sid: string, rid: string) => ['session', sid, 'run', rid, 'briefs'] as const,
  exports: (sid: string, rid: string) => ['session', sid, 'run', rid, 'exports'] as const,
  exportPolicy: (sid: string, rid: string) => ['session', sid, 'run', rid, 'export-policy'] as const,
  metrics: (sid: string, rid: string, asOf: number) => ['session', sid, 'run', rid, 'metrics', asOfBucket(asOf)] as const,
  notifications: ['notifications'] as const,
  admin: {
    accounts: ['admin', 'accounts'] as const,
    grants: (sid?: string) => ['admin', 'grants', sid ?? 'all'] as const,
    providers: ['admin', 'providers'] as const,
    jobs: ['admin', 'jobs'] as const,
    budget: ['admin', 'budget'] as const,
    storage: ['admin', 'storage'] as const,
    audit: (q: string, r: string) => ['admin', 'audit', q, r] as const,
    retention: ['admin', 'retention'] as const,
  },
};
