import { ApiRequestError } from '../../api'
import type { EventReadModel, ReplayReviewAdapter, TranscriptReadModel } from '../../contracts/replayReview'

export async function loadCompleteEventHistory(
  adapter: ReplayReviewAdapter,
  sourceSessionId: string,
  signal?: AbortSignal,
): Promise<EventReadModel[]> {
  const result: EventReadModel[] = []
  const seen = new Set<string>()
  let cursor = 0

  while (true) {
    if (signal?.aborted) throw new DOMException('The operation was aborted.', 'AbortError')
    const page = await adapter.listEvents(sourceSessionId, cursor, undefined, signal)
    if (page.next_cursor < cursor || (page.items.length > 0 && page.next_cursor <= cursor)) {
      throw new ApiRequestError('error', 'Event history cursor did not advance; the timeline cannot be loaded safely.', null, 'unsupported_profile')
    }
    for (const item of page.items) {
      if (!seen.has(item.id)) {
        seen.add(item.id)
        result.push(item)
      }
    }
    if (page.next_cursor === cursor) break
    cursor = page.next_cursor
  }

  return result.sort((left, right) => {
    const leftAvailableMs = left.received_ms ?? left.sim_ms
    const rightAvailableMs = right.received_ms ?? right.sim_ms
    return leftAvailableMs - rightAvailableMs || left.ordinal - right.ordinal || left.sim_ms - right.sim_ms
  })
}

export async function loadCompleteTranscript(
  adapter: ReplayReviewAdapter,
  sourceSessionId: string,
  signal?: AbortSignal,
): Promise<TranscriptReadModel> {
  const items: TranscriptReadModel['items'] = []
  const seen = new Set<string>()
  let cursor: string | null = null
  let message: string | undefined
  let job: TranscriptReadModel['job']

  while (true) {
    if (signal?.aborted) throw new DOMException('The operation was aborted.', 'AbortError')
    const page = await adapter.listTranscript(sourceSessionId, cursor, undefined, signal)
    if (page.state === 'unavailable') return page
    if (page.message) message = page.message
    if (page.job) job = page.job
    for (const item of page.items) {
      if (!seen.has(item.id)) {
        seen.add(item.id)
        items.push(item)
      }
    }
    const nextCursor = page.next_cursor ?? null
    if (nextCursor === null) break
    if (nextCursor === cursor) {
      if (page.items.length > 0) throw new ApiRequestError('error', 'Transcript cursor did not advance; transcript history cannot be loaded safely.', null, 'unsupported_profile')
      break
    }
    cursor = nextCursor
  }

  items.sort((left, right) => {
    const leftTime = left.session_start_ms ?? Number.POSITIVE_INFINITY
    const rightTime = right.session_start_ms ?? Number.POSITIVE_INFINITY
    return leftTime - rightTime || left.start_ms - right.start_ms || left.id.localeCompare(right.id)
  })
  return { state: items.length ? 'ready' : 'empty', items, ...(message ? { message } : {}), next_cursor: null, ...(job ? { job } : {}) }
}

export function createControlRequestId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  return `replay-control-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function createReviewRequestId(action: string): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return `review-${action}-${crypto.randomUUID()}`
  return `review-${action}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}
