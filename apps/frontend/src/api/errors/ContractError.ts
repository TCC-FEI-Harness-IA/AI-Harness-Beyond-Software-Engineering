// Resposta fora do contrato: campo obrigatório ausente, de tipo errado, ou corpo que não é
// o JSON esperado. Lançado pelos parsers de fronteira (README, FASE 02, seção 5).

import { AppError } from './AppError'
import { CONTRACT_ERROR_MESSAGE } from './messages'

export class ContractError extends AppError {
  constructor(reason: string) {
    super(`Violação de contrato: ${reason}`, CONTRACT_ERROR_MESSAGE)
  }
}
