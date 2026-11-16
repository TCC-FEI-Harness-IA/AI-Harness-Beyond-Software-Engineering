// Carrega uma sessão pelo caminho certo: as de uma publicação oficial (`pub_...`) vêm da API
// pública, que confere que a sessão pertence à publicação; as demais, da API privada da conta.

import type { SessionDocument } from '../domain/types/sessionDocument'
import { getOfficialSession } from './publicBenchmarkApi'
import { getSession } from './sessionApi'

export function loadSessionDocument(
  sessionId: string,
  containerId: string | null,
  signal?: AbortSignal,
): Promise<SessionDocument> {
  if (containerId !== null && containerId.startsWith('pub_')) {
    return getOfficialSession(containerId, sessionId, signal)
  }
  return getSession(sessionId, signal)
}
