/**
 * MockApiClient — in-process simulation of the FlowLens backend for the MOCK
 * frontend track. It reproduces server-owned behaviour (authorization, as-of
 * filtering, idempotency, optimistic versions, append-only review, stale marking,
 * job/export lifecycles) so screens exercise real states. All data is SYNTHETIC.
 */
import type { ApiClient, AsOf, Scope } from '../../client';
import { ApiError } from '../../errors';
import type {
  Account,
  AnalysisEstimate,
  AuditEntry,
  AuthSession,
  BriefView,
  BudgetView,
  Capability,
  EntityMemoryView,
  EvidenceBundle,
  EvidenceItemView,
  ExportJob,
  ExportPolicy,
  FindingView,
  HistoryItem,
  ImportDraft,
  ImportFileInput,
  ImportFileView,
  ImportIssue,
  JobView,
  JournalEntry,
  MetricsView,
  MutationOptions,
  NotificationItem,
  OptionSetView,
  OptionView,
  PermissionKey,
  PermissionMatrix,
  PermissionState,
  ProviderCheckResult,
  ProviderProfile,
  QueryResultView,
  ReplayMode,
  RetentionPolicy,
  Review,
  ReviewerState,
  RunView,
  RunwayMemoryView,
  SessionDetail,
  SessionGrant,
  SessionSummary,
  SourceKind,
  StorageView,
  TranscriptRow,
  TranscriptSegment,
  TranscriptView,
  WaveformView,
  WorkspaceSnapshot,
  BriefSection,
  ExportFormat,
} from '../../types';
import { delay, mockControl } from './control';
import { at, mid, sha } from './ids';
import { ACCOUNTS, DEMO_PASSWORD, ROLE_CAPABILITIES, ROLE_LABEL } from './seed/accounts';
import { FICTIONAL_LAYOUT } from './seed/layout';
import { AUDIO_ONLY, CALLSIGN_AMBIGUITY, DRAFT_IMPORT, HOLD_SHORT_VEHICLE, PROVIDER_OUTAGE, REPORT_CLEAR } from './seed/others';
import { RUNWAY27 } from './seed/runway27';
import type { ScenarioSpec, SegmentSpec } from './seed/spec';
import { MockStream } from './stream';
import {
  associationFor,
  buildWorld,
  entityStates,
  evidenceFor,
  findingFor,
  gapsFor,
  geometryFor,
  intentFor,
  loopFor,
  memoryEvents,
  optionFor,
  segAvailable,
  segEnd,
  segmentFor,
  segStart,
  seriesFor,
  sourceEvents,
  tracksFor,
  visible,
  waveformsFor,
  type World,
} from './world';

const AUTH_KEY = 'flowlens.mock.account';
const HOUR = 3_600_000;

interface SessionState {
  world: World;
  lifecycle: SessionSummary['lifecycle'];
  analysis: SessionSummary['analysis'];
  permissions: PermissionMatrix;
  runs: RunView[];
  staleRunIds: Set<string>;
  transcriptRevisions: Map<string, TranscriptSegment[]>;
  assocReviews: Map<string, { targetId: string | null; reason: string; at: string; actor: string; revision: number }[]>;
  findingReviews: Map<string, Review[]>;
  optionReviews: Map<string, Review[]>;
  briefs: BriefView[];
  exports: ExportJob[];
  providerAvailable: boolean;
  updatedAt: string;
}

interface IdempotencyRecord {
  hash: string;
  result: unknown;
}

function nowIso() {
  return new Date().toISOString();
}

function addHours(iso: string, hours: number) {
  return new Date(new Date(iso).getTime() + hours * HOUR).toISOString();
}

