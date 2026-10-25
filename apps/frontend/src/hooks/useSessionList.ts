// Carrega a lista de histórico (README, FASE 07, seção 4). `GET /v1/sessions` só devolve ids —
// o resumo exigido pela tela (input do usuário) obriga a buscar cada sessão individualmente.
// Feito com pool de concorrência limitada, render progressivo, tolerância a falha individual e
// cache em memória — nunca um `Promise.all` de N chamadas de uma vez.

import { useCallback, useEffect, useState } from 'react'
import { AppError } from '@/api/errors/AppError'
import { ContractError } from '@/api/errors/ContractError'
import { getSession, listSessionIds } from '@/api/sessionApi'
import { env } from '@/config/env'
import { truncate } from '@/domain/services/formatters'
import { sessionSummary } from '@/domain/services/sessionSummary'
import type { SessionSource } from '@/domain/types/sessionSource'
import type { SessionDocument } from '@/domain/types/sessionDocument'
import type { SessionSummaryView } from '@/domain/types/sessionSummaryView'
import { getCachedSession, setCachedSession } from './sessionCache'

export interface UseSessionList {
  /** Cresce conforme as sessões chegam, sempre ordenado por `createdAt` decrescente. */
  items: SessionSummaryView[]
  /** Quantas sessões ainda faltam hidratar (nem em `items`, nem em `failedIds`). */
  pendingCount: number
  isLoadingIds: boolean
  error: AppError | null
  failedIds: string[]
  reload: () => void
}

function toAppError(error: unknown): AppError {
  return error instanceof AppError ? error : new ContractError(String(error))
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

function toSummaryView(document: SessionDocument): SessionSummaryView {
  const summary = sessionSummary(document)
  return { ...summary, question: truncate(summary.fullQuestion, env.historySummaryMaxChars) }
}

function sortByCreatedAtDesc(items: SessionSummaryView[]): SessionSummaryView[] {
  return [...items].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
}

/**
 * `explicitIds` restringe a lista a sessões conhecidas (ex.: as de uma bateria de benchmark) e
 * dispensa `GET /v1/sessions`; `null` lista todas as sessões da fonte.
 */
export function useSessionList(source: SessionSource = 'history', explicitIds: readonly string[] | null = null): UseSessionList {
  const [ids, setIds] = useState<string[] | null>(null)
  const [isLoadingIds, setIsLoadingIds] = useState(true)
  const [error, setError] = useState<AppError | null>(null)
  const [items, setItems] = useState<SessionSummaryView[]>([])
  const [failedIds, setFailedIds] = useState<string[]>([])
  const [processedIds, setProcessedIds] = useState<string[]>([])
  const [reloadToken, setReloadToken] = useState(0)
  // Chave estável: um array novo com os mesmos ids não deve refazer a busca a cada render.
  const explicitKey = explicitIds === null ? null : explicitIds.join('\n')

  // Passo 1: busca os ids. Falha aqui vira `ErrorState` na tela inteira (requisito 1). Só a
  // hidratação de cada documento (o passo caro) é cacheada — `GET /v1/sessions` é uma chamada
  // leve, então cada `useSessionList` montado (lista e barra lateral do detalhe) a refaz.
  useEffect(() => {
    const controller = new AbortController()
    setIsLoadingIds(true)
    setError(null)
    setItems([])
    setFailedIds([])
    setProcessedIds([])
    setIds(null)

    if (explicitKey !== null) {
      setIds(explicitKey === '' ? [] : explicitKey.split('\n'))
      setIsLoadingIds(false)
      return () => controller.abort()
    }

    listSessionIds(controller.signal)
      .then((sessionIds) => {
        if (controller.signal.aborted) return
        setIds(sessionIds)
        setIsLoadingIds(false)
      })
      .catch((rawError: unknown) => {
        if (controller.signal.aborted || isAbortError(rawError)) return
        setError(toAppError(rawError))
        setIsLoadingIds(false)
      })

    return () => controller.abort()
  }, [reloadToken, source, explicitKey])

  // Passo 2: hidrata cada sessão com um pool de `env.historyFetchConcurrency` requisições
  // simultâneas. Causa desta complexidade toda: `GET /v1/sessions` devolve só ids — um
  // endpoint de listagem que já trouxesse o resumo eliminaria esta hidratação por completo
  // (não é alteração desta feature, que é só de frontend — ver README, seção 3.3).
  useEffect(() => {
    if (ids === null) return
    const currentIds = ids
    const controller = new AbortController()

    function appendItem(document: SessionDocument): void {
      setProcessedIds((prev) => prev.includes(document.id) ? prev : [...prev, document.id])
      if ((document.benchmark_details?.is_banchmark === true) !== (source === 'benchmark')) return
      setCachedSession(document, source)
      const view = toSummaryView(document)
      setItems((prev) => sortByCreatedAtDesc([...prev.filter((item) => item.id !== view.id), view]))
    }

    async function worker(cursor: { next: number }): Promise<void> {
      for (;;) {
        if (controller.signal.aborted) return
        const current = cursor.next
        cursor.next += 1
        const id = currentIds[current]
        if (id === undefined) return

        const cached = getCachedSession(id, source)
        if (cached) {
          appendItem(cached)
          continue
        }

        try {
          const document = await getSession(id, controller.signal)
          if (controller.signal.aborted) return
          appendItem(document)
        } catch (rawError) {
          if (controller.signal.aborted || isAbortError(rawError)) return
          // Falha individual (404/400/500) não derruba a lista inteira (requisito 4): o id
          // vira um card discreto de erro, e os outros seguem hidratando normalmente.
          setFailedIds((prev) => (prev.includes(id) ? prev : [...prev, id]))
        }
      }
    }

    const cursor = { next: 0 }
    const poolSize = Math.max(1, Math.min(env.historyFetchConcurrency, ids.length))
    const workers = Array.from({ length: poolSize }, () => worker(cursor))
    void Promise.all(workers)

    return () => controller.abort()
  }, [ids, source])

  const reload = useCallback(() => setReloadToken((token) => token + 1), [])

  const pendingCount = ids === null ? 0 : Math.max(0, ids.length - processedIds.length - failedIds.length)

  return { items, pendingCount, isLoadingIds, error, failedIds, reload }
}
