import type { AssistReviewReadModel, EvidenceRef, EvidenceResolution, ReviewReceipt } from '../../contracts/replayReview'
import type { AsyncState } from '../../contracts/replayReview'
import { ReviewEditor } from './ReviewEditor'

function evidenceKey(ref: EvidenceRef): string {
  return `${ref.kind}:${ref.id}`
}

function resolutionLabel(resolution: EvidenceResolution | undefined, relation?: 'linked' | 'possible_link'): string {
  if (resolution?.state === 'unavailable') return 'unavailable'
  if (resolution?.state === 'unresolved') return 'unresolved'
  if (resolution?.state === 'resolved') return relation === 'possible_link' ? 'possible_link' : resolution.link_status ?? relation ?? 'linked'
  return relation ?? 'unresolved'
}

function highlightRefs(item: AssistReviewReadModel['highlights'][number]): EvidenceRef[] {
  const refs: EvidenceRef[] = [
    ...item.transcript_segment_ids.map((id): EvidenceRef => ({ kind: 'transcript_segment', id })),
    ...item.session_event_ids.map((id): EvidenceRef => ({ kind: 'session_event', id })),
  ]
  if (item.linked_alert_id) refs.push({ kind: 'detector_alert', id: item.linked_alert_id })
  return refs
}

function LinkList({ refs, relation, selectedRef, resolutions, onSelect }: {
  refs: EvidenceRef[]
  relation?: 'linked' | 'possible_link'
  selectedRef: EvidenceRef | null
  resolutions: Map<string, EvidenceResolution>
  onSelect: (ref: EvidenceRef, relation?: 'linked' | 'possible_link') => void
}) {
  if (refs.length === 0) return <p className="assist-empty">No typed evidence references supplied.</p>
  return (
    <ul className="assist-link-list">
      {refs.map((ref) => {
        const current = selectedRef?.kind === ref.kind && selectedRef.id === ref.id
        const state = resolutionLabel(resolutions.get(evidenceKey(ref)), relation)
        return (
          <li key={evidenceKey(ref)}>
            <button id={`evidence-${ref.kind}-${ref.id}`} className={`evidence-select-button ${current ? 'selected' : ''}`} type="button" onClick={() => onSelect(ref, relation)}>
              <span className={`evidence-relation relation-${state}`}>{state.replaceAll('_', ' ')}</span>
              <span><code>{ref.kind}</code> · <strong>{ref.id}</strong></span>
              {current && <small>Selected · {resolutions.get(evidenceKey(ref))?.summary ?? 'resolving this exact reference'}</small>}
            </button>
          </li>
        )
      })}
    </ul>
  )
}

