import type {
  AssistReviewReadModel,
  AsyncState,
  EventReadModel,
  EvidenceRef,
  EvidenceResolution,
  ReplayFrameReadModel,
  ReplaySourceReadModel,
  ReviewAnnotationReadModel,
  TranscriptReadModel,
} from '../../contracts/replayReview'

function key(ref: EvidenceRef): string {
  return `${ref.kind}:${ref.id}`
}

function openText(ref: EvidenceRef, resolutions: Map<string, EvidenceResolution>): string {
  const item = resolutions.get(key(ref))
  if (item?.state === 'unavailable') return 'UNAVAILABLE'
  if (item?.state === 'unresolved') return 'UNRESOLVED'
  if (item?.state === 'resolved') return 'Open exact reference'
  return 'Resolve exact reference'
}

function reviewAnnotationLine(item: ReviewAnnotationReadModel, index: number): string {
  const decision = item.decision ? `${item.decision} · ` : ''
  const detail = item.correction ?? item.reason ?? item.text ?? 'No annotation detail supplied.'
  const audit = item.timestamp === undefined ? '' : ` · reviewer timestamp ${item.timestamp}`
  const sim = item.session_ms === null || item.session_ms === undefined ? '' : ` · ${item.session_ms} ms SIM`
  return `${item.id ?? `annotation-${index}`} · ${decision}${item.target_id ?? item.assessment_type ?? 'target unavailable'} · ${item.reviewer} · ${detail}${audit}${sim}`
}

