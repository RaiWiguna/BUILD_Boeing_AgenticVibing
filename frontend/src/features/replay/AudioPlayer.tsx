import { useEffect, useMemo, useRef, useState } from 'react'
import { ApiRequestError } from '../../api'
import type { AsyncState, AudioAssetReadModel, ReplayReviewAdapter, TranscriptReadModel } from '../../contracts/replayReview'

interface AudioPlayerProps {
  adapter: ReplayReviewAdapter
  sourceSessionId: string
  transcript: AsyncState<TranscriptReadModel>
  requestedMs: number
  audioFocus: { asset_id: string; at_ms: number } | null
  disabled: boolean
  onSeek: (timeMs: number) => void
}

function errorState(error: unknown): AsyncState<AudioAssetReadModel> {
  if (error instanceof ApiRequestError) return { state: error.kind, message: error.message }
  if (error instanceof DOMException && error.name === 'AbortError') return { state: 'loading' }
  return { state: 'error', message: error instanceof Error ? error.message : 'Audio asset could not be loaded.' }
}

export function AudioPlayer({ adapter, sourceSessionId, transcript, requestedMs, audioFocus, disabled, onSeek }: AudioPlayerProps) {
  const transcriptData = transcript.state === 'ready' || transcript.state === 'degraded'
    ? transcript.data
    : transcript.state === 'empty' ? transcript.data ?? null : null
  const assetId = useMemo(() => transcriptData?.items.find((item) => item.asset_id)?.asset_id, [transcriptData])
  const [audioState, setAudioState] = useState<AsyncState<AudioAssetReadModel>>({ state: 'empty' })
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    if (!sourceSessionId) {
      setAudioState({ state: 'empty' })
      return
    }
    const controller = new AbortController()
    let active = true
    let loadedAsset: Extract<AudioAssetReadModel, { state: 'ready' }> | null = null
    setAudioState({ state: 'loading' })
    void adapter.loadAudioAsset(sourceSessionId, assetId, controller.signal).then((asset) => {
      if (!active) {
        if (asset.state === 'ready') asset.release()
        return
      }
      if (asset.state === 'ready') {
        loadedAsset = asset
        setAudioState({ state: 'ready', data: asset })
      } else {
        setAudioState({ state: 'unavailable', data: asset, message: asset.message })
      }
    }).catch((error: unknown) => {
      if (active && !(error instanceof DOMException && error.name === 'AbortError')) setAudioState(errorState(error))
    })
    return () => {
      active = false
      controller.abort()
      loadedAsset?.release()
    }
  }, [adapter, assetId, sourceSessionId])

  const audio = audioState.state === 'ready' && audioState.data.state === 'ready' ? audioState.data : null

  useEffect(() => {
    if (!audio || audio.alignment.state !== 'mapped' || !audioRef.current) return
    const positionSeconds = adapter.sessionMsToAudioSeconds(audio.alignment, requestedMs)
    if (positionSeconds !== null && Math.abs(audioRef.current.currentTime - positionSeconds) > 0.15) {
      audioRef.current.currentTime = positionSeconds
    }
  }, [adapter, audio, requestedMs])

  useEffect(() => {
    if (!audio || !audioRef.current || !audioFocus || audio.asset_id !== audioFocus.asset_id) return
    // Asset-relative selection may move audio alone. It never implies a replay/session mapping.
    audioRef.current.currentTime = audioFocus.at_ms / 1000
  }, [audio, audioFocus])

  const stateMessage = audioState.state === 'loading'
    ? 'Checking audio through the replay adapter…'
    : audioState.state === 'empty'
      ? 'No audio asset is available for this source.'
      : audioState.state === 'ready'
        ? null
        : audioState.message

  const alignToAudio = () => {
    if (!audio || audio.alignment.state !== 'mapped' || !audioRef.current) return
    const sessionMs = adapter.audioSecondsToSessionMs(audio.alignment, audioRef.current.currentTime)
    if (sessionMs !== null) onSeek(sessionMs)
  }

  return (
    <section className="panel audio-player-panel" aria-labelledby="audio-player-heading">
      <div className="section-heading-row">
        <div><p className="eyebrow">AUDIO / TRANSCRIPT</p><h2 id="audio-player-heading">Source audio playback</h2><p className="muted">Audio time is asset-relative. Session alignment is shown only when the adapter supplies a mapping.</p></div>
        <span className={`connection-badge ${audio?.alignment.state === 'mapped' ? 'connection-ready' : 'connection-unsupported'}`}>
          {audio?.alignment.state === 'mapped' ? 'SESSION MAPPING AVAILABLE' : 'ALIGNMENT UNKNOWN'}
        </span>
      </div>

      {audio ? (
        <div className="audio-ready-state">
          <p className="audio-alignment-note">
            {audio.alignment.state === 'mapped'
              ? `Mapped: session_ms = audio_ms + ${audio.alignment.offset_ms} ms${audio.alignment.uncertainty_ms === undefined ? '' : ` · uncertainty ${audio.alignment.uncertainty_ms} ms`}.`
              : `Unaligned playback only. ${audio.alignment.reason} Transcript segments remain audio-relative and are not shown as session-synced.`}
          </p>
          {audioFocus && audioFocus.asset_id === audio.asset_id && <p className="audio-alignment-note">Selected evidence at audio-relative {audioFocus.at_ms} ms · replay timeline is unchanged unless the adapter supplies a session mapping.</p>}
          <audio ref={audioRef} controls preload="metadata" src={audio.object_url} aria-label="Replay source audio" />
          <button className="button button-secondary" type="button" onClick={alignToAudio} disabled={disabled || audio.alignment.state !== 'mapped'}>Seek replay to audio position</button>
        </div>
      ) : (
        <div className={`audio-unavailable state-${audioState.state}`} role={audioState.state === 'unauthorized' || audioState.state === 'error' || audioState.state === 'conflict' ? 'alert' : 'status'}>
          {audioState.state === 'loading' && <span className="spinner" />}
          <strong>{audioState.state === 'unauthorized' ? 'Audio access unauthorized' : audioState.state === 'error' ? 'Audio unavailable' : 'Playback unavailable'}</strong>
          <p>{stateMessage}</p>
          {adapter.mode === 'api' && <small>The inspected backend has no private audio asset route or separate source-read credential.</small>}
          {adapter.mode === 'fixture' && <small>Fixture transcript text is authored for layout only; no audio bytes or playback success are supplied.</small>}
        </div>
      )}
      {transcriptData?.message && <p className="audio-alignment-note">{transcriptData.message}</p>}
    </section>
  )
}
