// Consultas de benchmark sobre o tripé genérico `useAsync` (README, FASE 02, seção 11).

import { getBenchmarkDataset, getBenchmarkSession, listBenchmarkSessions } from '@/api/benchmarkApi'
import type { BenchmarkDataset, BenchmarkSessionDocument } from '@/domain/types/benchmarkSession'
import { type AsyncState, useAsync } from './useAsync'

type WithReload<T> = AsyncState<T> & { reload: () => void }

export function useBenchmarkDataset(): WithReload<BenchmarkDataset> {
  return useAsync((signal) => getBenchmarkDataset(signal), [])
}

/** Lista as baterias; `refreshToken` diferente força nova busca (ex.: ao fim de uma bateria). */
export function useBenchmarkSessions(refreshToken = 0): WithReload<BenchmarkSessionDocument[]> {
  return useAsync((signal) => listBenchmarkSessions(signal), [refreshToken])
}

/** Carrega uma bateria; `null` não busca nada e resolve com `null`. */
export function useBenchmarkSession(
  benchmarkSessionId: string | null,
  refreshToken = 0,
): WithReload<BenchmarkSessionDocument | null> {
  return useAsync(
    (signal) =>
      benchmarkSessionId === null
        ? Promise.resolve(null)
        : getBenchmarkSession(benchmarkSessionId, signal),
    [benchmarkSessionId, refreshToken],
  )
}