function clockLabel(ms: number) {
  const s = Math.floor(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

export class MockApiClient implements ApiClient {
  readonly kind = 'MOCK' as const;
  readonly stream: MockStream;

  private sessions = new Map<string, SessionState>();
  private order: string[] = [];
  private accounts: Account[] = [];
  private grants: SessionGrant[] = [];
  private imports = new Map<string, ImportDraft>();
  private notifications: NotificationItem[] = [];
  private audit: AuditEntry[] = [];
  private jobs: JobView[] = [];
  private profiles: ProviderProfile[] = [];
  private retention = new Map<string, RetentionPolicy['purge_status']>();
  private idempotency = new Map<string, IdempotencyRecord>();
  private currentAccountId: string | null = null;

  constructor() {
    this.stream = new MockStream(
      (sessionId) => this.latestRun(this.sessions.get(sessionId))?.run.id ?? null,
      () => this.accounts.find((a) => a.role === 'EVALUATOR')?.id ?? null,
    );
    this.seed();
    let nonce = mockControl.getState().resetDataNonce;
    mockControl.subscribe((s) => {
      if (s.resetDataNonce !== nonce) {
        nonce = s.resetDataNonce;
        const keep = this.currentAccountId;
        this.seed();
        this.currentAccountId = keep;
      }
    });
    try {
      const stored = sessionStorage.getItem(AUTH_KEY);
      if (stored && this.accounts.some((a) => a.id === stored && a.active)) this.currentAccountId = stored;
    } catch {
      /* storage unavailable */
    }
  }

  /* ── Seed ────────────────────────────────────────────────────────── */

  private seed() {
    this.sessions.clear();
    this.order = [];
    this.accounts = ACCOUNTS.map((a) => ({ ...a }));
    this.grants = [];
    this.imports.clear();
    this.idempotency.clear();
    this.retention.clear();
    const specs: ScenarioSpec[] = [RUNWAY27, HOLD_SHORT_VEHICLE, REPORT_CLEAR, AUDIO_ONLY, CALLSIGN_AMBIGUITY, PROVIDER_OUTAGE, DRAFT_IMPORT];
    for (const spec of specs) this.addSession(spec);

    const s1 = this.sessions.get(mid('session:runway27'))!;
    const run03 = s1.runs[1]!.run.id;
    const run02 = s1.runs[0]!.run.id;
    s1.staleRunIds.add(run02);
    s1.briefs = [
      this.buildBrief(s1, run03, at('05:22'), 1, '2026-10-08T14:20:00Z', 'Created before correction E-14 was available.'),
      this.buildBrief(s1, run03, at('18:40'), 2, '2026-10-08T14:32:00Z', null),
    ];
    s1.exports = [
      { id: mid('export:s1:1'), session_id: s1.world.sessionId, run_id: run03, brief_id: s1.briefs[0]!.brief.id, format: 'HTML', status: 'EXPIRED', include_journal: true, redacted: true, created_at: '2026-09-30T10:00:00Z', expires_at: '2026-10-01T10:00:00Z', size_bytes: 48_211, failure: null },
      { id: mid('export:s1:2'), session_id: s1.world.sessionId, run_id: run02, brief_id: null, format: 'CSV', status: 'REVOKED', include_journal: false, redacted: true, created_at: '2026-10-08T13:10:00Z', expires_at: '2026-10-09T13:10:00Z', size_bytes: 9_402, failure: 'Permission changed after export was created.' },
    ];

    this.profiles = [
      { id: mid('profile:stt'), provider: 'GOOGLE_STT', model: 'chirp_3', transport: 'STT_V2_INLINE', region: 'us', locale: 'en-US', readiness: 'UNVERIFIED', timeout_seconds: 60, version: 'stt-profile-1', store: false },
      { id: mid('profile:gemini'), provider: 'GEMINI', model: 'gemini-3.8-flash', transport: 'GEMINI_DEVELOPER_INTERACTIONS', region: null, locale: null, readiness: 'UNVERIFIED', timeout_seconds: 45, version: 'gemini-profile-1', store: false },
    ];

    for (const sessionId of this.order) {
      for (const acc of this.accounts) {
        if (acc.role === 'ADMIN' || !acc.active) continue;
        this.grants.push({ id: mid(`grant:${sessionId}:${acc.id}`), session_id: sessionId, account_id: acc.id, capabilities: ROLE_CAPABILITIES[acc.role], granted_by: 'Nizam Rahman', granted_at: '2026-10-01T09:00:00Z' });
      }
    }

    this.notifications = [
      { id: mid('notif:1'), at: '2026-10-08T14:32:00Z', title: 'Analysis run #03 completed', detail: 'Runway 27 · Readback · 5 findings available', tone: 'ready', href: `/s/${s1.world.sessionId}/review/findings`, read: false },
      { id: mid('notif:2'), at: '2026-10-08T13:12:00Z', title: 'Export revoked', detail: 'CSV export for run #02 — permission changed', tone: 'notice', href: `/s/${s1.world.sessionId}/debrief`, read: false },
      { id: mid('notif:3'), at: '2026-10-04T09:41:00Z', title: 'Analysis partial', detail: 'Audio-only · Tower · provider unavailable after transcription', tone: 'discrepancy', href: `/sessions?selected=${mid('session:audioonly')}`, read: false },
    ];

    this.jobs = [
      { id: mid('job:1'), session_id: s1.world.sessionId, session_title: s1.world.spec.title, run_label: '#03', stage: 'OPTIONS', status: 'SUCCEEDED', attempt: 1, completed_units: 2, total_units: 2, updated_at: '2026-10-08T14:32:00Z', failure: null },
      { id: mid('job:2'), session_id: mid('session:audioonly'), session_title: 'Audio-only · Tower', run_label: '#01', stage: 'INTENT', status: 'FAILED', attempt: 3, completed_units: 41, total_units: 58, updated_at: '2026-10-04T09:41:00Z', failure: 'PROVIDER_UNAVAILABLE · retries exhausted' },
      { id: mid('job:3'), session_id: mid('session:audioonly'), session_title: 'Audio-only · Tower', run_label: '#01', stage: 'STT', status: 'SUCCEEDED', attempt: 1, completed_units: 18, total_units: 18, updated_at: '2026-10-04T09:30:00Z', failure: null },
      { id: mid('job:4'), session_id: mid('session:holdshort'), session_title: 'Hold short · Vehicle', run_label: '#01', stage: 'FINDINGS', status: 'SUCCEEDED', attempt: 1, completed_units: 1, total_units: 1, updated_at: '2026-10-07T10:18:00Z', failure: null },
      { id: mid('job:5'), session_id: mid('session:reportclear'), session_title: 'Report clear · Open loop', run_label: '#01', stage: 'BRIEF', status: 'RETRY_WAIT', attempt: 2, completed_units: 0, total_units: 1, updated_at: '2026-10-08T12:02:00Z', failure: 'PROVIDER_QUOTA_EXCEEDED · retry in 4 min' },
    ];

    const actions = ['session.open', 'evidence.read', 'finding.review', 'export.create', 'auth.login', 'grant.update', 'transcript.correct', 'analysis.create', 'provider.check', 'export.download'];
    const actors = ['Dana Whitfield', 'Sam Ortiz', 'Ira Santoso', 'Nizam Rahman'];
    this.audit = Array.from({ length: 84 }, (_, i) => {
      const sid = this.order[i % this.order.length]!;
      const action = actions[(i * 7) % actions.length]!;
      const actor = actors[(i * 3) % actors.length]!;
      const denied = action === 'finding.review' && actor === 'Ira Santoso';
      return {
        id: mid(`audit:${i}`),
        at: new Date(Date.parse('2026-10-08T14:40:00Z') - i * 37 * 60_000).toISOString(),
        actor,
        capability: denied ? 'session.read' : action.startsWith('auth') ? '—' : action.split('.')[0]!,
        action,
        object: action.split('.')[0]!,
        session_title: action.startsWith('auth') ? null : this.sessions.get(sid)!.world.spec.title,
        result: denied ? 'DENIED' : i % 23 === 5 ? 'CONFLICT' : 'OK',
        correlation_id: `corr_${sha(`audit:${i}`).slice(0, 10)}`,
      } satisfies AuditEntry;
    });
  }

  private addSession(spec: ScenarioSpec) {
    const world = buildWorld(spec);
    this.sessions.set(world.sessionId, {
      world,
      lifecycle: spec.lifecycle,
      analysis: spec.analysis,
      permissions: structuredClone(spec.permissions),
      runs: world.runs,
      staleRunIds: new Set(),
      transcriptRevisions: new Map(),
      assocReviews: new Map(),
      findingReviews: new Map(),
      optionReviews: new Map(),
      briefs: [],
      exports: [],
      providerAvailable: spec.providerAvailable,
      updatedAt: spec.updatedAt,
    });
    this.order.push(world.sessionId);
    return world.sessionId;
  }

  /* ── Guards ──────────────────────────────────────────────────────── */

  private account() {
    if (mockControl.getState().sessionExpired) {
      throw new ApiError('AUTH_REQUIRED', 'Your sign-in has expired.', { recovery: 'Sign in again. Committed reviews are kept.' });
    }
    const acc = this.accounts.find((a) => a.id === this.currentAccountId);
    if (!acc || !acc.active) throw new ApiError('AUTH_REQUIRED', 'Sign in to continue.', { recovery: 'Sign in with an individual account.' });
    return acc;
  }

  private caps(): Capability[] {
    return ROLE_CAPABILITIES[this.account().role];
  }

  private require(cap: Capability, what: string) {
    const acc = this.account();
    if (!ROLE_CAPABILITIES[acc.role].includes(cap)) {
      this.log(acc, cap, `${what}`, 'DENIED', null);
      throw new ApiError('ACCESS_DENIED', `Your role (${ROLE_LABEL[acc.role]}) does not include ${cap}.`, { recovery: 'Ask an administrator for a session grant that includes this capability.', details: { capability: cap } });
    }
    return acc;
  }

  private session(sessionId: string) {
    const s = this.sessions.get(sessionId);
    if (!s) throw new ApiError('NOT_FOUND', 'Session not found or not shared with you.', { recovery: 'Return to the session catalogue.' });
    const acc = this.account();
    if (acc.role !== 'ADMIN' && !this.grants.some((g) => g.session_id === sessionId && g.account_id === acc.id)) {
      throw new ApiError('ACCESS_DENIED', 'This session is not shared with your account.', { recovery: 'Ask an administrator for a session grant.' });
    }
    return s;
  }

  private run(s: SessionState, runId: string) {
    const r = s.runs.find((x) => x.run.id === runId);
    if (!r) throw new ApiError('NOT_FOUND', 'Analysis run not found for this session.', { recovery: 'Choose another run from the header.' });
    return r;
  }

  private latestRun(s: SessionState | undefined) {
    if (!s) return null;
    const done = s.runs.filter((r) => r.run.status === 'COMPLETED' || r.run.status === 'PARTIAL');
    return done[done.length - 1] ?? s.runs[s.runs.length - 1] ?? null;
  }

  private mutationGuards(opts: MutationOptions) {
    if (mockControl.getState().connectionLost) {
      throw new ApiError('CONNECTION_LOST', 'Changes are paused while the connection is resynchronising.', { recovery: 'Wait for “Connected”, then save again. Nothing was queued.' });
    }
    if (!opts.idempotencyKey) throw new ApiError('IDEMPOTENCY_CONFLICT', 'Missing idempotency key.');
  }

  private async idem<T>(opts: MutationOptions, payload: unknown, fn: () => T | Promise<T>): Promise<T> {
    await delay();
    this.mutationGuards(opts);
    const hash = JSON.stringify(payload);
    const prior = this.idempotency.get(opts.idempotencyKey);
    if (prior) {
      if (prior.hash !== hash) throw new ApiError('IDEMPOTENCY_CONFLICT', 'This request key was already used with different content.', { recovery: 'Reload and try again.' });
      return structuredClone(prior.result) as T;
    }
    const result = await fn();
    this.idempotency.set(opts.idempotencyKey, { hash, result: structuredClone(result) });
    return result;
  }

  private requireProvider(s?: SessionState) {
    if (mockControl.getState().providerOutage || (s && !s.providerAvailable)) {
      throw new ApiError('PROVIDER_UNAVAILABLE', 'The analysis provider is unavailable. Stored results remain readable.', { recovery: 'Try again later. No new results were generated.' });
    }
  }

  private log(acc: Account, capability: string, action: string, result: AuditEntry['result'], sessionTitle: string | null) {
    this.audit.unshift({ id: crypto.randomUUID(), at: nowIso(), actor: acc.name, capability, action, object: action.split('.')[0]!, session_title: sessionTitle, result, correlation_id: `corr_${crypto.randomUUID().slice(0, 10)}` });
  }

  private notify(item: Omit<NotificationItem, 'id' | 'at' | 'read'>) {
    this.notifications.unshift({ ...item, id: crypto.randomUUID(), at: nowIso(), read: false });
  }

  /* ── Auth ────────────────────────────────────────────────────────── */

  private authSession(acc: Account): AuthSession {
    const now = Date.now();
    return { account: { ...acc }, capabilities: ROLE_CAPABILITIES[acc.role], expires_at: new Date(now + 8 * HOUR).toISOString(), idle_expires_at: new Date(now + HOUR).toISOString() };
  }

  async getAuthSession() {
    await delay();
    if (mockControl.getState().sessionExpired) return null;
    const acc = this.accounts.find((a) => a.id === this.currentAccountId && a.active);
    return acc ? this.authSession(acc) : null;
  }

  async login(email: string, password: string) {
    await delay();
    const acc = this.accounts.find((a) => a.email.toLowerCase() === email.trim().toLowerCase());
    if (!acc || password !== DEMO_PASSWORD) throw new ApiError('AUTH_REQUIRED', 'Email or password is incorrect.', { recovery: 'Check the details and try again.' });
    if (!acc.active) throw new ApiError('ACCESS_DENIED', 'This account is deactivated.', { recovery: 'Contact an administrator.' });
    this.currentAccountId = acc.id;
    mockControl.getState().set({ sessionExpired: false });
    acc.last_login_at = nowIso();
    try {
      sessionStorage.setItem(AUTH_KEY, acc.id);
    } catch {
      /* ignore */
    }
    this.log(acc, '—', 'auth.login', 'OK', null);
    return this.authSession(acc);
  }

  async logout() {
    await delay();
    this.currentAccountId = null;
    try {
      sessionStorage.removeItem(AUTH_KEY);
    } catch {
      /* ignore */
    }
  }

  async demoAccounts() {
    return this.accounts.filter((a) => a.active).map((a) => ({ email: a.email, role: a.role, name: a.name }));
  }

  /* ── Sessions ────────────────────────────────────────────────────── */

  private summary(s: SessionState): SessionSummary {
    const spec = s.world.spec;
    const latest = this.latestRun(s);
    const openFindings = latest ? this.findingViews(s, latest.run.id, 'DEBRIEF', spec.durationMs).filter((f) => ['OPEN', 'UNDER_REVIEW'].includes(f.finding.status)).length : 0;
    const notices = spec.notices.map((n, i) => ({ ...n, id: `${spec.key}:notice:${i}` }));
    if (s.permissions.cloud_audio.state !== 'ALLOWED' && !notices.some((n) => n.title.startsWith('Cloud'))) notices.push({ id: `${spec.key}:notice:cloud`, tone: 'notice', title: 'Cloud permission incomplete', detail: 'Cloud audio is undetermined' });
    return {
      id: s.world.sessionId,
      title: spec.title,
      context: spec.context,
      source_kind: 'SYNTHETIC',
      lifecycle: s.lifecycle,
      duration_ms: spec.durationMs,
      recorded_at: spec.recordedAt,
      updated_at: s.updatedAt,
      source_ready: s.lifecycle !== 'PREPARING',
      analysis: s.analysis,
      domain_validation: 'NOT_DOMAIN_VALIDATED',
      channels: spec.channels,
      has_tracks: spec.hasTracks,
      has_layout: spec.hasLayout,
      layout_label: spec.hasLayout ? (spec.hasTracks ? 'Taxi + Runway 27' : 'Layout only') : null,
      latest_run_id: latest?.run.id ?? null,
      latest_run_label: latest ? `${latest.label} · revision ${latest.input_revision}` : null,
      open_findings: openFindings,
      notices,
    };
  }

  async listSessions() {
    await delay();
    const acc = this.account();
    if (mockControl.getState().emptyCatalogue) return [];
    return this.order
      .filter((id) => acc.role === 'ADMIN' || this.grants.some((g) => g.session_id === id && g.account_id === acc.id))
      .map((id) => this.summary(this.sessions.get(id)!))
      .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  }

  async getSession(sessionId: string): Promise<SessionDetail> {
    await delay();
    const s = this.session(sessionId);
    return {
      ...this.summary(s),
      manifest: s.world.manifest,
      permissions: s.permissions,
      runs: s.runs,
      entities: s.world.entities,
      layout: s.world.spec.hasLayout ? FICTIONAL_LAYOUT : null,
      provider_profile_ids: this.profiles.map((p) => p.id),
      default_as_of_ms: (() => {
        const f = s.world.spec.findings.find((x) => x.priority === 'ATTENTION') ?? s.world.spec.findings[0];
        return f ? Math.min(s.world.spec.durationMs, at(f.available)) : 0;
      })(),
      labels: s.world.labels,
    };
  }

  async getWaveforms(sessionId: string): Promise<WaveformView[]> {
    await delay();
    return waveformsFor(this.session(sessionId).world);
  }

  /* ── Imports ─────────────────────────────────────────────────────── */

  private detect(file: ImportFileInput): Pick<ImportFileView, 'detected_type' | 'kind'> {
    const name = file.name.toLowerCase();
    if (name.endsWith('.wav')) return { detected_type: 'WAV', kind: 'AUDIO' };
    if (name.endsWith('.flac')) return { detected_type: 'FLAC', kind: 'AUDIO' };
    if (name.endsWith('.jsonl')) return { detected_type: 'JSONL', kind: 'EVENTS' };
    if (name.endsWith('.json')) return { detected_type: 'JSON', kind: name.includes('layout') ? 'LAYOUT' : name.includes('track') ? 'TRACK' : 'EVENTS' };
    if (name.endsWith('.csv')) return { detected_type: 'CSV', kind: 'TRACK' };
    return { detected_type: 'UNKNOWN', kind: 'UNKNOWN' };
  }

  private validateImport(draft: ImportDraft) {
    const issues: ImportIssue[] = [];
    draft.files = draft.files.map((f) => {
      let status: ImportFileView['status'] = 'VALID';
      if (f.size_bytes === 0) {
        status = 'INVALID';
        issues.push({ code: 'EMPTY_FILE', file: f.name, field: null, row: null, message: 'File is empty.', blocking: true, recovery: 'Remove the file or choose the correct export.' });
      } else if (f.detected_type === 'UNKNOWN') {
        status = 'INVALID';
        issues.push({ code: 'UNSUPPORTED_TYPE', file: f.name, field: null, row: null, message: 'Content type is not supported (WAV, FLAC, JSON, JSONL, CSV).', blocking: true, recovery: 'Remove the file or convert it to a supported format.' });
      } else if (f.detected_type === 'CSV') {
        status = 'INVALID';
        issues.push({ code: 'UNKNOWN_UNITS', file: f.name, field: 'x', row: 1, message: 'Units for x/y are not declared; FlowLens does not guess CSV fields or units.', blocking: true, recovery: 'Declare units and column mapping in the manifest, or remove the file.' });
      }
      return { ...f, status };
    });
    const audio = draft.files.filter((f) => f.kind === 'AUDIO');
    if (!audio.length) issues.push({ code: 'NO_AUDIO', file: '—', field: null, row: null, message: 'At least one audio file (WAV or FLAC) is required.', blocking: true, recovery: 'Add an audio file.' });
    if (!draft.files.some((f) => f.kind === 'TRACK' && f.status === 'VALID')) issues.push({ code: 'TRACK_MISSING', file: '—', field: null, row: null, message: 'No track data. Movement conformance will be disabled.', blocking: false, recovery: 'Optional: add a JSON track export.' });
    draft.layout_version = draft.files.some((f) => f.kind === 'LAYOUT' && f.status === 'VALID') ? 'fictional-2' : null;
    draft.coverage = { audio: audio.length > 0, tracks: draft.files.some((f) => f.kind === 'TRACK' && f.status === 'VALID'), vehicles: null, speaker_identity: null, quality: 'AMBIGUOUS', gaps: [] };
    draft.issues = issues;
    draft.checksum_verified = draft.files.every((f) => f.status !== 'VALIDATING');
    draft.status = issues.some((i) => i.blocking) ? 'NEEDS_REMEDIATION' : 'READY';
    draft.version += 1;
  }

  private fileViews(files: ImportFileInput[], importId: string): ImportFileView[] {
    return files.map((f, i) => {
      const det = this.detect(f);
      const seconds = det.kind === 'AUDIO' ? 360 + Math.round((f.size % 240_000) / 1000) : null;
      return {
        id: mid(`${importId}:file:${f.name}:${i}`),
        name: f.name,
        ...det,
        size_bytes: f.size,
        channels: det.kind === 'AUDIO' ? 2 : null,
        duration_ms: seconds ? seconds * 1000 : null,
        channel_label: det.kind === 'AUDIO' ? (f.name.toLowerCase().includes('ground') ? 'Ground · Class B' : 'Tower · Class B') : det.kind === 'LAYOUT' ? 'Fictional aerodrome' : null,
        sha256: sha(`${importId}:${f.name}:${f.size}`),
        status: 'VALIDATING',
      };
    });
  }

  async createImport(input: { title: string; sourceKind: SourceKind; files: ImportFileInput[] }, opts: MutationOptions) {
    return this.idem(opts, input, () => {
      const acc = this.require('session.import', 'import.create');
      const id = crypto.randomUUID();
      const draft: ImportDraft = {
        id,
        version: 1,
        status: 'VALIDATING',
        title: input.title.trim() || 'Untitled session',
        source_kind: input.sourceKind,
        files: this.fileViews(input.files, id),
        issues: [],
        clock: { offset_ms: 0, timezone: 'UTC', uncertainty_ms: 40, mapping_version: 'clock-1', source_start_utc: '2026-10-08T14:20:00Z' },
        layout_version: null,
        checksum_verified: false,
        permissions: {
          local_read: { state: 'ALLOWED', note: 'Files are stored on this deployment.' },
          cloud_audio: { state: 'UNDETERMINED', note: 'Required for automatic transcription.' },
          cloud_transcript: { state: 'ALLOWED', note: 'Transcript text may be sent for analysis.' },
          reviewer_access: { state: 'ALLOWED', note: 'Granted reviewers may open evidence.' },
          report_export: { state: 'ALLOWED', note: 'Reports may be exported from analysis results.' },
          audio_export: { state: 'DENIED', note: 'Audio cannot be exported outside the deployment.' },
        },
        retention_days: 180,
        coverage: { audio: false, tracks: false, vehicles: null, speaker_identity: null, quality: 'AMBIGUOUS', gaps: [] },
        committed_session_id: null,
      };
      this.imports.set(id, draft);
      setTimeout(() => this.validateImport(draft), 1400);
      this.log(acc, 'session.import', 'import.create', 'OK', draft.title);
      return structuredClone(draft);
    });
  }

  async getImport(importId: string) {
    await delay();
    this.account();
    const d = this.imports.get(importId);
    if (!d) throw new ApiError('NOT_FOUND', 'Import draft not found.', { recovery: 'Start a new import.' });
    return structuredClone(d);
  }

  async addImportFiles(importId: string, files: ImportFileInput[], opts: MutationOptions) {
    return this.idem(opts, { importId, files }, () => {
      this.require('session.import', 'import.update');
      const d = this.imports.get(importId);
      if (!d) throw new ApiError('NOT_FOUND', 'Import draft not found.');
      d.files.push(...this.fileViews(files, `${importId}:${d.version}`));
      d.status = 'VALIDATING';
      setTimeout(() => this.validateImport(d), 1100);
      return structuredClone(d);
    });
  }

  async removeImportFile(importId: string, fileId: string, opts: MutationOptions) {
    return this.idem(opts, { importId, fileId }, () => {
      this.require('session.import', 'import.update');
      const d = this.imports.get(importId);
      if (!d) throw new ApiError('NOT_FOUND', 'Import draft not found.');
      d.files = d.files.filter((f) => f.id !== fileId);
      this.validateImport(d);
      return structuredClone(d);
    });
  }

  async setImportPermission(importId: string, key: PermissionKey, state: PermissionState, basis: string, opts: MutationOptions) {
    return this.idem(opts, { importId, key, state, basis }, () => {
      this.require('session.import', 'import.permission');
      const d = this.imports.get(importId);
      if (!d) throw new ApiError('NOT_FOUND', 'Import draft not found.');
      if (opts.expectedVersion != null && opts.expectedVersion !== d.version) throw new ApiError('VERSION_CONFLICT', 'The import changed since you opened it.', { recovery: 'Reload the preview.' });
      d.permissions[key] = { state, note: basis.trim() ? `Basis: ${basis.trim()}` : d.permissions[key].note };
      d.version += 1;
      return structuredClone(d);
    });
  }

  async commitImport(importId: string, opts: MutationOptions) {
    return this.idem(opts, { importId }, () => {
      const acc = this.require('session.import', 'import.commit');
      const d = this.imports.get(importId);
      if (!d) throw new ApiError('NOT_FOUND', 'Import draft not found.');
      if (d.status !== 'READY') throw new ApiError('INVALID_IMPORT', 'Resolve blocking validation issues before saving.', { recovery: 'Fix or remove the files listed in Validation.' });
      if (d.permissions.local_read.state !== 'ALLOWED') throw new ApiError('SOURCE_PERMISSION_REQUIRED', 'Local read permission is required to store the source.', { recovery: 'Record the local-read basis.' });
      const audio = d.files.filter((f) => f.kind === 'AUDIO');
      const duration = Math.max(...audio.map((f) => f.duration_ms ?? 0));
      const spec: ScenarioSpec = {
        ...DRAFT_IMPORT,
        key: `import-${importId.slice(0, 8)}`,
        title: d.title,
        durationMs: duration,
        recordedAt: d.clock.source_start_utc ?? nowIso(),
        updatedAt: nowIso(),
        hasLayout: !!d.layout_version,
        hasTracks: d.coverage.tracks,
        permissions: structuredClone(d.permissions),
        retentionDays: d.retention_days ?? 180,
        notices: [],
      };
      const sessionId = this.addSession(spec);
      this.order = [sessionId, ...this.order.filter((x) => x !== sessionId)];
      for (const a of this.accounts.filter((x) => x.active && x.role !== 'ADMIN')) {
        this.grants.push({ id: crypto.randomUUID(), session_id: sessionId, account_id: a.id, capabilities: ROLE_CAPABILITIES[a.role], granted_by: acc.name, granted_at: nowIso() });
      }
      d.status = 'COMMITTED';
      d.committed_session_id = sessionId;
      this.log(acc, 'session.import', 'import.commit', 'OK', d.title);
      return this.summary(this.sessions.get(sessionId)!);
    });
  }

  async estimateAnalysis(sessionId: string, profileId: string): Promise<AnalysisEstimate> {
    await delay();
    const s = this.session(sessionId);
    const blockers: string[] = [];
    if (s.lifecycle === 'ARCHIVED') blockers.push('Archived sessions are read-only.');
    if (s.permissions.cloud_audio.state !== 'ALLOWED') blockers.push(`Cloud audio permission is ${s.permissions.cloud_audio.state}.`);
    if (s.permissions.cloud_transcript.state !== 'ALLOWED') blockers.push(`Cloud transcript permission is ${s.permissions.cloud_transcript.state}.`);
    const unverified = this.profiles.filter((p) => p.readiness !== 'READY');
    if (unverified.length) blockers.push(`Provider profile not verified: ${unverified.map((p) => (p.provider === 'GOOGLE_STT' ? 'Google STT' : 'Gemini')).join(', ')}. Run a readiness check in Settings.`);
    if (mockControl.getState().providerOutage) blockers.push('Analysis provider is unavailable.');
    void profileId;
    const minutes = Math.round((s.world.spec.durationMs / 60_000) * s.world.spec.channels.length * 10) / 10;
    return { stt_requests: Math.ceil((s.world.spec.durationMs / 50_000) * s.world.spec.channels.length), gemini_requests: Math.ceil(s.world.spec.durationMs / 30_000), audio_minutes: minutes, budget_label: 'Within monthly research budget (MOCK)', blockers };
  }

  async startAnalysis(sessionId: string, profileId: string, opts: MutationOptions) {
    return this.idem(opts, { sessionId, profileId }, async () => {
      const acc = this.require('analysis.create', 'analysis.create');
      const s = this.session(sessionId);
      const est = await this.estimateAnalysis(sessionId, profileId);
      if (est.blockers.length) {
        const code = est.blockers.some((b) => b.startsWith('Cloud')) ? 'CLOUD_TRANSFER_BLOCKED' : 'PROVIDER_UNAVAILABLE';
        throw new ApiError(code, est.blockers[0]!, { recovery: 'Resolve the blockers listed above.' });
      }
      const view = this.newRun(s, acc, s.runs.length ? s.runs[s.runs.length - 1]!.input_revision : 1);
      return view;
    });
  }

  private newRun(s: SessionState, acc: Account, inputRevision: number) {
    // Seed runs need not start at #01 (Runway 27 keeps #02/#03), so number after the highest label.
    const highest = Math.max(0, ...s.runs.map((r) => Number(r.label.slice(1)) || 0));
    const label = `#${String(highest + 1).padStart(2, '0')}`;
    const id = crypto.randomUUID();
    const base = this.latestRun(s)?.run;
    const view: RunView = {
      run: { id, session_id: s.world.sessionId, analysis_run_id: id, revision: inputRevision, status: 'QUEUED', input_hash: sha(`${id}:input`), config_hash: sha(`${id}:config`), model_version: 'MOCK', api_version: 'mock-interactions-1', sdk_version: 'mock-sdk-1', prompt_version: 'prompt-v1', reducer_version: 'reducer-v1', rule_version: 'lab-1', usage: base?.usage ?? null },
      label,
      input_revision: inputRevision,
      created_at: nowIso(),
      completed_at: null,
      failure: null,
      coverage_note: null,
    };
    s.world.labels[id] = `Run ${label}`;
    s.runs.push(view);
    s.analysis = 'QUEUED';
    const job: JobView = { id: crypto.randomUUID(), session_id: s.world.sessionId, session_title: s.world.spec.title, run_label: label, stage: 'STT', status: 'QUEUED', attempt: 1, completed_units: 0, total_units: 6, updated_at: nowIso(), failure: null };
    this.jobs.unshift(job);
    this.log(acc, 'analysis.create', 'analysis.create', 'OK', s.world.spec.title);
    const stages: JobView['stage'][] = ['STT', 'INTENT', 'ASSOCIATION', 'FINDINGS', 'OPTIONS', 'BRIEF'];
    let step = 0;
    const tick = () => {
      if (view.run.status === 'CANCELLED') return;
      step += 1;
      view.run.status = 'RUNNING';
      s.analysis = 'RUNNING';
      job.status = 'RUNNING';
      job.stage = stages[Math.min(step - 1, stages.length - 1)]!;
      job.completed_units = step;
      job.updated_at = nowIso();
      this.stream.emit(s.world.sessionId, 'JOB_PROGRESS', { session_id: s.world.sessionId, analysis_run_id: id, revision: inputRevision, job_id: job.id, stage: job.stage, status: 'RUNNING', completed_units: step, total_units: 6 });
      if (step < 6) {
        setTimeout(tick, 700);
        return;
      }
      if (!s.world.spec.segments.length) {
        // Newly imported MOCK session: attach the synthetic open-loop scenario content.
        const filled = { ...REPORT_CLEAR, key: s.world.spec.key, title: s.world.spec.title, durationMs: Math.max(s.world.spec.durationMs, at('12:00')), permissions: s.permissions, runs: [] };
        // Same scenario key → same deterministic session ID; labels are carried over.
        const labels = s.world.labels;
        s.world = buildWorld(filled);
        Object.assign(s.world.labels, labels);
      }
      view.run.status = 'COMPLETED';
      view.completed_at = nowIso();
      s.analysis = 'COMPLETED';
      s.updatedAt = nowIso();
      job.status = 'SUCCEEDED';
      job.updated_at = nowIso();
      this.stream.emit(s.world.sessionId, 'JOB_PROGRESS', { session_id: s.world.sessionId, analysis_run_id: id, revision: inputRevision, job_id: job.id, stage: 'BRIEF', status: 'COMPLETED', completed_units: 6, total_units: 6 });
      this.notify({ title: `Analysis run ${label} completed`, detail: `${s.world.spec.title} · results available`, tone: 'ready', href: `/s/${s.world.sessionId}/review/findings?run=${id}` });
    };
    setTimeout(tick, 600);
    return view;
  }

  async cancelRun(scope: Scope, opts: MutationOptions) {
    return this.idem(opts, scope, () => {
      this.require('analysis.create', 'analysis.cancel');
      const s = this.session(scope.sessionId);
      const r = this.run(s, scope.runId);
      if (r.run.status === 'QUEUED' || r.run.status === 'RUNNING') {
        r.run.status = 'CANCELLED';
        s.analysis = this.latestRun(s)?.run.status ?? 'NOT_ANALYZED';
      }
      return r;
    });
  }

  /* ── Workspace ───────────────────────────────────────────────────── */

  private reviewerOf(s: SessionState, callsign: string): ReviewerState {
    const ids = s.world.spec.findings.filter((f) => f.entity === callsign).map((f) => s.world.findingIds.get(f.key)!);
    const reviews = ids.flatMap((id) => s.findingReviews.get(id) ?? []).sort((a, b) => a.recorded_at.localeCompare(b.recorded_at));
    const last = reviews[reviews.length - 1];
    if (!last) return 'UNREVIEWED';
    return last.decision === 'CONFIRMED' ? 'CONFIRMED' : last.decision === 'DISMISSED' ? 'DISMISSED' : 'UNRESOLVED';
  }

  private hiddenCount(s: SessionState, mode: ReplayMode, asOf: number) {
    if (mode !== 'AS_KNOWN') return 0;
    return s.world.spec.segments.filter((x) => segStart(x) <= asOf && segAvailable(x) > asOf).length + s.world.spec.findings.filter((f) => at(f.t) <= asOf && at(f.available) > asOf).length;
  }

  async getSnapshot(scope: Scope, asOf: AsOf): Promise<WorkspaceSnapshot> {
    await delay();
    const s = this.session(scope.sessionId);
    const run = this.run(s, scope.runId);
    const forceStale = mockControl.getState().staleTracks;
    const w = s.world;
    const runId = run.run.id;
    const findings = this.findingViews(s, runId, asOf.mode, asOf.asOfMs).map((f) => f.finding);
    const markers: WorkspaceSnapshot['event_markers'] = w.spec.segments
      .filter((x) => visible(asOf.mode, asOf.asOfMs, segStart(x), segAvailable(x)) || asOf.mode === 'DEBRIEF')
      .map((x) => ({ id: w.evIds.get(x.key)!, t: segStart(x), kind: x.act === 'INSTRUCTION' ? 'INSTRUCTION' : x.act === 'CORRECTION' ? 'CORRECTION' : x.act === 'REPORT' ? 'REPORT' : 'READBACK', label: `${x.evidence} · ${x.entity ?? 'Unknown'}` }));
    for (const f of w.spec.findings) if (asOf.mode === 'DEBRIEF' || visible(asOf.mode, asOf.asOfMs, at(f.t), at(f.available))) markers.push({ id: w.findingIds.get(f.key)!, t: at(f.t), kind: 'FINDING', label: `${f.key} · ${f.title}` });
    return {
      as_of_ms: asOf.asOfMs,
      mode: asOf.mode,
      snapshot: {
        session_id: w.sessionId,
        analysis_run_id: runId,
        revision: run.input_revision,
        as_of_ms: asOf.asOfMs,
        mode: asOf.mode,
        sequence: 1,
        events: sourceEvents(w, runId, asOf.mode, asOf.asOfMs),
        memory: memoryEvents(w, runId, asOf.mode, asOf.asOfMs, forceStale),
        findings,
        quality: w.manifest.coverage.quality,
      },
      entities: entityStates(w, asOf.mode, asOf.asOfMs, forceStale, (c) => this.reviewerOf(s, c)),
      tracks: tracksFor(w, runId, asOf.asOfMs, forceStale),
      series: seriesFor(w, asOf.asOfMs, forceStale),
      open_loops: w.spec.loops.map((l) => loopFor(w, l, runId, asOf.mode, asOf.asOfMs)).filter((l): l is NonNullable<typeof l> => !!l),
      geometry: geometryFor(w, runId, asOf.asOfMs, forceStale),
      gaps: gapsFor(w),
      event_markers: markers.sort((a, b) => a.t - b.t),
      hidden_after_as_of: this.hiddenCount(s, asOf.mode, asOf.asOfMs),
    };
  }

  async getEntityMemory(scope: Scope, entityId: string, asOf: AsOf): Promise<EntityMemoryView> {
    const snap = await this.getSnapshot(scope, asOf);
    const s = this.session(scope.sessionId);
    const w = s.world;
    const entity = w.entities.find((e) => e.id === entityId);
    if (!entity) throw new ApiError('NOT_FOUND', 'Object not found in this session.');
    const state = snap.entities.find((e) => e.entity_id === entityId)!;
    const segs = w.spec.segments.filter((x) => x.entity === entity.callsign);
    const vis = segs.filter((x) => visible(asOf.mode, asOf.asOfMs, segStart(x), segAvailable(x)));
    const lastInstr = [...vis].reverse().find((x) => x.act === 'INSTRUCTION');
    const lastHeard = lastInstr ? [...vis].reverse().find((x) => x.act !== 'INSTRUCTION' && segStart(x) > segStart(lastInstr)) : undefined;
    const interp = (x?: SegmentSpec) => (x?.quality === 'AMBIGUOUS' ? 'AMBIGUOUS' : 'SUPPORTED') as EntityMemoryView['observed']['interpretation'];
    const history: HistoryItem[] = [];
    for (const x of segs) {
      const shown = visible(asOf.mode, asOf.asOfMs, segStart(x), segAvailable(x));
      if (!shown) continue;
      const title = x.act === 'INSTRUCTION' ? 'Instruction received' : x.act === 'READBACK' ? 'Candidate readback' : x.act === 'CORRECTION' ? 'Correction' : x.act === 'REPORT' ? 'Report' : 'Transmission';
      history.push({ id: w.evIds.get(x.key)!, t: segStart(x), title, detail: `${x.role === 'CONTROLLER' ? 'ATC' : x.role === 'VEHICLE' ? 'Vehicle' : 'Pilot'}: “${x.text}”`, tone: x.effects?.readback === 'MISMATCH' ? 'discrepancy' : x.act === 'CORRECTION' ? 'notice' : 'data', evidence_id: w.evIds.get(x.key)!, available_ms: segAvailable(x), debrief_only: segAvailable(x) > asOf.asOfMs });
    }
    for (const f of w.spec.findings.filter((x) => x.entity === entity.callsign)) {
      if (!visible(asOf.mode, asOf.asOfMs, at(f.t), at(f.available))) continue;
      history.push({ id: w.findingIds.get(f.key)!, t: at(f.t), title: f.category === 'READBACK_DISCREPANCY' ? 'Discrepancy detected' : f.title, detail: f.statement, tone: f.priority === 'ATTENTION' ? 'discrepancy' : f.priority === 'NOTICE' ? 'notice' : 'muted', evidence_id: w.findingIds.get(f.key)!, available_ms: at(f.available), debrief_only: at(f.available) > asOf.asOfMs });
    }
    const reviewer = this.reviewerOf(s, entity.callsign);
    history.push({ id: `${entityId}:review`, t: asOf.asOfMs, title: reviewer === 'UNREVIEWED' ? 'Review not yet recorded' : `Reviewer: ${reviewer.toLowerCase()}`, detail: reviewer === 'UNREVIEWED' ? 'Awaiting evaluator review.' : 'Recorded as an append-only review.', tone: 'muted', evidence_id: null, available_ms: null, debrief_only: false });
    history.sort((a, b) => a.t - b.t);
    const ids = vis.map((x) => w.evIds.get(x.key)!);
    return {
      entity,
      state,
      said: lastInstr ? { quote: lastInstr.text, evidence_id: w.evIds.get(lastInstr.key)!, lifecycle: state.instruction.state, interpretation: interp(lastInstr), reviewer, highlight: lastInstr.highlight ?? null } : null,
      heard: lastHeard ? { quote: lastHeard.text, evidence_id: w.evIds.get(lastHeard.key)!, readback: state.readback.state, interpretation: interp(lastHeard), reviewer, highlight: lastHeard.highlight ?? null, speaker: lastHeard.entity ? `Candidate · ${lastHeard.entity}` : 'Candidate · unknown' } : null,
      observed: { movement: state.movement.state, statement: state.movement.state === 'NOT_EVALUABLE' ? 'Position not available; movement conformance cannot be assessed yet.' : (state.movement.summary ?? 'Unknown'), reason: state.movement.reason, interpretation: state.track_status === 'MISSING' ? 'CANDIDATE' : 'SUPPORTED', reviewer },
      history,
      open_loops: snap.open_loops.filter((l) => l.entity_ids.includes(entityId)),
      provenance: { input_revision: this.run(s, scope.runId).input_revision, reducer_version: 'reducer-v1', rule_version: 'lab-1', evidence_ids: ids, updated_at: s.updatedAt },
      hidden_after_as_of: segs.filter((x) => segStart(x) <= asOf.asOfMs && !visible(asOf.mode, asOf.asOfMs, segStart(x), segAvailable(x))).length + segs.filter((x) => segStart(x) > asOf.asOfMs).length,
    };
  }

  async getRunwayMemory(scope: Scope, runwayId: string, asOf: AsOf): Promise<RunwayMemoryView> {
    const snap = await this.getSnapshot(scope, asOf);
    const s = this.session(scope.sessionId);
    const w = s.world;
    const related = w.entities.filter((e) => w.spec.segments.some((x) => x.entity === e.callsign && (x.runway === '27' || x.runway === '09')));
    return {
      runway_id: runwayId,
      coverage: !w.spec.hasTracks ? 'AUDIO_ONLY' : w.spec.gaps.length || w.entities.some((e) => !w.spec.tracks.some((t) => t.entity === e.callsign)) ? 'PARTIAL' : 'COMPLETE',
      objects: related.map((e) => ({ entity: e, state: snap.entities.find((x) => x.entity_id === e.id)! })),
      active_instructions: w.spec.segments
        .filter((x) => x.act === 'INSTRUCTION' && x.runway && visible(asOf.mode, asOf.asOfMs, segStart(x), segAvailable(x)))
        .map((x) => ({ entity_id: w.entityByCallsign.get(x.entity!)!.id, summary: x.effects?.instructionSummary ?? x.text, evidence_id: w.evIds.get(x.key)!, t: segStart(x) }))
        .reverse(),
      occupancy: w.entities.map((e) => {
        const g = snap.geometry.find((x) => x.entity_id === e.id)!;
        const spec = w.spec.tracks.find((t) => t.entity === e.callsign);
        const intervals = spec?.footprint && g.status === 'EVALUATED'
          ? spec.waypoints.reduce<{ start_ms: number; end_ms: number }[]>((acc, [c, , y], i, arr) => {
              const next = arr[i + 1];
              if (Math.abs(y) <= 23 && next && Math.abs(next[2]) <= 23) acc.push({ start_ms: at(c), end_ms: Math.min(at(next[0]), asOf.asOfMs) });
              return acc;
            }, []).filter((r) => r.start_ms <= asOf.asOfMs)
          : [];
        return { entity_id: e.id, intervals, status: g.status, reason: g.reason };
      }),
      open_loops: snap.open_loops,
      gaps: w.spec.gaps,
    };
  }

  /* ── Transcript ──────────────────────────────────────────────────── */

  private transcriptRows(s: SessionState, runId: string, mode: ReplayMode, asOf: number): TranscriptRow[] {
    const w = s.world;
    const stale = s.staleRunIds.has(runId);
    return w.spec.segments
      .filter((x) => mode === 'DEBRIEF' || visible(mode, asOf, segStart(x), segAvailable(x)))
      .map((x) => {
        const original = segmentFor(w, x, runId);
        const revisions = s.transcriptRevisions.get(x.key) ?? [];
        const latest = revisions[revisions.length - 1] ?? original;
        let association = associationFor(w, x, runId);
        const reviews = s.assocReviews.get(x.key) ?? [];
        const lastReview = reviews[reviews.length - 1];
        if (association && lastReview) {
          association = { ...association, revision: lastReview.revision, status: lastReview.targetId ? 'CONFIRMED_BY_REVIEW' : 'AMBIGUOUS', target_intent_id: lastReview.targetId ? mid(`${w.spec.key}:intent:${w.spec.segments.find((y) => w.segIds.get(y.key) === lastReview.targetId)?.key}`) : null };
        }
        const targets: TranscriptRow['association_targets'] = [];
        if (x.assoc?.alternatives?.length) {
          for (const alt of x.assoc.alternatives) {
            const evLabel = alt.split(' ').pop();
            const seg = w.spec.segments.find((y) => y.evidence === evLabel);
            if (seg) targets.push({ id: w.segIds.get(seg.key)!, label: alt, entity: seg.entity });
          }
        } else if (x.assoc?.target) {
          const seg = w.spec.segments.find((y) => y.key === x.assoc!.target)!;
          targets.push({ id: w.segIds.get(seg.key)!, label: `${seg.entity ?? 'Unknown'} · ${seg.act === 'INSTRUCTION' ? 'Instruction' : 'Transmission'} ${seg.evidence}`, entity: seg.entity });
        }
        return {
          segment: latest,
          original,
          revisions,
          label: x.key,
          evidence_label: x.evidence,
          intent: s.analysis === 'PARTIAL' && x.act === 'UNKNOWN' ? null : intentFor(w, x, runId),
          association,
          association_targets: targets,
          stale_dependents: revisions.length ? w.spec.findings.filter((f) => f.evidence.includes(x.key)).length + 2 : stale ? 1 : 0,
        };
      });
  }

  async getTranscript(scope: Scope, asOf: AsOf): Promise<TranscriptView> {
    await delay();
    const s = this.session(scope.sessionId);
    this.run(s, scope.runId);
    return { rows: this.transcriptRows(s, scope.runId, asOf.mode, asOf.asOfMs), channels: s.world.spec.channels, hidden_after_as_of: asOf.mode === 'AS_KNOWN' ? s.world.spec.segments.filter((x) => segAvailable(x) > asOf.asOfMs).length : 0 };
  }

  private segBySegId(s: SessionState, segmentId: string) {
    const spec = s.world.spec.segments.find((x) => s.world.segIds.get(x.key) === segmentId);
    if (!spec) throw new ApiError('NOT_FOUND', 'Transcript segment not found.');
    return spec;
  }

  private assertWritable(s: SessionState) {
    if (s.lifecycle === 'ARCHIVED') throw new ApiError('ACCESS_DENIED', 'Archived sessions are read-only.', { recovery: 'Open the session in read-only mode.' });
  }

  private maybeConflict(targetLabel: string) {
    if (!mockControl.getState().versionConflictNext) return;
    mockControl.getState().set({ versionConflictNext: false });
    throw new ApiError('VERSION_CONFLICT', `${targetLabel} was updated by Sam Ortiz while you were editing.`, { recovery: 'Your draft is kept. Load the latest revision, then save again.', details: { actor: 'Sam Ortiz' } });
  }

  async correctTranscript(scope: Scope, segmentId: string, input: { text: string; reason: string }, opts: MutationOptions) {
    return this.idem(opts, { scope, segmentId, input }, async () => {
      const acc = this.require('review.write', 'transcript.correct');
      const s = this.session(scope.sessionId);
      this.assertWritable(s);
      const spec = this.segBySegId(s, segmentId);
      const revs = s.transcriptRevisions.get(spec.key) ?? [];
      const current = revs[revs.length - 1] ?? segmentFor(s.world, spec, scope.runId);
      if (opts.expectedVersion != null && opts.expectedVersion !== current.revision) throw new ApiError('VERSION_CONFLICT', 'A newer transcript revision exists.', { recovery: 'Your draft is kept. Load the latest revision, then save again.' });
      this.maybeConflict(`Segment ${spec.key}`);
      if (!input.reason.trim()) throw new ApiError('INVALID_IMPORT', 'A reason is required.', { fields: [{ field: 'reason', message: 'Required' }] });
      const rev: TranscriptSegment = { ...current, id: crypto.randomUUID(), revision: current.revision + 1, text: input.text.trim(), origin: 'HUMAN_CORRECTION', reason: input.reason.trim(), supersedes_id: current.id, recorded_at: nowIso() };
      s.transcriptRevisions.set(spec.key, [...revs, rev]);
      s.runs.forEach((r) => s.staleRunIds.add(r.run.id));
      s.briefs.forEach((b) => {
        if (!b.stale) {
          b.stale = true;
          b.stale_reason = `Transcript ${spec.key} was corrected after this brief was created.`;
        }
      });
      s.updatedAt = nowIso();
      this.log(acc, 'review.write', 'transcript.correct', 'OK', s.world.spec.title);
      this.stream.emit(s.world.sessionId, 'TRANSCRIPT_REVISION', rev);
      return { rows: this.transcriptRows(s, scope.runId, 'DEBRIEF', s.world.spec.durationMs), channels: s.world.spec.channels, hidden_after_as_of: 0 };
    });
  }

  async reviewAssociation(scope: Scope, segmentId: string, input: { targetId: string | null; reason: string }, opts: MutationOptions) {
    return this.idem(opts, { scope, segmentId, input }, async () => {
      const acc = this.require('review.write', 'association.review');
      const s = this.session(scope.sessionId);
      this.assertWritable(s);
      const spec = this.segBySegId(s, segmentId);
      const reviews = s.assocReviews.get(spec.key) ?? [];
      const currentRevision = reviews.length + 1;
      if (opts.expectedVersion != null && opts.expectedVersion !== currentRevision) throw new ApiError('VERSION_CONFLICT', 'A newer association review exists.', { recovery: 'Load the latest revision, then save again.' });
      this.maybeConflict(`Association for ${spec.key}`);
      s.assocReviews.set(spec.key, [...reviews, { targetId: input.targetId, reason: input.reason.trim(), at: nowIso(), actor: acc.name, revision: currentRevision + 1 }]);
      this.log(acc, 'review.write', 'association.review', 'OK', s.world.spec.title);
      return { rows: this.transcriptRows(s, scope.runId, 'DEBRIEF', s.world.spec.durationMs), channels: s.world.spec.channels, hidden_after_as_of: 0 };
    });
  }

  /* ── Findings / options / evidence ───────────────────────────────── */

  private findingViews(s: SessionState, runId: string, mode: ReplayMode, asOf: number): FindingView[] {
    const w = s.world;
    const stale = s.staleRunIds.has(runId);
    return w.spec.findings
      .filter((f) => visible(mode, asOf, at(f.t), at(f.available)))
      .map((f) => {
        const base = findingFor(w, f, runId, stale);
        const reviews = s.findingReviews.get(base.id) ?? [];
        const last = reviews[reviews.length - 1];
        const status = last ? (last.decision === 'CONFIRMED' ? 'CONFIRMED' : last.decision === 'DISMISSED' ? 'DISMISSED' : 'UNRESOLVED') : base.status;
        return {
          finding: { ...base, status, revision: base.revision + reviews.length },
          label: f.key,
          title: f.title,
          entity_label: f.entity,
          source_alert: f.sourceAlert ?? { status: 'NOT_AVAILABLE', severity: null, note: 'No source alert was recorded.' },
          movement: f.movement,
          reviews,
          correction_note: f.correctionNote && (mode === 'DEBRIEF' || asOf >= at('05:26')) ? f.correctionNote : null,
        };
      })
      .sort((a, b) => {
        const rank = { ATTENTION: 0, NOTICE: 1, INFO: 2 } as const;
        return rank[a.finding.priority] - rank[b.finding.priority] || b.finding.event_time_ms - a.finding.event_time_ms;
      });
  }

  async listFindings(scope: Scope, asOf: AsOf) {
    await delay();
    const s = this.session(scope.sessionId);
    this.run(s, scope.runId);
    return this.findingViews(s, scope.runId, asOf.mode, asOf.asOfMs);
  }

  private makeReview(s: SessionState, acc: Account, runId: string, targetId: string, targetRevision: number, decision: Review['decision'], reason: string, evidence: Review['evidence'], supersedes: string | null): Review {
    return { id: crypto.randomUUID(), session_id: s.world.sessionId, analysis_run_id: runId, revision: 1, target_id: targetId, target_revision: targetRevision, actor_id: acc.id, expected_version: targetRevision, decision, reason, supersedes_id: supersedes, evidence, event_time_ms: 0, available_time_ms: null, recorded_at: nowIso() };
  }

  async reviewFinding(scope: Scope, findingId: string, input: { decision: 'CONFIRMED' | 'DISMISSED' | 'UNRESOLVED'; reason: string }, opts: MutationOptions) {
    return this.idem(opts, { scope, findingId, input }, () => {
      const acc = this.require('review.write', 'finding.review');
      const s = this.session(scope.sessionId);
      this.assertWritable(s);
      const view = this.findingViews(s, scope.runId, 'DEBRIEF', s.world.spec.durationMs).find((f) => f.finding.id === findingId);
      if (!view) throw new ApiError('NOT_FOUND', 'Finding not found.');
      if (opts.expectedVersion != null && opts.expectedVersion !== view.finding.revision) throw new ApiError('VERSION_CONFLICT', 'A newer review revision exists for this finding.', { recovery: 'Your draft is kept. Load the latest revision, then save again.' });
      if (mockControl.getState().versionConflictNext) {
        const other = this.accounts.find((a) => a.role === 'CONTROLLER_REVIEW')!;
        const list = s.findingReviews.get(findingId) ?? [];
        s.findingReviews.set(findingId, [...list, this.makeReview(s, other, scope.runId, findingId, view.finding.revision, 'UNRESOLVED', 'Audio is clipped at the runway slot; needs a second listen.', view.finding.evidence, list[list.length - 1]?.id ?? null)]);
        this.maybeConflict(`Finding ${view.label}`);
      }
      if (input.reason.trim().length < 3) throw new ApiError('INVALID_IMPORT', 'A reason is required.', { fields: [{ field: 'reason', message: 'Required' }] });
      const list = s.findingReviews.get(findingId) ?? [];
      const review = this.makeReview(s, acc, scope.runId, findingId, view.finding.revision, input.decision, input.reason.trim(), view.finding.evidence, list[list.length - 1]?.id ?? null);
      s.findingReviews.set(findingId, [...list, review]);
      s.updatedAt = nowIso();
      this.log(acc, 'review.write', 'finding.review', 'OK', s.world.spec.title);
      this.stream.emit(s.world.sessionId, 'REVIEW_ADDED', review);
      return review;
    });
  }

  async listOptions(scope: Scope, asOf: AsOf): Promise<OptionSetView> {
    await delay();
    const s = this.session(scope.sessionId);
    this.run(s, scope.runId);
    const w = s.world;
    const caps = this.caps();
    const options: OptionView[] = w.spec.options
      .filter((o) => visible(asOf.mode, asOf.asOfMs, at(o.asOf), at(o.available)))
      .map((o) => {
        const base = optionFor(w, o, scope.runId);
        const reviews = s.optionReviews.get(base.id) ?? [];
        const last = reviews[reviews.length - 1];
        const evidenceLabels: Record<string, string> = {};
        for (const k of o.evidence) {
          const seg = w.spec.segments.find((x) => x.key === k);
          if (seg) evidenceLabels[w.evIds.get(seg.key)!] = seg.evidence;
          else if (w.findingIds.has(k)) evidenceLabels[w.findingIds.get(k)!] = k;
        }
        return {
          option: { ...base, revision: base.revision + reviews.length, review_status: last ? (last.decision as OptionView['option']['review_status']) : 'UNREVIEWED' },
          label: o.key,
          title: o.title,
          evaluation_question: o.question,
          evidence_labels: evidenceLabels,
          reviews,
          review_allowed: caps.includes('review.write') && s.lifecycle !== 'ARCHIVED',
        };
      });
    return {
      options,
      insufficient: w.spec.insufficient.map((x) => ({ entity_id: w.entityByCallsign.get(x.entity)?.id ?? x.entity, entity_label: x.entity, needed: x.needed, reason: x.reason })),
      provider_available: s.providerAvailable && !mockControl.getState().providerOutage,
    };
  }

  async reviewOption(scope: Scope, optionId: string, input: { decision: 'RELEVANT' | 'NOT_RELEVANT' | 'UNSUPPORTED' | 'UNRESOLVED'; reason: string }, opts: MutationOptions) {
    return this.idem(opts, { scope, optionId, input }, async () => {
      const acc = this.require('review.write', 'option.review');
      const s = this.session(scope.sessionId);
      this.assertWritable(s);
      const set = await this.listOptions(scope, { mode: 'DEBRIEF', asOfMs: s.world.spec.durationMs });
      const view = set.options.find((o) => o.option.id === optionId);
      if (!view) throw new ApiError('NOT_FOUND', 'Option not found.');
      if (opts.expectedVersion != null && opts.expectedVersion !== view.option.revision) throw new ApiError('VERSION_CONFLICT', 'A newer rating exists for this option.', { recovery: 'Load the latest revision, then save again.' });
      this.maybeConflict(view.label);
      const list = s.optionReviews.get(optionId) ?? [];
      const review = this.makeReview(s, acc, scope.runId, optionId, view.option.revision, input.decision, input.reason.trim(), view.option.evidence, list[list.length - 1]?.id ?? null);
      s.optionReviews.set(optionId, [...list, review]);
      this.log(acc, 'review.write', 'option.review', 'OK', s.world.spec.title);
      this.stream.emit(s.world.sessionId, 'REVIEW_ADDED', review);
      return review;
    });
  }

  async getEvidence(scope: Scope, id: string, asOf: AsOf): Promise<EvidenceBundle> {
    await delay();
    const s = this.session(scope.sessionId);
    const run = this.run(s, scope.runId);
    const w = s.world;
    const caps = this.caps();
    let segKeys: string[];
    let label = w.labels[id] ?? 'Evidence';
    let title: string;
    let finding: (typeof w.spec.findings)[number] | undefined;
    const fKey = [...w.findingIds.entries()].find(([, v]) => v === id)?.[0];
    const oKey = [...w.optionIds.entries()].find(([, v]) => v === id)?.[0];
    const sKey = w.spec.segments.find((x) => w.evIds.get(x.key) === id || w.segIds.get(x.key) === id)?.key;
    if (fKey) {
      finding = w.spec.findings.find((f) => f.key === fKey)!;
      segKeys = finding.evidence;
      title = finding.title;
    } else if (oKey) {
      const o = w.spec.options.find((x) => x.key === oKey)!;
      segKeys = o.evidence.filter((k) => k.startsWith('T-'));
      title = o.title;
    } else if (sKey) {
      const seg = w.spec.segments.find((x) => x.key === sKey)!;
      segKeys = seg.assoc?.target ? [seg.assoc.target, sKey] : [sKey];
      label = seg.evidence;
      title = seg.act === 'INSTRUCTION' ? 'Instruction' : seg.act === 'CORRECTION' ? 'Correction' : seg.act === 'REPORT' ? 'Report' : 'Readback';
    } else {
      throw new ApiError('EVIDENCE_UNAVAILABLE', 'Evidence could not be resolved for this session and run.', { recovery: 'The item may belong to another run. Check the run selector.' });
    }
    const segs = segKeys.map((k) => w.spec.segments.find((x) => x.key === k)).filter((x): x is SegmentSpec => !!x);
    const items: EvidenceItemView[] = segs.map((x) => {
      const ch = w.spec.channels[x.ch];
      const revs = s.transcriptRevisions.get(x.key);
      const ev = evidenceFor(w, x, run.run.id);
      return {
        evidence: revs?.length ? { ...ev, quote: x.text } : ev,
        label: x.evidence,
        role: x.act === 'INSTRUCTION' || x.act === 'REQUEST' ? 'SAID' : x.act === 'UNKNOWN' ? 'EVENT' : 'HEARD',
        channel: ch?.label ?? null,
        speaker: x.role === 'CONTROLLER' ? `ATC · ${ch?.label ?? 'Tower'}` : `Candidate · ${x.entity ?? 'unknown'}`,
        highlight: x.highlight ?? null,
        available_ms: segAvailable(x),
      };
    });
    const heard = segs.find((x) => x.assoc);
    const quality = finding?.quality ?? segs[0]?.quality ?? 'SUPPORTED';
    const forceStale = mockControl.getState().staleTracks;
    const trackSpec = finding ? w.spec.tracks.find((t) => t.entity === finding!.entity) : undefined;
    return {
      id,
      label,
      title,
      as_of_ms: asOf.asOfMs,
      items,
      slots: finding?.slots ?? [],
      range: segs.length ? { start_ms: Math.min(...segs.map(segStart)), end_ms: Math.max(...segs.map(segEnd)) } : null,
      association: heard?.assoc ? { status: (s.assocReviews.get(heard.key)?.length ? 'CONFIRMED_BY_REVIEW' : heard.assoc.status), note: heard.assoc.unknowns?.includes('speaker identity') ? 'Speaker identity not confirmed.' : heard.assoc.status === 'AMBIGUOUS' ? 'Pairing kept unresolved; alternatives listed.' : 'Pairing accepted by validation, not by domain review.' } : null,
      source_events: sourceEvents(w, run.run.id, 'DEBRIEF', w.spec.durationMs).filter((e) => !finding || e.source_event_id === `alert-${finding.key}` || (finding.category === 'QUALITY_GAP' && e.kind === 'QUALITY')),
      track_note: forceStale && trackSpec ? 'Track stale (age 38 s). Movement is NOT_EVALUABLE at this as-of.' : (finding?.trackNote ?? (trackSpec ? null : 'No track for this object in the source.')),
      provenance: { model_version: 'MOCK', prompt_version: 'prompt-v1', rule_version: 'lab-1', input_revision: run.input_revision, source_quality: quality, applicability: finding ? 'LAB_ONLY' : null },
      alternatives: heard?.assoc?.alternatives?.length ? heard.assoc.alternatives : ['No alternative pairing within ±60 s of this transmission.'],
      audio_access: caps.includes('audio.play') && !mockControl.getState().audioAccessDenied ? 'ALLOWED' : 'DENIED',
    };
  }

  async reanalyze(scope: Scope, opts: MutationOptions) {
    return this.idem(opts, scope, () => {
      const acc = this.require('analysis.create', 'analysis.create');
      const s = this.session(scope.sessionId);
      this.assertWritable(s);
      this.requireProvider(s);
      const latest = this.latestRun(s)!;
      return this.newRun(s, acc, latest.input_revision + 1);
    });
  }

  /* ── Debrief ─────────────────────────────────────────────────────── */

  async getJournal(scope: Scope, asOf: AsOf): Promise<JournalEntry[]> {
    await delay();
    const s = this.session(scope.sessionId);
    const w = s.world;
    const out: JournalEntry[] = [];
    for (const x of w.spec.segments) {
      if (!visible(asOf.mode, asOf.asOfMs, segStart(x), segAvailable(x))) continue;
      if (!x.entity && x.act !== 'READBACK') continue;
      const kind: JournalEntry['kind'] = x.act === 'INSTRUCTION' ? 'INSTRUCTION' : x.act === 'CORRECTION' ? 'CORRECTION' : x.act === 'REPORT' ? 'REPORT' : 'READBACK';
      const title = kind === 'INSTRUCTION' ? 'Instruction' : kind === 'CORRECTION' ? 'Correction' : kind === 'REPORT' ? 'Report' : 'Readback';
      const detail = kind === 'INSTRUCTION' ? `ATC to ${x.entity}: ${x.effects?.instructionSummary ?? x.text}.` : `“${x.text}”`;
      out.push({ id: w.evIds.get(x.key)!, t: segStart(x), kind, title, detail, label: x.evidence, tone: x.effects?.readback === 'MISMATCH' ? 'discrepancy' : 'data' });
    }
    for (const f of w.spec.findings) {
      if (!visible(asOf.mode, asOf.asOfMs, at(f.t), at(f.available))) continue;
      out.push({ id: w.findingIds.get(f.key)!, t: at(f.t), kind: 'FINDING', title: `Finding ${f.key}`, detail: f.statement, label: f.key, tone: f.priority === 'ATTENTION' ? 'discrepancy' : 'muted' });
    }
    for (const [fid, reviews] of s.findingReviews) {
      for (const r of reviews) out.push({ id: r.id, t: s.world.spec.durationMs, kind: 'REVIEW', title: 'Review recorded', detail: `${w.labels[fid]} · ${r.decision.toLowerCase()} — “${r.reason}”`, label: w.labels[fid] ?? 'Review', tone: 'muted' });
    }
    return out.sort((a, b) => a.t - b.t);
  }

  private buildBrief(s: SessionState, runId: string, asOf: number, revision: number, createdAt: string, staleReason: string | null): BriefView {
    const w = s.world;
    const mode: ReplayMode = 'DEBRIEF';
    const states = entityStates(w, mode, asOf, false, (c) => this.reviewerOf(s, c));
    const findings = this.findingViews(s, runId, mode, asOf);
    const loops = w.spec.loops.map((l) => loopFor(w, l, runId, mode, asOf)).filter((l): l is NonNullable<typeof l> => !!l);
    const label = (id: string) => w.labels[id] ?? 'E-?';
    type Item = BriefView['sections'][number]['items'][number];
    const item = (statement: string, ids: string[], detail: string | null, unknowns: string[] = []): Item => ({ statement, evidence_ids: (ids.length ? ids : [w.manifest.id]) as [string, ...string[]], unknowns, detail, evidence_labels: ids.map(label) });
    const sections: BriefView['sections'] = [];
    const known: Item[] = states.filter((st) => st.instruction.evidence_id).map((st) => {
      const e = w.entities.find((x) => x.id === st.entity_id)!;
      const seg = w.spec.segments.find((x) => w.evIds.get(x.key) === st.instruction.evidence_id);
      return item(`${e.callsign} received instruction: ${st.instruction.summary}.`, [st.instruction.evidence_id!], `Supported by transcript and audio at ${seg?.t ?? '—'}.`);
    });
    const push = (section: BriefSection, title: string, items: Item[]) => items.length && sections.push({ section, title, items });
    push('KNOWN_SITUATION', 'Known situation', known.slice(0, 3));
    push('CONTEXT_CHANGES', 'Context changes', w.spec.segments.filter((x) => x.act === 'CORRECTION' && segStart(x) <= asOf).map((x) => item(`Later correction names RWY ${x.runway}.`, [w.evIds.get(x.key)!], `Occurred at ${x.t} after the initial readback.`)));
    push('OPEN_LOOPS', 'Still open', loops.filter((l) => l.status === 'OPEN').map((l) => {
      const spec = w.spec.loops.find((x) => w.loopIds.get(x.key) === l.id)!;
      return item(`${spec.detail.replace(/\.$/, '')} — not observed in stored coverage.`, [l.evidence[0].id], 'Additional data is needed to complete the context.', l.coverage_known ? [] : ['coverage gap']);
    }));
    push('FINDINGS', 'Findings', findings.filter((f) => f.finding.status !== 'DISMISSED').map((f) => item(`${f.label} · ${f.title}: ${f.finding.statement}`, f.finding.evidence.map((e) => e.id), `Priority ${f.finding.priority} · ${f.finding.status.replace('_', ' ').toLowerCase()}`, f.finding.unknowns)));
    push('REVIEW_STATUS', 'Review status', findings.slice(0, 1).map((f) => item(f.reviews.length ? `${f.reviews.length} reviewer decision(s) recorded for ${f.label}.` : `No reviewer decision recorded for ${f.label}.`, [f.finding.evidence[0].id], 'Review records are append-only.')));
    const unknown: Item[] = states.filter((st) => st.movement.state === 'NOT_EVALUABLE').map((st) => {
      const e = w.entities.find((x) => x.id === st.entity_id)!;
      const f = w.spec.findings.find((x) => x.entity === e.callsign);
      return item(`${e.callsign}: ${st.movement.reason ?? 'movement not evaluable'}. Movement conformance cannot be assessed.`, f ? findingFor(w, f, runId, false).evidence.map((x) => x.id) : [], null, ['movement']);
    });
    for (const g of w.spec.gaps) unknown.push(item(`Audio gap ${clockLabel(g.start_ms)}–${clockLabel(g.end_ms)} on all channels.`, [w.manifest.id], 'Communication in this interval is unknown.', ['communication during gap']));
    push('UNKNOWN_COVERAGE', 'Unknown & coverage', unknown);
    const top = findings.find((f) => f.finding.priority === 'ATTENTION');
    const evidence = findings.flatMap((f) => f.finding.evidence).slice(0, 6);
    return {
      brief: {
        id: mid(`${w.spec.key}:brief:${revision}`),
        session_id: w.sessionId,
        analysis_run_id: runId,
        revision,
        as_of_ms: asOf,
        items: sections.flatMap((x) => x.items.map(({ statement, evidence_ids, unknowns }) => ({ statement, evidence_ids, unknowns }))),
        labels: ['SYNTHETIC', 'MOCK', 'NOT_DOMAIN_VALIDATED', 'DEBRIEF'],
        model_version: 'MOCK',
        prompt_version: 'brief-prompt-v1',
        evidence: (evidence.length ? evidence : [evidenceFor(w, w.spec.segments[0]!, runId)]) as BriefView['brief']['evidence'],
        event_time_ms: asOf,
        available_time_ms: asOf,
        recorded_at: createdAt,
      },
      label: `Brief revision ${revision}`,
      stale: !!staleReason,
      stale_reason: staleReason,
      sections,
      spotlight: top ? { finding_id: top.finding.id, title: `${top.entity_label} · ${top.title}`, detail: top.finding.statement, metric: top.label, metric_label: `${top.finding.priority.toLowerCase()} · ${top.finding.status.toLowerCase()}` } : null,
    };
  }

  async listBriefs(scope: Scope) {
    await delay();
    const s = this.session(scope.sessionId);
    return [...s.briefs].reverse();
  }

  async createBrief(scope: Scope, asOfMs: number, opts: MutationOptions) {
    return this.idem(opts, { scope, asOfMs }, () => {
      const acc = this.require('export.create', 'brief.create');
      const s = this.session(scope.sessionId);
      this.requireProvider(s);
      if (!s.world.spec.segments.length) throw new ApiError('NOT_EVALUABLE', 'There are no analysis results to brief yet.', { recovery: 'Run an analysis first.' });
      const b = this.buildBrief(s, scope.runId, asOfMs, s.briefs.length + 1, nowIso(), null);
      s.briefs.push(b);
      this.log(acc, 'export.create', 'brief.create', 'OK', s.world.spec.title);
      return b;
    });
  }

  async getExportPolicy(scope: Scope): Promise<ExportPolicy> {
    await delay();
    const s = this.session(scope.sessionId);
    const caps = this.caps();
    const allowed = s.permissions.report_export.state === 'ALLOWED' && caps.includes('export.create');
    return {
      report_allowed: allowed,
      audio_allowed: s.permissions.audio_export.state === 'ALLOWED' && caps.includes('export.create'),
      redaction_required: !caps.includes('audio.play') || s.permissions.reviewer_access.state !== 'ALLOWED',
      expiry_hours: 24,
      reason: !caps.includes('export.create') ? 'Your role does not include export.create.' : s.permissions.report_export.state !== 'ALLOWED' ? `Report export is ${s.permissions.report_export.state}.` : null,
    };
  }

  async listExports(scope: Scope) {
    await delay();
    const s = this.session(scope.sessionId);
    const now = Date.now();
    s.exports.forEach((e) => {
      if (e.status === 'READY' && Date.parse(e.expires_at) < now) e.status = 'EXPIRED';
    });
    return [...s.exports].reverse();
  }

  async createExport(scope: Scope, input: { format: ExportFormat; briefId: string | null; includeJournal: boolean; redacted: boolean }, opts: MutationOptions) {
    return this.idem(opts, { scope, input }, async () => {
      const acc = this.require('export.create', 'export.create');
      const s = this.session(scope.sessionId);
      const policy = await this.getExportPolicy(scope);
      if (!policy.report_allowed) throw new ApiError('ACCESS_DENIED', policy.reason ?? 'Report export is not allowed.', { recovery: 'Ask an administrator to review export permissions.' });
      if (policy.redaction_required && !input.redacted) throw new ApiError('ACCESS_DENIED', 'Redaction is required for your grant.', { recovery: 'Keep “Redact restricted evidence” on.' });
      const created = nowIso();
      const job: ExportJob = { id: crypto.randomUUID(), session_id: s.world.sessionId, run_id: scope.runId, brief_id: input.briefId, format: input.format, status: 'PREPARING', include_journal: input.includeJournal, redacted: input.redacted, created_at: created, expires_at: addHours(created, policy.expiry_hours), size_bytes: null, failure: null };
      s.exports.push(job);
      setTimeout(() => {
        job.status = 'READY';
        job.size_bytes = input.format === 'JSON' ? 61_204 : input.format === 'CSV' ? 8_930 : 44_512;
        this.notify({ title: `${input.format} export ready`, detail: `${s.world.spec.title} · expires in ${policy.expiry_hours} h`, tone: 'ready', href: `/s/${s.world.sessionId}/debrief` });
      }, 2200);
      this.log(acc, 'export.create', 'export.create', 'OK', s.world.spec.title);
      return { ...job };
    });
  }

  async downloadExport(exportId: string) {
    await delay();
    const acc = this.require('export.create', 'export.download');
    for (const s of this.sessions.values()) {
      const job = s.exports.find((e) => e.id === exportId);
      if (!job) continue;
      if (job.status !== 'READY') throw new ApiError('EVIDENCE_UNAVAILABLE', `Export is ${job.status.toLowerCase()}.`, { recovery: 'Create a new export if permission allows.' });
      const brief = s.briefs.find((b) => b.brief.id === job.brief_id) ?? s.briefs[s.briefs.length - 1];
      const run = s.runs.find((r) => r.run.id === job.run_id);
      const base = `flowlens-${s.world.spec.key}-${run?.label.replace('#', 'run') ?? 'run'}-${job.format.toLowerCase()}`;
      const header = { source_kind: 'SYNTHETIC', labels: ['MOCK', 'NOT_DOMAIN_VALIDATED'], session: s.world.spec.title, run: run?.label, input_revision: run?.input_revision, model_version: 'MOCK', prompt_version: 'prompt-v1', rule_version: 'lab-1', schema_version: '1.0.0', timebase: 'session_time_ms (relative)', redacted: job.redacted, generated_at: nowIso() };
      const rows = brief?.sections.flatMap((sec) => sec.items.map((i) => ({ section: sec.title, statement: i.statement, evidence: i.evidence_labels.join(' '), unknowns: i.unknowns.join('; ') }))) ?? [];
      this.log(acc, 'export.create', 'export.download', 'OK', s.world.spec.title);
      if (job.format === 'JSON') return { filename: `${base}.json`, mime: 'application/json', content: JSON.stringify({ provenance: header, brief: brief?.brief ?? null, items: rows }, null, 2) };
      if (job.format === 'CSV') {
        // Neutralise spreadsheet formula injection (PRD §19.3).
        const cell = (v: string) => `"${(/^[=+\-@\t\r]/.test(v) ? `'${v}` : v).replace(/"/g, '""')}"`;
        const lines = ['section,statement,evidence,unknowns', ...rows.map((r) => [r.section, r.statement, r.evidence, r.unknowns].map(cell).join(','))];
        return { filename: `${base}.csv`, mime: 'text/csv', content: `# ${JSON.stringify(header)}\n${lines.join('\n')}` };
      }
      const esc = (v: string) => v.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
      const html = `<!doctype html><meta charset="utf-8"><title>${esc(s.world.spec.title)} — FlowLens debrief (MOCK)</title><style>body{font:15px/1.5 system-ui;max-width:760px;margin:40px auto;color:#191b20}h1{font-weight:500}small{color:#616975}li{margin:6px 0}</style><h1>${esc(s.world.spec.title)}</h1><p><small>SYNTHETIC · MOCK · NOT_DOMAIN_VALIDATED · ${esc(brief?.label ?? '')} · ${esc(run?.label ?? '')}</small></p>${(brief?.sections ?? []).map((sec) => `<h2>${esc(sec.title)}</h2><ul>${sec.items.map((i) => `<li>${esc(i.statement)} <small>[${esc(i.evidence_labels.join(', '))}]</small></li>`).join('')}</ul>`).join('')}<hr><pre>${esc(JSON.stringify(header, null, 2))}</pre>`;
      return { filename: `${base}.html`, mime: 'text/html', content: html };
    }
    throw new ApiError('NOT_FOUND', 'Export not found.');
  }

  async getMetrics(scope: Scope, asOfMs: number): Promise<MetricsView> {
    await delay();
    const s = this.session(scope.sessionId);
    const w = s.world;
    const minutes = Math.ceil(w.spec.durationMs / 60_000);
    const perMinute = Array.from({ length: minutes }, (_, m) => {
      const a = m * 60_000;
      const b = a + 60_000;
      const occupied = w.spec.segments.reduce((sum, x) => sum + Math.max(0, Math.min(b, segEnd(x)) - Math.max(a, segStart(x))), 0);
      const gap = w.spec.gaps.some((g) => g.start_ms < b && g.end_ms > a);
      return { minute: m, occupied_ms: occupied, gap };
    });
    const visibleSegs = w.spec.segments.filter((x) => segStart(x) <= asOfMs);
    let switches = 0;
    visibleSegs.reduce<string | null>((prev, x) => {
      if (x.entity && prev && x.entity !== prev) switches += 1;
      return x.entity ?? prev;
    }, null);
    const counts = new Map<string, number>();
    w.spec.findings.forEach((f) => counts.set(f.category, (counts.get(f.category) ?? 0) + 1));
    const LABEL: Record<string, string> = { READBACK_DISCREPANCY: 'Readback discrepancy', OPEN_LOOP: 'Open loop', QUALITY_GAP: 'Source / quality gap', CRITICAL_SLOT_UNCERTAIN: 'Critical slot uncertain', MOVEMENT_DIVERGENCE: 'Movement divergence', SPEECH_RECORD_DISCREPANCY: 'Speech–record discrepancy' };
    const active = visibleSegs.reduce((sum, x) => sum + Math.min(asOfMs, segEnd(x)) - segStart(x), 0);
    const hasPrev = s.runs.length > 1;
    const loops = w.spec.loops.map((l) => loopFor(w, l, scope.runId, 'DEBRIEF', asOfMs)).filter((l) => l && l.status === 'OPEN').length;
    return {
      experimental: true,
      active_audio_ms: active,
      previous_active_audio_ms: hasPrev ? Math.round(active * 0.94) : null,
      open_loops_at_as_of: loops,
      previous_open_loops: hasPrev ? loops + 1 : null,
      object_switches: switches,
      previous_object_switches: hasPrev ? switches : null,
      per_minute: perMinute,
      reference_ms: 20_000,
      reference_label: 'LAB_RULE reference 20 s/min',
      breakdown: [...counts.entries()].map(([category, count]) => ({ category: category as MetricsView['breakdown'][number]['category'], label: LABEL[category] ?? category, count })).sort((a, b) => b.count - a.count),
    };
  }

  async ask(scope: Scope, asOf: AsOf, question: string, opts: MutationOptions): Promise<QueryResultView> {
    return this.idem(opts, { scope, asOf, question }, async () => {
      this.account();
      const s = this.session(scope.sessionId);
      this.requireProvider(s);
      const w = s.world;
      const q = question.toLowerCase();
      const base = { id: crypto.randomUUID(), question, as_of_ms: asOf.asOfMs, mode: asOf.mode, context_range: { start_ms: 0, end_ms: asOf.asOfMs }, model_version: 'MOCK', asked_at: nowIso() };
      if (/\b(mark|confirm|dismiss|delete|change|set|update)\b/.test(q)) {
        return { ...base, status: 'INSUFFICIENT_CONTEXT', items: [], note: 'Questions are read-only. To change state, use the review actions on the finding, transcript or option.' };
      }
      if (/\b(clear|safe|cleared to|can .* (depart|land|cross))\b/.test(q)) {
        return { ...base, status: 'INSUFFICIENT_CONTEXT', items: [], note: 'Unknown — FlowLens does not indicate whether the runway is clear or an action is safe. It shows only recorded communication and observations; the controller keeps all authority.' };
      }
      const snap = await this.getSnapshot(scope, asOf);
      const entity = w.entities.find((e) => q.includes(e.callsign.toLowerCase()) || e.aliases.some((a) => q.includes(a.toLowerCase())) || q.includes(e.callsign.slice(3).toLowerCase()));
      const lbl = (id: string) => w.labels[id] ?? '—';
      if (entity) {
        const st = snap.entities.find((e) => e.entity_id === entity.id)!;
        const items: QueryResultView['items'] = [];
        if (st.instruction.evidence_id) items.push({ statement: `Last instruction: ${st.instruction.summary} (${st.instruction.state}).`, evidence_ids: [st.instruction.evidence_id], evidence_labels: [lbl(st.instruction.evidence_id)], unknowns: [] });
        if (st.readback.evidence_id) items.push({ statement: `Readback state: ${st.readback.summary ?? st.readback.state}.`, evidence_ids: [st.readback.evidence_id], evidence_labels: [lbl(st.readback.evidence_id)], unknowns: [] });
        for (const l of snap.open_loops.filter((x) => x.entity_ids.includes(entity.id) && x.status === 'OPEN')) {
          items.push({ statement: `Still pending: ${w.spec.loops.find((x) => w.loopIds.get(x.key) === l.id)?.detail ?? l.kind} Not observed in stored coverage.`, evidence_ids: [l.evidence[0].id], evidence_labels: [lbl(l.evidence[0].id)], unknowns: l.coverage_known ? [] : ['coverage gap'] });
        }
        items.push({ statement: `Movement: ${st.movement.state}${st.movement.reason ? ` — ${st.movement.reason}` : ''}.`, evidence_ids: [], evidence_labels: [], unknowns: st.movement.state === 'NOT_EVALUABLE' ? ['movement'] : [] });
        return { ...base, status: items.length > 1 ? 'COMPLETE' : 'PARTIAL', items, note: null };
      }
      const rwy = /runway\s*(\d{2})|\brwy\s*(\d{2})|\b(27|09)\b/.exec(q);
      if (rwy) {
        const r = rwy[1] ?? rwy[2] ?? rwy[3];
        const seg = [...w.spec.segments].reverse().find((x) => x.act === 'INSTRUCTION' && x.runway === r && visible(asOf.mode, asOf.asOfMs, segStart(x), segAvailable(x)));
        if (seg) return { ...base, status: 'COMPLETE', items: [{ statement: `Last instruction related to runway ${r}: ${seg.entity} — ${seg.effects?.instructionSummary ?? seg.text} at ${seg.t}.`, evidence_ids: [w.evIds.get(seg.key)!], evidence_labels: [seg.evidence], unknowns: [] }], note: 'This does not indicate whether the runway is clear.' };
      }
      return { ...base, status: 'INSUFFICIENT_CONTEXT', items: [], note: 'Unknown — not covered by this session, run and as-of. FlowLens answers only from this session’s evidence and does not give general aviation advice.' };
    });
  }

  /* ── Notifications ───────────────────────────────────────────────── */

  async listNotifications() {
    await delay();
    this.account();
    return this.notifications.slice(0, 20).map((n) => ({ ...n }));
  }

  async markNotificationsRead() {
    await delay();
    this.notifications.forEach((n) => (n.read = true));
  }

  /* ── Admin ───────────────────────────────────────────────────────── */

  async listAccounts() {
    await delay();
    this.require('admin.manage', 'admin.users');
    return this.accounts.map((a) => ({ ...a }));
  }

  async setAccountActive(accountId: string, active: boolean, opts: MutationOptions) {
    return this.idem(opts, { accountId, active }, () => {
      const acc = this.require('admin.manage', 'admin.user.update');
      const target = this.accounts.find((a) => a.id === accountId);
      if (!target) throw new ApiError('NOT_FOUND', 'Account not found.');
      if (target.id === acc.id) throw new ApiError('ACCESS_DENIED', 'You cannot deactivate your own account.');
      target.active = active;
      this.log(acc, 'admin.manage', active ? 'user.activate' : 'user.deactivate', 'OK', null);
      return { ...target };
    });
  }

  async resetAccountPassword(accountId: string, opts: MutationOptions) {
    return this.idem(opts, { accountId }, () => {
      const acc = this.require('admin.manage', 'admin.user.reset');
      const target = this.accounts.find((a) => a.id === accountId);
      if (!target) throw new ApiError('NOT_FOUND', 'Account not found.');
      target.must_change_password = true;
      this.log(acc, 'admin.manage', 'user.reset_password', 'OK', null);
      return { ...target };
    });
  }

  async listGrants(sessionId?: string) {
    await delay();
    this.require('admin.manage', 'admin.grants');
    return this.grants.filter((g) => !sessionId || g.session_id === sessionId).map((g) => ({ ...g }));
  }

  async addGrant(input: { sessionId: string; accountId: string; capabilities: Capability[] }, opts: MutationOptions) {
    return this.idem(opts, input, () => {
      const acc = this.require('admin.manage', 'admin.grant.add');
      const grant: SessionGrant = { id: crypto.randomUUID(), session_id: input.sessionId, account_id: input.accountId, capabilities: input.capabilities, granted_by: acc.name, granted_at: nowIso() };
      this.grants = this.grants.filter((g) => !(g.session_id === input.sessionId && g.account_id === input.accountId));
      this.grants.push(grant);
      this.log(acc, 'admin.manage', 'grant.add', 'OK', this.sessions.get(input.sessionId)?.world.spec.title ?? null);
      return grant;
    });
  }

  async revokeGrant(grantId: string, opts: MutationOptions) {
    return this.idem(opts, { grantId }, () => {
      const acc = this.require('admin.manage', 'admin.grant.revoke');
      const grant = this.grants.find((g) => g.id === grantId);
      this.grants = this.grants.filter((g) => g.id !== grantId);
      if (grant) {
        this.log(acc, 'admin.manage', 'grant.revoke', 'OK', this.sessions.get(grant.session_id)?.world.spec.title ?? null);
        this.stream.emit(grant.session_id, 'RESYNC_REQUIRED', { session_id: grant.session_id, analysis_run_id: null, revision: 1, reason: 'PERMISSION_CHANGED', snapshot_sequence: 0 });
      }
    });
  }

  async listProviderProfiles() {
    await delay();
    this.require('admin.manage', 'admin.providers');
    return this.profiles.map((p) => ({ ...p }));
  }

  async checkProviderProfile(profileId: string, opts: MutationOptions): Promise<ProviderCheckResult> {
    return this.idem(opts, { profileId, n: Date.now() }, async () => {
      const acc = this.require('admin.manage', 'provider.check');
      await new Promise((r) => setTimeout(r, 900));
      const p = this.profiles.find((x) => x.id === profileId);
      if (!p) throw new ApiError('NOT_FOUND', 'Provider profile not found.');
      const outage = mockControl.getState().providerOutage;
      p.readiness = outage ? 'UNAVAILABLE' : 'READY';
      this.log(acc, 'admin.manage', 'provider.check', outage ? 'DENIED' : 'OK', null);
      return { profile_id: p.id, readiness: p.readiness, checked_at: nowIso(), message: outage ? 'Provider unreachable (MOCK outage scenario). No request was sent.' : 'MOCK readiness check passed. This is not a real provider smoke test.' };
    });
  }

  async listJobs() {
    await delay();
    this.require('admin.manage', 'admin.jobs');
    return this.jobs.map((j) => ({ ...j }));
  }

  async retryJob(jobId: string, opts: MutationOptions) {
    return this.idem(opts, { jobId }, () => {
      this.require('admin.manage', 'job.retry');
      const j = this.jobs.find((x) => x.id === jobId);
      if (!j) throw new ApiError('NOT_FOUND', 'Job not found.');
      if (!['FAILED', 'RETRY_WAIT'].includes(j.status)) throw new ApiError('VERSION_CONFLICT', 'Only failed or waiting jobs can be retried.');
      j.status = 'QUEUED';
      j.attempt += 1;
      j.failure = null;
      j.updated_at = nowIso();
      setTimeout(() => {
        const outage = mockControl.getState().providerOutage;
        j.status = outage ? 'FAILED' : 'SUCCEEDED';
        j.failure = outage ? 'PROVIDER_UNAVAILABLE' : null;
        j.completed_units = outage ? j.completed_units : (j.total_units ?? j.completed_units);
        j.updated_at = nowIso();
      }, 1800);
      return { ...j };
    });
  }

  async cancelJob(jobId: string, opts: MutationOptions) {
    return this.idem(opts, { jobId }, () => {
      this.require('admin.manage', 'job.cancel');
      const j = this.jobs.find((x) => x.id === jobId);
      if (!j) throw new ApiError('NOT_FOUND', 'Job not found.');
      if (['SUCCEEDED', 'FAILED', 'CANCELLED'].includes(j.status)) throw new ApiError('VERSION_CONFLICT', 'This job has already finished.');
      j.status = 'CANCELLED';
      j.updated_at = nowIso();
      return { ...j };
    });
  }

  async getBudget(): Promise<BudgetView> {
    await delay();
    this.require('admin.manage', 'admin.budget');
    return { period: 'October 2026', spent_microunits: 18_400_000, limit_microunits: 60_000_000, stt_audio_ms: 9_820_000, gemini_tokens: 412_800 };
  }

  async getStorage(): Promise<StorageView> {
    await delay();
    this.require('admin.manage', 'admin.storage');
    const high = mockControl.getState().diskHighWater;
    const capacity = 512 * 1024 ** 3;
    const used = capacity * (high ? 0.91 : 0.62);
    const parts = [
      ['raw', 'Raw source assets', 0.46],
      ['derived', 'Derived audio', 0.27],
      ['database', 'Database (SQLite + WAL)', 0.04],
      ['exports', 'Exports', 0.03],
      ['backup', 'Local backup staging', 0.17],
      ['scratch', 'Scratch', 0.03],
    ] as const;
    return { capacity_bytes: capacity, used_bytes: used, warning_ratio: 0.8, hold_ratio: 0.9, breakdown: parts.map(([key, label, r]) => ({ key, label, bytes: Math.round(used * r) })), imports_held: high };
  }

  async listAudit(filter: { query?: string; result?: AuditEntry['result'] | 'ALL' }) {
    await delay();
    this.require('admin.manage', 'admin.audit');
    const q = filter.query?.trim().toLowerCase();
    return this.audit.filter((a) => (!filter.result || filter.result === 'ALL' || a.result === filter.result) && (!q || `${a.actor} ${a.action} ${a.session_title ?? ''} ${a.correlation_id}`.toLowerCase().includes(q)));
  }

  async listRetention(): Promise<RetentionPolicy[]> {
    await delay();
    this.require('admin.manage', 'admin.retention');
    return this.order.map((id) => {
      const s = this.sessions.get(id)!;
      return { session_id: id, session_title: s.world.spec.title, source_kind: 'SYNTHETIC', retention_days: s.world.spec.retentionDays, basis: 'Synthetic data created for this project.', purge_status: this.retention.get(id) ?? 'NONE' };
    });
  }

  async requestPurge(sessionId: string, reason: string, opts: MutationOptions) {
    return this.idem(opts, { sessionId, reason }, async () => {
      const acc = this.require('admin.manage', 'retention.purge_request');
      if (reason.trim().length < 8) throw new ApiError('INVALID_IMPORT', 'Give a reason of at least 8 characters.', { fields: [{ field: 'reason', message: 'Too short' }] });
      this.retention.set(sessionId, 'REQUESTED');
      this.log(acc, 'admin.manage', 'retention.purge_request', 'OK', this.sessions.get(sessionId)?.world.spec.title ?? null);
      return (await this.listRetention()).find((r) => r.session_id === sessionId)!;
    });
  }
}
