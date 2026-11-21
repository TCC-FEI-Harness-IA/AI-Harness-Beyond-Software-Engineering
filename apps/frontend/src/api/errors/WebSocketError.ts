// Falha ao abrir a conexão do WebSocket, ou fechamento anômalo (código diferente de 1000).
// Carrega o código de fechamento, quando existe (README, FASE 02, seção 6 e 8).

import { AppError } from './AppError'
import { wsCloseCodeMessage } from './messages'

export class WebSocketError extends AppError {
  public readonly code: number | null

  constructor(message: string, userMessage: string, code: number | null = null) {
    super(message, userMessage)
    this.code = code
  }

  static fromCloseCode(code: number): WebSocketError {
    return new WebSocketError(
      `WebSocket fechado com código ${code}.`,
      wsCloseCodeMessage(code),
      code,
    )
  }
}
