import { afterEach, describe, expect, it, vi } from 'vitest'
import completedFixture from '@/test/fixtures/session-a1-completed-15msgs.json'

const BASE_ENV: Record<string, string> = {
  VITE_API_BASE_URL: 'http://localhost:8000',
  VITE_WS_BASE_URL: 'ws://localhost:8000',
  VITE_API_PREFIX: '/v1',
  VITE_REQUEST_TIMEOUT_MS: '5000',
  VITE_WS_OPEN_TIMEOUT_MS: '15000',
  VITE_DEFAULT_PROVIDER: 'open_router',
  VITE_AVAILABLE_MODELS: 'openai/gpt-4o-mini',
  VITE_DEFAULT_MODEL: 'openai/gpt-4o-mini',
  VITE_DEFAULT_MAX_TOKENS: '1200',
  VITE_DEFAULT_TEMPERATURE: '0.3',
  VITE_HISTORY_FETCH_CONCURRENCY: '6',
  VITE_HISTORY_SUMMARY_MAX_CHARS: '120',
  VITE_HISTORY_SIDEBAR_SUMMARY_MAX_CHARS: '48',
  VITE_ENABLE_DEBUG_PANEL: 'false',
}

function stubEnv(overrides: Record<string, string> = {}): void {
  for (const [key, value] of Object.entries({ ...BASE_ENV, ...overrides })) {
    vi.stubEnv(key, value)
  }
}

// Mesmo motivo do `httpClient.test.ts`: reimporta tudo a partir do mesmo `resetModules()` para
// preservar `instanceof` nas classes de erro.
async function importSessionApi() {
  vi.resetModules()
  stubEnv()
  const [sessionApi, errors] = await Promise.all([import('./sessionApi'), import('./errors')])
  return { ...sessionApi, ...errors }
}

function fakeResponse(status: number, body: string): Response {
  return { status, text: () => Promise.resolve(body) } as Response
}

describe('sessionApi', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('listSessionIds devolve o array de dentro do envelope', async () => {
    const fetchMock = vi.fn().mockResolvedValue(fakeResponse(200, JSON.stringify({ session_ids: ['sess_a', 'sess_b'] })))
    vi.stubGlobal('fetch', fetchMock)
    const { listSessionIds } = await importSessionApi()

    await expect(listSessionIds()).resolves.toEqual(['sess_a', 'sess_b'])
  })

  it('getSession parseia o documento completo e escapa o id na URL', async () => {
    const fetchMock = vi.fn().mockResolvedValue(fakeResponse(200, JSON.stringify(completedFixture)))
    vi.stubGlobal('fetch', fetchMock)
    const { getSession } = await importSessionApi()

    const document = await getSession('sess com espaço')

    expect(document.id).toBe(completedFixture.id)
    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toContain(encodeURIComponent('sess com espaço'))
  })

  it('getSession com sessão inexistente lança HttpError 404', async () => {
    const fetchMock = vi.fn().mockResolvedValue(fakeResponse(404, JSON.stringify({ detail: 'não existe' })))
    vi.stubGlobal('fetch', fetchMock)
    const { getSession, HttpError } = await importSessionApi()

    await expect(getSession('sess_inexistente')).rejects.toBeInstanceOf(HttpError)
  })
})
