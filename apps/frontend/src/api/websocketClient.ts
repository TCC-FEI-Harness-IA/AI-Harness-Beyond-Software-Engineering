// Única abstração de WebSocket do app (README, FASE 02, seção 8). Protocolo de execução
// única: um frame de abertura, N frames de evento, um fechamento — sem reconexão automática.

import { env } from '../config/env'
import type { DefaultInputDTO } from '../domain/types/defaultInput'
import type { ReasoningErrorFrame, ReasoningEventDTO } from '../domain/types/reasoningEvent'
import { AppError } from './errors/AppError'
import { ContractError } from './errors/ContractError'
import { WebSocketError } from './errors/WebSocketError'
import { WS_OPEN_TIMEOUT_MESSAGE } from './errors/messages'
import { parseReasoningFrame } from './parsers/reasoningFrame'

// Caminho constante do módulo — nenhum literal de rota espalhado (README, seção 8, item 1).
const REASONING_PATH = '/message/reasoning'

export interface ReasoningStreamHandlers {
  onEvent: (event: ReasoningEventDTO) => void
  onErrorFrame: (frame: ReasoningErrorFrame) => void
  onClose: (code: number) => void
  onFailure: (error: AppError) => void
}

export interface ReasoningStreamHandle {
  close: () => void
}

export function openReasoningStream(
  payload: DefaultInputDTO,
  handlers: ReasoningStreamHandlers,
): ReasoningStreamHandle {
  const socket = new WebSocket(`${env.wsBaseUrl}${REASONING_PATH}`)
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
    socket.send(JSON.stringify(payload))
  }

  function onMessage(event: MessageEvent): void {
    if (closed) return

    let raw: unknown
    try {
      raw = JSON.parse(String(event.data))
    } catch {
      handlers.onFailure(
        new ContractError(`frame do WebSocket não é JSON válido: ${String(event.data).slice(0, 200)}`),
      )
      return
    }

    try {
      const frame = parseReasoningFrame(raw)
      if ('subtype' in frame) {
        handlers.onEvent(frame)
      } else {
        handlers.onErrorFrame(frame)
      }
    } catch (error) {
      handlers.onFailure(error instanceof AppError ? error : new ContractError(String(error)))
    }
  }

  function onClose(event: CloseEvent): void {
    if (closed) return
    closed = true
    detach()

    handlers.onClose(event.code)
    if (event.code !== 1000) {
      handlers.onFailure(WebSocketError.fromCloseCode(event.code))
    }
  }

  // Sem detalhe útil no navegador (requisito 6) — apenas registra; quem decide é o onclose,
  // que sempre vem em seguida.
  function onError(): void {
    console.warn('[websocketClient] evento "error" recebido; aguardando "close" para decidir.')
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
      socket.close(1000)
    },
  }
}
