// Importa uma bateria completa a partir do ZIP exportado, expondo o estado do envio (enviando,
// erro, bateria importada) para o botão da tela.

import { useCallback, useEffect, useRef, useState } from 'react'
import { importBenchmarkSession } from '../api/benchmarkApi'
import type { AppError } from '../api/errors/AppError'
import type { BenchmarkSessionDocument } from '../domain/types/benchmarkSession'
import { toAppError } from './useArchiveDownload'

export interface UseBenchmarkSessionImport {
  isImporting: boolean
  /** Falha do último envio; limpa ao tentar de novo. */
  error: AppError | null
  /** Bateria criada pelo último envio bem-sucedido. */
  imported: BenchmarkSessionDocument | null
  start: (file: File) => void
}

export function useBenchmarkSessionImport(
  onImported?: (session: BenchmarkSessionDocument) => void,
): UseBenchmarkSessionImport {
  const [isImporting, setIsImporting] = useState(false)
  const [error, setError] = useState<AppError | null>(null)
  const [imported, setImported] = useState<BenchmarkSessionDocument | null>(null)
  const controllerRef = useRef<AbortController | null>(null)
  const onImportedRef = useRef(onImported)
  onImportedRef.current = onImported

  // O envio nasce de uma escolha de arquivo, nunca da montagem: abortar na desmontagem é seguro.
  useEffect(() => () => controllerRef.current?.abort(), [])

  const start = useCallback((file: File) => {
    if (controllerRef.current !== null) return
    const controller = new AbortController()
    controllerRef.current = controller
    setIsImporting(true)
    setError(null)
    setImported(null)

    importBenchmarkSession(file, controller.signal)
      .then((session) => {
        if (controller.signal.aborted) return
        setImported(session)
        onImportedRef.current?.(session)
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted) return
        setError(toAppError(failure))
      })
      .finally(() => {
        controllerRef.current = null
        if (!controller.signal.aborted) setIsImporting(false)
      })
  }, [])

  return { isImporting, error, imported, start }
}
