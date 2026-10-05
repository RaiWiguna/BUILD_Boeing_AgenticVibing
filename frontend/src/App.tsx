import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { ApiReplayReviewAdapter } from './adapters/apiReplayReview'
import { FixtureReplayReviewAdapter } from './adapters/fixtureReplayReview'
import type {
  AsyncState,
  DashboardAdapter,
  OperatorAccess,
  OverviewReadModel,
  SessionReadModel,
  SessionViewReadModel,
} from './contracts/replayReview'
import { ApiRequestError } from './api'

const configuredMode = import.meta.env.VITE_FLOWLENS_MODE
const mode: 'fixture' | 'api' = configuredMode === 'api' ? 'api' : 'fixture'
const invalidMode = configuredMode !== undefined && configuredMode !== '' && configuredMode !== 'fixture' && configuredMode !== 'api'

function createAdapter(value: 'fixture' | 'api'): DashboardAdapter {
  return value === 'api' ? new ApiReplayReviewAdapter() : new FixtureReplayReviewAdapter()
}

function errorState(error: unknown): AsyncState<never> {
  if (error instanceof ApiRequestError) return { state: error.kind, message: error.message }
  if (error instanceof DOMException && error.name === 'AbortError') return { state: 'loading' }
  return { state: 'error', message: error instanceof Error ? error.message : 'An unexpected error occurred.' }
}

function formatTime(milliseconds: number): string {
  const totalSeconds = Math.floor(milliseconds / 1000)
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0')
  const seconds = (totalSeconds % 60).toString().padStart(2, '0')
  return `${minutes}:${seconds}`
}

function formatWallTime(milliseconds: number | null): string {
  if (milliseconds === null) return 'fixture clock'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(milliseconds)
}

function StateMessage({ state, emptyLabel }: { state: AsyncState<unknown>; emptyLabel?: string }) {
  if (state.state === 'loading') return <div className="state-message"><span className="spinner" /> Loading from {mode === 'api' ? 'the local API' : 'the inline fixture'}…</div>
  if (state.state === 'empty') return <div className="state-message">{emptyLabel ?? 'No records are available.'}</div>
  if (state.state === 'ready' || state.state === 'degraded') return null
  return <div className={`state-message state-${state.state}`} role="alert">{state.message}</div>
}

