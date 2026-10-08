import type { ApiErrorCode } from './types';

export interface FieldIssue {
  field: string;
  message: string;
}

/** Typed API error mirroring PRD §22.3: code, safe message, field issues, request ID, recovery hint. */
export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly requestId: string;
  readonly recovery: string | null;
  readonly fields: FieldIssue[];
  readonly details: Record<string, unknown>;

  constructor(code: ApiErrorCode, message: string, opts: { recovery?: string; fields?: FieldIssue[]; details?: Record<string, unknown> } = {}) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.requestId = `req_${Math.random().toString(36).slice(2, 10)}`;
    this.recovery = opts.recovery ?? null;
    this.fields = opts.fields ?? [];
    this.details = opts.details ?? {};
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export function hasCode(error: unknown, ...codes: ApiErrorCode[]) {
  return isApiError(error) && codes.includes(error.code);
}

const TITLES: Record<ApiErrorCode, string> = {
  AUTH_REQUIRED: 'Sign in required',
  ACCESS_DENIED: 'Access restricted',
  INVALID_IMPORT: 'Import is not valid',
  SOURCE_PERMISSION_REQUIRED: 'Source permission required',
  CLOUD_TRANSFER_BLOCKED: 'Cloud transfer blocked',
  ALIGNMENT_REQUIRED: 'Clock alignment required',
  NOT_EVALUABLE: 'Not evaluable',
  VERSION_CONFLICT: 'A newer revision exists',
  IDEMPOTENCY_CONFLICT: 'Request conflict',
  PROVIDER_UNAVAILABLE: 'Analysis provider unavailable',
  PROVIDER_QUOTA_EXCEEDED: 'Provider quota exceeded',
  BUDGET_EXCEEDED: 'Budget exceeded',
  INVALID_AI_OUTPUT: 'AI output rejected',
  SOURCE_REVISION_CHANGED: 'Source revision changed',
  EVIDENCE_UNAVAILABLE: 'Evidence unavailable',
  NOT_FOUND: 'Not found',
  CONNECTION_LOST: 'Connection lost',
};

export function errorTitle(error: unknown) {
  return isApiError(error) ? TITLES[error.code] : 'Something went wrong';
}
