// Modelo, limite de tokens por sessão e temperatura — configuração de execução compartilhada pelos
// dois fluxos de inferência (README, FASE 04, seção 4). Vive em Context para sobreviver à navegação
// entre a home e as telas de chat, sem precisar passar por props em cascata.
//
// O `maxTokens` é o limite de tokens imposto pelo front a cada sessão. Ele nunca passa do limite por
// sessão do backend (`GET /v1/limits`, `LLM_MAX_TOKENS`): assim que o limite do backend chega, o
// valor salvo é rebaixado a ele, e nenhum valor digitado o ultrapassa.
//
// Os modelos escolhíveis vêm do catálogo do backend (`GET /v1/models`, coleção `models` do MongoDB).
// Assim que o catálogo chega, um modelo salvo que não está nele volta para o default — ou para o
// primeiro do catálogo, se nem o default estiver cadastrado.

import type { ReactNode } from 'react'
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { getBackendLimits } from '@/api/limitsApi'
import { getModelCatalog } from '@/api/modelsApi'
import type { RunConfig } from '@/api/messageApi'
import { env } from '@/config/env'
import { type ModelProvider, isModelProvider } from '@/domain/enums/modelProvider'
import type { BackendLimits } from '@/domain/types/backendLimits'
import type { ModelInfo } from '@/domain/types/modelInfo'

const STORAGE_KEY = 'tcc.runConfig'

interface StoredRunConfig {
  modelName: string
  maxTokens: number
  temperature: number
  provider?: string
}

export type ModelsStatus = 'loading' | 'ready' | 'error'

interface RunConfigState {
  config: RunConfig
  /** Limite de tokens por sessão do backend; `null` enquanto não chegou (ou se não pôde ser lido). */
  maxTokensLimit: number | null
  /** Catálogo de modelos escolhíveis (`GET /v1/models`); vazio enquanto não chegou ou se falhou. */
  models: readonly ModelInfo[]
  modelsStatus: ModelsStatus
  /** Busca o catálogo de novo — usado depois de cadastrar, editar ou remover um modelo. */
  reloadModels: () => void
  setModelName: (model: string) => void
  setMaxTokens: (value: number) => void
  setTemperature: (value: number) => void
  setProvider: (value: string) => void
  reset: () => void
}

const RunConfigContext = createContext<RunConfigState | undefined>(undefined)

function defaultConfig(): RunConfig {
  return {
    modelName: env.defaultModel,
    provider: env.defaultProvider,
    maxTokens: env.defaultMaxTokens,
    temperature: env.defaultTemperature,
  }
}

function clampTemperature(value: number): number {
  if (!Number.isFinite(value)) return env.defaultTemperature
  return Math.min(1, Math.max(0, value))
}

function clampMaxTokens(value: number, limit: number | null): number {
  const tokens = Number.isFinite(value) ? Math.max(1, Math.trunc(value)) : env.defaultMaxTokens
  return limit === null ? tokens : Math.min(limit, tokens)
}

// Um provedor que o backend não conhece — ou que saiu de VITE_AVAILABLE_PROVIDERS — volta
// para o default em vez de produzir um payload que o backend recusaria com 422.
function normalizeProvider(value: unknown): ModelProvider {
  if (!isModelProvider(value) || !env.availableProviders.includes(value)) {
    return env.defaultProvider
  }
  return value
}

function isStoredRunConfig(value: unknown): value is StoredRunConfig {
  if (typeof value !== 'object' || value === null) return false
  const candidate = value as Partial<StoredRunConfig>
  return (
    typeof candidate.modelName === 'string' &&
    typeof candidate.maxTokens === 'number' &&
    typeof candidate.temperature === 'number'
  )
}

// localStorage pode lançar em janela privada — o app segue com o default nesse caso. O modelo
// salvo só é conferido quando o catálogo chega (ver `pickCatalogModel`).
function readStoredConfig(): RunConfig {
  const base = defaultConfig()
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (raw === null) return base

    const parsed: unknown = JSON.parse(raw)
    if (!isStoredRunConfig(parsed)) return base

    return {
      ...base,
      modelName: parsed.modelName,
      maxTokens: clampMaxTokens(parsed.maxTokens, null),
      temperature: clampTemperature(parsed.temperature),
      provider: normalizeProvider(parsed.provider),
    }
  } catch {
    return base
  }
}

// Um modelo fora do catálogo produziria um payload que o backend recusaria (README, FASE 04,
// seção 4): volta para o default, ou para o primeiro do catálogo quando nem o default está nele.
function pickCatalogModel(current: string, models: readonly ModelInfo[]): string {
  const names = models.map((model) => model.model_name)
  if (names.length === 0 || names.includes(current)) return current
  return names.includes(env.defaultModel) ? env.defaultModel : (names[0] ?? current)
}

