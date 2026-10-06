import type { AsyncState, EvidenceRef, TranscriptReadModel } from '../../contracts/replayReview'
import { ReviewEditor } from './ReviewEditor'

function confidence(value: number | null | undefined): string {
  return value === null || value === undefined ? 'Unavailable' : `${(value * 100).toFixed(0)}% · uncalibrated`
}

function selected(ref: EvidenceRef | null, id: string): boolean {
  return ref?.kind === 'transcript_segment' && ref.id === id
}

export function TranscriptPanel({
  mode, sourceSessionId, transcript, evaluatorAccess, selectedRef, selectionMessage, onSelectEvidence, onCorrect, onRefresh,
}: {
  mode: 'fixture' | 'api'
  sourceSessionId: string
  transcript: AsyncState<TranscriptReadModel>
  evaluatorAccess: 'granted' | 'denied' | 'unknown'
  selectedRef: EvidenceRef | null
  selectionMessage?: string
  onSelectEvidence: (ref: EvidenceRef) => void
  onCorrect: (segmentId: string, expectedRevision: number, text: string, reason: string, requestId: string) => Promise<import('../../contracts/replayReview').ReviewReceipt>
  onRefresh: () => Promise<void>
}) {
  const data = transcript.state === 'ready' || transcript.state === 'degraded' || transcript.state === 'unavailable'
    ? transcript.data
    : transcript.state === 'empty' ? transcript.data ?? null : null
  const items = data?.items ?? []
  const message = transcript.state === 'loading' ? 'Loading transcript through the replay adapter…'
    : transcript.state === 'empty' ? data?.message ?? 'No transcript records are available.'
      : transcript.state === 'ready' || transcript.state === 'degraded' ? data?.message
        : transcript.message

  return (
    <section className="panel assist-panel transcript-panel" aria-labelledby="transcript-panel-heading">
      <div className="panel-topline"><p className="eyebrow">09 / TRANSCRIPT PROVENANCE</p><span className={`small-label ${mode === 'fixture' ? 'fixture-text' : ''}`}>{mode === 'fixture' ? 'AUTHORED SYNTHETIC FIXTURE' : 'SCOPED API READ'}</span></div>
      <div className="section-heading-row">
        <div><h2 id="transcript-panel-heading">Transcript revisions</h2><p className="muted">Raw source text and reviewer revisions remain separate; audio-relative timestamps are never treated as replay time without a mapping.</p></div>
        <span className="small-label">{items.length} segment{items.length === 1 ? '' : 's'}</span>
      </div>
      {message && <p className={`assist-panel-message state-${transcript.state}`} role={transcript.state === 'error' || transcript.state === 'unauthorized' ? 'alert' : 'status'}>{message}</p>}
      {mode === 'fixture' && <p className="fixture-disclaimer">Fixture only · these are authored examples. No ASR ran, no partner source is present, and confidence values are not calibrated.</p>}
      {items.length === 0 ? (
        <p className="assist-empty">Transcript content is unavailable in this view. Existing replay context remains separate.</p>
      ) : (
        <div className="transcript-segment-list">
          {items.map((segment) => {
            const revisionIsCorrected = /corrected/i.test(segment.correction_status ?? '')
            const rawSourceText = segment.raw_text ?? (revisionIsCorrected ? null : segment.text)
            const hasRevision = rawSourceText !== null && rawSourceText !== segment.text
            const segmentRef: EvidenceRef = { kind: 'transcript_segment', id: segment.id }
            const isSelected = selected(selectedRef, segment.id)
            return (
              <article className={`transcript-segment ${isSelected ? 'is-evidence-selected' : ''}`} id={`transcript-${segment.id}`} key={segment.id} tabIndex={-1}>
                <div className="assist-card-heading">
                  <div><span className="assist-id">{segment.id}</span><h3>{segment.channel_id ?? 'Channel unknown'} · {segment.speaker_label ?? 'Speaker unknown'}</h3></div>
                  <span className={`correction-badge correction-${(segment.correction_status ?? 'unknown').toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}>{segment.correction_status ?? 'status unavailable'}</span>
                </div>
                <div className="transcript-text-columns">
                  <div><span className="micro-label">{mode === 'fixture' ? 'AUTHORED RAW TEXT · NOT ASR' : 'RAW ASR SOURCE TEXT'}</span><p>{rawSourceText ?? 'Raw source text is unavailable in this scoped read model; no substitute is inferred.'}</p></div>
                  <div><span className="micro-label">CURRENT REVISION · r{segment.revision ?? 'unknown'}</span><p>{segment.text}</p></div>
                </div>
                {hasRevision && <p className="revision-note">Correction is an append-only reviewer revision. The raw text above is retained.</p>}
                <dl className="assist-meta-grid">
                  <div><dt>Asset time</dt><dd>{segment.start_ms}–{segment.end_ms} ms · {segment.timebase}</dd></div>
                  <div><dt>Session alignment</dt><dd>{segment.alignment_state === 'mapped' && segment.session_start_ms !== null && segment.session_start_ms !== undefined ? `${segment.session_start_ms} ms SIM` : 'UNKNOWN · not placed on replay timeline'}</dd></div>
                  <div><dt>Speaker provenance</dt><dd>{segment.speaker_source ?? 'Unavailable'} · {confidence(segment.speaker_confidence)}</dd></div>
                  <div><dt>ASR confidence</dt><dd>{confidence(segment.asr_confidence)}</dd></div>
                  <div><dt>Language</dt><dd>{segment.language ?? 'Unavailable'}</dd></div>
                  <div><dt>Model / provider version</dt><dd>{segment.model_version ?? 'Unavailable'}</dd></div>
                  <div><dt>Asset ID</dt><dd><code>{segment.asset_id ?? 'Unavailable'}</code></dd></div>
                  <div><dt>Revision basis</dt><dd>segment {segment.id} · r{segment.revision ?? 'unknown'}</dd></div>
                </dl>
                <button className={`evidence-select-button ${isSelected ? 'selected' : ''}`} type="button" onClick={() => onSelectEvidence(segmentRef)}>
                  {isSelected ? 'Selected exact transcript reference' : 'Open exact transcript reference'} · {segment.id}
                </button>
                {isSelected && selectionMessage && <p className="evidence-context-note">{selectionMessage}</p>}
                {evaluatorAccess === 'granted' ? (
                  <ReviewEditor
                    targetId={segment.id}
                    expectedRevision={segment.revision}
                    initialText={segment.text}
                    correction
                    onSubmit={(_decision, text, reason, requestId) => segment.revision === null
                      ? Promise.resolve({ request_id: requestId, revision: 0, status: 'unavailable', message: 'No source revision was supplied; no correction request was sent.' })
                      : onCorrect(segment.id, segment.revision, text, reason, requestId)}
                    onRefresh={onRefresh}
                  />
                ) : (
                  <p className="assist-empty">Correction editor unavailable: evaluator review scope is {evaluatorAccess}. No correction request was sent.</p>
                )}
              </article>
            )
          })}
        </div>
      )}
      {data?.job && <p className="job-state">Job {data.job.id} · {data.job.status} · provider {data.job.provider ?? 'unknown'} · model {data.job.model ?? data.job.version ?? 'unknown'}</p>}
      <p className="assist-scope-note">Source {sourceSessionId || 'not selected'} · session time, audio time, and audit time remain separate.</p>
    </section>
  )
}
