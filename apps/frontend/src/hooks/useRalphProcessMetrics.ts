// Busca, sob demanda, as sessões Ralph das questões analisadas e guarda só as métricas do processo
// (as sessões completas são grandes). As métricas ficam num cache de módulo: reabrir a análise ou
// mudar a seleção não rebusca o que já foi carregado.

import { useCallback, useEffect, useRef, useState } from 'react'
import { getSession } from '@/api/sessionApi'
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

function snapshot(sessionIds: readonly string[]): Map<string, RalphProcessMetrics> {
  const result = new Map<string, RalphProcessMetrics>()
  for (const id of sessionIds) {
    const metrics = metricsCache.get(id)
    if (metrics !== undefined) result.set(id, metrics)
  }
  return result
}

export function useRalphProcessMetrics(sessionIds: readonly string[]): RalphProcessMetricsState {
  const [enabled, setEnabled] = useState(false)
  const [metrics, setMetrics] = useState(() => snapshot(sessionIds))
  const [running, setRunning] = useState(false)
  const [failed, setFailed] = useState(0)
  const idsKey = sessionIds.join('|')
  const idsRef = useRef(sessionIds)
  idsRef.current = sessionIds

  useEffect(() => {
    const ids = idsRef.current
    setMetrics(snapshot(ids))
    setFailed(0)
    if (!enabled) return undefined
    const pending = ids.filter((id) => !metricsCache.has(id))
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
          const document = await getSession(id, controller.signal)
          metricsCache.set(id, ralphProcessMetrics(document))
        } catch {
          if (controller.signal.aborted) return
          failures += 1
          setFailed(failures)
        }
        if (!controller.signal.aborted) setMetrics(snapshot(ids))
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