export function DebriefPanel({
  mode, source, frame, events, transcript, assist, annotations, resolutions, onSelectEvidence,
}: {
  mode: 'fixture' | 'api'
  source: AsyncState<ReplaySourceReadModel>
  frame: ReplayFrameReadModel | null
  events: AsyncState<EventReadModel[]>
  transcript: AsyncState<TranscriptReadModel>
  assist: AsyncState<AssistReviewReadModel>
  annotations: ReviewAnnotationReadModel[]
  resolutions: Map<string, EvidenceResolution>
  onSelectEvidence: (ref: EvidenceRef) => void
}) {
  const sourceData = source.state === 'ready' || source.state === 'degraded' ? source.data : null
  const assistData = assist.state === 'ready' || assist.state === 'degraded' || assist.state === 'unavailable' ? assist.data : null
  const factEvents = events.state === 'ready' || events.state === 'degraded'
    ? events.data.filter((event) => !['TRACK', 'ASSESSMENT', 'REVIEW_ANNOTATION'].includes(event.type.toUpperCase()))
    : []
  const transcriptData = transcript.state === 'ready' || transcript.state === 'degraded' ? transcript.data : null
  const unknownRefs = [...resolutions.values()].filter((item) => item.state === 'unresolved' || item.state === 'unavailable')
  const unknownSegments = transcriptData?.items.filter((item) => item.alignment_state === 'unknown') ?? []
  const allAnnotations = [...annotations, ...(assistData?.review_annotations ?? [])]
  const uniqueAnnotations = [...new Map(allAnnotations.map((item, index) => [item.id ?? `${item.target_id ?? item.assessment_type}-${item.revision ?? index}`, item])).values()]
  const analysis = assistData?.analysis
  const optionCandidates = assistData?.evaluator_access === 'granted' && assistData.candidates.state === 'ready' && assistData.candidates.evaluator_access === 'granted'
    ? assistData.candidates.items
    : []
  const optionCount = optionCandidates.length

  return (
    <section className="panel assist-panel debrief-panel" aria-labelledby="debrief-panel-heading">
      <div className="panel-topline"><p className="eyebrow">11 / DEBRIEF</p><span className="small-label">PROVENANCE + LIMITS</span></div>
      <div className="section-heading-row"><div><h2 id="debrief-panel-heading">Evidence debrief</h2><p className="muted">Source facts, candidate interpretations, unknowns and reviewer annotations are separated below.</p></div><span className={`mode-pill mode-${mode}`}>{mode === 'fixture' ? 'FIXTURE DEBRIEF' : 'API DEBRIEF'}</span></div>
      {mode === 'fixture' && <p className="fixture-disclaimer">Authored synthetic examples only · not ASR output, partner replay, server results, domain review, or operational evidence.</p>}

      <div className="debrief-provenance-grid">
        <div><span className="micro-label">SOURCE</span><strong>{sourceData?.label ?? 'Unavailable'}</strong><small>{sourceData?.provenance ?? 'No scoped replay-source manifest is available.'}</small><small>Source version: {sourceData?.source_version ?? frame?.snapshot?.source_version ?? 'Unavailable'}</small></div>
        <div><span className="micro-label">ANALYSIS</span><strong>{analysis?.id ?? 'Unavailable'}</strong><small>Model: {analysis?.model_version ?? 'Unavailable'} · rule: {analysis?.rule_version ?? 'Unavailable'}</small><small>Window: {analysis?.window_start_ms === null || analysis?.window_start_ms === undefined || analysis?.window_end_ms === null || analysis?.window_end_ms === undefined ? 'Unavailable' : `${analysis.window_start_ms}–${analysis.window_end_ms} ms SIM`}</small><small>Input hash: {analysis?.input_hash ?? 'Unavailable'} · transcript revision basis: {analysis?.transcript_revision_basis ?? 'Unavailable'}</small></div>
        <div><span className="micro-label">PROVIDER STATUS</span><strong>{assistData?.provider_availability === 'unavailable' ? 'Unavailable' : assistData?.provider_availability === 'available' ? 'Available' : 'Unknown'}</strong><small>{assistData?.message ?? (assist.state === 'unavailable' ? assist.message : 'Provider/job state was not supplied.')}</small><small>Evaluator capability: {assistData?.evaluator_access ?? 'Unknown'}</small></div>
      </div>

      <div className="debrief-section source-facts">
        <h3>Source facts</h3>
        {factEvents.length ? <ul>{factEvents.map((event) => {
          const ref: EvidenceRef = { kind: 'session_event', id: event.id }
          return <li key={event.id}><span className="debrief-kind">Source event · {event.sim_ms} ms SIM</span><p>{event.type}: {event.message}</p><button type="button" className="debrief-link" onClick={() => onSelectEvidence(ref)}>{openText(ref, resolutions)} · {event.id}</button></li>
        })}</ul> : <p className="assist-empty">{events.state === 'unavailable' ? events.message : 'No source event facts are available in this read model.'}</p>}
        {frame?.snapshot?.alerts.map((alert) => {
          const ref: EvidenceRef = { kind: 'detector_alert', id: alert.id }
          return <div className="debrief-source-alert" key={alert.id}><span className="debrief-kind">Source alert · {alert.id}</span><p>{alert.rule} · {alert.status} · supplied severity {alert.severity}</p><button type="button" className="debrief-link" onClick={() => onSelectEvidence(ref)}>{openText(ref, resolutions)} · detector_alert:{alert.id}</button><small>Severity and lifecycle are source read-model values; assist review does not alter them.</small></div>
        })}
      </div>

      <div className="debrief-section candidate-summary">
        <h3>Candidate outputs</h3>
        {assistData?.evaluator_access === 'granted' ? (
          <>
            {assistData.highlights.map((highlight) => <div key={highlight.id} className="debrief-candidate"><span className="debrief-kind">Highlight · {highlight.id} · {highlight.link_status ?? 'unresolved'}</span><p>{highlight.statement}</p><small>Provider {highlight.provider_version} · rule {highlight.rule_version} · status {highlight.status}</small>{highlight.transcript_segment_ids.map((id) => { const ref: EvidenceRef = { kind: 'transcript_segment', id }; return <button className="debrief-link" key={id} onClick={() => onSelectEvidence(ref)}>{openText(ref, resolutions)} · transcript_segment:{id}</button> })}{highlight.session_event_ids.map((id) => { const ref: EvidenceRef = { kind: 'session_event', id }; return <button className="debrief-link" key={id} onClick={() => onSelectEvidence(ref)}>{openText(ref, resolutions)} · session_event:{id}</button> })}</div>)}
            {optionCandidates.map((candidate) => <div key={candidate.id} className="debrief-candidate"><span className="debrief-kind">Evaluator option candidate · {candidate.id} · {candidate.review_status}</span><p>{candidate.statement}</p>{candidate.rationale && <small>{candidate.rationale}</small>}<small>Source {candidate.source_version ?? 'unknown'} · model {candidate.model_version ?? 'unknown'} · rule {candidate.rule_version ?? 'unknown'}</small>{candidate.supporting_evidence.map((ref) => <button className="debrief-link" key={key(ref)} onClick={() => onSelectEvidence(ref)}>{openText(ref, resolutions)} · {ref.kind}:{ref.id}</button>)}</div>)}
            <p className="debrief-count">{optionCount} evaluator-only option candidate{optionCount === 1 ? '' : 's'} shown. No operational action is available.</p>
          </>
        ) : <p className="assist-empty">Candidate outputs are unavailable or evaluator access was not granted; no options are included in this debrief.</p>}
      </div>

      <div className="debrief-section debrief-unknowns">
        <h3>Unknown / unavailable</h3>
        <ul>
          {unknownSegments.map((segment) => <li key={segment.id}>Transcript <code>{segment.id}</code> remains audio-relative {segment.start_ms}–{segment.end_ms} ms; replay alignment is unknown.</li>)}
          {transcriptData?.items.filter((item) => item.speaker_confidence === null || item.asr_confidence === null).map((segment) => <li key={`confidence-${segment.id}`}>Transcript <code>{segment.id}</code> has unavailable speaker/ASR confidence; no zero or calibrated value is inferred.</li>)}
          {unknownRefs.map((item) => <li key={key(item.ref)}>{item.state.toUpperCase()} · {item.ref.kind}:{item.ref.id} {item.summary ?? ''}</li>)}
          {assist.state === 'unavailable' && <li>Assist routes or scoped data are unavailable: {assist.message}</li>}
          {analysis?.window_start_ms == null || analysis?.window_end_ms == null ? <li>Analysis range is unavailable; no full-session conclusion is implied.</li> : null}
          {sourceData?.source_version == null && <li>Source version/provenance manifest is unavailable.</li>}
          {unknownSegments.length === 0 && unknownRefs.length === 0 && assist.state !== 'unavailable' && analysis?.window_start_ms != null ? <li>No additional unknown reference has been selected in this debrief view.</li> : null}
        </ul>
      </div>

      <div className="debrief-section reviewer-notes">
        <h3>Reviewer annotations</h3>
        {uniqueAnnotations.length ? <ul>{uniqueAnnotations.map((item, index) => <li key={item.id ?? `${item.target_id}-${index}`}>{reviewAnnotationLine(item, index)}</li>)}</ul> : <p className="assist-empty">No reviewer annotations are supplied.</p>}
        <p className="time-separation-note">Reviewer timestamps are audit/server timestamps when supplied; they are not converted to session time. Unknown session alignment remains unknown.</p>
      </div>

      <div className="debrief-usage-limit"><strong>Use boundary</strong><p>Offline replay/evaluation only. This panel is not for an active controller position, live feed, audio capture, clearance, or operational recommendation. Reviewer conclusions require domain review; operational validation is not established.</p><p>Export unavailable: the current report route is instructor-only and can contain restricted ground truth. No participant-safe assist export route is present.</p></div>
    </section>
  )
}
