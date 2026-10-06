import {
  ApiRequestError,
  apiRequest,
  browserApiTransport,
  isAbortError,
  makeWebSocketUrl,
  type ApiTransport,
  type ApiWebSocket,
  type Decoder,
} from '../api'
import type {
  ApiAssistMessageWire,
  ApiEventPageWire,
  ApiEventWire,
  ApiHighlightWire,
  ApiOptionWire,
  ApiReviewReceiptWire,
  ApiSnapshotWire,
} from '../contracts/apiWire'
import type {
  AudioAlignmentReadModel,
  AudioAssetReadModel,
  AssistReviewReadModel,
  AssistHighlightReadModel,
  AssistUpdateReadModel,
  CandidateReadModel,
  EventPageReadModel,
  EvidenceRef,
  EvidenceResolution,
  ReplayFrameReadModel,
  ReplayReviewAdapter,
  ReplaySourceReadModel,
  ReviewOpenResult,
  ReviewSpeed,
  ReviewControl,
  ReviewReceipt,
  SubscriptionState,
  TranscriptReadModel,
} from '../contracts/replayReview'
import { ApiDashboardAdapter } from './apiDashboard'
import {
  decodeApiEventPage,
  decodeApiSnapshot,
  decodeCandidatePage,
  decodeHighlightPage,
  decodeControlReceipt,
  decodeEvidenceResolutions,
  decodeReviewReceipt,
  decodeReplayFrame,
  decodeSession,
  decodeTranscriptPage,
  decodeWebSocketMessage,
  toEventPageReadModel,
  toJobReadModel,
  toReplaySnapshotReadModel,
  toTranscriptReadModel,
} from './apiDecoders'

export interface ScopedApiCredential {
  token: string
  expires_at_ms?: number
}

export interface ScopedApiCredentials {
  source_read?: ScopedApiCredential
  review_control?: ScopedApiCredential
  source_review?: ScopedApiCredential
  /** Evaluator-scoped assist read capability; never used for transcript correction writes. */
  reviewer?: ScopedApiCredential
}

export interface ApiReplayScope {
  source_session_id: string
  review_session_id?: string
}

export interface ApiReplayReviewAdapterOptions {
  transport?: ApiTransport
  credentials?: ScopedApiCredentials
  scope?: ApiReplayScope
  replay_assist_profile?: boolean
  websocket_origin?: string
  reconnect_min_ms?: number
  reconnect_max_ms?: number
}

type CredentialName = 'source_read' | 'review_control' | 'source_review' | 'reviewer'

interface SubscriptionBase {
  active: boolean
  source_session_id: string
  token: string
  credential: CredentialName
  socket: ApiWebSocket | null
  reconnect_timer: ReturnType<typeof setTimeout> | null
  expiry_timer: ReturnType<typeof setTimeout> | null
  attempts: number
  state_listener?: (state: SubscriptionState, message?: string) => void
}

interface SourceSubscription extends SubscriptionBase {
  session_id: string
  expected_sequence_step: number
  listener: (frame: ReplayFrameReadModel | null) => void
  last_sequence: number | null
  last_frame?: ReplayFrameReadModel
  resyncing: boolean
  resync_generation: number
  controller: AbortController
  cleanup?: () => void
}

interface AssistSubscription extends SubscriptionBase {
  listener: (state: AssistUpdateReadModel) => void
  last_sequence: number | null
  awaiting_snapshot: boolean
  profile_checked: boolean
  cleanup?: () => void
}

const CURRENT_API_UNAVAILABLE = 'The local backend does not implement the replay/assist API profile.'
let requestCounter = 0

export class ApiReplayReviewAdapter extends ApiDashboardAdapter implements ReplayReviewAdapter {
  readonly mode = 'api' as const
  readonly supported_speeds: readonly ReviewSpeed[] = [0.5, 1, 2, 4]
  private readonly transport: ApiTransport
  private readonly websocketOrigin?: string
  private readonly reconnectMinMs: number
  private readonly reconnectMaxMs: number
  private readonly replayAssistProfile: boolean
  private credentials: ScopedApiCredentials
  private sourceScope?: ApiReplayScope
  private readonly audioUrlsBySource = new Map<string, Set<string>>()
  private readonly sourceSubscriptions = new Set<SourceSubscription>()
  private readonly assistSubscriptions = new Set<AssistSubscription>()
  private readonly sourceByListener = new Map<(frame: ReplayFrameReadModel | null) => void, SourceSubscription>()
  private readonly assistByListener = new Map<(state: AssistUpdateReadModel) => void, AssistSubscription>()
  private activeSourceId: string | null = null

  constructor(options: ApiReplayReviewAdapterOptions = {}) {
    const transport = options.transport ?? browserApiTransport
    super(transport)
    this.transport = transport
    this.credentials = options.credentials ?? {}
    this.sourceScope = options.scope
    this.replayAssistProfile = options.replay_assist_profile ?? false
    this.websocketOrigin = options.websocket_origin
    this.reconnectMinMs = Math.max(100, options.reconnect_min_ms ?? 500)
    this.reconnectMaxMs = Math.max(this.reconnectMinMs, options.reconnect_max_ms ?? 10_000)
  }

  /** Tokens stay in this adapter instance's memory and are never serialized or added to URLs. */
  setCredentials(credentials: ScopedApiCredentials): void {
    const changed = credentialChanged(this.credentials.source_read, credentials.source_read)
      || credentialChanged(this.credentials.review_control, credentials.review_control)
      || credentialChanged(this.credentials.source_review, credentials.source_review)
      || credentialChanged(this.credentials.reviewer, credentials.reviewer)
    this.credentials = credentials
    if (changed) this.stopAllSubscriptions('Credentials changed; reopen the replay subscriptions.', 'disconnected')
  }

  clearCredentials(): void {
    this.stopAllSubscriptions('Replay credentials were cleared.', 'unauthorized')
    this.credentials = {}
    this.sourceScope = undefined
    this.releaseAllAudioUrls()
  }

  dispose(): void {
    this.stopAllSubscriptions('Replay adapter was disposed.', 'disconnected')
    this.credentials = {}
    this.activeSourceId = null
    this.sourceScope = undefined
    this.releaseAllAudioUrls()
  }

