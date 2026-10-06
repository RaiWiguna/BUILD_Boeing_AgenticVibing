import type {
  AdapterMode,
  AsyncState,
  ReplayFrameReadModel,
  ReviewControl,
  ReviewOpenResult,
  ReviewReceipt,
  ReviewSpeed,
} from '../../contracts/replayReview'
import { createControlRequestId } from './ReplayController'

interface ReplayControlsProps {
  mode: AdapterMode
  frame: ReplayFrameReadModel | null
  frameState: AsyncState<ReplayFrameReadModel>
  requestedMs: number
  supportedSpeeds: readonly ReviewSpeed[]
  reviewOpen: boolean
  canOpenReview: boolean
  openReviewState: AsyncState<ReviewOpenResult>
  controlState: AsyncState<ReviewReceipt>
  onOpenReview: () => void
  onControl: (control: ReviewControl) => void
  onRefresh: () => void
}

type ControlIntent =
  | { type: 'START' | 'PAUSE' }
  | { type: 'SEEK'; at_ms: number }
  | { type: 'SET_SPEED'; speed: ReviewSpeed }

function timeLabel(milliseconds: number | null | undefined): string {
  return milliseconds === null || milliseconds === undefined ? 'Unavailable' : `${milliseconds} ms`
}

export function ReplayControls({
  mode, frame, frameState, requestedMs, supportedSpeeds, reviewOpen, canOpenReview,
  openReviewState, controlState, onOpenReview, onControl, onRefresh,
}: ReplayControlsProps) {
  const snapshot = frame?.snapshot
  const busy = openReviewState.state === 'loading' || controlState.state === 'loading'
  const streamDisconnected = frameState.state === 'disconnected'
  const canControl = mode === 'fixture' || reviewOpen
  const disabled = busy || !frame || !snapshot || streamDisconnected || !canControl || controlState.state === 'conflict'
  const revision = snapshot?.revision ?? 0
  const playbackMs = snapshot?.playback_ms
  const atReplayEnd = playbackMs !== null && playbackMs !== undefined
    && snapshot?.review_end_ms !== undefined
    && playbackMs >= snapshot.review_end_ms

  const submit = (intent: ControlIntent) => {
    const common = { expected_revision: revision, request_id: createControlRequestId() }
    const control: ReviewControl = intent.type === 'SEEK'
      ? { ...common, ...intent }
      : intent.type === 'SET_SPEED'
        ? { ...common, ...intent }
        : { ...common, ...intent }
    onControl(control)
  }
  const isRunning = snapshot?.status.toUpperCase() === 'RUNNING'
  const statusMessage = controlState.state === 'ready' && controlState.data.status === 'accepted'
    ? `Control receipt accepted · revision ${controlState.data.revision}.`
    : controlState.state === 'loading'
      ? 'Control request pending; duplicate submit is disabled.'
      : controlState.state === 'conflict' || controlState.state === 'error' || controlState.state === 'unauthorized' || controlState.state === 'unavailable' || controlState.state === 'disconnected'
      ? controlState.message
      : controlState.state === 'ready' && controlState.data.message
        ? controlState.data.message
        : null

  return (
    <section className="panel replay-controls-panel" aria-labelledby="replay-controls-heading">
      <div className="section-heading-row">
        <div><p className="eyebrow">REVIEW CONTROLS</p><h2 id="replay-controls-heading">Playback and seek</h2><p className="muted">Every control carries the current expected revision and a request identity.</p></div>
        <span className={`connection-badge ${streamDisconnected ? 'connection-disconnected' : canControl ? 'connection-ready' : 'connection-unsupported'}`}>
          {streamDisconnected ? 'DISCONNECTED · LAST FRAME RETAINED' : canControl ? `REVISION ${revision}` : 'REVIEW CONTROL UNAVAILABLE'}
        </span>
      </div>

      {mode === 'api' && !reviewOpen && (
        <div className="review-open-box">
          <div>
            <strong>Open a frozen server review</strong>
            <p>{canOpenReview ? 'The selected source is ended. The adapter can request a separate review-control credential.' : 'The current source must be ended or interrupted before the backend can create a frozen review.'}</p>
          </div>
          <button className="button button-primary" type="button" onClick={onOpenReview} disabled={!canOpenReview || busy}>
            {openReviewState.state === 'loading' ? 'Opening…' : 'Open review'}
          </button>
        </div>
      )}

      <div className="playback-control-row">
        <div className="playback-actions">
          <button className="button button-primary" type="button" onClick={() => submit({ type: 'START' })} disabled={disabled || isRunning || atReplayEnd}>
            START
          </button>
          <button className="button button-secondary" type="button" onClick={() => submit({ type: 'PAUSE' })} disabled={disabled || !isRunning}>
            PAUSE
          </button>
          <label className="playback-speed-control">
            <span>Supported speed</span>
            <select value={snapshot?.speed ?? 1} disabled={disabled} onChange={(event) => submit({ type: 'SET_SPEED', speed: Number(event.target.value) as ReviewSpeed })}>
              {supportedSpeeds.map((speed) => <option key={speed} value={speed}>{speed}×</option>)}
            </select>
          </label>
        </div>
        <dl className="playback-time-readouts">
          <div><dt>Requested</dt><dd>{timeLabel(requestedMs)}</dd></div>
          <div><dt>Playback</dt><dd>{timeLabel(snapshot?.playback_ms)}</dd></div>
          <div><dt>Actual frame</dt><dd>{timeLabel(frame?.frame_ms)} <small>sim_ms</small></dd></div>
          <div><dt>Frame status</dt><dd>{snapshot?.status ?? frameState.state}</dd></div>
        </dl>
      </div>

      {statusMessage && <p className={`state-message ${controlState.state === 'conflict' ? 'state-conflict' : controlState.state === 'error' || controlState.state === 'unauthorized' ? `state-${controlState.state}` : ''}`} role="status">{statusMessage}</p>}
      {atReplayEnd && !isRunning && <p className="playback-note">Replay is at its recorded end. Seek to an earlier session time to start playback.</p>}
      {controlState.state === 'conflict' && <button className="button button-quiet reconcile-button" type="button" onClick={onRefresh}>Refresh and reconcile current revision</button>}
      {openReviewState.state === 'error' || openReviewState.state === 'conflict' || openReviewState.state === 'unauthorized' || openReviewState.state === 'unavailable' || openReviewState.state === 'disconnected'
        ? <p className={`state-message state-${openReviewState.state}`} role="alert">{openReviewState.message}</p>
        : openReviewState.state === 'ready' && openReviewState.data.message
          ? <p className="state-message">{openReviewState.data.message}</p>
          : null}
      {frameState.state === 'disconnected' && <p className="state-message state-disconnected" role="status">{frameState.message}. Controls are paused until the source is connected again; the displayed frame is retained without extrapolation.</p>}
      {mode === 'api' && !reviewOpen && <p className="playback-note">No control receipt is claimed until the adapter receives the backend response. API source-read access remains a separate unavailable capability.</p>}
    </section>
  )
}
