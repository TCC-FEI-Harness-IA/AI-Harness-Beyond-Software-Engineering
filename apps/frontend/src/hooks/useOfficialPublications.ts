// Resultados oficiais (públicos) sobre o tripé `useAsync`.

import { getOfficialPublication, listOfficialPublications } from '@/api/publicBenchmarkApi'
import type { OfficialPublication } from '@/domain/types/officialPublication'
import { type AsyncState, useAsync } from './useAsync'

type WithReload<T> = AsyncState<T> & { reload: () => void }

export function useOfficialPublications(): WithReload<OfficialPublication[]> {
  return useAsync((signal) => listOfficialPublications(signal), [])
}

/** Carrega uma publicação; `null` não busca nada. */
export function useOfficialPublication(publicationId: string | null): WithReload<OfficialPublication | null> {
  return useAsync(
    (signal) => (publicationId === null ? Promise.resolve(null) : getOfficialPublication(publicationId, signal)),
    [publicationId],
  )
}
