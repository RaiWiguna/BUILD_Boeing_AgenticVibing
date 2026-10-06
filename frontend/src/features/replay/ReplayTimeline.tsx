import { useEffect, useState } from 'react'
import type {
  AsyncState,
  EventReadModel,
  EvidenceRef,
  ReplayFrameReadModel,
  ReviewAnnotationReadModel,
  TranscriptReadModel,
} from '../../contracts/replayReview'

interface ReplayTimelineProps {
  sourceSessionId: string
  frame: ReplayFrameReadModel | null
  events: AsyncState<EventReadModel[]>
  transcript: AsyncState<TranscriptReadModel>
  annotations: ReviewAnnotationReadModel[]
  requestedMs: number
  rangeEndMs: number
  disabled: boolean
  onSeek: (timeMs: number) => void
  selectedRef?: EvidenceRef | null
}

type TimelineLane = {
  id: string
  label: string
  items: EventReadModel[]
  empty: string
}

function timeLabel(value: number): string {
  const seconds = value / 1000
  return `${seconds.toFixed(3)} s · ${Math.round(value)} ms`
}

function eventLaneId(event: EventReadModel): string {
  const kind = event.type.toUpperCase()
  if (kind === 'TRACK') return 'track'
  if (kind === 'CLEARANCE' || kind.includes('CLEARANCE') || kind.startsWith('CLR')) return 'clearance'
  if (kind.startsWith('ALERT')) return 'alert'
  return 'source'
}

function eventAvailableMs(event: EventReadModel): number {
  return event.received_ms ?? event.sim_ms
}

function stateCopy(state: AsyncState<unknown>, empty: string): string | null {
  if (state.state === 'loading') return 'Loading through the replay adapter…'
  if (state.state === 'empty') return empty
  if (state.state === 'ready' || state.state === 'degraded') return null
  return state.message
}

