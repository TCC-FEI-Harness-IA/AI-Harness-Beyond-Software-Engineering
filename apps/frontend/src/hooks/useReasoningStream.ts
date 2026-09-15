// Orquestração do fluxo do Ralph: abre `WS /v1/message/reasoning`, liga os frames ao
// `reasoningRunReducer` e mantém o `ThinkingRun` da tela (README, FASE 05, seção 6).

import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { AppError } from '../api/errors/AppError'
import { ContractError } from '../api/errors/ContractError'
import { buildInferencePayload, openReasoning, type RunConfig } from '../api/messageApi'
import type { ReasoningStreamHandle } from '../api/websocketClient'
import { RUN_STATUS } from '../domain/enums/runStatus'
import { createEmptyRun, reasoningRunReducer, type RunAction } from '../domain/services/reasoningRunReducer'
import type { ThinkingRun } from '../domain/types/thinkingRun'

export interface UseReasoningStream {
  run: ThinkingRun
  isStreaming: boolean
  start: (question: string) => void
  cancel: () => void
  reset: () => void
}

type HookAction =
  | RunAction
  | { kind: 'start'; question: string; modelName: string }
  | { kind: 'idle'; modelName: string }

// `reasoningRunReducer` só conhece as quatro ações de evento do contrato (README, FASE 05,
// seção 4) — abrir um `ThinkingRun` vazio para uma pergunta nova é orquestração do hook, não
// lógica de processamento de evento, então este wrapper fino só resolve isso e delega tudo o
// mais para o reducer puro, sem duplicar nenhuma regra dele.
function hookReducer(run: ThinkingRun, action: HookAction): ThinkingRun {
  if (action.kind === 'start') {
    return { ...createEmptyRun(action.question, action.modelName), status: RUN_STATUS.RUNNING }
  }
  if (action.kind === 'idle') {
    return createEmptyRun('', action.modelName)
  }
  return reasoningRunReducer(run, action)
}

function toDisplayableError(error: unknown): AppError {
  return error instanceof AppError ? error : new ContractError(String(error))
}

export function useReasoningStream(config: RunConfig): UseReasoningStream {
  const [run, dispatch] = useReducer(hookReducer, config.modelName, (modelName) => createEmptyRun('', modelName))
  const [isStreaming, setIsStreaming] = useState(false)
  const handleRef = useRef<ReasoningStreamHandle | null>(null)
  const mountedRef = useRef(true)
  const configRef = useRef(config)
  configRef.current = config

  useEffect(() => {
    // Mesmo motivo do `useSimpleInference` (FASE 04): o StrictMode roda montagem → limpeza →
    // montagem de novo em desenvolvimento, e sem isto a limpeza simulada travaria
    // `mountedRef.current` em `false` para sempre mesmo com o componente genuinamente montado.
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      handleRef.current?.close()
      handleRef.current = null
    }
  }, [])

  const start = useCallback((question: string) => {
    // Nunca abre duas conexões (README, FASE 05, seção 6, requisito 5).
    if (handleRef.current) return

    let payload
    try {
      payload = buildInferencePayload(question, configRef.current)
    } catch (error) {
      dispatch({ kind: 'failure', error: toDisplayableError(error) })
      return
    }

    dispatch({ kind: 'start', question, modelName: configRef.current.modelName })
    setIsStreaming(true)

    const handle = openReasoning(payload, {
      onEvent: (event) => {
        if (!mountedRef.current) return
        dispatch({ kind: 'event', event })
      },
      onErrorFrame: (frame) => {
        if (!mountedRef.current) return
        dispatch({ kind: 'errorFrame', frame })
      },
      onFrameWarning: (message) => {
        if (!mountedRef.current) return
        console.warn('[useReasoningStream] frame ignorado:', message)
        dispatch({ kind: 'warning', message })
      },
      onClose: (code) => {
        handleRef.current = null
        if (!mountedRef.current) return
        dispatch({ kind: 'closed', code })
        setIsStreaming(false)
      },
      onFailure: (error) => {
        if (!mountedRef.current) return
        dispatch({ kind: 'failure', error })
      },
    })

    handleRef.current = handle
  }, [])

  // `handle.close()` desliga os próprios listeners do socket antes de fechar (FASE 02) — não
  // há como um evento chegar depois disto, então nenhum guard extra é necessário aqui.
  const cancel = useCallback(() => {
    handleRef.current?.close()
    handleRef.current = null
    setIsStreaming(false)
  }, [])

  const reset = useCallback(() => {
    handleRef.current?.close()
    handleRef.current = null
    setIsStreaming(false)
    dispatch({ kind: 'idle', modelName: configRef.current.modelName })
  }, [])

  return { run, isStreaming, start, cancel, reset }
}
