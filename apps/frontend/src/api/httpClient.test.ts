import { afterEach, describe, expect, it, vi } from 'vitest'

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

// `vi.resetModules()` cria um novo registro de módulos — reimportar só `httpClient` faria as
// classes de erro que ele lança virem de uma instância de módulo diferente da importada
// estaticamente no topo deste arquivo, quebrando `instanceof`. Por isso os dois são
// reimportados juntos, a partir do mesmo reset.
async function importHttpClient(overrides: Record<string, string> = {}) {
  vi.resetModules()
  stubEnv(overrides)
  const [{ httpClient }, errors] = await Promise.all([import('./httpClient'), import('./errors')])
  return { httpClient, ...errors }
}

function fakeResponse(status: number, body: string): Response {
  return { status, text: () => Promise.resolve(body) } as Response
}

describe('httpClient', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('chama o parser quando a resposta é 200', async () => {
    const fetchMock = vi.fn().mockResolvedValue(fakeResponse(200, JSON.stringify({ foo: 'bar' })))
    vi.stubGlobal('fetch', fetchMock)
    const { httpClient } = await importHttpClient()

    const parse = vi.fn().mockReturnValue('valor-tipado')
    const result = await httpClient.get('/qualquer', parse)

    expect(parse).toHaveBeenCalledWith({ foo: 'bar' })
    expect(result).toBe('valor-tipado')
  })

  it('lança HttpError com a mensagem "Chat não encontrado." em 404', async () => {
    const fetchMock = vi.fn().mockResolvedValue(fakeResponse(404, JSON.stringify({ detail: 'x' })))
    vi.stubGlobal('fetch', fetchMock)
    const { httpClient, HttpError } = await importHttpClient()

    const error: unknown = await httpClient.get('/sessions/inexistente', (raw) => raw).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(HttpError)
    expect(error).toMatchObject({ userMessage: 'Chat não encontrado.', status: 404 })
  })

  it('lança ContractError quando o corpo não é JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue(fakeResponse(200, 'isso não é json'))
    vi.stubGlobal('fetch', fetchMock)
    const { httpClient, ContractError } = await importHttpClient()

    await expect(httpClient.get('/qualquer', (raw) => raw)).rejects.toBeInstanceOf(ContractError)
  })

  it('lança TimeoutError quando estoura o timeout configurado', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn((_url: string, init?: RequestInit) => {
      return new Promise((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => {
          reject(new DOMException('A operação foi abortada.', 'AbortError'))
        })
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    const { httpClient, TimeoutError } = await importHttpClient({ VITE_REQUEST_TIMEOUT_MS: '50' })

    const promise = httpClient.get('/qualquer', (raw) => raw)
    const assertion = expect(promise).rejects.toBeInstanceOf(TimeoutError)
    await vi.advanceTimersByTimeAsync(60)
    await assertion
  })

  it('erro com corpo vazio não tenta parsear JSON e o detail vem null', async () => {
    const fetchMock = vi.fn().mockResolvedValue(fakeResponse(500, ''))
    vi.stubGlobal('fetch', fetchMock)
    const { httpClient, HttpError } = await importHttpClient()

    const error: unknown = await httpClient.get('/qualquer', (raw) => raw).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(HttpError)
    expect(error).toMatchObject({ detail: null })
  })

  it('erro com corpo não-JSON não lança ao ler o detail, e o detail vem null', async () => {
    const fetchMock = vi.fn().mockResolvedValue(fakeResponse(500, 'Internal Server Error'))
    vi.stubGlobal('fetch', fetchMock)
    const { httpClient, HttpError } = await importHttpClient()

    const error: unknown = await httpClient.get('/qualquer', (raw) => raw).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(HttpError)
    expect(error).toMatchObject({ detail: null })
  })

  it('erro com "detail" de tipo diferente de string vira detail null', async () => {
    const fetchMock = vi.fn().mockResolvedValue(fakeResponse(500, JSON.stringify({ detail: { code: 1 } })))
    vi.stubGlobal('fetch', fetchMock)
    const { httpClient, HttpError } = await importHttpClient()

    const error: unknown = await httpClient.get('/qualquer', (raw) => raw).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(HttpError)
    expect(error).toMatchObject({ detail: null })
  })

  it('lança NetworkError quando o fetch rejeita por um motivo que não é abort', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    vi.stubGlobal('fetch', fetchMock)
    const { httpClient, NetworkError } = await importHttpClient()

    await expect(httpClient.get('/qualquer', (raw) => raw)).rejects.toBeInstanceOf(NetworkError)
  })

  // Regressão: o `AbortError` cru vazava para a tela como "Violação de contrato: AbortError:
  // signal is aborted without reason" — a camada `api/` só pode rejeitar com `AppError`, e um
  // cancelamento pedido pelo próprio app não é resposta malformada do servidor.
  it('cancelamento do chamador vira CanceledError, não o AbortError cru', async () => {
    const fetchMock = vi.fn((_url: string, init?: RequestInit) => {
      return new Promise((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => {
          reject(new DOMException('signal is aborted without reason', 'AbortError'))
        })
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    const { httpClient, CanceledError, AppError } = await importHttpClient()

    const controller = new AbortController()
    const promise = httpClient.get('/qualquer', (raw) => raw, controller.signal)
    controller.abort()

    const error: unknown = await promise.catch((e: unknown) => e)
    expect(error).toBeInstanceOf(CanceledError)
    expect(error).toBeInstanceOf(AppError)
    expect(error).not.toBeInstanceOf(DOMException)
  })
})

describe('httpClient.getBlob', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('devolve o corpo da resposta como Blob, sem interpretá-lo como JSON', async () => {
    const zip = new Blob(['PK'], { type: 'application/zip' })
    const fetchMock = vi.fn().mockResolvedValue({ status: 200, blob: () => Promise.resolve(zip) })
    vi.stubGlobal('fetch', fetchMock)
    const { httpClient } = await importHttpClient()

    expect(await httpClient.getBlob('/arquivo.zip')).toBe(zip)
    expect(fetchMock.mock.calls[0]?.[0]).toBe('http://localhost:8000/v1/arquivo.zip')
  })

  it('traduz o status de erro em HttpError com o detail do servidor', async () => {
    const detail = 'A bateria ainda está em execução.'
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(fakeResponse(409, JSON.stringify({ detail }))))
    const { httpClient, HttpError } = await importHttpClient()

    const error: unknown = await httpClient.getBlob('/arquivo.zip').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(HttpError)
    expect(error).toMatchObject({
      status: 409,
      detail,
      userMessage: 'A operação não é possível no estado atual do recurso.',
    })
  })
})
