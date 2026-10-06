import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { ApiReplayReviewAdapter } from './adapters/apiReplayReview'
import { FixtureReplayReviewAdapter, FIXTURE_FRAME_MS } from './adapters/fixtureReplayReview'
import { AlertEvidence } from './features/runway/AlertEvidence'
import { CandidatePanel } from './features/assist/CandidatePanel'
import { DebriefPanel } from './features/assist/DebriefPanel'
import { TranscriptPanel } from './features/assist/TranscriptPanel'
import { AudioPlayer } from './features/replay/AudioPlayer'
import { RunwayBoard } from './features/runway/RunwayBoard'
import { RunwayMap } from './features/runway/RunwayMap'
import { ReplayControls } from './features/replay/ReplayControls'
import { ReplayTimeline } from './features/replay/ReplayTimeline'
import { createControlRequestId, loadCompleteEventHistory, loadCompleteTranscript } from './features/replay/ReplayController'
import { SourceSetup } from './features/replay/SourceSetup'
import type {
  AsyncState,
  AssistReviewReadModel,
  AssistUpdateReadModel,
  EventReadModel,
  EvidenceRef,
  EvidenceResolution,
  OperatorAccess,
  OverviewReadModel,
  ReplayFrameReadModel,
  ReplayReviewAdapter,
  ReplaySourceReadModel,
  ReviewControl,
  ReviewOpenResult,
  ReviewReceipt,
  SessionReadModel,
  SessionViewReadModel,
  TranscriptReadModel,
} from './contracts/replayReview'
import { ApiRequestError } from './api'

const configuredMode = import.meta.env.VITE_FLOWLENS_MODE
const mode: 'fixture' | 'api' = configuredMode === 'api' ? 'api' : 'fixture'
const invalidMode = configuredMode !== undefined && configuredMode !== '' && configuredMode !== 'fixture' && configuredMode !== 'api'
const configuredFixtureView = import.meta.env.VITE_FLOWLENS_FIXTURE_VIEW
const fixtureView: 'evaluator' | 'training' = configuredFixtureView === 'training' ? 'training' : 'evaluator'
const invalidFixtureView = configuredFixtureView !== undefined && configuredFixtureView !== '' && configuredFixtureView !== 'training' && configuredFixtureView !== 'evaluator'

function createAdapter(value: 'fixture' | 'api'): ReplayReviewAdapter {
  return value === 'api' ? new ApiReplayReviewAdapter() : new FixtureReplayReviewAdapter({ view: fixtureView })
}

function errorState(error: unknown): AsyncState<never> {
  if (error instanceof ApiRequestError) {
    if (error.reason === 'unsupported_profile' && /layout|coordinate system|geometry/i.test(error.message)) {
      return { state: 'unsupported-layout', message: error.message }
    }
    return { state: error.kind, message: error.message }
  }
  if (error instanceof DOMException && error.name === 'AbortError') return { state: 'loading' }
  return { state: 'error', message: error instanceof Error ? error.message : 'An unexpected error occurred.' }
}

function formatTime(milliseconds: number): string {
  const totalSeconds = Math.floor(milliseconds / 1000)
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0')
  const seconds = (totalSeconds % 60).toString().padStart(2, '0')
  return `${minutes}:${seconds}`
}

function formatWallTime(milliseconds: number | null): string {
  if (milliseconds === null) return 'fixture clock'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(milliseconds)
}

function evidenceKey(ref: EvidenceRef): string {
  return `${ref.kind}:${ref.id}`
}

function StateMessage({ state, emptyLabel }: { state: AsyncState<unknown>; emptyLabel?: string }) {
  if (state.state === 'loading') return <div className="state-message"><span className="spinner" /> Loading from {mode === 'api' ? 'the local API' : 'the inline fixture'}…</div>
  if (state.state === 'empty') return <div className="state-message">{emptyLabel ?? 'No records are available.'}</div>
  if (state.state === 'ready' || state.state === 'degraded') return null
  return <div className={`state-message state-${state.state}`} role="alert">{state.message}</div>
}

