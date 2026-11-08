// Orquestração do fluxo simples: chama `POST /v1/message/default`, mantém o `SimpleRun` da
// tela e trata otimismo, erro e cancelamento (README, FASE 04, seção 7).

import { useCallback, useEffect, useRef, useState } from 'react'
import { AppError } from '../api/errors/AppError'
import { CanceledError } from '../api/errors/CanceledError'
import { ContractError } from '../api/errors/ContractError'
import { buildInferencePayload, sendDefaultMessage, type RunConfig } from '../api/messageApi'
import { RUN_STATUS } from '../domain/enums/runStatus'
import { simpleRunFromResponse } from '../domain/services/buildSimpleRun'
import type { SimpleMessage, SimpleRun } from '../domain/types/simpleRun'
import { useDeferredTeardown } from './useDeferredTeardown'

export interface UseSimpleInference {
  run: SimpleRun
  isBusy: boolean
  send: (question: string) => void
  retry: () => void
  reset: () => void
}

const EMPTY_RUN: SimpleRun = {
  sessionId: null,
  status: RUN_STATUS.IDLE,
  messages: [],
  totals: null,
  error: null,
}

function createUserMessageId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `msg_${crypto.randomUUID()}`
  }
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2)}`
}

// `sendDefaultMessage` só deveria rejeitar com `AppError` (contrato da camada `api/`) — um
// erro inesperado ainda precisa virar algo exibível, em vez de quebrar o estado da tela.
function toDisplayableError(error: unknown): AppError {
  return error instanceof AppError ? error : new ContractError(String(error))
}

export function useSimpleInference(config: RunConfig): UseSimpleInference {
  const [run, setRun] = useState<SimpleRun>(EMPTY_RUN)
  const [isBusy, setIsBusy] = useState(false)
  const lastQuestionRef = useRef<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const mountedRef = useRef(true)
  const configRef = useRef(config)
  configRef.current = config

  useEffect(() => {
    // Redefine para `true` a cada execução do efeito — não só no `useRef(true)` inicial.
    // Em desenvolvimento, o StrictMode roda montagem → limpeza → montagem de novo para
    // detectar efeitos impuros; sem isto, a limpeza simulada deixaria `mountedRef.current`
    // travado em `false` para sempre, mesmo com o componente genuinamente montado.
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  // Abortar direto na limpeza cancelava, na passagem simulada do StrictMode, a requisição
  // que a montagem anterior tinha acabado de disparar — o auto-start de `SimpleChatPage`
  // morria assim, e o `AbortError` chegava à tela como "formato inesperado".
  useDeferredTeardown(() => abortControllerRef.current?.abort())

  const runInference = useCallback((question: string) => {
    const controller = new AbortController()
    abortControllerRef.current = controller
    setIsBusy(true)

    let payload
    try {
      payload = buildInferencePayload(question, configRef.current)
    } catch (error) {
      setIsBusy(false)
      setRun((prev) => ({ ...prev, status: RUN_STATUS.FAILED, error: toDisplayableError(error) }))
      return
    }

    sendDefaultMessage(payload, controller.signal)
      .then((response) => {
        if (!mountedRef.current) return
        const pairRun = simpleRunFromResponse(question, response, configRef.current.modelName)
        setRun((prev) => ({
          sessionId: pairRun.sessionId,
          status: RUN_STATUS.COMPLETED,
          // Substitui a mensagem otimista do usuário (sem stats) pelo par completo que
          // `simpleRunFromResponse` monta — mesmo conteúdo, agora com a resposta ao lado.
          messages: [...prev.messages.slice(0, -1), ...pairRun.messages],
          totals: pairRun.totals,
          error: null,
        }))
      })
      .catch((error: unknown) => {
        // Cancelamento é decisão do próprio app (`reset()`, desmontagem): quem cancelou já
        // sabe o que aconteceu e o estado que ele quis deixar na tela não pode virar "falhou".
        if (!mountedRef.current || error instanceof CanceledError) return
        setRun((prev) => ({ ...prev, status: RUN_STATUS.FAILED, error: toDisplayableError(error) }))
      })
      .finally(() => {
        if (mountedRef.current) setIsBusy(false)
      })
  }, [])

  const send = useCallback(
    (question: string) => {
      const trimmed = question.trim()
      if (trimmed === '' || isBusy) return

      lastQuestionRef.current = trimmed
      const userMessage: SimpleMessage = {
        id: createUserMessageId(),
        role: 'user',
        content: trimmed,
        stats: null,
      }
      setRun((prev) => ({
        ...prev,
        status: RUN_STATUS.RUNNING,
        error: null,
        messages: [...prev.messages, userMessage],
      }))

      runInference(trimmed)
    },
    [isBusy, runInference],
  )

  const retry = useCallback(() => {
    const question = lastQuestionRef.current
    if (question === null || isBusy) return
    setRun((prev) => ({ ...prev, status: RUN_STATUS.RUNNING, error: null }))
    runInference(question)
  }, [isBusy, runInference])

  const reset = useCallback(() => {
    lastQuestionRef.current = null
    abortControllerRef.current?.abort()
    setRun(EMPTY_RUN)
    setIsBusy(false)
  }, [])

  return { run, isBusy, send, retry, reset }
}
