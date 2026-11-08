// Execução de bateria de benchmark em andamento. Vive acima das rotas (em `AppRouter`) para que a
// conexão sobreviva à navegação: o usuário pode abrir as sessões de uma questão e voltar à página
// do BenchMark sem interromper a bateria — só recarregar a página ou cancelar a encerra.

import type { ReactNode } from 'react'
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { AppError } from '@/api/errors/AppError'
import { ContractError } from '@/api/errors/ContractError'
import { type BenchmarkRunParams, buildBenchmarkRunPayload } from '@/api/benchmarkApi'
import {
  type BenchmarkStreamHandle,
  type BenchmarkStreamHandlers,
  openBenchmarkRerunStream,
  openBenchmarkStream,
} from '@/api/benchmarkStreamClient'
import type { BenchmarkDatasetId, BenchmarkSessionDocument } from '@/domain/types/benchmarkSession'

export type BenchmarkRunPhase =
  'idle' | 'connecting' | 'running' | 'finished' | 'cancelled' | 'error'

export interface BenchmarkRunState {
  phase: BenchmarkRunPhase
  /** Último estado recebido da bateria; `null` antes do primeiro frame. */
  session: BenchmarkSessionDocument | null
  /** Benchmark da bateria atual (conhecido antes do primeiro frame); `null` quando ociosa. */
  benchmark: BenchmarkDatasetId | null
  error: AppError | null
  /** Recusa do servidor (frame `error`) ou falha da conexão, já em texto para o usuário. */
  rejection: string | null
  /** Questões da reexecução atual (ou encerrada há pouco); vazio numa bateria nova. */
  rerunQuestionIds: string[]
  /** Incrementa a cada bateria que termina — sinaliza às listas que precisam recarregar. */
  finishedCount: number
}

interface BenchmarkRunContextValue extends BenchmarkRunState {
  isActive: boolean
  start: (params: BenchmarkRunParams) => void
  /** Reexecuta os fluxos errados de uma ou mais questões da mesma bateria já encerrada. */
  rerun: (benchmarkSessionId: string, questionIds: string | string[], benchmark: BenchmarkDatasetId) => void
  cancel: () => void
  dismiss: () => void
}

const INITIAL_STATE: BenchmarkRunState = {
  phase: 'idle',
  session: null,
  benchmark: null,
  error: null,
  rejection: null,
  rerunQuestionIds: [],
  finishedCount: 0,
}

const BenchmarkRunContext = createContext<BenchmarkRunContextValue | undefined>(undefined)

function toAppError(error: unknown): AppError {
  return error instanceof AppError ? error : new ContractError(String(error))
}

export function BenchmarkRunProvider({ children }: { children: ReactNode }): JSX.Element {
  const [state, setState] = useState<BenchmarkRunState>(INITIAL_STATE)
  const handleRef = useRef<BenchmarkStreamHandle | null>(null)

  useEffect(() => () => handleRef.current?.close(), [])

  const connect = useCallback(
    (
      open: (handlers: BenchmarkStreamHandlers) => BenchmarkStreamHandle,
      benchmark: BenchmarkDatasetId,
      rerunQuestionIds: string[],
    ) => {
      setState((prev) => ({
        ...prev,
        phase: 'connecting',
        session: null,
        benchmark,
        error: null,
        rejection: null,
        rerunQuestionIds,
      }))
      handleRef.current = open({
        onSession: (session, isFinal) => {
          setState((prev) => ({
            ...prev,
            session,
            phase: isFinal ? 'finished' : 'running',
            finishedCount: isFinal ? prev.finishedCount + 1 : prev.finishedCount,
          }))
        },
        onErrorFrame: (content) => setState((prev) => ({ ...prev, rejection: content })),
        onClose: () => {
          handleRef.current = null
        },
        onFailure: (error) => {
          handleRef.current = null
          // Uma bateria que não conclui fecha com 1011 depois do frame `result`: o desfecho já
          // está no documento, então o fechamento não vira um erro de conexão por cima dele.
          setState((prev) =>
            prev.phase === 'finished'
              ? prev
              : {
                  ...prev,
                  phase: 'error',
                  error,
                  rejection: prev.rejection ?? error.userMessage,
                  finishedCount: prev.finishedCount + 1,
                },
          )
        },
        onFrameWarning: (message) => console.warn(`[BenchmarkRunContext] ${message}`),
      })
    },
    [],
  )

  const start = useCallback(
    (params: BenchmarkRunParams) => {
      if (handleRef.current) return

      let payload
      try {
        payload = buildBenchmarkRunPayload(params)
      } catch (error) {
        const appError = toAppError(error)
        setState((prev) => ({
          ...prev,
          phase: 'error',
          session: null,
          benchmark: params.benchmark ?? 'vestibular',
          error: appError,
          rejection: appError.userMessage,
          rerunQuestionIds: [],
        }))
        return
      }

      connect(
        (handlers) => openBenchmarkStream(payload, handlers),
        params.benchmark ?? 'vestibular',
        [],
      )
    },
    [connect],
  )

  const rerun = useCallback(
    (benchmarkSessionId: string, questionIds: string | string[], benchmark: BenchmarkDatasetId) => {
      if (handleRef.current) return
      if (Array.isArray(questionIds) && questionIds.length === 0) return
      connect(
        (handlers) => openBenchmarkRerunStream(benchmarkSessionId, questionIds, handlers),
        benchmark,
        typeof questionIds === 'string' ? [questionIds] : [...questionIds],
      )
    },
    [connect],
  )

  const cancel = useCallback(() => {
    if (!handleRef.current) return
    handleRef.current.close()
    handleRef.current = null
    setState((prev) => ({ ...prev, phase: 'cancelled', finishedCount: prev.finishedCount + 1 }))
  }, [])

  const dismiss = useCallback(() => {
    if (handleRef.current) return
    setState((prev) => ({ ...INITIAL_STATE, finishedCount: prev.finishedCount }))
  }, [])

  const value = useMemo<BenchmarkRunContextValue>(
    () => ({
      ...state,
      isActive: state.phase === 'connecting' || state.phase === 'running',
      start,
      rerun,
      cancel,
      dismiss,
    }),
    [state, start, rerun, cancel, dismiss],
  )

  return <BenchmarkRunContext.Provider value={value}>{children}</BenchmarkRunContext.Provider>
}

export function useBenchmarkRun(): BenchmarkRunContextValue {
  const context = useContext(BenchmarkRunContext)
  if (!context) {
    throw new Error('useBenchmarkRun precisa ser usado dentro de um BenchmarkRunProvider')
  }
  return context
}
