// `GET /v1/sessions` e `GET /v1/sessions/{id}` (README, FASE 02, seção 9).

import type { SessionDocument } from '../domain/types/sessionDocument'
import { httpClient } from './httpClient'
import { parseSessionDocument } from './parsers/sessionDocument'
import { parseSessionList } from './parsers/sessionList'

const SESSIONS_PATH = '/sessions'

// Devolve já o array de dentro do envelope `{ session_ids: [...] }` — nenhum consumidor
// precisa conhecer a forma da resposta.
export async function listSessionIds(signal?: AbortSignal): Promise<string[]> {
  const response = await httpClient.get(SESSIONS_PATH, parseSessionList, signal)
  return response.session_ids
}

export function getSession(sessionId: string, signal?: AbortSignal): Promise<SessionDocument> {
  return httpClient.get(`${SESSIONS_PATH}/${encodeURIComponent(sessionId)}`, parseSessionDocument, signal)
}
