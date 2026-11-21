// Estourou `env.requestTimeoutMs` (ou `env.wsOpenTimeoutMs`, no caso do WebSocket).

import { AppError } from './AppError'
import { TIMEOUT_ERROR_MESSAGE } from './messages'

export class TimeoutError extends AppError {
  constructor(timeoutMs: number) {
    super(`A requisição excedeu o timeout de ${timeoutMs}ms.`, TIMEOUT_ERROR_MESSAGE)
  }
}
