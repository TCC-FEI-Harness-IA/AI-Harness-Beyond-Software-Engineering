// `unknown` → `SessionListResponse` (README, FASE 02, seção 5) — `GET /v1/sessions`.

import type { SessionListResponse } from '@/domain/types/sessionListResponse'
import { ContractError } from '../errors/ContractError'
import { requireArray, requireObject } from './primitives'

export function parseSessionList(raw: unknown): SessionListResponse {
  const obj = requireObject(raw, 'sessionList')
  const rawIds = requireArray(obj, 'session_ids', 'session_ids')

  const session_ids = rawIds.map((id, index) => {
    if (typeof id !== 'string') {
      throw new ContractError(
        `campo "session_ids[${index}]" deveria ser string, recebeu: ${JSON.stringify(id)}`,
      )
    }
    return id
  })

  return { session_ids }
}
