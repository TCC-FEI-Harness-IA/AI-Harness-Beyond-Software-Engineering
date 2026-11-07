// WebSocket de `WS /v1/benchmark/run` (README, FASE 02, seção 8): um frame de abertura com os
// parâmetros da bateria, N frames `progress` com o documento inteiro da bateria e um `result`
// final. Fechar a conexão pelo cliente interrompe a bateria no servidor.
//
// `WS /v1/benchmark/sessions/{id}/questions/{question_id}/rerun` fala o mesmo protocolo de frames,
// mas sem frame de abertura: a configuração do modelo vem da própria bateria persistida.

import { env } from '../config/env'
import type { BenchmarkRunInput, BenchmarkSessionDocument } from '../domain/types/benchmarkSession'
import { AppError } from './errors/AppError'
import { WebSocketError } from './errors/WebSocketError'
import { WS_OPEN_TIMEOUT_MESSAGE } from './errors/messages'
import { parseBenchmarkFrame } from './parsers/benchmarkSession'

const BENCHMARK_RUN_PATH = '/benchmark/run'
const BENCHMARK_SESSIONS_PATH = '/benchmark/sessions'
const NORMAL_CLOSE = 1000

export interface BenchmarkStreamHandlers {
  /** Estado atual da bateria; `isFinal` marca o frame `result`, já encerrado. */
  onSession: (session: BenchmarkSessionDocument, isFinal: boolean) => void
  /** O servidor recusou os parâmetros (frame `error`), antes de criar a bateria. */
  onErrorFrame: (content: string) => void
  onClose: (code: number) => void
  onFailure: (error: AppError) => void
  /** Um frame ilegível foi descartado; a conexão segue aberta. */
  onFrameWarning: (message: string) => void
}

export interface BenchmarkStreamHandle {
  close: () => void
}

/** Abre a bateria: envia `payload` como frame de abertura e entrega o estado a cada mudança. */
export function openBenchmarkStream(
  payload: BenchmarkRunInput,
  handlers: BenchmarkStreamHandlers,
): BenchmarkStreamHandle {
  return openStream(BENCHMARK_RUN_PATH, payload, handlers)
}

/** Reexecuta os fluxos errados de uma questão de uma bateria encerrada. */
export function openBenchmarkRerunStream(
  benchmarkSessionId: string,
  questionId: string,
  handlers: BenchmarkStreamHandlers,
): BenchmarkStreamHandle {
  const path = `${BENCHMARK_SESSIONS_PATH}/${encodeURIComponent(benchmarkSessionId)}/questions/${encodeURIComponent(questionId)}/rerun`
  return openStream(path, null, handlers)
}

function openStream(
  path: string,
  payload: BenchmarkRunInput | null,
  handlers: BenchmarkStreamHandlers,
): BenchmarkStreamHandle {
  const socket = new WebSocket(`${env.wsBaseUrl}${path}`)
  let opened = false
  let closed = false

  function detach(): void {
    clearTimeout(openTimer)
    socket.removeEventListener('open', onOpen)
    socket.removeEventListener('message', onMessage)
    socket.removeEventListener('close', onClose)
    socket.removeEventListener('error', onError)
  }

  function onOpen(): void {
    if (opened || closed) return
    opened = true
    clearTimeout(openTimer)
    if (payload !== null) socket.send(JSON.stringify(payload))
  }

  function onMessage(event: MessageEvent): void {
    if (closed) return

    let raw: unknown
    try {
      raw = JSON.parse(String(event.data))
    } catch {
      handlers.onFrameWarning(
        `frame do WebSocket não é JSON válido: ${String(event.data).slice(0, 200)}`,
      )
      return
    }

    try {
      const frame = parseBenchmarkFrame(raw)
      if (frame.type === 'error') {
        handlers.onErrorFrame(frame.content)
      } else {
        handlers.onSession(frame.benchmark_session, frame.type === 'result')
      }
    } catch (error) {
      /* v8 ignore next */
      const message = error instanceof AppError ? error.message : String(error)
      handlers.onFrameWarning(message)
    }
  }

  function onClose(event: CloseEvent): void {
    if (closed) return
    closed = true
    detach()

    handlers.onClose(event.code)
    if (event.code !== NORMAL_CLOSE) {
      handlers.onFailure(WebSocketError.fromCloseCode(event.code))
    }
  }

  function onError(): void {
    console.warn(
      '[benchmarkStreamClient] evento "error" recebido; aguardando "close" para decidir.',
    )
  }

  const openTimer = setTimeout(() => {
    if (opened || closed) return
    closed = true
    detach()
    socket.close()
    handlers.onFailure(
      new WebSocketError('Timeout esperando o WebSocket abrir.', WS_OPEN_TIMEOUT_MESSAGE),
    )
  }, env.wsOpenTimeoutMs)

  socket.addEventListener('open', onOpen)
  socket.addEventListener('message', onMessage)
  socket.addEventListener('close', onClose)
  socket.addEventListener('error', onError)

  return {
    close: () => {
      if (closed) return
      closed = true
      detach()
      socket.close(NORMAL_CLOSE)
    },
  }
}