function App() {
  const adapter = useMemo(() => createAdapter(mode), [])
  const [overviewState, setOverviewState] = useState<AsyncState<OverviewReadModel>>({ state: 'loading' })
  const [sessionsState, setSessionsState] = useState<AsyncState<SessionReadModel[]>>({ state: mode === 'api' ? 'empty' : 'loading' })
  const [sessionState, setSessionState] = useState<AsyncState<SessionViewReadModel>>({ state: 'empty' })
  const [access, setAccess] = useState<OperatorAccess | null>(null)
  const [operatorKey, setOperatorKey] = useState('')
  const [selectedScenario, setSelectedScenario] = useState('')
  const [selectedSessionId, setSelectedSessionId] = useState('')
  const [busyAction, setBusyAction] = useState<'login' | 'create' | 'refresh' | null>(null)
  const [sourceState, setSourceState] = useState<AsyncState<ReplaySourceReadModel>>({ state: 'empty' })
  const [frameState, setFrameState] = useState<AsyncState<ReplayFrameReadModel>>({ state: 'empty' })
  const [eventHistoryState, setEventHistoryState] = useState<AsyncState<EventReadModel[]>>({ state: 'empty' })
  const [transcriptState, setTranscriptState] = useState<AsyncState<TranscriptReadModel>>({ state: 'empty' })
  const [assistState, setAssistState] = useState<AsyncState<AssistReviewReadModel>>({ state: 'loading' })
  const [selectedEvidenceRef, setSelectedEvidenceRef] = useState<EvidenceRef | null>(null)
  const [evidenceResolutions, setEvidenceResolutions] = useState<Map<string, EvidenceResolution>>(() => new Map())
  const [evidenceContextMessage, setEvidenceContextMessage] = useState('')
  const [audioEvidenceFocus, setAudioEvidenceFocus] = useState<{ asset_id: string; at_ms: number } | null>(null)
  const [requestedTimeMs, setRequestedTimeMs] = useState(mode === 'fixture' ? FIXTURE_FRAME_MS : 0)
  const [reviewOpen, setReviewOpen] = useState(mode === 'fixture')
  const [openReviewState, setOpenReviewState] = useState<AsyncState<ReviewOpenResult>>({ state: 'empty' })
  const [controlState, setControlState] = useState<AsyncState<ReviewReceipt>>({ state: 'empty' })
  const activeSession = sessionState.state === 'ready' ? sessionState.data : null
  const activeFrame = frameState.state === 'ready' || frameState.state === 'degraded' || frameState.state === 'disconnected'
    ? frameState.data ?? null
    : null

  const refreshAssist = useCallback(async () => {
    if (!selectedSessionId) return
    const model = await adapter.loadAssistReview(selectedSessionId)
    if (model.state === 'unavailable') setAssistState({ state: 'unavailable', data: model, message: model.message ?? 'Assist data is unavailable.' })
    else setAssistState({ state: 'ready', data: model })
    const transcript = await loadCompleteTranscript(adapter, selectedSessionId)
    if (transcript.state === 'unavailable') setTranscriptState({ state: 'unavailable', data: transcript, message: transcript.message ?? 'Transcript route is unavailable.' })
    else if (transcript.state === 'empty') setTranscriptState({ state: 'empty', data: transcript })
    else setTranscriptState({ state: 'ready', data: transcript })
  }, [adapter, selectedSessionId])

  const updateReplayFrame = useCallback((frame: ReplayFrameReadModel) => {
    // Keep the adapter's requested time distinct from the returned snapshot playhead.
    setRequestedTimeMs(frame.requested_ms)
    if (frame.state === 'disconnected') {
      setFrameState({ state: 'disconnected', data: frame, message: frame.connection_message ?? 'Source stream disconnected; retained frame shown.' })
    } else if (frame.state === 'unavailable') {
      setFrameState({ state: 'unavailable', data: frame, message: frame.connection_message ?? 'Source frame is unavailable.' })
    } else if (frame.quality !== 'known' || frame.state === 'degraded') {
      setFrameState({ state: 'degraded', data: frame, message: frame.connection_message ?? `Frame quality is ${frame.quality}.` })
    } else {
      setFrameState({ state: 'ready', data: frame })
    }
  }, [])

  const loadOverview = useCallback(async (signal?: AbortSignal) => {
    if (invalidMode) return
    setOverviewState({ state: 'loading' })
    try {
      const overview = await adapter.loadOverview(signal)
      setOverviewState(overview.scenarios.length ? { state: 'ready', data: overview } : { state: 'empty' })
      setSelectedScenario((current) => current || overview.scenarios[0]?.id || '')
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      setOverviewState(errorState(error))
    }
  }, [adapter])

  const loadSessions = useCallback(async (token = '', signal?: AbortSignal) => {
    setSessionsState({ state: 'loading' })
    try {
      const sessions = await adapter.listSessions(token, signal)
      if (sessions.length === 0) {
        setSessionsState({ state: 'empty' })
        setSelectedSessionId('')
        setSessionState({ state: 'empty' })
        return
      }
      setSessionsState({ state: 'ready', data: sessions })
      setSelectedSessionId((current) => sessions.some((item) => item.id === current) ? current : sessions[0].id)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      if (error instanceof ApiRequestError && error.kind === 'unauthorized') setAccess(null)
      setSessionsState(errorState(error))
    }
  }, [adapter])

  const loadSession = useCallback(async (sessionId: string, token = access?.token ?? '') => {
    if (!sessionId) return
    setSelectedSessionId(sessionId)
    setSessionState({ state: 'loading' })
    try {
      const view = await adapter.loadSession(token, sessionId)
      setSessionState({ state: 'ready', data: view })
    } catch (error) {
      if (error instanceof ApiRequestError && error.kind === 'unauthorized') setAccess(null)
      setSessionState(errorState(error))
    }
  }, [adapter, access?.token])

  useEffect(() => {
    if (invalidMode) return
    const controller = new AbortController()
    void loadOverview(controller.signal)
    if (mode === 'fixture') void loadSessions('', controller.signal)
    return () => controller.abort()
  }, [loadOverview, loadSessions])

  useEffect(() => {
    if (invalidMode || !selectedSessionId || (mode === 'api' && !access)) return
    void loadSession(selectedSessionId, access?.token ?? '')
  }, [selectedSessionId, access, loadSession])

  useEffect(() => {
    if (invalidMode || !selectedSessionId || (mode === 'api' && !access)) {
      setSourceState({ state: 'empty' })
      setFrameState({ state: 'empty' })
      return
    }

    const controller = new AbortController()
    let unsubscribe: () => void = () => {}
    setSourceState({ state: 'loading' })
    if (mode === 'fixture' || reviewOpen) setFrameState({ state: 'loading' })
    else setFrameState({ state: 'unavailable', message: 'Open a frozen server review to load a replay frame. The current session snapshot is not a historical frame.' })

    void (async () => {
      try {
        const source = await adapter.loadSource(selectedSessionId, controller.signal)
        if (controller.signal.aborted) return
        setSourceState(source.quality === 'known'
          ? { state: 'ready', data: source }
          : { state: 'degraded', data: source, message: `Source quality is ${source.quality}.` })
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setSourceState(errorState(error))
      }

      if (controller.signal.aborted || (mode === 'api' && !reviewOpen)) return
      const initialTime = mode === 'fixture' ? FIXTURE_FRAME_MS : 0
      try {
        const frame = await adapter.loadFrame(selectedSessionId, initialTime, controller.signal)
        if (controller.signal.aborted) return
        updateReplayFrame(frame)
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setFrameState(errorState(error))
        return
      }

      try {
        unsubscribe = adapter.subscribeSource(
          selectedSessionId,
          (nextFrame) => { if (nextFrame) updateReplayFrame(nextFrame) },
          (state, message) => {
            if (state === 'connected' || state === 'loading') return
            if (state === 'disconnected') {
              setFrameState((current) => 'data' in current && current.data
                ? { state: 'disconnected', data: current.data, message: message ?? 'Source stream disconnected; retained frame shown.' }
                : { state: 'disconnected', message: message ?? 'Source stream disconnected before a frame was received.' })
            } else if (state === 'unauthorized') {
              setFrameState({ state: 'unauthorized', message: message ?? 'Replay access expired; restricted frame projection cleared.' })
            } else if (state === 'error' || state === 'unavailable') {
              setFrameState((current) => 'data' in current && current.data
                ? { state: 'disconnected', data: current.data, message: message ?? 'Source stream is unavailable; the last frame is retained.' }
                : { state: 'error', message: message ?? 'Source stream is unavailable.' })
            }
          },
        )
      } catch (error) {
        if (!(error instanceof DOMException && error.name === 'AbortError')) setFrameState(errorState(error))
      }
    })()

    return () => {
      controller.abort()
      unsubscribe()
    }
  }, [adapter, access, reviewOpen, selectedSessionId, updateReplayFrame])

  useEffect(() => {
    if (!selectedSessionId || (mode === 'api' && !access)) {
      setEventHistoryState({ state: 'empty' })
      setTranscriptState({ state: 'empty' })
      return
    }
    const controller = new AbortController()
    setEventHistoryState({ state: 'loading' })
    setTranscriptState({ state: 'loading' })
    void loadCompleteEventHistory(adapter, selectedSessionId, controller.signal).then((items) => {
      if (!controller.signal.aborted) setEventHistoryState(items.length ? { state: 'ready', data: items } : { state: 'empty' })
    }).catch((error: unknown) => {
      if (!controller.signal.aborted && !(error instanceof DOMException && error.name === 'AbortError')) setEventHistoryState(errorState(error))
    })
    void loadCompleteTranscript(adapter, selectedSessionId, controller.signal).then((transcript) => {
      if (controller.signal.aborted) return
      if (transcript.state === 'unavailable') {
        setTranscriptState({ state: 'unavailable', data: transcript, message: transcript.message ?? 'Transcript route is unavailable.' })
      } else if (transcript.state === 'empty') {
        setTranscriptState({ state: 'empty', data: transcript })
      } else {
        setTranscriptState({ state: 'ready', data: transcript })
      }
    }).catch((error: unknown) => {
      if (!controller.signal.aborted && !(error instanceof DOMException && error.name === 'AbortError')) setTranscriptState(errorState(error))
    })
    return () => controller.abort()
  }, [access, adapter, reviewOpen, selectedSessionId])

  useEffect(() => {
    if (!selectedSessionId || (mode === 'api' && !access)) {
      setAssistState({ state: 'empty' })
      return
    }
    if (mode === 'api' && !reviewOpen) {
      setAssistState({ state: 'unavailable', message: 'Open a frozen review first. The current backend still has no scoped assist routes or source_read credential.' })
      return
    }

    const controller = new AbortController()
    let unsubscribe: () => void = () => {}
    setAssistState({ state: 'loading' })
    void adapter.loadAssistReview(selectedSessionId, undefined, controller.signal).then((model) => {
      if (controller.signal.aborted) return
      if (model.state === 'unavailable') setAssistState({ state: 'unavailable', data: model, message: model.message ?? 'Assist routes are unavailable.' })
      else setAssistState({ state: 'ready', data: model })
    }).catch((error: unknown) => {
      if (!controller.signal.aborted && !(error instanceof DOMException && error.name === 'AbortError')) setAssistState(errorState(error))
    })

    const applyUpdate = (update: AssistUpdateReadModel) => {
      if (update.type === 'snapshot') {
        const model: AssistReviewReadModel = {
          state: update.highlights.length || update.candidates.items.length ? 'ready' : 'empty',
          provider_availability: 'unknown',
          evaluator_access: update.candidates.evaluator_access,
          highlights: update.highlights,
          candidates: update.candidates,
          review_annotations: update.review_annotations,
          jobs: update.jobs,
          analysis: update.candidates.analysis ?? null,
        }
        setAssistState({ state: 'ready', data: model })
        if (update.transcripts.state === 'ready') setTranscriptState({ state: 'ready', data: update.transcripts })
        return
      }
      if (update.type === 'transcript') {
        setTranscriptState(update.data.state === 'unavailable' ? { state: 'unavailable', data: update.data, message: update.data.message ?? 'Transcript unavailable.' } : update.data.state === 'empty' ? { state: 'empty', data: update.data } : { state: 'ready', data: update.data })
        return
      }
      if (update.type === 'unavailable') {
        setAssistState({ state: 'unavailable', message: update.message })
        return
      }
      if (update.type === 'error') {
        setAssistState({ state: 'error', message: update.message })
        return
      }
      if (update.type === 'state') {
        if (update.state === 'unauthorized') setAssistState({ state: 'unauthorized', message: update.message ?? 'Assist access is unauthorized.' })
        else if (update.state === 'error') setAssistState({ state: 'error', message: update.message ?? 'Assist stream failed.' })
        else if (update.state === 'disconnected') setAssistState((current) => current.state === 'ready' || current.state === 'degraded' ? { state: 'degraded', data: current.data, message: update.message ?? 'Assist stream disconnected; last projection retained.' } : { state: 'disconnected', message: update.message ?? 'Assist stream disconnected.' })
        else if (update.state === 'unavailable') setAssistState({ state: 'unavailable', message: update.message ?? 'Assist routes are unavailable.' })
        return
      }
      setAssistState((current) => {
        const model = current.state === 'ready' || current.state === 'degraded' || current.state === 'unavailable' ? current.data : null
        if (!model) return current
        if (update.type === 'highlight') return { state: 'ready', data: { ...model, highlights: [...model.highlights.filter((item) => item.id !== update.data.id), update.data] } }
        if (update.type === 'candidate') return { state: 'ready', data: { ...model, candidates: update.data } }
        if (update.type === 'review_annotation') return { state: 'ready', data: { ...model, review_annotations: [...model.review_annotations, update.data] } }
        if (update.type === 'job') return { state: 'ready', data: { ...model, jobs: [...model.jobs.filter((item) => item.id !== update.data.id), update.data] } }
        return current
      })
    }

    try {
      unsubscribe = adapter.subscribeAssist(selectedSessionId, applyUpdate, (state, message) => {
        if (state === 'connected' || state === 'loading') return
        if (state === 'unavailable') setAssistState({ state: 'unavailable', message: message ?? 'Assist stream is unavailable.' })
        else if (state === 'unauthorized') setAssistState({ state: 'unauthorized', message: message ?? 'Assist access is unauthorized.' })
        else if (state === 'error') setAssistState({ state: 'error', message: message ?? 'Assist stream failed.' })
        else if (state === 'disconnected') setAssistState((current) => current.state === 'ready' || current.state === 'degraded' ? { state: 'degraded', data: current.data, message: message ?? 'Assist stream disconnected.' } : { state: 'disconnected', message: message ?? 'Assist stream disconnected.' })
      })
    } catch (error) {
      setAssistState(errorState(error))
    }
    return () => { controller.abort(); unsubscribe() }
  }, [access, adapter, reviewOpen, selectedSessionId])

  useEffect(() => {
    if (!selectedEvidenceRef) return
    const ref = selectedEvidenceRef
    const targetId = ref.kind === 'transcript_segment'
      ? `transcript-${ref.id}`
      : ref.kind === 'detector_alert' ? `alert-${ref.id}` : `timeline-ref-session_event-${ref.id}`
    document.getElementById(targetId)?.scrollIntoView({ block: 'center' })
  }, [selectedEvidenceRef])

  useEffect(() => () => {
    if (adapter instanceof ApiReplayReviewAdapter) adapter.dispose()
  }, [adapter])

  const onOpenReview = async () => {
    if (mode !== 'api' || !access || !selectedSessionId) return
    setOpenReviewState({ state: 'loading' })
    try {
      const result = await adapter.openReview(selectedSessionId, access.token)
      if (result.status !== 'accepted' || !result.review_session_id) {
        setOpenReviewState({ state: 'unavailable', data: result, message: result.message ?? 'The backend did not open a review session.' })
        return
      }
      setOpenReviewState({ state: 'ready', data: result })
      setControlState({ state: 'empty' })
      setRequestedTimeMs(0)
      setReviewOpen(true)
    } catch (error) {
      const failure = errorState(error)
      setOpenReviewState(failure)
      if (failure.state === 'unauthorized') setAccess(null)
    }
  }

  const onReviewControl = async (control: ReviewControl) => {
    if (!selectedSessionId || !activeFrame?.snapshot) return false
    setControlState({ state: 'loading' })
    let receipt: ReviewReceipt
    try {
      receipt = await adapter.controlReview(selectedSessionId, control)
    } catch (error) {
      const failure = errorState(error)
      setControlState(failure)
      if (failure.state === 'conflict') {
        try {
          const current = await adapter.loadFrame(selectedSessionId, activeFrame.snapshot.playback_ms ?? requestedTimeMs)
          updateReplayFrame(current)
        } catch {
          // Keep the last committed frame and the conflict message visible for explicit reconciliation.
        }
      }
      return false
    }

    if (receipt.status === 'conflict') {
      setControlState({ state: 'conflict', message: receipt.message ?? 'Review revision changed. Refresh the frame before retrying.' })
      return false
    }
    if (receipt.status === 'unavailable') {
      setControlState({ state: 'unavailable', data: receipt, message: receipt.message ?? 'Review control is unavailable.' })
      return false
    }

    setControlState({ state: 'ready', data: receipt })
    const requested = control.type === 'SEEK' ? control.at_ms : activeFrame.snapshot.playback_ms ?? requestedTimeMs
    if (control.type === 'SEEK') setRequestedTimeMs(control.at_ms)
    try {
      updateReplayFrame(await adapter.loadFrame(selectedSessionId, requested))
      return true
    } catch (error) {
      setFrameState(errorState(error))
      return false
    }
  }

  const onEvidenceSelect = async (ref: EvidenceRef, relation?: 'linked' | 'possible_link') => {
    setSelectedEvidenceRef(ref)
    setAudioEvidenceFocus(null)
    setEvidenceContextMessage('Resolving typed evidence reference through the replay adapter…')
    if (!selectedSessionId) {
      setEvidenceContextMessage('No source session is selected; reference was not looked up.')
      return
    }
    try {
      const analysisId = assistState.state === 'ready' || assistState.state === 'degraded' || assistState.state === 'unavailable'
        ? assistState.data?.analysis?.id
        : undefined
      const values = await adapter.resolveEvidence(selectedSessionId, [ref], requestedTimeMs, undefined, analysisId)
      const resolution = values.find((item) => item.ref.kind === ref.kind && item.ref.id === ref.id)
      if (!resolution) {
        setEvidenceContextMessage('UNRESOLVED · adapter returned no matching typed reference.')
        return
      }
      const decorated = { ...resolution, ...(relation ? { link_status: relation } : {}) }
      setEvidenceResolutions((current) => new Map(current).set(evidenceKey(ref), decorated))
      if (resolution.state === 'unavailable') {
        setEvidenceContextMessage('UNAVAILABLE · the backend has no authorized lookup for this reference type or scope.')
        return
      }
      if (resolution.state === 'unresolved') {
        setEvidenceContextMessage('UNRESOLVED · this exact reference is missing, outside the selected time, or outside the available scope.')
        return
      }
      const context = resolution.context
      if (context?.timebase === 'session') {
        if (context.at_ms > requestedTimeMs) {
          setEvidenceContextMessage(`Resolved reference at ${context.at_ms} ms SIM is later than the selected replay time; it was not exposed or sought.`)
          return
        }
        try {
          const frame = await adapter.loadFrame(selectedSessionId, context.at_ms)
          updateReplayFrame(frame)
          setEvidenceContextMessage(`Opened exact source reference at ${context.at_ms} ms SIM through the read-only frame port. No replay command was sent.`)
        } catch (error) {
          const failure = errorState(error)
          setEvidenceContextMessage(`Reference resolved at ${context.at_ms} ms SIM, but frame context is ${failure.state}: ${'message' in failure ? failure.message : 'unavailable'}. No replay command was sent.`)
        }
        return
      }
      if (context?.timebase === 'audio-relative') {
        setAudioEvidenceFocus({ asset_id: context.asset_id, at_ms: context.at_ms })
        setEvidenceContextMessage(`Selected exact audio-relative reference at ${context.at_ms} ms in asset ${context.asset_id}. Session alignment remains unknown; replay time was not moved.`)
        return
      }
      setEvidenceContextMessage(context?.timebase === 'unknown'
        ? `Resolved reference; ${context.reason} Timeline and audio remain unsynchronized.`
        : 'Resolved reference has no safe temporal context; timeline and audio remain unchanged.')
    } catch (error) {
      const failure = errorState(error)
      setEvidenceContextMessage(`${failure.state.toUpperCase()} · ${'message' in failure ? failure.message : 'Evidence lookup is loading.'}`)
    }
  }

  const onCorrectTranscript = async (segmentId: string, expectedRevision: number, text: string, reason: string, requestId: string): Promise<ReviewReceipt> => {
    const receipt = await adapter.correctTranscript(selectedSessionId, segmentId, expectedRevision, text, reason, requestId)
    if (receipt.status === 'accepted') {
      await refreshAssist().catch(() => undefined)
      appendReceiptAnnotation(receipt.annotation)
    }
    return receipt
  }

  const onReviewHighlight = async (highlightId: string, expectedRevision: number, decision: 'confirmed' | 'dismissed' | 'unresolved', reason: string, requestId: string): Promise<ReviewReceipt> => {
    const receipt = await adapter.reviewHighlight(selectedSessionId, highlightId, expectedRevision, decision, reason, requestId)
    if (receipt.status === 'accepted') {
      await refreshAssist().catch(() => undefined)
      appendReceiptAnnotation(receipt.annotation)
    }
    return receipt
  }

  const onReviewCandidate = async (candidateId: string, analysisId: string, expectedRevision: number, decision: 'confirmed' | 'dismissed' | 'unresolved', reason: string, requestId: string): Promise<ReviewReceipt> => {
    const receipt = await adapter.reviewCandidate(selectedSessionId, candidateId, expectedRevision, decision, reason, analysisId, requestId)
    if (receipt.status === 'accepted') {
      await refreshAssist().catch(() => undefined)
      appendReceiptAnnotation(receipt.annotation)
    }
    return receipt
  }

  const appendReceiptAnnotation = (annotation: ReviewReceipt['annotation']) => {
    if (!annotation) return
    setAssistState((current) => {
      if (current.state !== 'ready' && current.state !== 'degraded' && current.state !== 'unavailable') return current
      if (!current.data) return current
      if (current.data.review_annotations.some((item) => item.id && item.id === annotation.id)) return current
      return { ...current, data: { ...current.data, review_annotations: [...current.data.review_annotations, annotation] } }
    })
  }

  const onReplayRefresh = async () => {
    if (!selectedSessionId || !activeFrame?.snapshot) return
    const lastFrame = activeFrame
    try {
      updateReplayFrame(await adapter.loadFrame(selectedSessionId, activeFrame.snapshot.playback_ms ?? requestedTimeMs))
      setControlState({ state: 'empty' })
    } catch (error) {
      const failure = errorState(error)
      setFrameState(failure.state === 'disconnected'
        ? { state: 'disconnected', data: lastFrame, message: failure.message }
        : failure)
    }
  }

  const onLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const key = operatorKey.trim()
    if (key.length < 16) {
      setSessionsState({ state: 'error', message: 'The local operator key must contain at least 16 characters.' })
      return
    }
    setBusyAction('login')
    setOperatorKey('')
    try {
      const newAccess = await adapter.authenticateOperator(key)
      setAccess(newAccess)
      await loadSessions(newAccess.token)
    } catch (error) {
      setSessionsState(errorState(error))
    } finally {
      setBusyAction(null)
    }
  }

  const onCreateSession = async () => {
    if (!access || !selectedScenario) return
    setBusyAction('create')
    try {
      const created = await adapter.createSession(access.token, selectedScenario)
      await loadSessions(access.token)
      setSelectedSessionId(created.id)
      if (selectedSessionId === created.id) await loadSession(created.id, access.token)
    } catch (error) {
      setSessionsState(errorState(error))
    } finally {
      setBusyAction(null)
    }
  }

  const onRefresh = async () => {
    setBusyAction('refresh')
    await loadOverview()
    if (mode === 'fixture') await loadSessions('')
    else if (access) {
      await loadSessions(access.token)
      if (selectedSessionId) await loadSession(selectedSessionId, access.token)
    }
    setBusyAction(null)
  }

  const onSessionChange = (sessionId: string) => {
    if (adapter instanceof ApiReplayReviewAdapter) adapter.clearCredentials()
    setReviewOpen(mode === 'fixture')
    setOpenReviewState({ state: 'empty' })
    setControlState({ state: 'empty' })
    setAssistState({ state: 'loading' })
    setSelectedEvidenceRef(null)
    setEvidenceResolutions(new Map())
    setEvidenceContextMessage('')
    setAudioEvidenceFocus(null)
    setRequestedTimeMs(mode === 'fixture' ? FIXTURE_FRAME_MS : 0)
    setSelectedSessionId(sessionId)
  }

  if (invalidMode || invalidFixtureView) {
    return <main className="config-error"><p className="eyebrow">Configuration error</p><h1>Unsupported frontend configuration</h1><p><code>VITE_FLOWLENS_MODE</code> must be <code>fixture</code> or <code>api</code>, and <code>VITE_FLOWLENS_FIXTURE_VIEW</code> must be <code>evaluator</code> or <code>training</code>. The app did not switch modes automatically.</p></main>
  }

  const overview = overviewState.state === 'ready' || overviewState.state === 'degraded' ? overviewState.data : null
  const sessions = sessionsState.state === 'ready' ? sessionsState.data : []
  const canOpenReview = activeSession?.session.id === selectedSessionId
    && ['ENDED', 'INTERRUPTED'].includes(activeSession.session.status.toUpperCase())
  const replayActionPending = openReviewState.state === 'loading' || controlState.state === 'loading' || controlState.state === 'conflict'
  const assistProjection = assistState.state === 'ready' || assistState.state === 'degraded' || assistState.state === 'unavailable' ? assistState.data : null
  const evaluatorAccess = assistProjection?.evaluator_access ?? 'unknown'

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#main" aria-label="ATC FlowLens home">
          <span className="brand-mark" aria-hidden="true"><span /><span /><span /></span>
          <span className="brand-copy"><strong>FLOWLENS</strong><small>ATC REPLAY LAB</small></span>
        </a>
        <div className="topbar-right">
          <span className={`mode-pill mode-${mode}`}><i /> {mode === 'api' ? 'LOCAL API' : 'FIXTURE MODE'}</span>
          <span className="boundary-label">{mode === 'fixture' ? `AUTHORED SYNTHETIC · ${fixtureView.toUpperCase()} VIEW` : 'OFFLINE REPLAY · NOT OPERATIONAL'}</span>
        </div>
      </header>

      <main id="main" className="workspace">
        <section className="page-heading">
          <div>
            <p className="eyebrow">FRONTEND REPLAY REVIEW / FE-05</p>
            <h1>Replay review workspace</h1>
            <p className="lede">Source context, replay timeline, transcript provenance, evaluator evidence review and debrief for offline replay.</p>
          </div>
          <button className="button button-secondary refresh-button" onClick={() => void onRefresh()} disabled={busyAction !== null}>
            <span className={busyAction === 'refresh' ? 'refresh-glyph spinning' : 'refresh-glyph'} aria-hidden="true">↻</span>
            Refresh data
          </button>
        </section>

        <section className="overview-grid" aria-label="Data source overview">
          <article className="panel runtime-panel">
            <div className="panel-topline"><p className="eyebrow">01 / SOURCE</p><span className="small-label">Explicit mode</span></div>
            <h2>{mode === 'api' ? 'Backend connection' : 'Fixture adapter'}</h2>
            <p className="muted">{overview?.source_label ?? (mode === 'api' ? 'Fetching local backend status and scenario catalogue.' : 'Loading an authored fixture; no backend request is made.')}</p>
            <div className="source-status-row">
              <span className={`status-dot ${overview?.health.state === 'online' ? 'is-online' : mode === 'fixture' ? 'is-fixture' : 'is-waiting'}`} />
              <strong>{overview?.health.state === 'online' ? 'Connected' : mode === 'fixture' ? 'Ready' : overviewState.state === 'loading' ? 'Checking' : 'Unavailable'}</strong>
              <span className="muted">{overview?.health.state === 'online' ? `v${overview.health.version}` : mode === 'fixture' ? 'fixture-1' : 'same-origin /health'}</span>
            </div>
            <div className="source-meta">
              <div><span>Adapter</span><strong>{mode === 'api' ? 'ApiReplayReviewAdapter' : 'FixtureReplayReviewAdapter'}</strong></div>
              <div><span>Backend mode</span><strong>{overview?.health.state === 'online' ? overview.health.mode : mode === 'fixture' ? 'not connected' : 'waiting for response'}</strong></div>
              <div><span>Fallback</span><strong>Disabled</strong></div>
            </div>
            <StateMessage state={overviewState} emptyLabel="No scenario records returned by the backend." />
          </article>

          <article className="panel scenario-panel">
            <div className="panel-topline"><p className="eyebrow">02 / SCENARIOS</p><span className="count-pill">{overview?.scenarios.length ?? '—'} available</span></div>
            <h2>Scenario catalogue</h2>
            <p className="muted">Fetched from the configured adapter. Domain review status is shown as supplied.</p>
            <StateMessage state={overviewState} emptyLabel="No scenarios are available." />
            {overview && overview.scenarios.length > 0 && (
              <div className="scenario-list">
                {overview.scenarios.slice(0, 4).map((item) => (
                  <button className={`scenario-row ${selectedScenario === item.id ? 'selected' : ''}`} key={item.id} onClick={() => setSelectedScenario(item.id)}>
                    <span className="scenario-index">{item.id.slice(0, 2).toUpperCase()}</span>
                    <span className="scenario-copy"><strong>{item.title}</strong><small>{item.objective}</small></span>
                    <span className="review-status">{item.domain_review.replaceAll('_', ' ')}</span>
                  </button>
                ))}
                {overview.scenarios.length > 4 && <p className="more-scenarios">+ {overview.scenarios.length - 4} more in the API catalogue</p>}
              </div>
            )}
          </article>
        </section>

        {mode === 'api' ? (
          <section className="panel access-panel" aria-labelledby="access-heading">
            <div className="panel-topline"><p className="eyebrow">03 / LOCAL SESSION DATA</p><span className="small-label">Training source · separate replay controls</span></div>
            <div className="access-heading-row">
              <div><h2 id="access-heading">Connect to a local training session</h2><p className="muted">Operator access is kept in memory for this tab and sent only to the same-origin local API.</p></div>
              {access && <button className="button button-quiet" onClick={() => { if (adapter instanceof ApiReplayReviewAdapter) adapter.clearCredentials(); setAccess(null); setReviewOpen(false); setOpenReviewState({ state: 'empty' }); setControlState({ state: 'empty' }); setSessionsState({ state: 'empty' }); setSessionState({ state: 'empty' }); setSelectedSessionId('') }}>Disconnect</button>}
            </div>
            {!access ? (
              <form className="access-form" onSubmit={(event) => void onLogin(event)}>
                <label className="field-label" htmlFor="operator-key">Local operator key</label>
                <div className="form-line"><input id="operator-key" type="password" autoComplete="off" value={operatorKey} onChange={(event) => setOperatorKey(event.target.value)} placeholder="Paste the key from the local backend runtime" minLength={16} maxLength={200} /><button className="button button-primary" type="submit" disabled={busyAction === 'login' || !operatorKey.trim()}>{busyAction === 'login' ? 'Connecting…' : 'Connect'}</button></div>
                <p className="field-note">The key is never stored in localStorage or added to a URL.</p>
              </form>
            ) : (
              <div className="session-controls">
                <div className="session-picker-wrap">
                  <label className="field-label" htmlFor="session-picker">Training session</label>
                  <select id="session-picker" value={selectedSessionId} onChange={(event) => onSessionChange(event.target.value)}>
                    <option value="">Select a session</option>
                    {sessions.map((item) => <option key={item.id} value={item.id}>{item.scenario.title} · {item.id} · {item.status}</option>)}
                  </select>
                </div>
                <button className="button button-primary" onClick={() => void onCreateSession()} disabled={busyAction !== null || !selectedScenario}>{busyAction === 'create' ? 'Creating…' : 'Create synthetic session'}</button>
              </div>
            )}
            {(access || sessionsState.state !== 'empty') && <StateMessage state={sessionsState} emptyLabel={access ? 'No local sessions yet. Choose a scenario above to create a synthetic training session.' : undefined} />}
          </section>
        ) : (
          <section className="panel fixture-note" aria-label="Fixture mode details">
            <div className="fixture-stamp">SYNTHETIC<br />FIXTURE</div>
            <div><p className="eyebrow">03 / FIXTURE MODE</p><h2>Synthetic replay review fixture</h2><p className="muted">Authored layout, tracks, transcript revisions, highlights and candidate review examples. No ASR, AI provider, partner simulator, server result, domain review or operational validation is represented.</p></div>
          </section>
        )}

        <section className="panel session-panel" aria-labelledby="session-heading">
          <div className="panel-topline"><p className="eyebrow">04 / SESSION SNAPSHOT</p><span className={`session-status status-${activeSession?.snapshot.status.toLowerCase() ?? 'idle'}`}>{activeSession?.snapshot.status ?? 'NO SESSION SELECTED'}</span></div>
          <div className="session-heading-row"><div><h2 id="session-heading">{activeSession?.session.scenario.title ?? 'Session data'}</h2><p className="muted">{activeSession ? `${activeSession.session.id} · ${activeSession.session.condition} · seed ${activeSession.session.seed}` : 'Select or create a local session to fetch its public snapshot.'}</p></div><span className="time-readout">{activeSession ? formatTime(activeSession.snapshot.sim_ms) : '—:—'}<small>SIM TIME</small></span></div>
          {!activeSession && (sessionState.state === 'loading' || sessionState.state === 'empty') && <StateMessage state={sessionState} emptyLabel="Session snapshots are loaded through the active adapter." />}
          {activeSession && (
            <>
              <div className="metric-grid">
                <Metric label="Observed tracks" value={activeSession.snapshot.track_count.toString().padStart(2, '0')} detail="Public snapshot" />
                <Metric label="Alerts in snapshot" value={activeSession.snapshot.alert_count.toString().padStart(2, '0')} detail="No UI recalculation" />
                <Metric label="Snapshot event tail" value={activeSession.events.length.toString().padStart(2, '0')} detail="Full cursor history loads below" />
                <Metric label="Data quality" value={activeSession.snapshot.data_quality.toUpperCase()} detail={`Runway ${activeSession.snapshot.runway_state}`} />
              </div>
              <div className="snapshot-footer"><span>Updated {formatWallTime(activeSession.session.created_utc_ms)}</span><span>sequence {activeSession.snapshot.sequence} · revision {activeSession.snapshot.revision}</span></div>
              <div className="event-list-heading"><span>EVENT TRACE</span><span>ORDINAL / SIM TIME</span></div>
              <ol className="event-list">
                {activeSession.events.slice(0, 5).map((item) => <li key={item.id}><span className="event-ordinal">{item.ordinal.toString().padStart(3, '0')}</span><span className="event-kind">{item.type.replaceAll('_', ' ')}</span><span className="event-message">{item.message}</span><time>{formatTime(item.sim_ms)}</time></li>)}
                {activeSession.events.length === 0 && <li className="empty-event">No event records returned for this view.</li>}
              </ol>
            </>
          )}
          {sessionState.state === 'disconnected' || sessionState.state === 'unauthorized' || sessionState.state === 'conflict' || sessionState.state === 'error'
            ? <StateMessage state={sessionState} />
            : null}
        </section>

        <SourceSetup mode={mode} source={sourceState} frame={frameState} selectedSourceId={selectedSessionId} />
        <ReplayControls
          mode={mode}
          frame={activeFrame}
          frameState={frameState}
          requestedMs={requestedTimeMs}
          supportedSpeeds={adapter.supported_speeds}
          reviewOpen={reviewOpen}
          canOpenReview={canOpenReview}
          openReviewState={openReviewState}
          controlState={controlState}
          onOpenReview={() => void onOpenReview()}
          onControl={(control) => void onReviewControl(control)}
          onRefresh={() => void onReplayRefresh()}
        />
        <ReplayTimeline
          sourceSessionId={selectedSessionId}
          frame={activeFrame}
          events={eventHistoryState}
          transcript={transcriptState}
          annotations={activeFrame?.snapshot?.review_annotations ?? []}
          requestedMs={requestedTimeMs}
          rangeEndMs={activeFrame?.snapshot?.review_end_ms ?? activeFrame?.frame_ms ?? 1}
          disabled={!activeFrame || frameState.state === 'disconnected' || !reviewOpen || replayActionPending}
          onSeek={(timeMs) => void onReviewControl({ type: 'SEEK', at_ms: timeMs, expected_revision: activeFrame?.snapshot?.revision ?? 0, request_id: createControlRequestId() })}
          selectedRef={selectedEvidenceRef}
        />
        <AudioPlayer
          adapter={adapter}
          sourceSessionId={selectedSessionId}
          transcript={transcriptState}
          requestedMs={requestedTimeMs}
          audioFocus={audioEvidenceFocus}
          disabled={!activeFrame || frameState.state === 'disconnected' || !reviewOpen || replayActionPending}
          onSeek={(timeMs) => void onReviewControl({ type: 'SEEK', at_ms: timeMs, expected_revision: activeFrame?.snapshot?.revision ?? 0, request_id: createControlRequestId() })}
        />
        <div className="runway-workspace-grid">
          <RunwayMap frame={activeFrame} frameState={frameState} />
          <RunwayBoard frame={activeFrame} />
        </div>
        <AlertEvidence adapter={adapter} sourceSessionId={selectedSessionId} frame={activeFrame} selectedRef={selectedEvidenceRef} onSelectEvidence={(ref) => void onEvidenceSelect(ref)} />
        <TranscriptPanel
          mode={mode}
          sourceSessionId={selectedSessionId}
          transcript={transcriptState}
          evaluatorAccess={evaluatorAccess}
          selectedRef={selectedEvidenceRef}
          selectionMessage={evidenceContextMessage}
          onSelectEvidence={(ref) => void onEvidenceSelect(ref)}
          onCorrect={onCorrectTranscript}
          onRefresh={refreshAssist}
        />
        <CandidatePanel
          mode={mode}
          sourceSessionId={selectedSessionId}
          state={assistState}
          selectedRef={selectedEvidenceRef}
          resolutions={evidenceResolutions}
          selectionMessage={evidenceContextMessage}
          onSelectEvidence={(ref, relation) => void onEvidenceSelect(ref, relation)}
          onReviewHighlight={onReviewHighlight}
          onReviewCandidate={onReviewCandidate}
          onRefresh={refreshAssist}
        />
        <DebriefPanel
          mode={mode}
          source={sourceState}
          frame={activeFrame}
          events={eventHistoryState}
          transcript={transcriptState}
          assist={assistState}
          annotations={activeFrame?.snapshot?.review_annotations ?? []}
          resolutions={evidenceResolutions}
          onSelectEvidence={(ref) => void onEvidenceSelect(ref)}
        />

        <footer className="workspace-footer"><span>ATC FlowLens · offline replay and synthetic training</span><span>Controller authority remains with the human operator.</span></footer>
      </main>
    </div>
  )
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>
}

export default App