  async openReview(sourceSessionId: string, operatorToken: string, signal?: AbortSignal): Promise<ReviewOpenResult> {
    if (!sourceSessionId || !operatorToken) throw invalidInput('A source session and operator credential are required to open a review.')
    this.activateSource(sourceSessionId)
    const opened = await this.scopedRequest('review_control', `/api/v1/sessions/${encodeURIComponent(sourceSessionId)}/reviews`, decodeOpenedReview, {
      method: 'POST', token: operatorToken, signal,
    })
    if (opened.source_id !== sourceSessionId) throw unsupported('Opened review belongs to a different source session.')
    this.sourceScope = { source_session_id: sourceSessionId, review_session_id: opened.id }
    this.credentials = {
      ...this.credentials,
      ...(opened.source_read_token ? { source_read: { token: opened.source_read_token } } : {}),
      review_control: { token: opened.token },
      // The operator credential remains a separate source-review capability; it is never sent as source_read.
      source_review: { token: operatorToken },
    }
    return { status: 'accepted', review_session_id: opened.id }
  }

  async loadSource(sourceSessionId: string, signal?: AbortSignal): Promise<ReplaySourceReadModel> {
    this.activateSource(sourceSessionId)
    this.assertSourceScope(sourceSessionId)
    const token = this.requireCredential('source_read')
    const session = await this.scopedRequest('source_read', `/api/v1/sessions/${encodeURIComponent(sourceSessionId)}`, decodeSession, {
      token,
      signal,
    })
    if (session.id !== sourceSessionId) throw unsupported('Session metadata ID does not match the requested source.')
    return {
      source_session_id: sourceSessionId,
      source_kind: session.condition === 'flowlens' || session.condition === 'baseline' ? 'synthetic' : 'unknown',
      label: session.condition === 'baseline' || session.condition === 'flowlens'
        ? 'SYNTHETIC / NOT OPERATIONALLY VALIDATED'
        : 'SOURCE PROFILE UNKNOWN',
      provenance: 'Current session metadata has no replay manifest or simulator provenance endpoint.',
      source_version: null,
      quality: 'unknown',
    }
  }

  async loadFrame(sourceSessionId: string, atMs: number, signal?: AbortSignal): Promise<ReplayFrameReadModel> {
    this.activateSource(sourceSessionId)
    this.assertSourceScope(sourceSessionId)
    if (!Number.isSafeInteger(atMs) || atMs < 0) throw invalidInput('Replay frame time must be a nonnegative integer in milliseconds.')

    const reviewSessionId = this.reviewSessionIdFor(sourceSessionId)
    const sessionId = reviewSessionId ?? sourceSessionId
    const credentialName: CredentialName = reviewSessionId ? 'review_control' : 'source_read'
    const token = this.requireCredential(credentialName)
    const snapshot = await this.scopedRequest(credentialName, `/api/v1/sessions/${encodeURIComponent(sessionId)}/snapshot`, decodeApiSnapshot, {
      token,
      signal,
    })
    this.assertSnapshotSource(snapshot, sourceSessionId)
    const frameTime = snapshot.playback_ms ?? snapshot.sim_ms
    if (frameTime !== atMs) {
      throw unavailable('This backend only exposes its current snapshot; it has no historical frame-at-time endpoint.')
    }
    return decodeReplayFrame({
      source_session_id: sourceSessionId,
      requested_ms: atMs,
      frame_ms: snapshot.sim_ms,
      snapshot,
    }, sourceSessionId, atMs)
  }

  async listEvents(sourceSessionId: string, cursor: number, untilMs?: number, signal?: AbortSignal): Promise<EventPageReadModel> {
    this.activateSource(sourceSessionId)
    this.assertSourceScope(sourceSessionId)
    if (!Number.isSafeInteger(cursor) || cursor < 0) throw invalidInput('Event cursor must be a nonnegative integer ordinal.')
    if (untilMs !== undefined && (!Number.isSafeInteger(untilMs) || untilMs < 0)) throw invalidInput('Event cutoff must be a nonnegative integer in session milliseconds.')
    const token = this.requireCredential('source_read')
    if (untilMs === undefined) {
      const page = await this.fetchEventPage(sourceSessionId, cursor, token, signal)
      return toEventPageReadModel(page)
    }

    // The current events route has no until_ms filter. Scan scoped pages and filter locally
    // so a later event can never leak into an earlier replay view.
    const rows: ApiEventWire[] = []
    let nextCursor = cursor
    while (true) {
      const page = await this.fetchEventPage(sourceSessionId, nextCursor, token, signal)
      if (page.next_cursor < nextCursor || (page.items.length > 0 && page.next_cursor === nextCursor)) {
        throw unsupported('Backend event cursor did not advance; the source page cannot be safely replayed.')
      }
      rows.push(...page.items.filter((event) => event.sim_ms <= untilMs))
      const exhausted = page.items.length === 0 && page.next_cursor === nextCursor
      nextCursor = page.next_cursor
      if (exhausted) break
    }
    return toEventPageReadModel({ items: rows, next_cursor: nextCursor })
  }

  async listTranscript(sourceSessionId: string, cursor: string | null = null, untilMs?: number, signal?: AbortSignal): Promise<TranscriptReadModel> {
    this.activateSource(sourceSessionId)
    this.assertSourceScope(sourceSessionId)
    if (untilMs !== undefined && (!Number.isSafeInteger(untilMs) || untilMs < 0)) throw invalidInput('Transcript cutoff must be a nonnegative integer in session milliseconds.')
    if (!this.replayAssistProfile) return { state: 'unavailable', items: [], next_cursor: cursor }

    const token = this.requireCredential('source_read')
    const query = new URLSearchParams()
    if (cursor !== null) query.set('cursor', cursor)
    if (untilMs !== undefined) query.set('until_ms', String(untilMs))
    const suffix = query.size ? `?${query.toString()}` : ''
    try {
      const page = await this.scopedRequest('source_read', `/api/v1/sessions/${encodeURIComponent(sourceSessionId)}/transcripts${suffix}`, decodeTranscriptPage, {
        token,
        signal,
      })
      return toTranscriptReadModel(page)
    } catch (error) {
      if (isMissingProfileRoute(error)) return { state: 'unavailable', items: [], next_cursor: cursor }
      throw error
    }
  }