export function ReplayTimeline({
  sourceSessionId, frame, events, transcript, annotations, requestedMs, rangeEndMs, disabled, onSeek, selectedRef = null,
}: ReplayTimelineProps) {
  const [draftMs, setDraftMs] = useState(requestedMs)
  useEffect(() => setDraftMs(requestedMs), [requestedMs])
  const eventItems = events.state === 'ready' || events.state === 'degraded' ? events.data : []
  const visibleEvents = eventItems.filter((event) => eventAvailableMs(event) <= requestedMs)
  const lanes: TimelineLane[] = [
    { id: 'source', label: 'SOURCE / COMMUNICATION', items: [], empty: 'No source communication or other source event by this selected time.' },
    { id: 'clearance', label: 'STRUCTURED CLEARANCE', items: [], empty: 'No recorded clearance by this selected time.' },
    { id: 'track', label: 'TRACK OBSERVATION', items: [], empty: 'No TRACK sample by this selected time.' },
    { id: 'alert', label: 'DETERMINISTIC ALERT', items: [], empty: 'No deterministic alert transition by this selected time.' },
  ]
  for (const item of visibleEvents) {
    const lane = lanes.find((candidate) => candidate.id === eventLaneId(item))
    lane?.items.push(item)
  }

  const transcriptModel = transcript.state === 'ready' || transcript.state === 'degraded' || transcript.state === 'unavailable'
    ? transcript.data
    : transcript.state === 'empty' ? transcript.data ?? null : null
  const segments = transcriptModel?.items ?? []
  const alignedSegments = segments.filter((segment) => {
    const availableAt = segment.session_end_ms ?? segment.session_start_ms
    return segment.session_start_ms !== undefined && segment.session_start_ms !== null && availableAt !== undefined && availableAt !== null && availableAt <= requestedMs
  })
  const unalignedSegments = segments.filter((segment) => segment.session_start_ms === undefined || segment.session_start_ms === null)
  const mappedAnnotations = annotations.filter((annotation) => annotation.session_ms !== undefined && annotation.session_ms !== null && annotation.session_ms <= requestedMs)
  const unalignedAnnotations = annotations.filter((annotation) => annotation.session_ms === undefined || annotation.session_ms === null)
  const endMs = Math.max(1, rangeEndMs, frame?.frame_ms ?? 0)
  const eventStateMessage = stateCopy(events, 'The source has no event records.')
  const transcriptStateMessage = stateCopy(transcript, 'No transcript records are available.')

  return (
    <section className="panel replay-timeline-panel" aria-labelledby="replay-timeline-heading">
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">06 / REPLAY TIMELINE</p>
          <h2 id="replay-timeline-heading">Selected replay time</h2>
          <p className="muted">Historical evidence is shown only through the requested session time. Event history is paged by the active adapter.</p>
        </div>
        <span className="small-label">{sourceSessionId || 'No source selected'}</span>
      </div>

      <div className="timeline-scrubber">
        <label htmlFor="replay-time-range">Requested time · {timeLabel(requestedMs)}</label>
        <input
          id="replay-time-range"
          aria-label="Seek requested replay time in session milliseconds"
          type="range"
          min={0}
          max={endMs}
          step={1}
          value={Math.min(draftMs, endMs)}
          disabled={disabled || !frame}
          onChange={(event) => setDraftMs(Number(event.target.value))}
        />
        <button className="button button-primary timeline-seek-button" type="button" disabled={disabled || !frame || draftMs === requestedMs} onClick={() => onSeek(draftMs)}>Seek to {draftMs} ms</button>
        <div className="timeline-range-labels"><span>0 ms session</span><span>{endMs} ms replay end</span></div>
      </div>

      {eventStateMessage && <div className={`state-message ${events.state === 'loading' ? '' : `state-${events.state}`}`} role={events.state === 'loading' ? 'status' : 'alert'}>{events.state === 'loading' && <span className="spinner" />}{eventStateMessage}</div>}
      {events.state === 'degraded' && <p className="state-message">{events.message}</p>}

      <div className="timeline-lanes" aria-label="Replay evidence lanes">
        {lanes.map((lane) => (
          <div className="timeline-lane" key={lane.id}>
            <h3>{lane.label}<small>{lane.items.length} visible</small></h3>
            {lane.items.length ? (
              <ol>
                {lane.items.map((item) => (
                  <li key={item.id} id={`timeline-ref-session_event-${item.id}`}>
                    <button className={`timeline-event timeline-event-${lane.id} ${selectedRef?.kind === 'session_event' && selectedRef.id === item.id ? 'is-evidence-selected' : ''}`} type="button" disabled={disabled} onClick={() => onSeek(eventAvailableMs(item))}>
                      <time aria-label={`Event available at session ${eventAvailableMs(item)} milliseconds`}>{timeLabel(eventAvailableMs(item))}</time>
                      <span><strong>{item.type.replaceAll('_', ' ')} · #{item.ordinal}</strong><small>{item.message}</small></span>
                      {item.target && <code>{item.target}</code>}
                      {item.type === 'TRACK' && item.observed_ms !== undefined && item.received_ms !== undefined
                        ? <em>sample {item.observed_ms} ms · received {item.received_ms} ms</em>
                        : item.received_ms !== undefined && item.received_ms !== item.sim_ms
                          ? <em>event sim {item.sim_ms} ms · received {item.received_ms} ms</em>
                          : null}
                    </button>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="timeline-empty">{events.state === 'ready' || events.state === 'degraded' ? lane.empty : 'Waiting for event history state.'}</p>
            )}
          </div>
        ))}

        <div className="timeline-lane" data-lane="transcript">
          <h3>TRANSCRIPT<small>{alignedSegments.length} time aligned</small></h3>
          {alignedSegments.length ? (
            <ol>{alignedSegments.map((segment) => (
              <li key={segment.id} id={`timeline-ref-transcript_segment-${segment.id}`}>
                <button className={`timeline-event timeline-event-transcript ${selectedRef?.kind === 'transcript_segment' && selectedRef.id === segment.id ? 'is-evidence-selected' : ''}`} type="button" disabled={disabled} onClick={() => onSeek(segment.session_end_ms ?? segment.session_start_ms!)}>
                  <time>{timeLabel(segment.session_start_ms!)}</time>
                  <span><strong>{segment.speaker_label ?? segment.channel_id ?? 'Unknown speaker'}</strong><small>{segment.text}</small></span>
                  <code>{segment.id}</code>
                </button>
              </li>
            ))}</ol>
          ) : (
            <p className="timeline-empty">{transcriptStateMessage ?? 'No mapped transcript segment by this selected time.'}</p>
          )}
          {transcriptModel?.message && <p className="timeline-caveat">{transcriptModel.message}</p>}
          {unalignedSegments.length > 0 && (
            <div className="timeline-unmapped">
              <strong>SESSION ALIGNMENT UNKNOWN · SHOWN OUTSIDE THE TIMELINE</strong>
              {unalignedSegments.map((segment) => (
                <p key={segment.id}><code>{segment.id}</code> · audio-relative {segment.start_ms}–{segment.end_ms} ms · {segment.text}</p>
              ))}
            </div>
          )}
        </div>

        <div className="timeline-lane" data-lane="annotation">
          <h3>REVIEWER ANNOTATION<small>{mappedAnnotations.length} session aligned</small></h3>
          {mappedAnnotations.length ? (
            <ol>{mappedAnnotations.map((annotation, index) => (
              <li key={annotation.id ?? `${annotation.target_id}-${annotation.revision ?? index}`}>
                <div className="timeline-annotation">
                  <time>{timeLabel(annotation.session_ms!)}</time>
                  <span>
                    <strong>{annotation.kind === 'assessment'
                      ? `ASSESSMENT · ${annotation.assessment_type ?? 'unspecified'}`
                      : `${annotation.decision?.toUpperCase() ?? 'REVIEW'} · ${annotation.target_id ?? 'target not supplied'}`}</strong>
                    <small>{annotation.kind === 'assessment'
                      ? annotation.text || JSON.stringify(annotation.values ?? {})
                      : annotation.correction ?? annotation.reason ?? 'No annotation detail supplied.'} · {annotation.reviewer}</small>
                  </span>
                </div>
              </li>
            ))}</ol>
          ) : (
            <p className="timeline-empty">{annotations.length === 0 ? 'No reviewer annotations are available.' : 'Annotation session time is not supplied.'}</p>
          )}
          {unalignedAnnotations.length > 0 && (
            <div className="timeline-unmapped">
              <strong>SESSION ALIGNMENT UNKNOWN · AUDIT TIME ONLY</strong>
              {unalignedAnnotations.map((annotation, index) => (
                <p key={annotation.id ?? `${annotation.target_id ?? annotation.assessment_type ?? 'annotation'}-${index}`}>
                  <code>{annotation.id ?? annotation.target_id ?? annotation.assessment_type ?? 'review annotation'}</code>
                  {' · '}{annotation.kind === 'assessment'
                    ? `${annotation.assessment_type}: ${annotation.text || JSON.stringify(annotation.values ?? {})}`
                    : `${annotation.decision ?? 'review'}: ${annotation.correction ?? annotation.reason ?? 'No annotation detail supplied.'}`}
                  {' · '}{annotation.reviewer}
                  {annotation.timestamp !== undefined && <> · audit timestamp {annotation.timestamp}</>}
                </p>
              ))}
            </div>
          )}
        </div>
      </div>
      <p className="timeline-footer">Actual frame {frame?.frame_ms ?? '—'} ms · requested {requestedMs} ms · playback {frame?.snapshot?.playback_ms ?? '—'} ms</p>
    </section>
  )
}
