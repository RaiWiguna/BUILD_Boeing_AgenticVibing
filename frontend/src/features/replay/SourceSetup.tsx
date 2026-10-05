import type { AsyncState, AdapterMode, ReplayFrameReadModel, ReplaySourceReadModel } from '../../contracts/replayReview'

interface SourceSetupProps {
  mode: AdapterMode
  source: AsyncState<ReplaySourceReadModel>
  frame: AsyncState<ReplayFrameReadModel>
  selectedSourceId: string
}

function StateNotice({ state, emptyText }: { state: AsyncState<unknown>; emptyText: string }) {
  if (state.state === 'ready' || state.state === 'degraded') return null
  if (state.state === 'loading') return <p className="context-notice"><span className="spinner" /> Loading through the selected adapter…</p>
  if (state.state === 'empty') return <p className="context-notice">{emptyText}</p>
  return <p className={`context-notice state-${state.state}`} role="status">{state.message}</p>
}

function supplied(value: string | null | undefined): string {
  return value && value.length > 0 ? value : 'Not supplied by this source profile'
}

function frameConnection(frame: AsyncState<ReplayFrameReadModel>): string {
  if (frame.state === 'unsupported-layout') return 'Unsupported layout'
  if (frame.state === 'disconnected') return 'Disconnected · last frame retained'
  if (frame.state === 'unauthorized') return 'Unauthorized'
  if (frame.state === 'error') return 'Error'
  if (frame.state === 'conflict') return 'Conflict'
  if (frame.state === 'degraded') return 'Degraded'
  if (frame.state === 'ready') return frame.data.state === 'disconnected' ? 'Disconnected · last frame retained' : frame.data.state ?? 'Ready'
  if (frame.state === 'loading') return 'Loading'
  return 'Unavailable'
}

export function SourceSetup({ mode, source, frame, selectedSourceId }: SourceSetupProps) {
  const sourceData = source.state === 'ready' || source.state === 'degraded' ? source.data : null
  const frameData = frame.state === 'ready' || frame.state === 'degraded' || frame.state === 'disconnected' ? frame.data : null
  const snapshot = frameData?.snapshot
  const synthetic = sourceData?.source_kind === 'synthetic'
  const connection = source.state === 'unauthorized' ? 'Unauthorized' : frameConnection(frame)

  return (
    <section className="panel source-context-panel" aria-labelledby="source-context-heading">
      <div className="panel-topline">
        <p className="eyebrow">05 / SOURCE CONTEXT</p>
        <span className={`source-kind-badge ${synthetic ? 'is-synthetic' : ''}`}>
          {sourceData?.label ?? (mode === 'fixture' ? 'SYNTHETIC FIXTURE' : 'API SOURCE READ')}
        </span>
      </div>
      <div className="source-context-heading-row">
        <div>
          <h2 id="source-context-heading">Source and frame</h2>
          <p className="muted">Replay metadata and access state supplied by the active adapter.</p>
          <p className="source-id-line">Selected source · <code>{selectedSourceId || 'none'}</code></p>
        </div>
        <span className={`connection-badge connection-${connection.toLowerCase().split(' ')[0]}`}>
          {connection}
        </span>
      </div>

      <StateNotice state={source} emptyText={mode === 'api' ? 'Connect to the local API and select a session to load source context.' : 'No fixture source is selected.'} />
      {source.state !== 'unauthorized' && <StateNotice state={frame} emptyText="No frame is available for the selected source." />}

      {sourceData && (
        <>
          {sourceData.source_kind === 'synthetic' && (
            <p className="synthetic-caveat">Synthetic baseline · not validated against operational activity.</p>
          )}
          <dl className="source-context-grid">
            <div><dt>Source session ID</dt><dd>{sourceData.source_session_id || selectedSourceId}</dd></div>
            <div><dt>Source kind</dt><dd>{sourceData.source_kind}</dd></div>
            <div><dt>Source quality</dt><dd>{sourceData.quality}</dd></div>
            <div><dt>Source version</dt><dd>{supplied(sourceData.source_version)}</dd></div>
            <div><dt>Provenance</dt><dd>{sourceData.provenance}</dd></div>
            <div><dt>Coverage</dt><dd>Not exposed by the current source read model</dd></div>
            <div><dt>Model readiness</dt><dd>Not exposed by the current source read model</dd></div>
            <div><dt>Viewer role</dt><dd>{snapshot ? `${snapshot.viewer_role} · ${snapshot.viewer_label}` : 'Not exposed by the current source read model'}</dd></div>
          </dl>
        </>
      )}

      {snapshot && (
        <div className="frame-context-strip" aria-label="Frame timing and layout">
          <span><small>FRAME SIM TIME</small><strong>{snapshot.sim_ms} ms</strong></span>
          <span><small>PLAYBACK TIME</small><strong>{snapshot.playback_ms === null ? `${frameData?.requested_ms ?? '—'} ms requested` : `${snapshot.playback_ms} ms`}</strong></span>
          <span><small>LAYOUT</small><strong>{snapshot.layout.id} · v{snapshot.layout.version}</strong></span>
          <span><small>ENGINE / SOURCE VERSION</small><strong>{snapshot.source_version}</strong></span>
          <span><small>CONFIG VERSION</small><strong>{supplied(snapshot.config_version)}</strong></span>
          <span><small>COORDINATES</small><strong>{snapshot.layout.coordinate_system}</strong></span>
        </div>
      )}

      {mode === 'api' && (source.state === 'unauthorized' || frame.state === 'unauthorized') && (
        <p className="source-capability-note">
          The current backend does not issue a separate source-read credential. Operator access is not reused for source evidence, and no fixture data is substituted.
        </p>
      )}
    </section>
  )
}
