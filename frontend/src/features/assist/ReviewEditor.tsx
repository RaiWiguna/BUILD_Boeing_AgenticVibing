import { useEffect, useState } from 'react'
import { ApiRequestError } from '../../api'
import type { ReviewReceipt } from '../../contracts/replayReview'
import { createReviewRequestId } from '../replay/ReplayController'

export type ReviewDecision = 'corrected' | 'confirmed' | 'dismissed' | 'unresolved'

type EditorState =
  | { status: 'idle' }
  | { status: 'pending'; request_id: string }
  | { status: 'accepted'; receipt: ReviewReceipt }
  | { status: 'conflict'; message: string; revision?: number; reconciled: boolean }
  | { status: 'unauthorized' | 'unavailable' | 'error'; message: string }

export function ReviewEditor({
  targetId, expectedRevision, initialText = '', correction = false, disabled = false,
  onSubmit, onRefresh,
}: {
  targetId: string
  expectedRevision: number | null
  initialText?: string
  correction?: boolean
  disabled?: boolean
  onSubmit: (decision: ReviewDecision, text: string, reason: string, requestId: string) => Promise<ReviewReceipt>
  onRefresh: () => Promise<void>
}) {
  const [draft, setDraft] = useState(initialText)
  const [reason, setReason] = useState('')
  const [state, setState] = useState<EditorState>({ status: 'idle' })
  const [reconciling, setReconciling] = useState(false)

  useEffect(() => {
    setDraft(initialText)
    setReason('')
    setState({ status: 'idle' })
  }, [targetId])

  const send = async (decision: ReviewDecision) => {
    const requestId = createReviewRequestId(decision)
    setState({ status: 'pending', request_id: requestId })
    try {
      const receipt = await onSubmit(decision, draft, reason, requestId)
      if (receipt.status === 'accepted') setState({ status: 'accepted', receipt })
      else if (receipt.status === 'conflict') setState({ status: 'conflict', message: receipt.message ?? 'Revision conflict.', revision: receipt.revision, reconciled: false })
      else setState({ status: 'unavailable', message: receipt.message ?? 'Review route is unavailable.' })
    } catch (error) {
      if (error instanceof ApiRequestError && ['unauthorized', 'forbidden', 'expired'].includes(error.reason)) {
        setState({ status: 'unauthorized', message: error.message })
      } else if (error instanceof ApiRequestError && error.reason === 'conflict') {
        setState({ status: 'conflict', message: error.message, reconciled: false })
      } else if (error instanceof ApiRequestError && ['not_found', 'service_unavailable', 'unsupported_profile'].includes(error.reason)) {
        setState({ status: 'unavailable', message: error.message })
      } else {
        setState({ status: 'error', message: error instanceof Error ? error.message : 'The review request failed.' })
      }
    }
  }

  const reconcile = async () => {
    setReconciling(true)
    try {
      await onRefresh()
      setState((current) => current.status === 'conflict'
        ? { ...current, reconciled: true, message: `${current.message} Refreshed read model is available; retry is still explicit.` }
        : current)
    } catch (error) {
      setState({ status: 'error', message: error instanceof Error ? error.message : 'Could not refresh the current revision.' })
    } finally {
      setReconciling(false)
    }
  }

  const conflictNeedsRefresh = state.status === 'conflict' && !state.reconciled
  const submitBlocked = disabled || expectedRevision === null || state.status === 'pending' || reconciling || conflictNeedsRefresh

  return (
    <div className="review-editor" aria-label={`Review editor for ${targetId}`}>
      {correction && (
        <label className="assist-field">
          <span>Corrected text draft · source text stays preserved</span>
          <textarea value={draft} onChange={(event) => setDraft(event.target.value)} rows={3} disabled={disabled || state.status === 'pending'} />
        </label>
      )}
      <label className="assist-field">
        <span>Reviewer reason (optional)</span>
        <input value={reason} onChange={(event) => setReason(event.target.value)} disabled={disabled || state.status === 'pending'} />
      </label>
      <div className="review-action-row">
        {correction ? (
          <button className="button button-secondary" type="button" disabled={submitBlocked || !draft.trim()} onClick={() => void send('corrected')}>
            {state.status === 'pending' ? 'Submitting…' : state.status === 'conflict' && state.reconciled ? `Retry with revision ${expectedRevision}` : 'Submit correction'}
          </button>
        ) : (
          (['confirmed', 'dismissed', 'unresolved'] as const).map((decision) => (
            <button key={decision} className={`button ${decision === 'confirmed' ? 'button-secondary' : 'button-quiet'}`} type="button" disabled={submitBlocked} onClick={() => void send(decision)}>
              {decision[0].toUpperCase() + decision.slice(1)}
            </button>
          ))
        )}
        {state.status === 'conflict' && (
          <button className="button button-primary" type="button" disabled={reconciling} onClick={() => void reconcile()}>
            {reconciling ? 'Refreshing…' : 'Refresh / reconcile'}
          </button>
        )}
      </div>
      {expectedRevision === null && <p className="review-status-message state-unavailable" role="status">Expected revision is unavailable; this action cannot be sent safely.</p>}
      {state.status !== 'idle' && (
        <p className={`review-status-message review-action-${state.status}`} role="status">
          {state.status === 'pending' && `PENDING · request ${state.request_id}`}
          {state.status === 'accepted' && `ACCEPTED${state.receipt.authority === 'fixture' ? ' · FIXTURE MEMORY ONLY' : state.receipt.authority === 'server' ? ' · SERVER RECEIPT' : ''} · revision ${state.receipt.revision}${state.receipt.message ? ` · ${state.receipt.message}` : ''}`}
          {state.status === 'conflict' && `CONFLICT · ${state.message}${state.revision === undefined ? '' : ` · latest revision ${state.revision}`}${state.reconciled ? ' · refreshed; explicit retry available' : ' · draft retained; refresh before retry'}`}
          {state.status === 'unauthorized' && `UNAUTHORIZED · ${state.message}`}
          {state.status === 'unavailable' && `UNAVAILABLE · ${state.message}`}
          {state.status === 'error' && `ERROR · ${state.message}`}
        </p>
      )}
    </div>
  )
}
