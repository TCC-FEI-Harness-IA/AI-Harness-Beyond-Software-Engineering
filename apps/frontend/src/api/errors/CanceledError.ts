// O próprio app abortou a requisição pelo `AbortSignal` do chamador — desmontagem da tela,
// `reset()` da execução. Não é falha de servidor nem de rede: quem cancelou já sabe o que
// aconteceu, então a `userMessage` só existe para o caso de alguém exibi-la por engano.

import { AppError } from './AppError'
import { CANCELED_ERROR_MESSAGE } from './messages'

export class CanceledError extends AppError {
  constructor() {
    super('A requisição foi cancelada pelo app.', CANCELED_ERROR_MESSAGE)
  }
}
