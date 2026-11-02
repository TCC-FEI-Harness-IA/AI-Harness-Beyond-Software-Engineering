// `unknown` → `BackendLimits`, a resposta de `GET /v1/limits`.

import type { BackendLimits } from '@/domain/types/backendLimits'
import { ContractError } from '../errors/ContractError'
import { requireNumber, requireObject } from './primitives'

export function parseBackendLimits(raw: unknown): BackendLimits {
  const obj = requireObject(raw, 'backendLimits')
  const maxTokensLimit = requireNumber(obj, 'max_tokens_limit', 'max_tokens_limit')
  if (!Number.isInteger(maxTokensLimit) || maxTokensLimit <= 0) {
    throw new ContractError(
      `campo "max_tokens_limit" deveria ser um inteiro positivo, recebeu: ${maxTokensLimit}`,
    )
  }
  return { max_tokens_limit: maxTokensLimit }
}
