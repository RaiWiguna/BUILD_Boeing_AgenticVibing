import type {
  DashboardAdapter,
  EventReadModel,
  OperatorAccess,
  OverviewReadModel,
  SessionReadModel,
  SessionViewReadModel,
  SnapshotReadModel,
} from '../contracts/replayReview'
import { apiRequest, type ApiTransport, type Decoder } from '../api'
import {
  decodeApiEventPage,
  decodeApiSnapshot,
  decodeHealth,
  decodeOperatorAccess,
  decodeScenarioList,
  decodeSession,
  decodeSessionList,
  toEventReadModel,
  toSnapshotReadModel,
} from './apiDecoders'

const decodeSnapshotReadModel: Decoder<SnapshotReadModel> = (value) => toSnapshotReadModel(decodeApiSnapshot(value))
const decodeSessionEvents: Decoder<EventReadModel[]> = (value) => decodeApiEventPage(value).items.map(toEventReadModel)

export class ApiDashboardAdapter implements DashboardAdapter {
  readonly mode = 'api' as const

  constructor(protected readonly apiTransport?: ApiTransport) {}

  async loadOverview(signal?: AbortSignal): Promise<OverviewReadModel> {
    const [health, scenarios] = await Promise.all([
      apiRequest('/health', decodeHealth, { signal, transport: this.apiTransport }),
      apiRequest('/api/v1/scenarios', decodeScenarioList, { signal, transport: this.apiTransport }),
    ])
    return { health, scenarios, source_label: 'Local backend · synthetic training API' }
  }

  async authenticateOperator(key: string, signal?: AbortSignal): Promise<OperatorAccess> {
    return apiRequest('/api/v1/auth/operator', decodeOperatorAccess, {
      method: 'POST',
      body: { key },
      signal,
      transport: this.apiTransport,
    })
  }

  async listSessions(token: string, signal?: AbortSignal): Promise<SessionReadModel[]> {
    return apiRequest('/api/v1/sessions', decodeSessionList, { token, signal, transport: this.apiTransport })
  }

  async createSession(token: string, scenarioId: string, signal?: AbortSignal): Promise<SessionReadModel> {
    return apiRequest('/api/v1/sessions', decodeSession, {
      token,
      method: 'POST',
      body: { scenario_id: scenarioId, seed: 42, condition: 'flowlens' },
      signal,
      transport: this.apiTransport,
    })
  }

  async loadSession(token: string, sessionId: string, signal?: AbortSignal): Promise<SessionViewReadModel> {
    const encodedId = encodeURIComponent(sessionId)
    const [snapshot, events] = await Promise.all([
      apiRequest(`/api/v1/sessions/${encodedId}/snapshot`, decodeSnapshotReadModel, { token, signal, transport: this.apiTransport }),
      apiRequest(`/api/v1/sessions/${encodedId}/events?cursor=0&limit=50`, decodeSessionEvents, { token, signal, transport: this.apiTransport }),
    ])
    const session: SessionReadModel = {
      id: snapshot.session_id,
      status: snapshot.status,
      scenario: snapshot.scenario,
      condition: snapshot.condition,
      seed: snapshot.seed,
      kind: snapshot.kind,
      created_utc_ms: null,
    }
    return { session, snapshot, events }
  }
}
