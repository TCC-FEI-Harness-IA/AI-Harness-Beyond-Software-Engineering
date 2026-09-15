// Carrega uma sessão persistida por id (README, FASE 07, seção 6). Cache-first: se a sessão já
// foi hidratada pela lista (ou por uma visita anterior ao mesmo detalhe), a tela renderiza sem
// nenhuma requisição de rede — requisito 7 da FASE 07 ("nenhuma requisição é refeita ao navegar
// lista → detalhe → lista").

import { useCallback, useEffect, useState } from 'react'
import { AppError } from '@/api/errors/AppError'
import { ContractError } from '@/api/errors/ContractError'
import { getSession } from '@/api/sessionApi'
import type { SessionDocument } from '@/domain/types/sessionDocument'
import { getCachedSession, setCachedSession } from './sessionCache'

export type UseSessionState =
  | { status: 'loading' }
  | { status: 'error'; error: AppError }
  | { status: 'success'; data: SessionDocument }

export interface UseSession {
  state: UseSessionState
  reload: () => void
}

function toAppError(error: unknown): AppError {
  return error instanceof AppError ? error : new ContractError(String(error))
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

export function useSession(sessionId: string): UseSession {
  const [state, setState] = useState<UseSessionState>(() => {
    const cached = getCachedSession(sessionId)
    return cached ? { status: 'success', data: cached } : { status: 'loading' }
  })
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    const cached = getCachedSession(sessionId)
    if (cached && reloadToken === 0) {
      setState({ status: 'success', data: cached })
      return
    }

    const controller = new AbortController()
    setState({ status: 'loading' })

    getSession(sessionId, controller.signal)
      .then((document) => {
        if (controller.signal.aborted) return
        setCachedSession(document)
        setState({ status: 'success', data: document })
      })
      .catch((rawError: unknown) => {
        if (controller.signal.aborted || isAbortError(rawError)) return
        setState({ status: 'error', error: toAppError(rawError) })
      })

    return () => controller.abort()
  }, [sessionId, reloadToken])

  const reload = useCallback(() => setReloadToken((token) => token + 1), [])

  return { state, reload }
}
