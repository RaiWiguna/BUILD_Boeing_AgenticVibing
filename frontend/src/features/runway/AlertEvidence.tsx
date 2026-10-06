import { useEffect, useMemo, useState } from 'react'
import { ApiRequestError, isAbortError } from '../../api'
import type { AsyncState, EvidenceRef, EvidenceResolution, ReplayFrameReadModel, ReplayReviewAdapter } from '../../contracts/replayReview'

function evidenceKey(ref: EvidenceRef): string {
  return `${ref.kind}:${ref.id}`
}

function evidenceFailure(error: unknown): AsyncState<EvidenceResolution[]> {
  if (error instanceof ApiRequestError) return { state: error.kind, message: error.message }
  return { state: 'error', message: error instanceof Error ? error.message : 'Evidence lookup failed.' }
}

function evidenceStateText(state: AsyncState<EvidenceResolution[]>): string {
  if (state.state === 'loading') return 'Resolving scoped evidence…'
  if (state.state === 'empty') return 'No evidence event IDs were supplied.'
  if (state.state === 'ready' || state.state === 'degraded') return ''
  return state.message
}

export function AlertEvidence({ adapter, sourceSessionId, frame, selectedRef = null, onSelectEvidence }: {
  adapter: ReplayReviewAdapter
  sourceSessionId: string
  frame: ReplayFrameReadModel | null
  selectedRef?: EvidenceRef | null
  onSelectEvidence?: (ref: EvidenceRef) => void
}) {
  const alerts = frame?.snapshot?.alerts ?? []
  const refs = useMemo(() => {
    const unique = new Map<string, EvidenceRef>()
    for (const alert of alerts) {
      for (const id of alert.evidence_event_ids) {
        const ref: EvidenceRef = { kind: 'session_event', id }
        unique.set(evidenceKey(ref), ref)
      }
    }
    return [...unique.values()]
  }, [alerts])
  const [resolutionState, setResolutionState] = useState<AsyncState<EvidenceResolution[]>>({ state: 'empty' })
  const cutoffMs = frame?.snapshot?.sim_ms

  useEffect(() => {
    if (!frame?.snapshot) {
      setResolutionState({ state: 'empty' })
      return
    }
    if (refs.length === 0) {
      setResolutionState({ state: 'empty' })
      return
    }

    const controller = new AbortController()
    setResolutionState({ state: 'loading' })
    void adapter.resolveEvidence(sourceSessionId, refs, cutoffMs, controller.signal)
      .then((items) => setResolutionState(items.length ? { state: 'ready', data: items } : { state: 'empty' }))
      .catch((error: unknown) => {
        if (!isAbortError(error)) setResolutionState(evidenceFailure(error))
      })
    return () => controller.abort()
  }, [adapter, cutoffMs, frame?.snapshot, refs, sourceSessionId])

  const resolutions = resolutionState.state === 'ready' || resolutionState.state === 'degraded' ? resolutionState.data : []
  const resolutionByKey = new Map(resolutions.map((item) => [evidenceKey(item.ref), item]))
  const snapshot = frame?.snapshot

  return (
    <section className="panel alert-evidence-panel" aria-labelledby="alert-evidence-heading">
      <div className="panel-topline"><p className="eyebrow">08 / DETERMINISTIC ALERTS</p><span className="small-label">Server supplied · evidence scoped</span></div>
      <div className="section-heading-row">
        <div><h2 id="alert-evidence-heading">Alert evidence</h2><p className="muted">Lifecycle, severity, metrics, age and assumptions are rendered from the read model.</p></div>
        {snapshot && <span className="alert-count-pill">{snapshot.alert_count} in frame</span>}
      </div>

      {!snapshot ? (
        <p className="board-empty">Alert details are unavailable until a source frame is accessible.</p>
      ) : alerts.length === 0 ? (
        <p className="board-empty">No deterministic alert rows were supplied. This is not a detector recomputation or a runway-clear finding.</p>
      ) : (
        <div className="alert-evidence-list">
          {alerts.map((alert) => {
            const acknowledgements = snapshot.acknowledgements.filter((item) => item.alert_id === alert.id)
            return (
              <article id={`alert-${alert.id}`} className={`deterministic-alert ${selectedRef?.kind === 'detector_alert' && selectedRef.id === alert.id ? 'is-evidence-selected' : ''}`} key={alert.id}>
                <div className="alert-title-row">
                  <div><span className="alert-id">{alert.id}</span><h3>{alert.rule}</h3></div>
                  <div className="alert-tags"><span className={`severity-tag severity-${alert.severity.toLowerCase()}`}>{alert.severity}</span><span className="lifecycle-tag">{alert.status}</span></div>
                </div>
                <p className="alert-reason">{alert.reason}</p>
                {onSelectEvidence && <button className="evidence-select-button" type="button" onClick={() => onSelectEvidence({ kind: 'detector_alert', id: alert.id })}>{selectedRef?.kind === 'detector_alert' && selectedRef.id === alert.id ? 'Selected' : 'Open'} exact alert reference · {alert.id}</button>}

                <dl className="alert-timing-grid">
                  <div><dt>Created</dt><dd>{alert.created_ms} ms SIM</dd></div>
                  <div><dt>Calculated</dt><dd>{alert.calculated_ms} ms SIM</dd></div>
                  <div><dt>Updated</dt><dd>{alert.updated_ms === undefined ? 'Not supplied' : `${alert.updated_ms} ms SIM`}</dd></div>
                  <div><dt>Data degraded</dt><dd>{String(alert.data_degraded)}</dd></div>
                </dl>

                <section className="alert-detail-block" aria-label={`Metrics for ${alert.id}`}>
                  <h4>Metrics · raw read model</h4>
                  <pre className="alert-metrics">{JSON.stringify(alert.metrics, null, 2) ?? '{}'}</pre>
                </section>
                <section className="alert-detail-block" aria-label={`Track ages for ${alert.id}`}>
                  <h4>Track ages supplied</h4>
                  {Object.keys(alert.track_ages_ms).length === 0
                    ? <p className="detail-empty">No track ages supplied.</p>
                    : <ul className="age-list">{Object.entries(alert.track_ages_ms).map(([id, age]) => <li key={id}><strong>{id}</strong><span>{age} ms age</span></li>)}</ul>}
                </section>
                <section className="alert-detail-block" aria-label={`Assumptions for ${alert.id}`}>
                  <h4>Assumptions</h4><p className="assumption-copy">{alert.assumptions}</p>
                </section>

                <section className="alert-detail-block evidence-block" aria-label={`Evidence for ${alert.id}`}>
                  <div className="evidence-heading"><h4>Evidence event IDs</h4><span>Source scope: {sourceSessionId}</span></div>
                  {alert.evidence_event_ids.length === 0 ? (
                    <p className="detail-empty">No event references supplied by this alert.</p>
                  ) : (
                    <ul className="evidence-list">
                      {alert.evidence_event_ids.map((id) => {
                        const ref: EvidenceRef = { kind: 'session_event', id }
                        const resolution = resolutionByKey.get(evidenceKey(ref))
                        return (
                          <li key={id}>
                            <span className="evidence-ref-kind">session_event</span>
                            <code>{id}</code>
                            <span className={`evidence-resolution resolution-${resolution?.state ?? 'pending'}`}>
                              {resolution?.state === 'resolved' ? resolution.summary ?? 'Resolved; no summary supplied'
                                : resolution?.state === 'unresolved' ? 'UNRESOLVED · exact source event was not found in scope/time'
                                  : resolution?.state === 'unavailable' ? 'UNAVAILABLE · this reference type or lookup is unsupported'
                                    : resolutionState.state === 'loading' ? 'Resolving…'
                                      : resolutionState.state === 'ready' || resolutionState.state === 'degraded' ? 'UNRESOLVED · resolver returned no matching reference'
                                        : evidenceStateText(resolutionState)}
                            </span>
                            {onSelectEvidence && <button type="button" className="evidence-select-button" onClick={() => onSelectEvidence(ref)}>{selectedRef?.kind === ref.kind && selectedRef.id === ref.id ? 'Selected' : 'Open'} exact event reference · {id}</button>}
                          </li>
                        )
                      })}
                    </ul>
                  )}
                  {resolutionState.state !== 'ready' && resolutionState.state !== 'degraded' && resolutionState.state !== 'empty' && (
                    <p className={`evidence-state state-${resolutionState.state}`} role="status">{evidenceStateText(resolutionState)}</p>
                  )}
                </section>

                <section className="alert-acknowledgements" aria-label={`Acknowledgements for ${alert.id}`}>
                  <h4>Acknowledgements · separate from lifecycle</h4>
                  {acknowledgements.length === 0
                    ? <p>No acknowledgement supplied.</p>
                    : <ul>{acknowledgements.map((item, index) => <li key={`${item.actor}-${item.sim_ms}-${index}`}><strong>{item.actor}</strong><span>{item.sim_ms} ms SIM</span></li>)}</ul>}
                </section>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