  async loadAssistReview(sourceSessionId: string, analysisId?: string, signal?: AbortSignal): Promise<AssistReviewReadModel> {
    this.activateSource(sourceSessionId)
    this.assertSourceScope(sourceSessionId)
    if (!this.replayAssistProfile) {
      return {
        state: 'unavailable',
        message: 'The inspected backend has no transcript, highlight, candidate, or assist-stream routes for this replay profile.',
        provider_availability: 'unknown',
        evaluator_access: 'unknown', highlights: [],
        candidates: { state: 'unavailable', evaluator_access: 'unknown', message: 'Evaluator options are unavailable from the current API.', items: [] },
        review_annotations: [], jobs: [], analysis: null,
      }
    }

    const token = this.requireCredential('reviewer')
    const query = analysisId ? `?analysis_id=${encodeURIComponent(analysisId)}` : ''
    try {
      const highlights = await this.scopedRequest('reviewer', `/api/v1/sessions/${encodeURIComponent(sourceSessionId)}/highlights${query}`, decodeHighlightPage, { token, signal })
      const candidates = analysisId
        ? await this.listCandidates(sourceSessionId, analysisId, signal)
        : { state: 'unavailable' as const, evaluator_access: 'unknown' as const, message: 'No immutable replay analysis ID was supplied by the backend.', items: [] }
      return {
        state: highlights.length > 0 || candidates.state === 'ready' ? 'ready' : 'empty',
        provider_availability: 'unknown',
        evaluator_access: candidates.state === 'ready' || highlights.length > 0 ? 'granted' : 'unknown',
        highlights,
        candidates,
        review_annotations: [],
        jobs: [],
        analysis: candidates.analysis ?? null,
      }
    } catch (error) {
      if (isMissingProfileRoute(error)) {
        return {
          state: 'unavailable', message: 'The backend does not implement the scoped assist review routes.',
          provider_availability: 'unknown',
          evaluator_access: 'unknown', highlights: [],
          candidates: { state: 'unavailable', evaluator_access: 'unknown', message: 'Evaluator options are unavailable from the current API.', items: [] },
          review_annotations: [], jobs: [], analysis: null,
        }
      }
      throw error
    }
  }

