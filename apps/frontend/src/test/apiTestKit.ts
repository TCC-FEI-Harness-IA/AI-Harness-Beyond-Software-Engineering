// Utilitários dos testes da camada `api/`: ambiente fixo, reimportação limpa e respostas falsas.
import { vi } from 'vitest'

const BASE_ENV: Record<string, string> = {
  VITE_API_BASE_URL: 'http://localhost:8000',
  VITE_WS_BASE_URL: 'ws://localhost:8000',
  VITE_API_PREFIX: '/v1',
  VITE_REQUEST_TIMEOUT_MS: '5000',
  VITE_WS_OPEN_TIMEOUT_MS: '15000',
  VITE_DEFAULT_PROVIDER: 'open_router',
  VITE_DEFAULT_MODEL: 'openai/gpt-4o-mini',
  VITE_DEFAULT_MAX_TOKENS: '1200',
  VITE_DEFAULT_TEMPERATURE: '0.3',
  VITE_HISTORY_FETCH_CONCURRENCY: '6',
  VITE_HISTORY_SUMMARY_MAX_CHARS: '120',
  VITE_HISTORY_SIDEBAR_SUMMARY_MAX_CHARS: '48',
  VITE_ENABLE_DEBUG_PANEL: 'false',
}

export function stubBaseEnv(): void {
  for (const [key, value] of Object.entries(BASE_ENV)) vi.stubEnv(key, value)
}

export function fakeResponse(status: number, body: unknown = ''): Response {
  const text = typeof body === 'string' ? body : JSON.stringify(body)
  return { status, text: () => Promise.resolve(text) } as Response
}

/** Chamadas registradas no `fetch` falso: URL, método, corpo e headers. */
export function fetchCalls(fetchMock: ReturnType<typeof vi.fn>): Array<{
  url: string
  method: string
  body: unknown
  headers: Headers
}> {
  return fetchMock.mock.calls.map(([url, init]) => {
    const request = init as RequestInit
    return {
      url: String(url),
      method: request.method ?? 'GET',
      body: typeof request.body === 'string' ? JSON.parse(request.body) : request.body,
      headers: new Headers(request.headers),
    }
  })
}
