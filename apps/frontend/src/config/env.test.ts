import { afterEach, describe, expect, it, vi } from 'vitest'
import type * as EnvModule from './env'

// env.ts lê as variáveis de ambiente no topo do módulo (export const env = loadEnv()),
// então cada cenário precisa stubar as variáveis e reimportar o módulo do zero.
const BASE_ENV: Record<string, string> = {
  VITE_API_BASE_URL: 'http://localhost:8000',
  VITE_WS_BASE_URL: 'ws://localhost:8000',
  VITE_API_PREFIX: '/v1',
  VITE_REQUEST_TIMEOUT_MS: '60000',
  VITE_WS_OPEN_TIMEOUT_MS: '15000',
  VITE_DEFAULT_PROVIDER: 'open_router',
  VITE_AVAILABLE_PROVIDERS: 'open_router,openai',
  VITE_AVAILABLE_MODELS: 'openai/gpt-4o-mini,openai/gpt-4o',
  VITE_DEFAULT_MODEL: 'openai/gpt-4o-mini',
  VITE_DEFAULT_MAX_TOKENS: '1200',
  VITE_DEFAULT_TEMPERATURE: '0.3',
  VITE_HISTORY_FETCH_CONCURRENCY: '6',
  VITE_HISTORY_SUMMARY_MAX_CHARS: '120',
  VITE_HISTORY_SIDEBAR_SUMMARY_MAX_CHARS: '48',
  VITE_ENABLE_DEBUG_PANEL: 'false',
}

function stubEnv(overrides: Record<string, string> = {}): void {
  const merged = { ...BASE_ENV, ...overrides }
  for (const [key, value] of Object.entries(merged)) {
    vi.stubEnv(key, value)
  }
}

async function importEnv(): Promise<typeof EnvModule> {
  vi.resetModules()
  return import('./env')
}

describe('config/env', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('carrega e converte as variáveis corretamente', async () => {
    stubEnv()
    const { env } = await importEnv()

    expect(env.apiBaseUrl).toBe('http://localhost:8000/v1')
    expect(env.wsBaseUrl).toBe('ws://localhost:8000/v1')
    expect(env.availableModels).toEqual(['openai/gpt-4o-mini', 'openai/gpt-4o'])
    expect(env.availableProviders).toEqual(['open_router', 'openai'])
    expect(env.defaultProvider).toBe('open_router')
    expect(env.defaultModel).toBe('openai/gpt-4o-mini')
    expect(env.defaultMaxTokens).toBe(1200)
    expect(env.defaultTemperature).toBeCloseTo(0.3)
    expect(env.enableDebugPanel).toBe(false)
    expect(Object.isFrozen(env)).toBe(true)
  })

  it('lança nomeando a variável quando o modelo padrão não está na lista', async () => {
    stubEnv({ VITE_DEFAULT_MODEL: 'modelo-inexistente' })
    await expect(importEnv()).rejects.toThrow(/VITE_DEFAULT_MODEL/)
  })

  it('lança quando a temperatura está fora de [0, 1]', async () => {
    stubEnv({ VITE_DEFAULT_TEMPERATURE: '1.5' })
    await expect(importEnv()).rejects.toThrow(/VITE_DEFAULT_TEMPERATURE/)
  })

  it('lança quando VITE_WS_BASE_URL não começa com ws:// ou wss://', async () => {
    stubEnv({ VITE_WS_BASE_URL: 'http://localhost:8000' })
    await expect(importEnv()).rejects.toThrow(/VITE_WS_BASE_URL/)
  })

  it('não gera barra dupla quando a URL base termina com /', async () => {
    stubEnv({ VITE_API_BASE_URL: 'http://localhost:8000/' })
    const { env } = await importEnv()
    expect(env.apiBaseUrl).toBe('http://localhost:8000/v1')
  })

  it('sem VITE_AVAILABLE_PROVIDERS, o provedor padrão é a única opção', async () => {
    stubEnv({ VITE_AVAILABLE_PROVIDERS: '', VITE_DEFAULT_PROVIDER: 'openai' })
    const { env } = await importEnv()
    expect(env.availableProviders).toEqual(['openai'])
  })

  it('lança nomeando a variável quando um provedor listado não existe no backend', async () => {
    stubEnv({ VITE_AVAILABLE_PROVIDERS: 'open_router,provedor-inexistente' })
    await expect(importEnv()).rejects.toThrow(/VITE_AVAILABLE_PROVIDERS/)
  })

  it('lança nomeando a variável quando o provedor padrão não existe no backend', async () => {
    stubEnv({ VITE_DEFAULT_PROVIDER: 'local', VITE_AVAILABLE_PROVIDERS: '' })
    await expect(importEnv()).rejects.toThrow(/VITE_DEFAULT_PROVIDER/)
  })

  it('lança nomeando a variável quando o provedor padrão está fora da lista', async () => {
    stubEnv({ VITE_DEFAULT_PROVIDER: 'openai', VITE_AVAILABLE_PROVIDERS: 'open_router' })
    await expect(importEnv()).rejects.toThrow(/VITE_DEFAULT_PROVIDER/)
  })
})
