// Tripé loading/error/data genérico, para que nenhuma tela reescreva a mesma lógica de
// carregamento (README, FASE 02, seção 11; regra 13 do README).

import { useCallback, useEffect, useRef, useState, type DependencyList } from 'react'
import { AppError } from '../api/errors/AppError'
import { ContractError } from '../api/errors/ContractError'

export type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: AppError }
  | { status: 'success'; data: T }

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

// `run` só deveria rejeitar com AppError (é o contrato da camada `api/`) — mas um erro
// inesperado ainda precisa virar algo exibível, em vez de quebrar o estado da tela.
function toAppError(error: unknown): AppError {
  return error instanceof AppError ? error : new ContractError(String(error))
}

export function useAsync<T>(
  run: (signal: AbortSignal) => Promise<T>,
  deps: DependencyList,
): AsyncState<T> & { reload: () => void } {
  const [state, setState] = useState<AsyncState<T>>({ status: 'loading' })
  const [reloadToken, setReloadToken] = useState(0)
  const mountedRef = useRef(true)

  useEffect(() => {
    // O StrictMode roda montagem → limpeza → montagem em desenvolvimento; sem religar a flag aqui,
    // a limpeza simulada a deixaria em `false` para sempre e toda resposta seria descartada.
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setState({ status: 'loading' })

    run(controller.signal)
      .then((data) => {
        if (!mountedRef.current || controller.signal.aborted) return
        setState({ status: 'success', data })
      })
      .catch((error: unknown) => {
        if (!mountedRef.current || controller.signal.aborted || isAbortError(error)) return
        setState({ status: 'error', error: toAppError(error) })
      })

    return () => {
      controller.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reloadToken])

  const reload = useCallback(() => {
    setReloadToken((token) => token + 1)
  }, [])

  return { ...state, reload }
}
