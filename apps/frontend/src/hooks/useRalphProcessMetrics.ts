// Busca, sob demanda, as sessões Ralph das questões analisadas e guarda só as métricas do processo
// (as sessões completas são grandes). As métricas ficam num cache de módulo: reabrir a análise ou
// mudar a seleção não rebusca o que já foi carregado.

import { useCallback, useEffect, useRef, useState } from 'react'
import { loadSessionDocument } from '@/api/sessionLoader'
import {
  type RalphProcessMetrics,
  ralphProcessMetrics,
} from '@/domain/services/ralphProcessMetrics'

const CONCURRENCY = 6
const metricsCache = new Map<string, RalphProcessMetrics>()

/** Só para testes: esvazia o cache entre cenários. */
export function clearRalphProcessMetricsCache(): void {
  metricsCache.clear()
}

export interface RalphProcessMetricsState {
  /** `true` depois que o usuário pediu a carga; a partir daí novas sessões entram sozinhas. */
  enabled: boolean
  running: boolean
  loaded: number
  failed: number
  total: number
  metrics: ReadonlyMap<string, RalphProcessMetrics>
  load: () => void
}

/** Chave do cache: a mesma sessão numa publicação oficial e numa conta são cópias independentes. */
function cacheKey(id: string, containers: ReadonlyMap<string, string> | undefined): string {
  return `${containers?.get(id) ?? 'privada'}:${id}`
}

function snapshot(
  sessionIds: readonly string[],
  containers: ReadonlyMap<string, string> | undefined,
): Map<string, RalphProcessMetrics> {
  const result = new Map<string, RalphProcessMetrics>()
  for (const id of sessionIds) {
    const metrics = metricsCache.get(cacheKey(id, containers))
    if (metrics !== undefined) result.set(id, metrics)
  }
  return result
}

/**
 * @param containerBySession Bateria (ou publicação oficial `pub_...`) de cada sessão: as sessões de
 * resultados oficiais são lidas pela API pública, sem login.
 */
export function useRalphProcessMetrics(
  sessionIds: readonly string[],
  containerBySession?: ReadonlyMap<string, string>,
): RalphProcessMetricsState {
  const [enabled, setEnabled] = useState(false)
  const [metrics, setMetrics] = useState(() => snapshot(sessionIds, containerBySession))
  const [running, setRunning] = useState(false)
  const [failed, setFailed] = useState(0)
  const idsKey = sessionIds.join('|')
  const idsRef = useRef(sessionIds)
  idsRef.current = sessionIds
  const containersRef = useRef(containerBySession)
  containersRef.current = containerBySession

  useEffect(() => {
    const ids = idsRef.current
    const containers = containersRef.current
    setMetrics(snapshot(ids, containers))
    setFailed(0)
    if (!enabled) return undefined
    const pending = ids.filter((id) => !metricsCache.has(cacheKey(id, containers)))
    if (pending.length === 0) {
      setRunning(false)
      return undefined
    }

    const controller = new AbortController()
    let cursor = 0
    let failures = 0
    setRunning(true)

    const worker = async (): Promise<void> => {
      while (cursor < pending.length && !controller.signal.aborted) {
        const id = pending[cursor] as string
        cursor += 1
        try {
          const document = await loadSessionDocument(id, containers?.get(id) ?? null, controller.signal)
          metricsCache.set(cacheKey(id, containers), ralphProcessMetrics(document))
        } catch {
          if (controller.signal.aborted) return
          failures += 1
          setFailed(failures)
        }
        if (!controller.signal.aborted) setMetrics(snapshot(ids, containers))
      }
    }

    void Promise.all(Array.from({ length: Math.min(CONCURRENCY, pending.length) }, worker)).then(() => {
      if (!controller.signal.aborted) setRunning(false)
    })

    return () => {
      controller.abort()
    }
  }, [enabled, idsKey])

  const load = useCallback(() => {
    setEnabled(true)
  }, [])

  return { enabled, running, loaded: metrics.size, failed, total: sessionIds.length, metrics, load }
}