  async loadAudioAsset(sourceSessionId: string, assetId?: string, signal?: AbortSignal): Promise<AudioAssetReadModel> {
    this.activateSource(sourceSessionId)
    this.assertSourceScope(sourceSessionId)
    if (!this.replayAssistProfile) return { state: 'unavailable', ...(assetId ? { asset_id: assetId } : {}), message: 'The inspected backend has no private audio asset route or source-read profile.' }
    if (!assetId) return { state: 'unavailable', message: 'No audio asset identity is available for this source.' }
    const token = this.requireCredential('source_read')
    const path = `/api/v1/sessions/${encodeURIComponent(sourceSessionId)}/audio-assets/${encodeURIComponent(assetId)}/content`
    let response: Response
    try {
      response = await this.transport.request(path, {
        method: 'GET',
        headers: { Accept: 'audio/*', Authorization: `Bearer ${token}` },
        signal,
      })
    } catch (error) {
      if (isAbortError(error)) throw error
      throw new ApiRequestError('disconnected', 'Could not reach the local API for the audio asset.', null, 'network')
    }
    if (response.status === 404) return { state: 'unavailable', asset_id: assetId, message: 'The backend does not expose this audio asset route or asset.' }
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        this.expireCredential('source_read')
        throw new ApiRequestError('unauthorized', 'Source-read access is unavailable for this audio asset.', response.status, response.status === 401 ? 'unauthorized' : 'forbidden')
      }
      if (response.status === 409) throw new ApiRequestError('conflict', 'The audio asset source scope changed.', 409, 'conflict')
      if (response.status === 503) throw new ApiRequestError('error', 'The audio asset service is unavailable.', 503, 'service_unavailable')
      throw new ApiRequestError('error', `The audio asset request failed with HTTP ${response.status}.`, response.status, 'http_error')
    }
    const blob = await response.blob()
    const mimeType = response.headers.get('Content-Type')?.split(';', 1)[0]?.trim() || blob.type
    if (!mimeType.startsWith('audio/')) throw unsupported('The audio asset response did not declare an audio media type.')
    const objectUrl = URL.createObjectURL(blob)
    const urls = this.audioUrlsBySource.get(sourceSessionId) ?? new Set<string>()
    urls.add(objectUrl)
    this.audioUrlsBySource.set(sourceSessionId, urls)
    let released = false
    return {
      state: 'ready', source_session_id: sourceSessionId, asset_id: assetId, object_url: objectUrl,
      mime_type: mimeType, duration_ms: null,
      alignment: { state: 'unknown', reason: 'The current audio content route does not provide a source-to-session time mapping.' },
      release: () => {
        if (released) return
        released = true
        URL.revokeObjectURL(objectUrl)
        const sourceUrls = this.audioUrlsBySource.get(sourceSessionId)
        sourceUrls?.delete(objectUrl)
        if (sourceUrls?.size === 0) this.audioUrlsBySource.delete(sourceSessionId)
      },
    }
  }

  sessionMsToAudioSeconds(alignment: AudioAlignmentReadModel, sessionMs: number): number | null {
    if (alignment.state !== 'mapped' || !Number.isFinite(sessionMs) || sessionMs < 0) return null
    const audioMs = sessionMs - alignment.offset_ms
    return audioMs < 0 ? null : audioMs / 1000
  }

  audioSecondsToSessionMs(alignment: AudioAlignmentReadModel, audioSeconds: number): number | null {
    if (alignment.state !== 'mapped' || !Number.isFinite(audioSeconds) || audioSeconds < 0) return null
    const sessionMs = Math.round(audioSeconds * 1000 + alignment.offset_ms)
    return Number.isSafeInteger(sessionMs) && sessionMs >= 0 ? sessionMs : null
  }

  async resolveEvidence(sourceSessionId: string, refs: EvidenceRef[], untilMs?: number, signal?: AbortSignal, analysisId?: string): Promise<EvidenceResolution[]> {
    this.activateSource(sourceSessionId)
    this.assertSourceScope(sourceSessionId)
    if (!this.replayAssistProfile || !this.credentials.source_read?.token) {
      return refs.map((ref) => ({ ref, state: 'unavailable' as const }))
    }
    const token = this.requireCredential('source_read')
    let raw: EvidenceResolution[]
    try {
      raw = await this.scopedRequest('source_read', `/api/v1/sessions/${encodeURIComponent(sourceSessionId)}/evidence`, decodeEvidenceResolutions, {
        method: 'POST', token, body: { refs, ...(untilMs === undefined ? {} : { until_ms: untilMs }), ...(analysisId === undefined ? {} : { analysis_id: analysisId }) }, signal,
      })
    } catch (error) {
      if (isMissingProfileRoute(error)) return refs.map((ref) => ({ ref, state: 'unavailable' }))
      throw error
    }
    const byRef = new Map(raw.map((item) => [`${item.ref.kind}:${item.ref.id}`, item]))
    return refs.map((ref) => byRef.get(`${ref.kind}:${ref.id}`) ?? { ref, state: 'unresolved' })
  }

  async listCandidates(sourceSessionId: string, analysisId: string, signal?: AbortSignal): Promise<CandidateReadModel> {
    this.activateSource(sourceSessionId)
    this.assertSourceScope(sourceSessionId)
    if (!this.replayAssistProfile) return { state: 'unavailable', evaluator_access: 'unknown', items: [] }
    const token = this.requireCredential('reviewer')
    try {
      return await this.scopedRequest(
        'reviewer',
        `/api/v1/sessions/${encodeURIComponent(sourceSessionId)}/replay-analyses/${encodeURIComponent(analysisId)}/options`,
        decodeCandidatePage,
        { token, signal },
      )
    } catch (error) {
      if (isMissingProfileRoute(error)) return { state: 'unavailable', evaluator_access: 'unknown', items: [] }
      throw error
    }
  }

  subscribeSource(
    sourceSessionId: string,
    listener: (frame: ReplayFrameReadModel | null) => void,
    stateListener?: (state: SubscriptionState, message?: string) => void,
  ): () => void {
    this.activateSource(sourceSessionId)
    this.assertSourceScope(sourceSessionId)
    this.sourceByListener.get(listener)?.cleanup?.()

    const reviewSessionId = this.reviewSessionIdFor(sourceSessionId)
    const credential: CredentialName = reviewSessionId ? 'review_control' : 'source_read'
    let token: string
    try {
      token = this.requireCredential(credential)
    } catch (error) {
      listener(null)
      stateListener?.('unauthorized', asMessage(error))
      return () => undefined
    }

    const subscription: SourceSubscription = {
      active: true,
      source_session_id: sourceSessionId,
      session_id: reviewSessionId ?? sourceSessionId,
      // Current Review.advance increments once per 50 ms manager clock pass while WS sends every 200 ms.
      expected_sequence_step: reviewSessionId ? 4 : 1,
      token,
      credential,
      socket: null,
      reconnect_timer: null,
      expiry_timer: null,
      attempts: 0,
      listener,
      state_listener: stateListener,
      last_sequence: null,
      resyncing: false,
      resync_generation: 0,
      controller: new AbortController(),
    }
    this.sourceSubscriptions.add(subscription)
    this.sourceByListener.set(listener, subscription)
    stateListener?.('loading')
    this.armExpiry(subscription)

    const cleanup = () => this.stopSourceSubscription(subscription, 'Source subscription closed.', 'disconnected')
    subscription.cleanup = cleanup
    void this.connectSource(subscription)
    return cleanup
  }

  subscribeAssist(
    sourceSessionId: string,
    listener: (state: AssistUpdateReadModel) => void,
    stateListener?: (state: SubscriptionState, message?: string) => void,
  ): () => void {
    this.activateSource(sourceSessionId)
    this.assertSourceScope(sourceSessionId)
    this.assistByListener.get(listener)?.cleanup?.()
    if (!this.replayAssistProfile) {
      stateListener?.('unavailable', CURRENT_API_UNAVAILABLE)
      listener({ type: 'unavailable', message: CURRENT_API_UNAVAILABLE })
      return () => undefined
    }

    let token: string
    try {
      token = this.requireCredential('reviewer')
    } catch (error) {
      const message = asMessage(error)
      listener({ type: 'state', state: 'unauthorized', message })
      stateListener?.('unauthorized', message)
      listener({ type: 'error', message })
      return () => undefined
    }

    const subscription: AssistSubscription = {
      active: true,
      source_session_id: sourceSessionId,
      token,
      credential: 'reviewer',
      socket: null,
      reconnect_timer: null,
      expiry_timer: null,
      attempts: 0,
      listener,
      state_listener: stateListener,
      last_sequence: null,
      awaiting_snapshot: false,
      profile_checked: false,
    }
    this.assistSubscriptions.add(subscription)
    this.assistByListener.set(listener, subscription)
    stateListener?.('loading')
    this.armExpiry(subscription)
    const cleanup = () => this.stopAssistSubscription(subscription, 'Assist subscription closed.', 'disconnected')
    subscription.cleanup = cleanup
    void this.connectAssist(subscription)
    return cleanup
  }

  async controlReview(sourceSessionId: string, control: ReviewControl): Promise<ReviewReceipt> {
    this.activateSource(sourceSessionId)
    this.assertReviewScope(sourceSessionId)
    const reviewSessionId = this.reviewSessionIdFor(sourceSessionId)
    if (!reviewSessionId) throw unavailable('A review session ID is required before review controls can be sent.')
    const token = this.requireCredential('review_control')
    if (!Number.isSafeInteger(control.expected_revision) || control.expected_revision < 0) throw invalidInput('Review revision must be a nonnegative integer.')
    const requestId = validateRequestId(control.request_id ?? makeRequestId('review-command'))
    const body: Record<string, unknown> = {
      command_id: requestId,
      expected_revision: control.expected_revision,
      type: control.type,
    }
    if (control.type === 'SEEK') {
      if (!Number.isSafeInteger(control.at_ms) || control.at_ms < 0) throw invalidInput('Seek time must be a nonnegative integer in milliseconds.')
      // The existing review command route accepts seconds; the UI port uses milliseconds.
      body.value = control.at_ms / 1000
    } else if (control.type === 'SET_SPEED') {
      body.value = control.speed
    }
    const raw = await this.scopedRequest('review_control', `/api/v1/sessions/${encodeURIComponent(reviewSessionId)}/commands`, undefinedDecoder, {
      method: 'POST', token, body,
    })
    const receipt = decodeControlReceipt(raw, reviewSessionId, requestId)
    return receipt
  }

  async correctTranscript(
    sourceSessionId: string,
    segmentId: string,
    expectedRevision: number,
    text: string,
    reason = 'Reviewer correction',
    requestId = makeRequestId('transcript-correction'),
  ): Promise<ReviewReceipt> {
    this.activateSource(sourceSessionId)
    this.assertSourceScope(sourceSessionId)
    if (!this.replayAssistProfile) return unavailableReceipt('The current backend has no transcript correction route.')
    if (!Number.isSafeInteger(expectedRevision) || expectedRevision < 0) throw invalidInput('Expected transcript revision must be a nonnegative integer.')
    if (typeof text !== 'string') throw invalidInput('Transcript correction text must be a string.')
    requestId = validateRequestId(requestId)
    const token = this.requireCredential('source_review')
    return this.postReviewReceipt(
      `/api/v1/sessions/${encodeURIComponent(sourceSessionId)}/transcripts/${encodeURIComponent(segmentId)}/corrections`,
      { request_id: requestId, expected_revision: expectedRevision, text, reason },
      requestId,
      token,
    )
  }

  async reviewCandidate(
    sourceSessionId: string,
    candidateId: string,
    expectedRevision: number,
    decision: 'confirmed' | 'dismissed' | 'unresolved',
    reason = 'Reviewer decision',
    analysisId?: string,
    requestId = makeRequestId('candidate-review'),
  ): Promise<ReviewReceipt> {
    this.activateSource(sourceSessionId)
    this.assertSourceScope(sourceSessionId)
    if (!this.replayAssistProfile) return unavailableReceipt('The current backend has no candidate review route.')
    if (!Number.isSafeInteger(expectedRevision) || expectedRevision < 0) throw invalidInput('Expected candidate revision must be a nonnegative integer.')
    if (!analysisId) throw unavailable('Candidate review requires its replay analysis ID.')
    requestId = validateRequestId(requestId)
    const token = this.requireCredential('source_review')
    return this.postReviewReceipt(
      `/api/v1/sessions/${encodeURIComponent(sourceSessionId)}/replay-analyses/${encodeURIComponent(analysisId)}/options/${encodeURIComponent(candidateId)}/review`,
      { request_id: requestId, expected_revision: expectedRevision, decision, reason },
      requestId,
      token,
    )
  }

  async reviewHighlight(
    sourceSessionId: string,
    highlightId: string,
    expectedRevision: number,
    decision: 'confirmed' | 'dismissed' | 'unresolved',
    reason = 'Reviewer decision',
    requestId = makeRequestId('highlight-review'),
  ): Promise<ReviewReceipt> {
    this.activateSource(sourceSessionId)
    this.assertSourceScope(sourceSessionId)
    if (!this.replayAssistProfile) return unavailableReceipt('The current backend has no highlight review route.')
    if (!Number.isSafeInteger(expectedRevision) || expectedRevision < 0) throw invalidInput('Expected highlight revision must be a nonnegative integer.')
    requestId = validateRequestId(requestId)
    const token = this.requireCredential('source_review')
    return this.postReviewReceipt(
      `/api/v1/sessions/${encodeURIComponent(sourceSessionId)}/highlights/${encodeURIComponent(highlightId)}/review`,
      { request_id: requestId, expected_revision: expectedRevision, decision, reason },
      requestId,
      token,
    )
  }

  private async postReviewReceipt(path: string, body: unknown, requestId: string, token: string): Promise<ReviewReceipt> {
    try {
      const receipt: ApiReviewReceiptWire = await this.scopedRequest('source_review', path, (value) => decodeReviewReceipt(value, requestId), {
        method: 'POST', token, body,
      })
      if (receipt.request_id !== requestId) throw unsupported('Review receipt request_id does not match the submitted action.')
      return {
        ...receipt,
        authority: 'server',
        ...(receipt.annotation ? { annotation: {
          kind: 'review_annotation', ...receipt.annotation, session_ms: null,
        } } : {}),
      }
    } catch (error) {
      if (isMissingProfileRoute(error)) return unavailableReceipt('The backend does not implement this replay review route.')
      throw error
    }
  }

  private async fetchEventPage(sourceSessionId: string, cursor: number, token: string, signal?: AbortSignal): Promise<ApiEventPageWire> {
    return this.scopedRequest(
      'source_read',
      `/api/v1/sessions/${encodeURIComponent(sourceSessionId)}/events?cursor=${cursor}&limit=500`,
      decodeApiEventPage,
      { token, signal },
    )
  }

  private async scopedRequest<T>(
    credential: CredentialName,
    path: string,
    decoder: Decoder<T>,
    options: { method?: 'GET' | 'POST'; token?: string; body?: unknown; signal?: AbortSignal },
  ): Promise<T> {
    try {
      return await apiRequest(path, decoder, { ...options, transport: this.transport })
    } catch (error) {
      if (error instanceof ApiRequestError && (error.reason === 'unauthorized' || error.reason === 'forbidden' || error.reason === 'expired')) {
        this.expireCredential(credential)
      }
      throw error
    }
  }

  private activateSource(sourceSessionId: string): void {
    if (this.activeSourceId !== null && this.activeSourceId !== sourceSessionId) {
      this.stopAllSubscriptions(`Source changed to ${sourceSessionId}; prior source projections were cleared.`, 'disconnected')
      this.releaseAudioUrlsForSource(this.activeSourceId)
      this.credentials = {}
      this.sourceScope = undefined
    }
    this.activeSourceId = sourceSessionId
  }

  private requireCredential(name: CredentialName): string {
    const credential = this.credentials[name]
    if (!credential?.token) throw new ApiRequestError('unauthorized', `A ${credentialLabel(name)} credential is required.`, 401, 'unauthorized')
    if (credential.expires_at_ms !== undefined && Date.now() >= credential.expires_at_ms) {
      this.expireCredential(name)
      throw new ApiRequestError('unauthorized', `The ${credentialLabel(name)} credential has expired.`, 401, 'expired')
    }
    return credential.token
  }

  private assertSourceScope(sourceSessionId: string): void {
    if (!sourceSessionId) throw invalidInput('Source session ID is required.')
    if (this.sourceScope && this.sourceScope.source_session_id !== sourceSessionId) {
      throw new ApiRequestError('unauthorized', 'The configured source-read scope does not match this source session.', 403, 'forbidden')
    }
  }

  private assertReviewScope(sourceSessionId: string): void {
    this.assertSourceScope(sourceSessionId)
    if (!this.sourceScope?.review_session_id) throw unavailable('Review controls require an explicit review session scope.')
  }

  private reviewSessionIdFor(sourceSessionId: string): string | null {
    if (this.sourceScope?.source_session_id !== sourceSessionId) return null
    return this.sourceScope.review_session_id ?? null
  }

  private assertSnapshotSource(snapshot: ApiSnapshotWire, requestedSourceId: string): void {
    const sourceId = snapshot.source_session_id ?? snapshot.metadata.id
    if (sourceId !== requestedSourceId) throw unsupported('Snapshot source ID does not match the requested source session.')
  }

  private async connectSource(subscription: SourceSubscription): Promise<void> {
    if (!subscription.active) return
    try {
      this.assertNotExpired(subscription.credential)
      const path = `/api/v1/sessions/${encodeURIComponent(subscription.session_id)}/stream`
      const socket = this.openWebSocket(path)
      subscription.socket = socket
      socket.onopen = () => {
        if (!subscription.active) return
        try {
          // SC-06 requires this token message to be the first WebSocket application message.
          socket.send(JSON.stringify({ token: subscription.token }))
        } catch (error) {
          this.handleSourceDisconnect(subscription, 'Could not send first-message WebSocket authentication.', error)
        }
      }
      socket.onmessage = (event) => {
        if (!subscription.active) return
        try {
          const message = decodeWebSocketMessage(parseSocketJson(event.data))
          if (message.profile !== 'source') throw unsupported('Source stream returned an assist-profile message.')
          this.acceptSourceSnapshot(subscription, message.snapshot)
        } catch (error) {
          subscription.state_listener?.('error', asMessage(error))
          this.stopSourceSubscription(subscription, asMessage(error), 'error')
        }
      }
      socket.onerror = () => {
        if (subscription.active) subscription.state_listener?.('disconnected', 'WebSocket connection encountered an error.')
      }
      socket.onclose = (event) => {
        subscription.socket = null
        if (!subscription.active) return
        if (event.code === 4401) {
          this.expireCredential(subscription.credential)
          this.stopSourceSubscription(subscription, 'Source stream authentication expired or was rejected.', 'unauthorized')
          return
        }
        if (event.code === 4403) {
          this.expireCredential(subscription.credential)
          this.stopSourceSubscription(subscription, 'Source stream access was denied.', 'unauthorized')
          return
        }
        if (event.code === 4404) {
          this.stopSourceSubscription(subscription, 'Source stream route is unavailable.', 'unavailable', true)
          return
        }
        this.handleSourceDisconnect(subscription, event.reason || 'Source stream disconnected.')
      }
    } catch (error) {
      this.handleSourceDisconnect(subscription, asMessage(error), error)
    }
  }

  private acceptSourceSnapshot(subscription: SourceSubscription, snapshot: ApiSnapshotWire): void {
    this.assertSnapshotSource(snapshot, subscription.source_session_id)
    const sequence = snapshot.sequence
    if (subscription.last_sequence !== null && sequence <= subscription.last_sequence) return
    if (subscription.last_sequence !== null && sequence > subscription.last_sequence + subscription.expected_sequence_step) {
      void this.resyncSource(subscription, sequence)
      return
    }
    this.deliverSourceSnapshot(subscription, snapshot)
  }

  private async resyncSource(subscription: SourceSubscription, incomingSequence: number): Promise<void> {
    if (!subscription.active || subscription.resyncing) return
    subscription.resyncing = true
    const generation = ++subscription.resync_generation
    subscription.state_listener?.('disconnected', `Snapshot sequence gap; resynchronizing from sequence ${incomingSequence}.`)
    try {
      const snapshot = await this.scopedRequest(
        subscription.credential,
        `/api/v1/sessions/${encodeURIComponent(subscription.session_id)}/snapshot`,
        decodeApiSnapshot,
        { token: subscription.token, signal: subscription.controller.signal },
      )
      if (!subscription.active || generation !== subscription.resync_generation) return
      this.assertSnapshotSource(snapshot, subscription.source_session_id)
      if (snapshot.sequence < incomingSequence || (subscription.last_sequence !== null && snapshot.sequence < subscription.last_sequence)) {
        this.handleSourceDisconnect(subscription, 'Full snapshot resync is older than the stream sequence.')
        return
      }
      this.deliverSourceSnapshot(subscription, snapshot)
    } catch (error) {
      if (!isAbortError(error)) this.handleSourceDisconnect(subscription, asMessage(error), error)
    } finally {
      if (generation === subscription.resync_generation) subscription.resyncing = false
    }
  }

  private deliverSourceSnapshot(subscription: SourceSubscription, snapshot: ApiSnapshotWire): void {
    subscription.last_sequence = snapshot.sequence
    subscription.attempts = 0
    const frame = frameFromSnapshot(snapshot, subscription.source_session_id, snapshot.playback_ms ?? snapshot.sim_ms)
    subscription.last_frame = frame
    subscription.state_listener?.('connected')
    subscription.listener(frame)
  }

  private handleSourceDisconnect(subscription: SourceSubscription, message: string, error?: unknown): void {
    if (!subscription.active) return
    if (error instanceof ApiRequestError && (error.reason === 'expired' || error.reason === 'unauthorized' || error.reason === 'forbidden')) {
      this.expireCredential(subscription.credential)
      this.stopSourceSubscription(subscription, message, 'unauthorized')
      return
    }
    subscription.state_listener?.('disconnected', message)
    if (subscription.last_frame) {
      subscription.listener({ ...subscription.last_frame, state: 'disconnected', connection_message: message })
    }
    this.scheduleSourceReconnect(subscription)
  }

  private scheduleSourceReconnect(subscription: SourceSubscription): void {
    if (!subscription.active || subscription.reconnect_timer !== null) return
    subscription.attempts += 1
    const delay = Math.min(this.reconnectMinMs * (2 ** Math.min(subscription.attempts - 1, 8)), this.reconnectMaxMs)
    subscription.reconnect_timer = setTimeout(() => {
      subscription.reconnect_timer = null
      void this.connectSource(subscription)
    }, delay)
  }

  private async connectAssist(subscription: AssistSubscription): Promise<void> {
    if (!subscription.active) return
    try {
      this.assertNotExpired(subscription.credential)
      if (!subscription.profile_checked) {
        try {
          await this.scopedRequest(
            'reviewer',
            `/api/v1/sessions/${encodeURIComponent(subscription.source_session_id)}/transcripts?cursor=`,
            decodeTranscriptPage,
            { token: subscription.token },
          )
          subscription.profile_checked = true
        } catch (error) {
          if (isMissingProfileRoute(error)) {
            subscription.listener({ type: 'unavailable', message: CURRENT_API_UNAVAILABLE })
            this.stopAssistSubscription(subscription, CURRENT_API_UNAVAILABLE, 'unavailable')
            return
          }
          throw error
        }
      }
      const path = `/api/v1/sessions/${encodeURIComponent(subscription.source_session_id)}/assist-stream`
      const socket = this.openWebSocket(path)
      subscription.socket = socket
      socket.onopen = () => {
        if (!subscription.active) return
        try {
          socket.send(JSON.stringify({ token: subscription.token }))
        } catch {
          socket.close(1011, 'Authentication message failed')
        }
      }
      socket.onmessage = (event) => {
        if (!subscription.active) return
        try {
          const decoded = decodeWebSocketMessage(parseSocketJson(event.data))
          if (decoded.profile !== 'assist') throw unsupported('Assist stream returned a source snapshot.')
          this.acceptAssistMessage(subscription, decoded.message)
        } catch (error) {
          subscription.listener({ type: 'error', message: asMessage(error) })
          this.stopAssistSubscription(subscription, asMessage(error), 'error')
        }
      }
      socket.onerror = () => {
        if (subscription.active) subscription.state_listener?.('disconnected', 'Assist stream encountered a connection error.')
      }
      socket.onclose = (event) => {
        subscription.socket = null
        if (!subscription.active) return
        if (event.code === 4401) {
          this.expireCredential(subscription.credential)
          this.stopAssistSubscription(subscription, 'Assist stream credential expired or was rejected.', 'unauthorized')
          return
        }
        if (event.code === 4403) {
          this.expireCredential(subscription.credential)
          this.stopAssistSubscription(subscription, 'Assist stream access was denied.', 'unauthorized')
          return
        }
        if (event.code === 4404) {
          subscription.listener({ type: 'unavailable', message: 'The backend does not implement the assist stream route.' })
          this.stopAssistSubscription(subscription, 'Assist stream route is unavailable.', 'unavailable')
          return
        }
        subscription.state_listener?.('disconnected', event.reason || 'Assist stream disconnected; reconnecting.')
        this.scheduleAssistReconnect(subscription)
      }
    } catch (error) {
      if (error instanceof ApiRequestError && ['expired', 'unauthorized', 'forbidden'].includes(error.reason)) {
        this.expireCredential(subscription.credential)
        this.stopAssistSubscription(subscription, error.message, 'unauthorized')
        return
      }
      if (error instanceof ApiRequestError && error.reason === 'not_found') {
        subscription.listener({ type: 'error', message: error.message })
        this.stopAssistSubscription(subscription, error.message, 'error')
        return
      }
      subscription.state_listener?.('disconnected', asMessage(error))
      this.scheduleAssistReconnect(subscription)
    }
  }

  private acceptAssistMessage(subscription: AssistSubscription, message: ApiAssistMessageWire): void {
    if (message.source_session_id !== subscription.source_session_id) throw unsupported('Assist message belongs to a different source session.')
    if (subscription.awaiting_snapshot && message.type !== 'snapshot') {
      subscription.socket?.close(1012, 'Waiting for full assist snapshot')
      return
    }
    if (subscription.last_sequence === null && message.type !== 'snapshot') throw unsupported('Assist stream must start with a full snapshot.')
    if (!subscription.awaiting_snapshot && subscription.last_sequence !== null && message.sequence <= subscription.last_sequence) return
    if (!subscription.awaiting_snapshot && subscription.last_sequence !== null && message.sequence > subscription.last_sequence + 1 && message.type !== 'snapshot') {
      subscription.awaiting_snapshot = true
      subscription.state_listener?.('disconnected', 'Assist sequence gap; reconnecting for a full scoped snapshot.')
      subscription.socket?.close(1012, 'Assist sequence gap')
      return
    }
    if (subscription.awaiting_snapshot && message.type !== 'snapshot') return
    subscription.last_sequence = message.sequence
    subscription.awaiting_snapshot = false
    subscription.attempts = 0
    subscription.state_listener?.('connected')
    this.deliverAssistMessage(subscription, message)
  }

  private deliverAssistMessage(subscription: AssistSubscription, message: ApiAssistMessageWire): void {
    switch (message.type) {
      case 'snapshot': {
        const transcripts = toTranscriptReadModel({ items: message.payload.transcripts, next_cursor: null })
        const candidates = candidateModelFromOptions(message.payload.options)
        subscription.listener({
          type: 'snapshot',
          transcripts,
          candidates,
          highlights: message.payload.highlights.map(toHighlightReadModel),
          review_annotations: message.payload.review_annotations,
          jobs: message.payload.jobs.map(toJobReadModel),
        })
        return
      }
      case 'segment':
        subscription.listener({ type: 'transcript', data: toTranscriptReadModel({ items: [message.payload.segment], next_cursor: null }) })
        return
      case 'option':
        subscription.listener({ type: 'candidate', data: candidateModelFromOptions([message.payload.option]) })
        return
      case 'highlight':
        subscription.listener({ type: 'highlight', data: toHighlightReadModel(message.payload.highlight) })
        return
      case 'review_annotation':
        subscription.listener({ type: 'review_annotation', data: message.payload.annotation })
        return
      case 'job_progress':
        subscription.listener({ type: 'job', data: toJobReadModel(message.payload.job) })
        return
      case 'error':
        subscription.listener({ type: 'error', message: `${message.payload.code}: ${message.payload.message}` })
        subscription.state_listener?.('error', message.payload.message)
        return
      default:
        assertNever(message)
    }
  }

  private scheduleAssistReconnect(subscription: AssistSubscription): void {
    if (!subscription.active || subscription.reconnect_timer !== null) return
    subscription.attempts += 1
    const delay = Math.min(this.reconnectMinMs * (2 ** Math.min(subscription.attempts - 1, 8)), this.reconnectMaxMs)
    subscription.reconnect_timer = setTimeout(() => {
      subscription.reconnect_timer = null
      void this.connectAssist(subscription)
    }, delay)
  }

  private openWebSocket(path: string): ApiWebSocket {
    const url = makeWebSocketUrl(path, this.websocketOrigin)
    return this.transport.openWebSocket(url)
  }

  private armExpiry(subscription: SubscriptionBase): void {
    const credential = this.credentials[subscription.credential]
    if (credential?.expires_at_ms === undefined) return
    const delay = Math.max(0, credential.expires_at_ms - Date.now())
    subscription.expiry_timer = setTimeout(() => {
      if (!subscription.active) return
      this.expireCredential(subscription.credential)
    }, delay)
  }

  private assertNotExpired(name: CredentialName): void {
    this.requireCredential(name)
  }

  private expireCredential(name: CredentialName): void {
    const current = this.credentials[name]
    if (!current) return
    this.credentials = { ...this.credentials, [name]: undefined }
    for (const subscription of [...this.sourceSubscriptions]) {
      if (subscription.credential === name) this.stopSourceSubscription(subscription, `${credentialLabel(name)} credential expired.`, 'unauthorized')
    }
    for (const subscription of [...this.assistSubscriptions]) {
      if (subscription.credential === name) this.stopAssistSubscription(subscription, `${credentialLabel(name)} credential expired.`, 'unauthorized')
    }
  }

  private stopSourceSubscription(subscription: SourceSubscription, message: string, state: SubscriptionState, clearProjection = state === 'unauthorized'): void {
    if (!subscription.active) return
    subscription.active = false
    subscription.controller.abort()
    subscription.resync_generation += 1
    if (subscription.reconnect_timer !== null) clearTimeout(subscription.reconnect_timer)
    if (subscription.expiry_timer !== null) clearTimeout(subscription.expiry_timer)
    subscription.reconnect_timer = null
    subscription.expiry_timer = null
    subscription.socket?.close(1000, 'Subscription closed')
    subscription.socket = null
    this.sourceSubscriptions.delete(subscription)
    if (this.sourceByListener.get(subscription.listener) === subscription) this.sourceByListener.delete(subscription.listener)
    subscription.last_frame = undefined
    if (clearProjection) subscription.listener(null)
    subscription.state_listener?.(state, message)
  }

  private stopAssistSubscription(subscription: AssistSubscription, message: string, state: SubscriptionState, clearProjection = state === 'unauthorized'): void {
    if (!subscription.active) return
    subscription.active = false
    if (subscription.reconnect_timer !== null) clearTimeout(subscription.reconnect_timer)
    if (subscription.expiry_timer !== null) clearTimeout(subscription.expiry_timer)
    subscription.reconnect_timer = null
    subscription.expiry_timer = null
    subscription.socket?.close(1000, 'Subscription closed')
    subscription.socket = null
    this.assistSubscriptions.delete(subscription)
    if (this.assistByListener.get(subscription.listener) === subscription) this.assistByListener.delete(subscription.listener)
    if (clearProjection) subscription.listener({ type: 'state', state, message })
    subscription.state_listener?.(state, message)
  }

  private stopAllSubscriptions(message: string, state: SubscriptionState): void {
    for (const subscription of [...this.sourceSubscriptions]) this.stopSourceSubscription(subscription, message, state, true)
    for (const subscription of [...this.assistSubscriptions]) this.stopAssistSubscription(subscription, message, state, true)
  }

  private releaseAudioUrlsForSource(sourceSessionId: string): void {
    for (const url of this.audioUrlsBySource.get(sourceSessionId) ?? []) URL.revokeObjectURL(url)
    this.audioUrlsBySource.delete(sourceSessionId)
  }

  private releaseAllAudioUrls(): void {
    for (const sourceSessionId of this.audioUrlsBySource.keys()) this.releaseAudioUrlsForSource(sourceSessionId)
  }
}

