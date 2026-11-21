// `/v1/public/benchmarks*` — resultados oficiais, sem login e sem chamadas ao modelo.

import type { OfficialPublication } from '../domain/types/officialPublication'
import type { SessionDocument } from '../domain/types/sessionDocument'
import { httpClient } from './httpClient'
import { parseOfficialPublication, parseOfficialPublicationList } from './parsers/officialPublication'
import { parseSessionDocument } from './parsers/sessionDocument'

const PUBLIC_PATH = '/public/benchmarks'

export function listOfficialPublications(signal?: AbortSignal): Promise<OfficialPublication[]> {
  return httpClient.get(PUBLIC_PATH, parseOfficialPublicationList, signal)
}

export function getOfficialPublication(publicationId: string, signal?: AbortSignal): Promise<OfficialPublication> {
  return httpClient.get(`${PUBLIC_PATH}/${encodeURIComponent(publicationId)}`, (raw) => parseOfficialPublication(raw), signal)
}

/** Sessão filha de uma publicação; o servidor confere que ela pertence à publicação. */
export function getOfficialSession(
  publicationId: string,
  sessionId: string,
  signal?: AbortSignal,
): Promise<SessionDocument> {
  return httpClient.get(
    `${PUBLIC_PATH}/${encodeURIComponent(publicationId)}/sessions/${encodeURIComponent(sessionId)}`,
    parseSessionDocument,
    signal,
  )
}
