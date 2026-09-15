// Espelho, no front, da classe Settings do backend: lê import.meta.env uma única vez,
// converte, valida e expõe um objeto congelado e tipado. Nenhum outro módulo do projeto
// pode ler import.meta.env — isso é verificado por lint (no-restricted-syntax) e por grep.

export interface AppEnv {
  readonly apiBaseUrl: string
  readonly wsBaseUrl: string
  readonly requestTimeoutMs: number
  readonly defaultProvider: string
  readonly availableModels: readonly string[]
  readonly defaultModel: string
  readonly defaultMaxTokens: number
  readonly defaultTemperature: number
  readonly historyFetchConcurrency: number
  readonly historySummaryMaxChars: number
  readonly historySidebarSummaryMaxChars: number
  readonly wsOpenTimeoutMs: number
  readonly enableDebugPanel: boolean
}

type EnvKey =
  | 'VITE_API_BASE_URL'
  | 'VITE_WS_BASE_URL'
  | 'VITE_API_PREFIX'
  | 'VITE_REQUEST_TIMEOUT_MS'
  | 'VITE_WS_OPEN_TIMEOUT_MS'
  | 'VITE_DEFAULT_PROVIDER'
  | 'VITE_AVAILABLE_MODELS'
  | 'VITE_DEFAULT_MODEL'
  | 'VITE_DEFAULT_MAX_TOKENS'
  | 'VITE_DEFAULT_TEMPERATURE'
  | 'VITE_HISTORY_FETCH_CONCURRENCY'
  | 'VITE_HISTORY_SUMMARY_MAX_CHARS'
  | 'VITE_HISTORY_SIDEBAR_SUMMARY_MAX_CHARS'
  | 'VITE_ENABLE_DEBUG_PANEL'

// Erro tipado que nomeia sempre a variável problemática — evita depurar em produção
// qual configuração faltou.
export class ConfigError extends Error {
  public readonly variable: string

  constructor(variable: string, reason: string) {
    super(`Configuração inválida: ${variable} — ${reason}`)
    this.name = 'ConfigError'
    this.variable = variable
  }
}

function readRaw(key: EnvKey): string | undefined {
  const value = import.meta.env[key]
  return value === undefined || value === '' ? undefined : value
}

function readString(key: EnvKey, defaultValue?: string): string {
  const raw = readRaw(key)
  if (raw !== undefined) return raw
  if (defaultValue !== undefined) return defaultValue
  throw new ConfigError(key, 'variável obrigatória ausente ou vazia')
}

function readNumber(key: EnvKey, defaultValue?: number): number {
  const raw = readRaw(key)
  if (raw === undefined) {
    if (defaultValue !== undefined) return defaultValue
    throw new ConfigError(key, 'variável obrigatória ausente ou vazia')
  }
  const parsed = Number(raw)
  if (Number.isNaN(parsed)) throw new ConfigError(key, 'precisa ser numérico')
  return parsed
}

function readFloat(key: EnvKey, defaultValue?: number): number {
  return readNumber(key, defaultValue)
}

function readBoolean(key: EnvKey, defaultValue?: boolean): boolean {
  const raw = readRaw(key)
  if (raw === undefined) {
    if (defaultValue !== undefined) return defaultValue
    throw new ConfigError(key, 'variável obrigatória ausente ou vazia')
  }
  const normalized = raw.trim().toLowerCase()
  if (normalized === 'true') return true
  if (normalized === 'false') return false
  throw new ConfigError(key, 'precisa ser "true" ou "false"')
}

function readList(key: EnvKey, defaultValue: readonly string[] = []): readonly string[] {
  const raw = readRaw(key)
  if (raw === undefined) return defaultValue
  return raw
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
}

function validateHttpUrl(key: EnvKey, value: string): void {
  let url: URL
  try {
    url = new URL(value)
  } catch {
    throw new ConfigError(key, 'precisa ser uma URL válida')
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new ConfigError(key, 'precisa usar http:// ou https://')
  }
}

function validateWsUrl(key: EnvKey, value: string): void {
  if (!/^wss?:\/\//.test(value)) {
    throw new ConfigError(key, 'precisa começar com ws:// ou wss://')
  }
}

// Concatena origem + prefixo normalizando barras duplicadas e barra final.
function joinUrl(base: string, prefix: string): string {
  const cleanBase = base.replace(/\/+$/, '')
  const cleanPrefix = `/${prefix.replace(/^\/+|\/+$/g, '')}`
  return `${cleanBase}${cleanPrefix}`
}

function loadEnv(): AppEnv {
  const apiBaseUrlRaw = readString('VITE_API_BASE_URL', 'http://localhost:8000')
  const wsBaseUrlRaw = readString('VITE_WS_BASE_URL', 'ws://localhost:8000')
  const apiPrefix = readString('VITE_API_PREFIX', '/v1')

  validateHttpUrl('VITE_API_BASE_URL', apiBaseUrlRaw)
  validateWsUrl('VITE_WS_BASE_URL', wsBaseUrlRaw)

  const availableModels = readList('VITE_AVAILABLE_MODELS')
  if (availableModels.length === 0) {
    throw new ConfigError('VITE_AVAILABLE_MODELS', 'precisa listar ao menos um modelo')
  }

  const defaultModel = readString('VITE_DEFAULT_MODEL')
  if (!availableModels.includes(defaultModel)) {
    throw new ConfigError(
      'VITE_DEFAULT_MODEL',
      `precisa pertencer a VITE_AVAILABLE_MODELS (${availableModels.join(', ')})`,
    )
  }

  // Num modelo de raciocínio, `max_tokens` cobre o raciocínio interno e a resposta. Neste
  // projeto o raciocínio sozinho já passou de 1000 tokens numa pergunta curta, então um teto
  // apertado sobra zero para a resposta e o provedor devolve conteúdo vazio.
  const defaultMaxTokens = readNumber('VITE_DEFAULT_MAX_TOKENS', 4000)
  if (!Number.isInteger(defaultMaxTokens) || defaultMaxTokens <= 0) {
    throw new ConfigError('VITE_DEFAULT_MAX_TOKENS', 'precisa ser um número inteiro positivo')
  }

  const defaultTemperature = readFloat('VITE_DEFAULT_TEMPERATURE', 0.3)
  if (defaultTemperature < 0 || defaultTemperature > 1) {
    throw new ConfigError('VITE_DEFAULT_TEMPERATURE', 'precisa estar entre 0 e 1')
  }

  return Object.freeze({
    apiBaseUrl: joinUrl(apiBaseUrlRaw, apiPrefix),
    wsBaseUrl: joinUrl(wsBaseUrlRaw, apiPrefix),
    requestTimeoutMs: readNumber('VITE_REQUEST_TIMEOUT_MS', 60000),
    defaultProvider: readString('VITE_DEFAULT_PROVIDER', 'open_router'),
    availableModels,
    defaultModel,
    defaultMaxTokens,
    defaultTemperature,
    historyFetchConcurrency: readNumber('VITE_HISTORY_FETCH_CONCURRENCY', 6),
    historySummaryMaxChars: readNumber('VITE_HISTORY_SUMMARY_MAX_CHARS', 120),
    historySidebarSummaryMaxChars: readNumber('VITE_HISTORY_SIDEBAR_SUMMARY_MAX_CHARS', 48),
    wsOpenTimeoutMs: readNumber('VITE_WS_OPEN_TIMEOUT_MS', 15000),
    enableDebugPanel: readBoolean('VITE_ENABLE_DEBUG_PANEL', false),
  })
}

export const env: AppEnv = loadEnv()
