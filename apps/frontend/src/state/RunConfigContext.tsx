// Modelo, teto de tokens e temperatura — configuração de execução compartilhada pelos dois
// fluxos de inferência (README, FASE 04, seção 4). Vive em Context para sobreviver à navegação
// entre a home e as telas de chat, sem precisar passar por props em cascata.

import type { ReactNode } from 'react'
import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import type { RunConfig } from '@/api/messageApi'
import { env } from '@/config/env'
import { type ModelProvider, isModelProvider } from '@/domain/enums/modelProvider'

const STORAGE_KEY = 'tcc.runConfig'

interface StoredRunConfig {
  modelName: string
  maxTokens: number
  temperature: number
  provider?: string
}

interface RunConfigState {
  config: RunConfig
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

function clampMaxTokens(value: number): number {
  if (!Number.isFinite(value)) return env.defaultMaxTokens
  return Math.max(1, Math.trunc(value))
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

// localStorage pode lançar em janela privada — o app segue com o default nesse caso. Um
// modelo salvo que saiu de `env.availableModels` também volta para o default em vez de
// produzir um payload que o backend recusaria com 422 (README, FASE 04, seção 4).
function readStoredConfig(): RunConfig {
  const base = defaultConfig()
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (raw === null) return base

    const parsed: unknown = JSON.parse(raw)
    if (!isStoredRunConfig(parsed)) return base

    return {
      ...base,
      modelName: env.availableModels.includes(parsed.modelName) ? parsed.modelName : base.modelName,
      maxTokens: clampMaxTokens(parsed.maxTokens),
      temperature: clampTemperature(parsed.temperature),
      provider: normalizeProvider(parsed.provider),
    }
  } catch {
    return base
  }
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
}

/** Provider da configuração de execução (modelo, max_tokens, temperature) dos dois fluxos. */
export function RunConfigProvider({ children }: RunConfigProviderProps): JSX.Element {
  const [config, setConfig] = useState<RunConfig>(readStoredConfig)

  const setModelName = useCallback((model: string) => {
    setConfig((prev) => {
      const next = { ...prev, modelName: model }
      persistConfig(next)
      return next
    })
  }, [])

  const setMaxTokens = useCallback((value: number) => {
    setConfig((prev) => {
      const next = { ...prev, maxTokens: clampMaxTokens(value) }
      persistConfig(next)
      return next
    })
  }, [])

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
    const base = defaultConfig()
    setConfig(base)
    persistConfig(base)
  }, [])

  const value = useMemo<RunConfigState>(
    () => ({ config, setModelName, setMaxTokens, setTemperature, setProvider, reset }),
    [config, setModelName, setMaxTokens, setTemperature, setProvider, reset],
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