export function CandidatePanel({
  mode, sourceSessionId, state, selectedRef, resolutions, selectionMessage,
  onSelectEvidence, onReviewHighlight, onReviewCandidate, onRefresh,
}: {
  mode: 'fixture' | 'api'
  sourceSessionId: string
  state: AsyncState<AssistReviewReadModel>
  selectedRef: EvidenceRef | null
  resolutions: Map<string, EvidenceResolution>
  selectionMessage?: string
  onSelectEvidence: (ref: EvidenceRef, relation?: 'linked' | 'possible_link') => void
  onReviewHighlight: (id: string, revision: number, decision: 'confirmed' | 'dismissed' | 'unresolved', reason: string, requestId: string) => Promise<ReviewReceipt>
  onReviewCandidate: (id: string, analysisId: string, revision: number, decision: 'confirmed' | 'dismissed' | 'unresolved', reason: string, requestId: string) => Promise<ReviewReceipt>
  onRefresh: () => Promise<void>
}) {
  const assist = state.state === 'ready' || state.state === 'degraded' || state.state === 'unavailable' ? state.data : null
  const canReview = assist?.evaluator_access === 'granted'
  const highlights = canReview ? assist.highlights : []
  const candidates = canReview && assist.candidates.evaluator_access === 'granted' && assist.candidates.state !== 'unavailable'
    ? assist.candidates.items
    : []
  const message = state.state === 'loading' ? 'Loading assist review through the replay adapter…'
    : state.state === 'empty' ? 'No assist review records are available.'
      : state.state === 'ready' || state.state === 'degraded' || state.state === 'unavailable' ? assist?.message ?? assist?.candidates.message
        : state.message

  return (
    <section className="panel assist-panel candidate-panel" aria-labelledby="candidate-panel-heading">
      <div className="panel-topline"><p className="eyebrow">10 / EVALUATOR REVIEW</p><span className="small-label">REPLAY CANDIDATES · NO COMMAND PATH</span></div>
      <div className="section-heading-row"><div><h2 id="candidate-panel-heading">Highlights and candidate options</h2><p className="muted">These are candidate review outputs; linked references do not establish truth or operational suitability.</p></div><span className="count-pill">{highlights.length + candidates.length} candidates</span></div>
      {message && <p className={`assist-panel-message state-${state.state}`} role={state.state === 'error' || state.state === 'unauthorized' ? 'alert' : 'status'}>{message}</p>}
      {mode === 'fixture' && <p className="fixture-disclaimer">Authored synthetic fixture · no AI provider, server result, partner data, or operational evidence is represented.</p>}
      {assist?.provider_availability === 'unavailable' && <p className="provider-unavailable" role="status">AI PROVIDER UNAVAILABLE · authored fixture rows remain labeled examples; replay remains usable.</p>}
      {!canReview && state.state !== 'loading' && (
        <div className="assist-empty">Evaluator capability is {assist?.evaluator_access ?? 'unknown'} for this view. No highlights or options are shown.</div>
      )}

      {canReview && (
        <>
          <div className="candidate-group-heading"><h3>Highlights</h3><span>Annotations · not deterministic alert severity</span></div>
          {highlights.length === 0 ? <p className="assist-empty">No highlight rows are available.</p> : (
            <div className="candidate-card-list">
              {highlights.map((highlight) => {
                const refs = highlightRefs(highlight)
                return (
                  <article className="candidate-card" key={highlight.id}>
                    <div className="assist-card-heading"><div><span className="assist-id">{highlight.id} · r{highlight.revision ?? 'unknown'}</span><h3>{highlight.category.replaceAll('_', ' ')}</h3></div><span className="review-status">{highlight.status}</span></div>
                    <p>{highlight.statement}</p>
                    <dl className="assist-meta-grid">
                      <div><dt>Review priority</dt><dd>{highlight.review_priority} · not severity</dd></div>
                      <div><dt>Link state</dt><dd>{highlight.link_status ?? 'unresolved relationship'}</dd></div>
                      <div><dt>Provider version</dt><dd>{highlight.provider_version}</dd></div>
                      <div><dt>Rule version</dt><dd>{highlight.rule_version}</dd></div>
                      <div className="meta-wide"><dt>Uncertainty</dt><dd>{highlight.uncertainty}</dd></div>
                    </dl>
                    <h4>Typed evidence refs</h4>
                    <LinkList refs={refs} relation={highlight.link_status ?? undefined} selectedRef={selectedRef} resolutions={resolutions} onSelect={onSelectEvidence} />
                    {selectedRef && refs.some((ref) => ref.kind === selectedRef.kind && ref.id === selectedRef.id) && selectionMessage && <p className="evidence-context-note">{selectionMessage}</p>}
                    <ReviewEditor
                      targetId={highlight.id}
                      expectedRevision={highlight.revision}
                      onSubmit={(decision, _text, reason, requestId) => highlight.revision === null
                        ? Promise.resolve({ request_id: requestId, revision: 0, status: 'unavailable', message: 'No highlight revision was supplied; no review request was sent.' })
                        : onReviewHighlight(highlight.id, highlight.revision, decision as 'confirmed' | 'dismissed' | 'unresolved', reason, requestId)}
                      onRefresh={onRefresh}
                    />
                  </article>
                )
              })}
            </div>
          )}

          <div className="candidate-group-heading"><h3>Candidate options</h3><span>Evaluator replay view only</span></div>
          {assist.candidates.state === 'unavailable' ? (
            <p className="assist-empty">Options unavailable · {assist.candidates.message ?? 'No scoped analysis route or evaluator result is available.'}</p>
          ) : candidates.length === 0 ? <p className="assist-empty">No candidate options supplied for this analysis.</p> : (
            <div className="candidate-card-list">
              {candidates.map((candidate) => {
                const analysisId = candidate.replay_analysis_id ?? assist.analysis?.id ?? ''
                return (
                  <article className="candidate-card option-card" key={candidate.id}>
                    <div className="assist-card-heading"><div><span className="assist-id">{candidate.id} · r{candidate.revision ?? 'unknown'}</span><h3>Hypothetical option candidate</h3></div><span className="review-status">{candidate.review_status}</span></div>
                    <p className="option-statement">{candidate.statement}</p>
                    {candidate.rationale && <div className="candidate-detail"><h4>Rationale</h4><p>{candidate.rationale}</p></div>}
                    <div className="option-lists"><div><h4>Preconditions</h4><ul>{(candidate.preconditions ?? []).map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul></div><div><h4>Unknowns</h4><ul>{(candidate.unknowns ?? []).map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul></div></div>
                    <dl className="assist-meta-grid">
                      <div><dt>Analysis ID</dt><dd>{analysisId || 'Unavailable'}</dd></div>
                      <div><dt>Source version</dt><dd>{candidate.source_version ?? assist.analysis?.source_version ?? 'Unavailable'}</dd></div>
                      <div><dt>Model version</dt><dd>{candidate.model_version ?? assist.analysis?.model_version ?? 'Unavailable'}</dd></div>
                      <div><dt>Rule version</dt><dd>{candidate.rule_version ?? assist.analysis?.rule_version ?? 'Unavailable'}</dd></div>
                      <div><dt>Analysis window</dt><dd>{assist.analysis?.window_start_ms === null || assist.analysis?.window_start_ms === undefined || assist.analysis?.window_end_ms === null || assist.analysis?.window_end_ms === undefined ? 'Unavailable' : `${assist.analysis.window_start_ms}–${assist.analysis.window_end_ms} ms SIM`}</dd></div>
                    </dl>
                    <h4>Typed supporting evidence refs</h4>
                    <LinkList refs={candidate.supporting_evidence} selectedRef={selectedRef} resolutions={resolutions} onSelect={onSelectEvidence} />
                    {selectedRef && candidate.supporting_evidence.some((ref) => ref.kind === selectedRef.kind && ref.id === selectedRef.id) && selectionMessage && <p className="evidence-context-note">{selectionMessage}</p>}
                    <ReviewEditor
                      targetId={candidate.id}
                      expectedRevision={candidate.revision}
                      onSubmit={(decision, _text, reason, requestId) => candidate.revision === null
                        ? Promise.resolve({ request_id: requestId, revision: 0, status: 'unavailable', message: 'No option revision was supplied; no review request was sent.' })
                        : onReviewCandidate(candidate.id, analysisId, candidate.revision, decision as 'confirmed' | 'dismissed' | 'unresolved', reason, requestId)}
                      onRefresh={onRefresh}
                    />
                  </article>
                )
              })}
            </div>
          )}
        </>
      )}
      <p className="assist-scope-note">Source {sourceSessionId || 'not selected'} · candidate text is data only. No execute, send-clearance, command, severity, or lifecycle action exists here.</p>
    </section>
  )
}