function decodeOpenedReview(value: unknown): { id: string; source_id: string; token: string; source_read_token?: string } {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw unsupported('The review response is not an object.')
  const item = value as Record<string, unknown>
  if (Object.keys(item).some((key) => !['id', 'source_id', 'token', 'source_read_token'].includes(key))) {
    throw unsupported('The review response contains unsupported credential fields.')
  }
  if (typeof item.id !== 'string' || !item.id || typeof item.source_id !== 'string' || !item.source_id || typeof item.token !== 'string' || !item.token) {
    throw unsupported('The review response omitted its identity or control credential.')
  }
  if (item.source_read_token !== undefined && (typeof item.source_read_token !== 'string' || !item.source_read_token)) {
    throw unsupported('The review response contains an invalid source-read credential.')
  }
  return {
    id: item.id,
    source_id: item.source_id,
    token: item.token,
    ...(item.source_read_token === undefined ? {} : { source_read_token: item.source_read_token as string }),
  }
}

function frameFromSnapshot(snapshot: ApiSnapshotWire, sourceSessionId: string, requestedMs: number): ReplayFrameReadModel {
  const quality = snapshot.runway.data_quality.toLowerCase()
  return {
    source_session_id: sourceSessionId,
    requested_ms: requestedMs,
    frame_ms: snapshot.sim_ms,
    track_count: snapshot.tracks.length,
    alert_count: snapshot.alerts.length,
    quality: ['nominal', 'good', 'ok'].includes(quality) ? 'known' : quality === 'unknown' ? 'unknown' : 'degraded',
    state: 'ready',
    snapshot: toReplaySnapshotReadModel(snapshot),
  }
}

