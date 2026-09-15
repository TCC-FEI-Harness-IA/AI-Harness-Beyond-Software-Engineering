// Cache em memória de `SessionDocument`, compartilhado por `useSessionList`, `useSession` e
// `HistorySidebar` (README, FASE 07, seção 4, requisito 5) — evita rebuscar a mesma sessão ao
// navegar lista → detalhe → lista. Módulo singleton: carregado uma única vez pelo bundler, então
// todo hook que o importa enxerga o mesmo `Map`.

import type { SessionDocument } from '@/domain/types/sessionDocument'

const cache = new Map<string, SessionDocument>()

export function getCachedSession(id: string): SessionDocument | undefined {
  return cache.get(id)
}

export function setCachedSession(document: SessionDocument): void {
  cache.set(document.id, document)
}

export function getAllCachedSessions(): SessionDocument[] {
  return [...cache.values()]
}
