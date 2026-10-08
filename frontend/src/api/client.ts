/**
 * ApiClient — the only data port screens may use. It mirrors PRD §22.2.
 * Today it is implemented by the MOCK adapter (src/api/adapters/mock); after G-BE
 * an HTTP adapter generated from OpenAPI replaces it without touching screens.
 */
import type {
  Account,
  AnalysisEstimate,
  AuditEntry,
  AuthSession,
  BriefView,
  BudgetView,
  EntityMemoryView,
  EvidenceBundle,
  ExportFormat,
  ExportJob,
  ExportPolicy,
  FindingView,
  ImportDraft,
  ImportFileInput,
  JobView,
  JournalEntry,
  MetricsView,
  MutationOptions,
  NotificationItem,
  OptionReviewStatus,
  OptionSetView,
  PermissionKey,
  PermissionState,
  ProviderCheckResult,
  ProviderProfile,
  QueryResultView,
  ReplayMode,
  RetentionPolicy,
  Review,
  ReviewDecision,
  Role,
  RunView,
  RunwayMemoryView,
  SessionDetail,
  SessionGrant,
  SessionSummary,
  SourceKind,
  StorageView,
  StreamEvent,
  TranscriptView,
  WaveformView,
  WorkspaceSnapshot,
  Capability,
} from './types';

export interface Scope {
  sessionId: string;
  runId: string;
}

export interface AsOf {
  asOfMs: number;
  mode: ReplayMode;
}

export interface ApiClient {
  readonly kind: 'MOCK' | 'HTTP';

  // Auth
  getAuthSession(): Promise<AuthSession | null>;
  login(email: string, password: string): Promise<AuthSession>;
  logout(): Promise<void>;
  demoAccounts(): Promise<{ email: string; role: Role; name: string }[]>;

  // Sessions & imports
  listSessions(): Promise<SessionSummary[]>;
  getSession(sessionId: string): Promise<SessionDetail>;
  getWaveforms(sessionId: string): Promise<WaveformView[]>;
  createImport(input: { title: string; sourceKind: SourceKind; files: ImportFileInput[] }, opts: MutationOptions): Promise<ImportDraft>;
  getImport(importId: string): Promise<ImportDraft>;
  addImportFiles(importId: string, files: ImportFileInput[], opts: MutationOptions): Promise<ImportDraft>;
  removeImportFile(importId: string, fileId: string, opts: MutationOptions): Promise<ImportDraft>;
  setImportPermission(importId: string, key: PermissionKey, state: PermissionState, basis: string, opts: MutationOptions): Promise<ImportDraft>;
  commitImport(importId: string, opts: MutationOptions): Promise<SessionSummary>;
  estimateAnalysis(sessionId: string, profileId: string): Promise<AnalysisEstimate>;
  startAnalysis(sessionId: string, profileId: string, opts: MutationOptions): Promise<RunView>;
  cancelRun(scope: Scope, opts: MutationOptions): Promise<RunView>;

  // Replay / workspace
  getSnapshot(scope: Scope, asOf: AsOf): Promise<WorkspaceSnapshot>;
  getEntityMemory(scope: Scope, entityId: string, asOf: AsOf): Promise<EntityMemoryView>;
  getRunwayMemory(scope: Scope, runwayId: string, asOf: AsOf): Promise<RunwayMemoryView>;

  // Review
  getTranscript(scope: Scope, asOf: AsOf): Promise<TranscriptView>;
  correctTranscript(scope: Scope, segmentId: string, input: { text: string; reason: string }, opts: MutationOptions): Promise<TranscriptView>;
  reviewAssociation(scope: Scope, segmentId: string, input: { targetId: string | null; reason: string }, opts: MutationOptions): Promise<TranscriptView>;
  listFindings(scope: Scope, asOf: AsOf): Promise<FindingView[]>;
  reviewFinding(scope: Scope, findingId: string, input: { decision: Extract<ReviewDecision, 'CONFIRMED' | 'DISMISSED' | 'UNRESOLVED'>; reason: string }, opts: MutationOptions): Promise<Review>;
  listOptions(scope: Scope, asOf: AsOf): Promise<OptionSetView>;
  reviewOption(scope: Scope, optionId: string, input: { decision: Exclude<OptionReviewStatus, 'UNREVIEWED'>; reason: string }, opts: MutationOptions): Promise<Review>;
  getEvidence(scope: Scope, evidenceOrFindingId: string, asOf: AsOf): Promise<EvidenceBundle>;
  reanalyze(scope: Scope, opts: MutationOptions): Promise<RunView>;

  // Debrief
  getJournal(scope: Scope, asOf: AsOf): Promise<JournalEntry[]>;
  listBriefs(scope: Scope): Promise<BriefView[]>;
  createBrief(scope: Scope, asOfMs: number, opts: MutationOptions): Promise<BriefView>;
  getExportPolicy(scope: Scope): Promise<ExportPolicy>;
  listExports(scope: Scope): Promise<ExportJob[]>;
  downloadExport(exportId: string): Promise<{ filename: string; mime: string; content: string }>;
  createExport(scope: Scope, input: { format: ExportFormat; briefId: string | null; includeJournal: boolean; redacted: boolean }, opts: MutationOptions): Promise<ExportJob>;
  getMetrics(scope: Scope, asOfMs: number): Promise<MetricsView>;
  ask(scope: Scope, asOf: AsOf, question: string, opts: MutationOptions): Promise<QueryResultView>;

  // Notifications
  listNotifications(): Promise<NotificationItem[]>;
  markNotificationsRead(): Promise<void>;

  // Admin / operator
  listAccounts(): Promise<Account[]>;
  setAccountActive(accountId: string, active: boolean, opts: MutationOptions): Promise<Account>;
  resetAccountPassword(accountId: string, opts: MutationOptions): Promise<Account>;
  listGrants(sessionId?: string): Promise<SessionGrant[]>;
  addGrant(input: { sessionId: string; accountId: string; capabilities: Capability[] }, opts: MutationOptions): Promise<SessionGrant>;
  revokeGrant(grantId: string, opts: MutationOptions): Promise<void>;
  listProviderProfiles(): Promise<ProviderProfile[]>;
  checkProviderProfile(profileId: string, opts: MutationOptions): Promise<ProviderCheckResult>;
  listJobs(): Promise<JobView[]>;
  retryJob(jobId: string, opts: MutationOptions): Promise<JobView>;
  cancelJob(jobId: string, opts: MutationOptions): Promise<JobView>;
  getBudget(): Promise<BudgetView>;
  getStorage(): Promise<StorageView>;
  listAudit(filter: { query?: string; result?: AuditEntry['result'] | 'ALL' }): Promise<AuditEntry[]>;
  listRetention(): Promise<RetentionPolicy[]>;
  requestPurge(sessionId: string, reason: string, opts: MutationOptions): Promise<RetentionPolicy>;
}

export type ConnectionState = 'CONNECTED' | 'RECONNECTING' | 'RESYNCING' | 'OFFLINE';

export interface StreamClient {
  subscribe(sessionId: string, onEvent: (event: StreamEvent) => void, onState: (state: ConnectionState, lastSequence: number) => void): () => void;
}