function candidateModelFromOptions(options: ApiOptionWire[]): CandidateReadModel {
  return {
    state: options.length ? 'ready' : 'empty',
    evaluator_access: 'granted',
    items: options.map((option) => ({
      id: option.id,
      replay_analysis_id: option.replay_analysis_id,
      revision: option.revision ?? null,
      statement: option.option_statement,
      rationale: option.rationale,
      supporting_evidence: option.supporting_evidence_ids,
      preconditions: option.preconditions,
      unknowns: option.unknowns,
      source_version: option.source_version,
      model_version: option.model_version,
      rule_version: option.rule_version,
      review_status: option.review_status,
    })),
  }
}

function toHighlightReadModel(value: ApiHighlightWire): AssistHighlightReadModel {
  return {
    id: value.id,
    revision: value.revision ?? null,
    category: value.category,
    review_priority: value.review_priority,
    statement: value.statement,
    transcript_segment_ids: value.transcript_segment_ids,
    session_event_ids: value.session_event_ids,
    uncertainty: value.uncertainty,
    provider_version: value.provider_version,
    rule_version: value.rule_version,
    status: value.status,
    ...(value.linked_alert_id === undefined ? {} : { linked_alert_id: value.linked_alert_id }),
    ...(value.link_status === undefined ? {} : { link_status: value.link_status }),
  }
}

