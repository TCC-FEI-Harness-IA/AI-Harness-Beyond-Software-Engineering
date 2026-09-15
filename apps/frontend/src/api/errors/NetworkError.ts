// `fetch` rejeitou por DNS, offline, ou outra falha de rede antes de haver resposta.

import { AppError } from './AppError'
import { NETWORK_ERROR_MESSAGE } from './messages'

export class NetworkError extends AppError {
  constructor(cause: unknown) {
    super(`Falha de rede: ${String(cause)}`, NETWORK_ERROR_MESSAGE)
  }
}
