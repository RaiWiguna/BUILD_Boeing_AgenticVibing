import type { ReplayFrameReadModel } from '../../contracts/replayReview'

function relativeSeconds(value: number): string {
  return `${value} s relative`
}

export function RunwayBoard({ frame }: { frame: ReplayFrameReadModel | null }) {
  const snapshot = frame?.snapshot
  if (!snapshot) {
    return <section className="panel runway-board-panel" aria-labelledby="runway-board-heading">
      <div className="panel-topline"><p className="eyebrow">07 / RUNWAY BOARD</p><span className="small-label">Read model values</span></div>
      <h2 id="runway-board-heading">Runway status and predictions</h2>
      <p className="board-empty">Runway state is unavailable until a source frame is accessible.</p>
    </section>
  }

  const runway = snapshot.runway
  const directionLabels = Object.keys(snapshot.layout.directions).sort()
  return (
    <section className="panel runway-board-panel" aria-labelledby="runway-board-heading">
      <div className="panel-topline"><p className="eyebrow">07 / RUNWAY BOARD</p><span className="small-label">Backend values · no UI detector</span></div>
      <div className="section-heading-row">
        <div><h2 id="runway-board-heading">{snapshot.layout.physical_runway_id}</h2><p className="muted">Direction labels: {directionLabels.length ? directionLabels.join(' / ') : 'not supplied'}</p></div>
        <span className={`runway-quality quality-${runway.data_quality.toLowerCase()}`}>{runway.data_quality}</span>
      </div>

      <div className="runway-status-grid">
        <div><small>OPEN FLAG · SOURCE VALUE</small><strong>{String(runway.open)}</strong></div>
        <div><small>RUNWAY STATE · SOURCE VALUE</small><strong>{runway.state}</strong></div>
        <div><small>OBSERVED OCCUPANTS</small><strong>{runway.observed_occupants.length ? runway.observed_occupants.join(', ') : 'None listed'}</strong></div>
        <div><small>DEGRADED IDS</small><strong>{runway.degraded_ids.length ? runway.degraded_ids.join(', ') : 'None listed'}</strong></div>
      </div>

      <section className="board-subsection" aria-labelledby="prediction-heading">
        <div className="subsection-heading"><h3 id="prediction-heading">Predicted occupancy windows</h3><span>{snapshot.predictions.length} supplied</span></div>
        {snapshot.predictions.length === 0 ? (
          <p className="board-empty">No prediction rows were supplied for this frame. This does not establish runway clear.</p>
        ) : (
          <div className="prediction-list">
            {snapshot.predictions.map((prediction, index) => (
              <article className="prediction-row" key={`${prediction.object_id}-${prediction.direction ?? 'unknown'}-${prediction.interval_index ?? index}`}>
                <div className="prediction-heading">
                  <strong>{prediction.object_id}</strong>
                  <span>{prediction.direction ? `Direction ${prediction.direction}` : 'Direction unavailable'}</span>
                  {prediction.exit_unknown && <em>EXIT UNKNOWN</em>}
                </div>
                <p className="prediction-window">Entry {relativeSeconds(prediction.entry_s)} · reported exit {relativeSeconds(prediction.exit_s)}</p>
                {prediction.exit_unknown && <p className="unknown-exit-copy">Exit state remains unknown; the reported window end is not a runway-clear time.</p>}
                <dl className="prediction-details">
                  <div><dt>Assumed entry range</dt><dd>{prediction.assumed_entry_range_s.join(' – ')} s</dd></div>
                  <div><dt>Assumed exit range</dt><dd>{prediction.assumed_exit_range_s.join(' – ')} s</dd></div>
                  <div><dt>Threshold ETA</dt><dd>{prediction.threshold_eta_s === null ? 'Not supplied' : relativeSeconds(prediction.threshold_eta_s)}</dd></div>
                  <div><dt>Physical resource</dt><dd>{prediction.physical_runway_id ?? 'Not supplied by prediction'}</dd></div>
                  <div><dt>Model version</dt><dd>{prediction.model_version ?? 'Not supplied'}</dd></div>
                  <div><dt>Source event ID</dt><dd>{prediction.source_event_id ?? 'Not supplied'}</dd></div>
                </dl>
                <p className="relative-time-note">Entry/exit values are relative seconds from calculation time, not absolute timestamps.</p>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="board-subsection" aria-labelledby="clearance-heading">
        <div className="subsection-heading"><h3 id="clearance-heading">Recorded clearances</h3><span>{snapshot.clearances.length} supplied</span></div>
        {snapshot.clearances.length === 0 ? <p className="board-empty">No clearance rows were supplied in this frame.</p> : (
          <ul className="clearance-list">
            {snapshot.clearances.map((clearance) => (
              <li key={clearance.id}>
                <span className="clearance-target">{clearance.target}</span>
                <span><strong>{clearance.instruction}</strong><small>RWY {clearance.runway} · {clearance.status} · readback {clearance.readback}</small></span>
                <span className="clearance-time">{clearance.issued_ms} ms SIM</span>
              </li>
            ))}
          </ul>
        )}
      </section>
      <p className="board-footer">Frame time: {snapshot.sim_ms} ms SIM · requested/playback: {snapshot.playback_ms === null ? `${frame.requested_ms} ms requested` : `${snapshot.playback_ms} ms playback`}</p>
    </section>
  )
}