function persistConfig(config: RunConfig): void {
  try {
    const toStore: StoredRunConfig = {
      modelName: config.modelName,
      maxTokens: config.maxTokens,
      temperature: config.temperature,
      provider: config.provider,
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(toStore))
  } catch {
    // Mesma tolerância da leitura — falha em persistir não pode quebrar a troca de configuração.
  }
}

interface RunConfigProviderProps {
  children: ReactNode
  /** Fonte do limite de tokens por sessão do backend; os testes a substituem. */
  loadLimits?: (signal: AbortSignal) => Promise<BackendLimits>
  /** Fonte do catálogo de modelos; os testes a substituem. */
  loadModels?: (signal: AbortSignal) => Promise<ModelInfo[]>
}

/** Provider da configuração de execução (modelo, max_tokens, temperature) dos dois fluxos. */
export function RunConfigProvider({
  children,
  loadLimits = getBackendLimits,
  loadModels = getModelCatalog,
}: RunConfigProviderProps): JSX.Element {
  const [config, setConfig] = useState<RunConfig>(readStoredConfig)
  const [maxTokensLimit, setMaxTokensLimit] = useState<number | null>(null)
  const [models, setModels] = useState<readonly ModelInfo[]>([])
  const [modelsStatus, setModelsStatus] = useState<ModelsStatus>('loading')
  const [modelsReloadToken, setModelsReloadToken] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    loadLimits(controller.signal)
      .then((limits) => {
        const limit = limits.max_tokens_limit
        setMaxTokensLimit(limit)
        setConfig((prev) => {
          if (prev.maxTokens <= limit) return prev
          const next = { ...prev, maxTokens: limit }
          persistConfig(next)
          return next
        })
      })
      .catch(() => {
        // Sem o limite do backend (fora do ar, resposta inválida, desmontagem), o campo segue sem
        // teto local; o backend continua recusando um `max_tokens` acima do dele.
      })
    return () => controller.abort()
  }, [loadLimits])

  useEffect(() => {
    const controller = new AbortController()
    loadModels(controller.signal)
      .then((catalog) => {
        setModels(catalog)
        setModelsStatus('ready')
        setConfig((prev) => {
          const modelName = pickCatalogModel(prev.modelName, catalog)
          if (modelName === prev.modelName) return prev
          const next = { ...prev, modelName }
          persistConfig(next)
          return next
        })
      })
      .catch(() => {
        // Sem o catálogo, a lista avisa a falha e o modelo em uso (salvo ou default) continua valendo.
        if (!controller.signal.aborted) setModelsStatus('error')
      })
    return () => controller.abort()
  }, [loadModels, modelsReloadToken])

  const reloadModels = useCallback(() => {
    setModelsReloadToken((token) => token + 1)
  }, [])

  const setModelName = useCallback((model: string) => {
    setConfig((prev) => {
      const next = { ...prev, modelName: model }
      persistConfig(next)
      return next
    })
  }, [])

  const setMaxTokens = useCallback((value: number) => {
    setConfig((prev) => {
      const next = { ...prev, maxTokens: clampMaxTokens(value, maxTokensLimit) }
      persistConfig(next)
      return next
    })
  }, [maxTokensLimit])

  const setTemperature = useCallback((value: number) => {
    setConfig((prev) => {
      const next = { ...prev, temperature: clampTemperature(value) }
      persistConfig(next)
      return next
    })
  }, [])

  const setProvider = useCallback((value: string) => {
    setConfig((prev) => {
      const next = { ...prev, provider: normalizeProvider(value) }
      persistConfig(next)
      return next
    })
  }, [])

  const reset = useCallback(() => {
    const defaults = defaultConfig()
    const base = {
      ...defaults,
      modelName: pickCatalogModel(defaults.modelName, models),
      maxTokens: clampMaxTokens(defaults.maxTokens, maxTokensLimit),
    }
    setConfig(base)
    persistConfig(base)
  }, [maxTokensLimit, models])

  const value = useMemo<RunConfigState>(
    () => ({
      config,
      maxTokensLimit,
      models,
      modelsStatus,
      reloadModels,
      setModelName,
      setMaxTokens,
      setTemperature,
      setProvider,
      reset,
    }),
    [
      config,
      maxTokensLimit,
      models,
      modelsStatus,
      reloadModels,
      setModelName,
      setMaxTokens,
      setTemperature,
      setProvider,
      reset,
    ],
  )

  return <RunConfigContext.Provider value={value}>{children}</RunConfigContext.Provider>
}

export function useRunConfig(): RunConfigState {
  const context = useContext(RunConfigContext)
  if (!context) {
    throw new Error('useRunConfig precisa ser usado dentro de um RunConfigProvider')
  }
  return context
}
