import type { AsyncState, ReplayFrameReadModel, ReplaySnapshotReadModel } from '../../contracts/replayReview'

const SVG_WIDTH = 1000
const SVG_HEIGHT = 380
const SVG_PADDING = 30

type Point = [number, number]
type GeometryBounds = { minX: number; minY: number; maxX: number; maxY: number }

function sessionTime(value: number): string {
  return `${value} ms SIM`
}

function geometryPoints(snapshot: ReplaySnapshotReadModel): Point[] {
  const layout = snapshot.layout
  return [
    ...layout.runway,
    ...layout.protected_area,
    ...layout.taxiways.flat(),
    ...layout.hold_lines.flat(),
  ]
}

function boundsOf(points: Point[]): GeometryBounds | null {
  if (points.length === 0) return null
  const xs = points.map(([x]) => x)
  const ys = points.map(([, y]) => y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  if (maxX <= minX || maxY <= minY) return null
  return { minX, minY, maxX, maxY }
}

function extent(bounds: GeometryBounds): { scale: number; offsetX: number; offsetY: number } {
  const width = bounds.maxX - bounds.minX
  const height = bounds.maxY - bounds.minY
  const scale = Math.min((SVG_WIDTH - SVG_PADDING * 2) / width, (SVG_HEIGHT - SVG_PADDING * 2) / height)
  return {
    scale,
    offsetX: (SVG_WIDTH - width * scale) / 2,
    offsetY: (SVG_HEIGHT - height * scale) / 2,
  }
}

function toX(x: number, bounds: GeometryBounds, view: ReturnType<typeof extent>): number {
  return view.offsetX + (x - bounds.minX) * view.scale
}

function toY(y: number, bounds: GeometryBounds, view: ReturnType<typeof extent>): number {
  return view.offsetY + (bounds.maxY - y) * view.scale
}

function pointsAttribute(points: Point[], bounds: GeometryBounds, view: ReturnType<typeof extent>): string {
  return points.map(([x, y]) => `${toX(x, bounds, view)},${toY(y, bounds, view)}`).join(' ')
}

function UnsupportedLayout({ reason }: { reason: string }) {
  return <div className="map-state map-state-unsupported" role="status"><strong>Unsupported layout</strong><span>{reason}</span></div>
}

export function RunwayMap({ frame, frameState }: { frame: ReplayFrameReadModel | null; frameState: AsyncState<ReplayFrameReadModel> }) {
  const snapshot = frame?.snapshot
  if (!snapshot) {
    if (frameState.state === 'unsupported-layout') {
      return <section className="panel runway-map-panel" aria-labelledby="runway-map-heading">
        <div className="panel-topline"><p className="eyebrow">06 / LOCAL GEOMETRY</p><span className="small-label">Unsupported layout</span></div>
        <h2 id="runway-map-heading">Runway map</h2>
        <UnsupportedLayout reason={frameState.message} />
      </section>
    }
    const stateMessage = frameState.state === 'loading' ? 'Loading frame through the selected adapter…'
      : frameState.state === 'empty' ? 'Select a source to load public layout geometry.'
        : frameState.state === 'disconnected' ? frameState.message
          : frameState.state === 'ready' || frameState.state === 'degraded' ? 'No layout geometry was returned with this frame.'
            : 'message' in frameState ? frameState.message : 'Map unavailable for this source.'
    return <section className="panel runway-map-panel" aria-labelledby="runway-map-heading">
      <div className="panel-topline"><p className="eyebrow">06 / LOCAL GEOMETRY</p><span className="small-label">SVG · LOCAL_METRES</span></div>
      <h2 id="runway-map-heading">Runway map</h2>
      <div className="map-state" role="status">{stateMessage}</div>
    </section>
  }

  if (snapshot.layout.coordinate_system !== 'LOCAL_METRES') {
    return <section className="panel runway-map-panel" aria-labelledby="runway-map-heading">
      <div className="panel-topline"><p className="eyebrow">06 / LOCAL GEOMETRY</p><span className="small-label">Unsupported coordinates</span></div>
      <h2 id="runway-map-heading">Runway map</h2>
      <UnsupportedLayout reason={`Coordinate system ${snapshot.layout.coordinate_system} is not LOCAL_METRES.`} />
    </section>
  }

  const allPoints = geometryPoints(snapshot)
  const bounds = boundsOf(allPoints)
  if (!bounds || snapshot.layout.runway.length < 3 || snapshot.layout.protected_area.length < 3) {
    return <section className="panel runway-map-panel" aria-labelledby="runway-map-heading">
      <div className="panel-topline"><p className="eyebrow">06 / LOCAL GEOMETRY</p><span className="small-label">Layout incomplete</span></div>
      <h2 id="runway-map-heading">Runway map</h2>
      <UnsupportedLayout reason="The source layout does not provide a usable runway and protected-area geometry. No replacement geometry was drawn." />
    </section>
  }

  const view = extent(bounds)
  const staleCount = snapshot.tracks.filter((track) => track.stale).length
  const observedCount = snapshot.tracks.length - staleCount

  return (
    <section className="panel runway-map-panel" aria-labelledby="runway-map-heading">
      <div className="panel-topline"><p className="eyebrow">06 / LOCAL GEOMETRY</p><span className="small-label">SVG · {snapshot.layout.coordinate_system}</span></div>
      <div className="section-heading-row">
        <div><h2 id="runway-map-heading">{snapshot.layout.name}</h2><p className="muted">{snapshot.layout.physical_runway_id} · layout {snapshot.layout.id} v{snapshot.layout.version}</p></div>
        <span className="map-frame-time">Frame {sessionTime(snapshot.sim_ms)}</span>
      </div>

      {frameState.state === 'disconnected' && (
        <p className="context-notice state-disconnected" role="status">
          {frameState.message} The map retains this frame and applies no position extrapolation.
        </p>
      )}

      <div className="map-canvas-wrap">
        <svg className="runway-map-svg" viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`} role="img" aria-labelledby="runway-map-title runway-map-description">
          <title id="runway-map-title">{snapshot.layout.name} runway layout and track positions</title>
          <desc id="runway-map-description">Layout geometry is plotted in local metres. Observed and stale last-known tracks are separately labeled. Predicted timing is shown in the runway board, not projected onto this map.</desc>
          <defs>
            <pattern id="runway-grid" width="25" height="25" patternUnits="userSpaceOnUse">
              <path d="M 25 0 L 0 0 0 25" fill="none" stroke="#263435" strokeWidth=".7" />
            </pattern>
          </defs>
          <rect width={SVG_WIDTH} height={SVG_HEIGHT} fill="url(#runway-grid)" />
          {snapshot.layout.protected_area.length >= 3 && <polygon className="map-protected-area" points={pointsAttribute(snapshot.layout.protected_area, bounds, view)} />}
          {snapshot.layout.taxiways.map((taxiway, index) => <polyline key={`taxiway-${index}`} className="map-taxiway" points={pointsAttribute(taxiway, bounds, view)} />)}
          {snapshot.layout.runway.length >= 3 && <polygon className="map-runway" points={pointsAttribute(snapshot.layout.runway, bounds, view)} />}
          {snapshot.layout.hold_lines.map((line, index) => <polyline key={`hold-${index}`} className="map-hold-line" points={pointsAttribute(line, bounds, view)} />)}

          {snapshot.tracks.map((track) => {
            const x = toX(track.x_m, bounds, view)
            const y = toY(track.y_m, bounds, view)
            const routePoints: Point[] = [[track.x_m, track.y_m], ...track.route]
            const width = track.length_m * view.scale
            const height = track.width_m * view.scale
            return (
              <g key={track.id} className={track.stale ? 'map-track map-track-last-known' : 'map-track map-track-observed'}>
                {track.route.length > 0 && <polyline className="map-route" points={pointsAttribute(routePoints, bounds, view)} />}
                <g transform={`translate(${x} ${y}) rotate(${-track.heading_deg})`}>
                  <rect x={-width / 2} y={-height / 2} width={width} height={height} rx={track.kind === 'aircraft' ? 2 : 0} className="map-track-footprint" />
                  {track.stale
                    ? <path d={`M ${-width / 2} ${-height / 2} L ${width / 2} ${height / 2} M ${width / 2} ${-height / 2} L ${-width / 2} ${height / 2}`} className="map-track-cross" />
                    : <circle r={Math.max(1.8, 3.2 * view.scale)} className="map-track-center" />}
                </g>
                <text x={x + 7} y={y - 9} className="map-track-label">{track.id} · {track.stale ? 'LAST-KNOWN' : 'OBSERVED'}</text>
              </g>
            )
          })}
          <g className="map-axis-marker" aria-hidden="true">
            <path d="M 42 335 L 98 335 M 42 335 L 42 283" />
            <path d="M 98 335 L 91 331 M 98 335 L 91 339 M 42 283 L 38 290 M 42 283 L 46 290" />
            <text x="102" y="339">+X</text><text x="36" y="276">+Y</text>
          </g>
        </svg>
      </div>

      <div className="map-legend" aria-label="Map symbol legend">
        <span><i className="legend-symbol legend-observed" /> Observed · current sample</span>
        <span><i className="legend-symbol legend-last-known" /> Last-known · stale</span>
        <span><i className="legend-symbol legend-route" /> Declared route</span>
        <span><i className="legend-symbol legend-hold" /> Hold line</span>
      </div>
      <div className="map-meta-row">
        <span>Observed tracks: {observedCount}</span><span>Last-known tracks: {staleCount}</span>
        <span>Layout extent X {bounds.minX}…{bounds.maxX} m · Y {bounds.minY}…{bounds.maxY} m</span>
      </div>
      <div className="layout-directions">
        <span className="layout-directions-title">Runway direction mapping supplied by layout</span>
        {Object.entries(snapshot.layout.directions).map(([direction, resource]) => <span key={direction}><strong>{direction}</strong> → {resource}</span>)}
        <small>Axes use local coordinates; the layout does not provide a true-north bearing.</small>
      </div>

      <div className="track-data-list">
        {snapshot.tracks.map((track) => (
          <article className={`track-data-row ${track.stale ? 'is-last-known' : ''}`} key={track.id}>
            <div className="track-data-heading"><strong>{track.callsign} · {track.id}</strong><span>{track.stale ? 'LAST-KNOWN · STALE' : 'OBSERVED'}</span></div>
            <p>{track.kind} · {track.phase} · footprint {track.length_m} × {track.width_m} m · speed {track.speed_mps} m/s · heading {track.heading_deg}° · runway {track.runway} · owner {track.owner}</p>
            <p>Sample {sessionTime(track.observed_ms)} · received {sessionTime(track.received_ms)} · {track.source} · event {track.event_id}</p>
          </article>
        ))}
      </div>
      {snapshot.layout.note && <p className="layout-note">Layout note: {snapshot.layout.note}</p>}
      {frame?.state === 'disconnected' && <p className="disconnected-frame-note" role="status">Disconnected · showing the last committed frame. No extrapolation is applied.</p>}
    </section>
  )
}
