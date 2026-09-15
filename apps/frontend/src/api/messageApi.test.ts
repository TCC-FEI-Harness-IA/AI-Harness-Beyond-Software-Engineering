import { afterEach, describe, expect, it, vi } from 'vitest'
import { buildInferencePayload, type RunConfig } from './messageApi'
import { ContractError } from './errors/ContractError'

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

function fakeResponse(status: number, body: string): Response {
  return { status, text: () => Promise.resolve(body) } as Response
}

const CONFIG: RunConfig = {
  modelName: 'openai/gpt-4o-mini',
  provider: 'open_router',
  maxTokens: 1000,
  temperature: 0.3,
}

describe('buildInferencePayload', () => {
  it('monta o corpo exato do contrato', () => {
    const payload = buildInferencePayload('Quais são todos os números primos entre 0 e 20?', CONFIG)

    expect(payload).toEqual({
      message: { user_input: 'Quais são todos os números primos entre 0 e 20?' },
      llm_model_config: {
        provider: 'open_router',
        provider_config: { model_name: 'openai/gpt-4o-mini', endpoint: null },
        max_tokens: 1000,
        temperature: 0.3,
      },
    })
  })

  it('lança quando a pergunta é vazia', () => {
    expect(() => buildInferencePayload('', CONFIG)).toThrow(ContractError)
    expect(() => buildInferencePayload('   ', CONFIG)).toThrow(ContractError)
  })

  it('arredonda a temperatura para 1 casa decimal', () => {
    const payload = buildInferencePayload('ping', { ...CONFIG, temperature: 0.75 })
    expect(payload.llm_model_config.temperature).toBeCloseTo(0.8)
  })

  it('lança quando a temperatura fica fora de [0, 1] após arredondar', () => {
    expect(() => buildInferencePayload('ping', { ...CONFIG, temperature: 1.4 })).toThrow(
      ContractError,
    )
  })

  it('lança quando max_tokens não é positivo', () => {
    expect(() => buildInferencePayload('ping', { ...CONFIG, maxTokens: 0 })).toThrow(ContractError)
  })
})

describe('sendDefaultMessage', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('faz POST em /message/default e devolve o corpo parseado', async () => {
    for (const [key, value] of Object.entries(BASE_ENV)) vi.stubEnv(key, value)
    const responseBody = {
      message: 'ping',
      response: 'pong',
      session_id: 'sess_test',
      tokens_input: 1,
      tokens_output: 1,
      inference_time_ms: 10,
    }
    const fetchMock = vi.fn().mockResolvedValue(fakeResponse(200, JSON.stringify(responseBody)))
    vi.stubGlobal('fetch', fetchMock)
    vi.resetModules()
    const { sendDefaultMessage } = await import('./messageApi')

    const payload = buildInferencePayload('ping', CONFIG)
    await expect(sendDefaultMessage(payload)).resolves.toEqual(responseBody)

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/message/default')
    expect(init.method).toBe('POST')
  })
})
