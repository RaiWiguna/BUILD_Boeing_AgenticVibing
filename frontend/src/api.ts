export type ApiErrorKind = 'disconnected' | 'unauthorized' | 'conflict' | 'error'
export type ApiErrorReason =
  | 'network'
  | 'unauthorized'
  | 'forbidden'
  | 'not_found'
  | 'conflict'
  | 'validation'
  | 'service_unavailable'
  | 'unsupported_profile'
  | 'malformed_json'
  | 'invalid_payload'
  | 'expired'
  | 'http_error'

export type Decoder<T> = (value: unknown) => T

export class ApiRequestError extends Error {
  constructor(
    readonly kind: ApiErrorKind,
    message: string,
    readonly status: number | null = null,
    readonly reason: ApiErrorReason = 'invalid_payload',
  ) {
    super(message)
    this.name = 'ApiRequestError'
  }
}

export interface ApiWebSocket {
  readonly readyState: number
  onopen: ((event: Event) => void) | null
  onmessage: ((event: MessageEvent) => void) | null
  onerror: ((event: Event) => void) | null
  onclose: ((event: CloseEvent) => void) | null
  send(data: string): void
  close(code?: number, reason?: string): void
}

export interface ApiTransport {
  request(input: RequestInfo | URL, init?: RequestInit): Promise<Response>
  openWebSocket(url: string): ApiWebSocket
}

export const browserApiTransport: ApiTransport = {
  request: (input, init) => fetch(input, init),
  openWebSocket: (url) => new WebSocket(url),
}

export interface ApiRequestOptions {
  method?: 'GET' | 'POST'
  token?: string
  body?: unknown
  signal?: AbortSignal
  transport?: ApiTransport
}

export async function apiRequest<T>(path: string, decode: Decoder<T>, options: ApiRequestOptions = {}): Promise<T> {
  let response: Response
  const transport = options.transport ?? browserApiTransport
  try {
    response = await transport.request(path, {
      method: options.method ?? 'GET',
      headers: {
        Accept: 'application/json',
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    })
  } catch (error) {
    if (isAbortError(error)) throw error
    throw new ApiRequestError('disconnected', 'Could not reach the local backend. Check that it is running, then retry.', null, 'network')
  }

  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    if (!response.ok) {
      throw responseError(response, undefined)
    }
    throw new ApiRequestError('error', 'The backend returned an invalid JSON response.', response.status, 'malformed_json')
  }

  if (!response.ok) throw responseError(response, payload)

  try {
    return decode(payload)
  } catch (error) {
    if (error instanceof ApiRequestError) throw error
    throw new ApiRequestError('error', 'The backend response does not match the frontend contract.', response.status, 'invalid_payload')
  }
}

export function makeWebSocketUrl(path: string, origin?: string): string {
  if (origin === undefined && typeof window === 'undefined') {
    throw new ApiRequestError('disconnected', 'WebSocket subscriptions require a browser origin.', null, 'network')
  }
  const url = new URL(path, origin ?? window.location.href)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.username = ''
  url.password = ''
  return url.toString()
}

function responseError(response: Response, payload: unknown): ApiRequestError {
  const detail = readErrorDetail(payload) || response.statusText || `HTTP ${response.status}`
  if (response.status === 401) return new ApiRequestError('unauthorized', detail, 401, 'unauthorized')
  if (response.status === 403) return new ApiRequestError('unauthorized', detail, 403, 'forbidden')
  if (response.status === 404) return new ApiRequestError('error', detail, 404, 'not_found')
  if (response.status === 409) return new ApiRequestError('conflict', detail, 409, 'conflict')
  if (response.status === 422) return new ApiRequestError('error', detail, 422, 'validation')
  if (response.status === 503) return new ApiRequestError('error', detail, 503, 'service_unavailable')
  return new ApiRequestError('error', detail, response.status, 'http_error')
}

function readErrorDetail(payload: unknown): string | null {
  if (!isRecord(payload)) return null
  const detail = payload.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      if (typeof item === 'object' && item !== null && !Array.isArray(item) && typeof item.msg === 'string') return item.msg
      return safeString(item)
    }).join('; ')
  }
  if (typeof detail === 'object' && detail !== null) return safeString(detail)
  return null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function safeString(value: unknown): string {
  try {
    const serialized = JSON.stringify(value)
    return serialized === undefined ? String(value) : serialized
  } catch {
    return String(value)
  }
}

export function isAbortError(error: unknown): boolean {
  return typeof error === 'object' && error !== null && 'name' in error && error.name === 'AbortError'
}