function parseSocketJson(value: unknown): unknown {
  if (typeof value !== 'string') throw unsupported('WebSocket message is not JSON text.')
  try {
    const parsed: unknown = JSON.parse(value)
    return parsed
  } catch {
    throw new ApiRequestError('error', 'WebSocket message contains malformed JSON.', null, 'malformed_json')
  }
}

function makeRequestId(prefix: string): string {
  requestCounter += 1
  const randomId = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : null
  return randomId ?? `${prefix}-${Date.now()}-${requestCounter}`
}

function validateRequestId(value: string): string {
  if (typeof value !== 'string' || value.length < 1 || value.length > 100) throw invalidInput('Request ID must contain 1 to 100 characters.')
  return value
}

function isMissingProfileRoute(error: unknown): boolean {
  return error instanceof ApiRequestError
    && error.status === 404
    && error.reason === 'not_found'
    && error.message.trim().toLowerCase() === 'not found'
}

function unavailableReceipt(message: string): ReviewReceipt {
  return { request_id: makeRequestId('unavailable'), revision: 0, status: 'unavailable', message }
}

function unavailable(message: string): ApiRequestError {
  return new ApiRequestError('error', message, null, 'unsupported_profile')
}

function unsupported(message: string): ApiRequestError {
  return new ApiRequestError('error', message, null, 'unsupported_profile')
}

function invalidInput(message: string): ApiRequestError {
  return new ApiRequestError('error', message, null, 'validation')
}

function asMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'An unexpected API adapter error occurred.'
}

function credentialLabel(name: CredentialName): string {
  if (name === 'source_read') return 'source-read'
  if (name === 'review_control') return 'review-control'
  if (name === 'source_review') return 'source-review'
  return 'reviewer'
}

function credentialChanged(previous?: ScopedApiCredential, next?: ScopedApiCredential): boolean {
  return previous?.token !== next?.token || previous?.expires_at_ms !== next?.expires_at_ms
}

function assertNever(value: never): never {
  throw unsupported(`Unsupported assist update: ${String(value)}.`)
}

const undefinedDecoder = (value: unknown): unknown => value