function App() {
  const adapter = useMemo(() => createAdapter(mode), [])
  const [overviewState, setOverviewState] = useState<AsyncState<OverviewReadModel>>({ state: 'loading' })
  const [sessionsState, setSessionsState] = useState<AsyncState<SessionReadModel[]>>({ state: mode === 'api' ? 'empty' : 'loading' })
  const [sessionState, setSessionState] = useState<AsyncState<SessionViewReadModel>>({ state: 'empty' })
  const [access, setAccess] = useState<OperatorAccess | null>(null)
  const [operatorKey, setOperatorKey] = useState('')
  const [selectedScenario, setSelectedScenario] = useState('')
  const [selectedSessionId, setSelectedSessionId] = useState('')
  const [busyAction, setBusyAction] = useState<'login' | 'create' | 'refresh' | null>(null)

  const loadOverview = useCallback(async (signal?: AbortSignal) => {
    if (invalidMode) return
    setOverviewState({ state: 'loading' })
    try {
      const overview = await adapter.loadOverview(signal)
      setOverviewState(overview.scenarios.length ? { state: 'ready', data: overview } : { state: 'empty' })
      setSelectedScenario((current) => current || overview.scenarios[0]?.id || '')
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      setOverviewState(errorState(error))
    }
  }, [adapter])

  const loadSessions = useCallback(async (token = '', signal?: AbortSignal) => {
    setSessionsState({ state: 'loading' })
    try {
      const sessions = await adapter.listSessions(token, signal)
      if (sessions.length === 0) {
        setSessionsState({ state: 'empty' })
        setSelectedSessionId('')
        setSessionState({ state: 'empty' })
        return
      }
      setSessionsState({ state: 'ready', data: sessions })
      setSelectedSessionId((current) => sessions.some((item) => item.id === current) ? current : sessions[0].id)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      if (error instanceof ApiRequestError && error.kind === 'unauthorized') setAccess(null)
      setSessionsState(errorState(error))
    }
  }, [adapter])

  const loadSession = useCallback(async (sessionId: string, token = access?.token ?? '') => {
    if (!sessionId) return
    setSelectedSessionId(sessionId)
    setSessionState({ state: 'loading' })
    try {
      const view = await adapter.loadSession(token, sessionId)
      setSessionState({ state: 'ready', data: view })
    } catch (error) {
      if (error instanceof ApiRequestError && error.kind === 'unauthorized') setAccess(null)
      setSessionState(errorState(error))
    }
  }, [adapter, access?.token])

  useEffect(() => {
    if (invalidMode) return
    const controller = new AbortController()
    void loadOverview(controller.signal)
    if (mode === 'fixture') void loadSessions('', controller.signal)
    return () => controller.abort()
  }, [loadOverview, loadSessions])

  useEffect(() => {
    if (invalidMode || !selectedSessionId || (mode === 'api' && !access)) return
    void loadSession(selectedSessionId, access?.token ?? '')
  }, [selectedSessionId, access, loadSession])

  useEffect(() => () => {
    if (adapter instanceof ApiReplayReviewAdapter) adapter.dispose()
  }, [adapter])

  const onLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const key = operatorKey.trim()
    if (key.length < 16) {
      setSessionsState({ state: 'error', message: 'The local operator key must contain at least 16 characters.' })
      return
    }
    setBusyAction('login')
    setOperatorKey('')
    try {
      const newAccess = await adapter.authenticateOperator(key)
      setAccess(newAccess)
      await loadSessions(newAccess.token)
    } catch (error) {
      setSessionsState(errorState(error))
    } finally {
      setBusyAction(null)
    }
  }

  const onCreateSession = async () => {
    if (!access || !selectedScenario) return
    setBusyAction('create')
    try {
      const created = await adapter.createSession(access.token, selectedScenario)
      await loadSessions(access.token)
      setSelectedSessionId(created.id)
      if (selectedSessionId === created.id) await loadSession(created.id, access.token)
    } catch (error) {
      setSessionsState(errorState(error))
    } finally {
      setBusyAction(null)
    }
  }

  const onRefresh = async () => {
    setBusyAction('refresh')
    await loadOverview()
    if (mode === 'fixture') await loadSessions('')
    else if (access) {
      await loadSessions(access.token)
      if (selectedSessionId) await loadSession(selectedSessionId, access.token)
    }
    setBusyAction(null)
  }

  const onSessionChange = (sessionId: string) => {
    setSelectedSessionId(sessionId)
  }

  if (invalidMode) {
    return <main className="config-error"><p className="eyebrow">Configuration error</p><h1>Unsupported frontend mode</h1><p><code>VITE_FLOWLENS_MODE</code> must be <code>fixture</code> or <code>api</code>. The app did not switch to either mode automatically.</p></main>
  }

  const overview = overviewState.state === 'ready' || overviewState.state === 'degraded' ? overviewState.data : null
  const sessions = sessionsState.state === 'ready' ? sessionsState.data : []
  const activeSession = sessionState.state === 'ready' ? sessionState.data : null

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#main" aria-label="ATC FlowLens home">
          <span className="brand-mark" aria-hidden="true"><span /><span /><span /></span>
          <span className="brand-copy"><strong>FLOWLENS</strong><small>ATC REPLAY LAB</small></span>
        </a>
        <div className="topbar-right">
          <span className={`mode-pill mode-${mode}`}><i /> {mode === 'api' ? 'LOCAL API' : 'FIXTURE MODE'}</span>
          <span className="boundary-label">SYNTHETIC TRAINING · NOT OPERATIONAL</span>
        </div>
      </header>

      <main id="main" className="workspace">
        <section className="page-heading">
          <div>
            <p className="eyebrow">FRONTEND FOUNDATION / FE-01</p>
            <h1>Replay review workspace</h1>
            <p className="lede">A typed, adapter-driven shell for local synthetic sessions and offline replay work.</p>
          </div>
          <button className="button button-secondary refresh-button" onClick={() => void onRefresh()} disabled={busyAction !== null}>
            <span className={busyAction === 'refresh' ? 'refresh-glyph spinning' : 'refresh-glyph'} aria-hidden="true">↻</span>
            Refresh data
          </button>
        </section>

        <section className="overview-grid" aria-label="Data source overview">
          <article className="panel runtime-panel">
            <div className="panel-topline"><p className="eyebrow">01 / SOURCE</p><span className="small-label">Explicit mode</span></div>
            <h2>{mode === 'api' ? 'Backend connection' : 'Fixture adapter'}</h2>
            <p className="muted">{overview?.source_label ?? (mode === 'api' ? 'Fetching local backend status and scenario catalogue.' : 'Loading an authored fixture; no backend request is made.')}</p>
            <div className="source-status-row">
              <span className={`status-dot ${overview?.health.state === 'online' ? 'is-online' : mode === 'fixture' ? 'is-fixture' : 'is-waiting'}`} />
              <strong>{overview?.health.state === 'online' ? 'Connected' : mode === 'fixture' ? 'Ready' : overviewState.state === 'loading' ? 'Checking' : 'Unavailable'}</strong>
              <span className="muted">{overview?.health.state === 'online' ? `v${overview.health.version}` : mode === 'fixture' ? 'fixture-1' : 'same-origin /health'}</span>
            </div>
            <div className="source-meta">
              <div><span>Adapter</span><strong>{mode === 'api' ? 'ApiReplayReviewAdapter' : 'FixtureReplayReviewAdapter'}</strong></div>
              <div><span>Backend mode</span><strong>{overview?.health.state === 'online' ? overview.health.mode : mode === 'fixture' ? 'not connected' : 'waiting for response'}</strong></div>
              <div><span>Fallback</span><strong>Disabled</strong></div>
            </div>
            <StateMessage state={overviewState} emptyLabel="No scenario records returned by the backend." />
          </article>

          <article className="panel scenario-panel">
            <div className="panel-topline"><p className="eyebrow">02 / SCENARIOS</p><span className="count-pill">{overview?.scenarios.length ?? '—'} available</span></div>
            <h2>Scenario catalogue</h2>
            <p className="muted">Fetched from the configured adapter. Domain review status is shown as supplied.</p>
            <StateMessage state={overviewState} emptyLabel="No scenarios are available." />
            {overview && overview.scenarios.length > 0 && (
              <div className="scenario-list">
                {overview.scenarios.slice(0, 4).map((item) => (
                  <button className={`scenario-row ${selectedScenario === item.id ? 'selected' : ''}`} key={item.id} onClick={() => setSelectedScenario(item.id)}>
                    <span className="scenario-index">{item.id.slice(0, 2).toUpperCase()}</span>
                    <span className="scenario-copy"><strong>{item.title}</strong><small>{item.objective}</small></span>
                    <span className="review-status">{item.domain_review.replaceAll('_', ' ')}</span>
                  </button>
                ))}
                {overview.scenarios.length > 4 && <p className="more-scenarios">+ {overview.scenarios.length - 4} more in the API catalogue</p>}
              </div>
            )}
          </article>
        </section>

        {mode === 'api' ? (
          <section className="panel access-panel" aria-labelledby="access-heading">
            <div className="panel-topline"><p className="eyebrow">03 / LOCAL SESSION DATA</p><span className="small-label">Read-only view · no commands</span></div>
            <div className="access-heading-row">
              <div><h2 id="access-heading">Connect to a local training session</h2><p className="muted">Operator access is kept in memory for this tab and sent only to the same-origin local API.</p></div>
              {access && <button className="button button-quiet" onClick={() => { setAccess(null); setSessionsState({ state: 'empty' }); setSessionState({ state: 'empty' }); setSelectedSessionId('') }}>Disconnect</button>}
            </div>
            {!access ? (
              <form className="access-form" onSubmit={(event) => void onLogin(event)}>
                <label className="field-label" htmlFor="operator-key">Local operator key</label>
                <div className="form-line"><input id="operator-key" type="password" autoComplete="off" value={operatorKey} onChange={(event) => setOperatorKey(event.target.value)} placeholder="Paste the key from the local backend runtime" minLength={16} maxLength={200} /><button className="button button-primary" type="submit" disabled={busyAction === 'login' || !operatorKey.trim()}>{busyAction === 'login' ? 'Connecting…' : 'Connect'}</button></div>
                <p className="field-note">The key is never stored in localStorage or added to a URL.</p>
              </form>
            ) : (
              <div className="session-controls">
                <div className="session-picker-wrap">
                  <label className="field-label" htmlFor="session-picker">Training session</label>
                  <select id="session-picker" value={selectedSessionId} onChange={(event) => onSessionChange(event.target.value)}>
                    <option value="">Select a session</option>
                    {sessions.map((item) => <option key={item.id} value={item.id}>{item.scenario.title} · {item.id} · {item.status}</option>)}
                  </select>
                </div>
                <button className="button button-primary" onClick={() => void onCreateSession()} disabled={busyAction !== null || !selectedScenario}>{busyAction === 'create' ? 'Creating…' : 'Create synthetic session'}</button>
              </div>
            )}
            {(access || sessionsState.state !== 'empty') && <StateMessage state={sessionsState} emptyLabel={access ? 'No local sessions yet. Choose a scenario above to create a synthetic training session.' : undefined} />}
          </section>
        ) : (
          <section className="panel fixture-note" aria-label="Fixture mode details">
            <div className="fixture-stamp">SYNTHETIC<br />FIXTURE</div>
            <div><p className="eyebrow">03 / FIXTURE MODE</p><h2>Adapter ready for replay UI tasks</h2><p className="muted">This authored fixture exercises the typed source, frame, event, evidence and revision ports. It contains no partner simulator data, ASR output or operational validation.</p></div>
          </section>
        )}

        <section className="panel session-panel" aria-labelledby="session-heading">
          <div className="panel-topline"><p className="eyebrow">04 / SESSION SNAPSHOT</p><span className={`session-status status-${activeSession?.snapshot.status.toLowerCase() ?? 'idle'}`}>{activeSession?.snapshot.status ?? 'NO SESSION SELECTED'}</span></div>
          <div className="session-heading-row"><div><h2 id="session-heading">{activeSession?.session.scenario.title ?? 'Session data'}</h2><p className="muted">{activeSession ? `${activeSession.session.id} · ${activeSession.session.condition} · seed ${activeSession.session.seed}` : 'Select or create a local session to fetch its public snapshot.'}</p></div><span className="time-readout">{activeSession ? formatTime(activeSession.snapshot.sim_ms) : '—:—'}<small>SIM TIME</small></span></div>
          {!activeSession && (sessionState.state === 'loading' || sessionState.state === 'empty') && <StateMessage state={sessionState} emptyLabel="Session snapshots are loaded through the active adapter." />}
          {activeSession && (
            <>
              <div className="metric-grid">
                <Metric label="Observed tracks" value={activeSession.snapshot.track_count.toString().padStart(2, '0')} detail="Public snapshot" />
                <Metric label="Alerts in snapshot" value={activeSession.snapshot.alert_count.toString().padStart(2, '0')} detail="No UI recalculation" />
                <Metric label="Timeline events" value={activeSession.events.length.toString().padStart(2, '0')} detail="First 50 events" />
                <Metric label="Data quality" value={activeSession.snapshot.data_quality.toUpperCase()} detail={`Runway ${activeSession.snapshot.runway_state}`} />
              </div>
              <div className="snapshot-footer"><span>Updated {formatWallTime(activeSession.session.created_utc_ms)}</span><span>sequence {activeSession.snapshot.sequence} · revision {activeSession.snapshot.revision}</span></div>
              <div className="event-list-heading"><span>EVENT TRACE</span><span>ORDINAL / SIM TIME</span></div>
              <ol className="event-list">
                {activeSession.events.slice(0, 5).map((item) => <li key={item.id}><span className="event-ordinal">{item.ordinal.toString().padStart(3, '0')}</span><span className="event-kind">{item.type.replaceAll('_', ' ')}</span><span className="event-message">{item.message}</span><time>{formatTime(item.sim_ms)}</time></li>)}
                {activeSession.events.length === 0 && <li className="empty-event">No event records returned for this view.</li>}
              </ol>
            </>
          )}
          {sessionState.state === 'disconnected' || sessionState.state === 'unauthorized' || sessionState.state === 'conflict' || sessionState.state === 'error'
            ? <StateMessage state={sessionState} />
            : null}
        </section>

        <footer className="workspace-footer"><span>ATC FlowLens · offline replay and synthetic training</span><span>Controller authority remains with the human operator.</span></footer>
      </main>
    </div>
  )
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>
}

export default App
