// Baixa o ZIP com as questões erradas no Ralph Loop de uma bateria, expondo o estado do download
// (gerando, erro, concluído) para o botão da tela.

import { useCallback, useEffect, useRef, useState } from 'react'
import { AppError } from '../api/errors/AppError'
import { ContractError } from '../api/errors/ContractError'
import { exportBenchmarkRalphErrors, ralphErrorsArchiveName } from '../api/benchmarkApi'
import { saveBlob } from './saveBlob'

export interface UseBenchmarkRalphErrorsExport {
  isExporting: boolean
  /** Falha do último download; limpa ao tentar de novo. */
  error: AppError | null
  /** `true` depois que o último download foi entregue ao navegador. */
  isDone: boolean
  start: () => void
}

function toAppError(error: unknown): AppError {
  return error instanceof AppError ? error : new ContractError(String(error))
}

export function useBenchmarkRalphErrorsExport(
  benchmarkSessionId: string,
): UseBenchmarkRalphErrorsExport {
  const [isExporting, setIsExporting] = useState(false)
  const [error, setError] = useState<AppError | null>(null)
  const [isDone, setIsDone] = useState(false)
  const controllerRef = useRef<AbortController | null>(null)

  // O download nasce de um clique, nunca da montagem: abortar na desmontagem é seguro no StrictMode.
  useEffect(() => () => controllerRef.current?.abort(), [])

  // Outra bateria é outro contexto: o resultado do download anterior não vale para ela.
  useEffect(() => {
    setError(null)
    setIsDone(false)
  }, [benchmarkSessionId])

  const start = useCallback(() => {
    if (controllerRef.current !== null) return
    const controller = new AbortController()
    controllerRef.current = controller
    setIsExporting(true)
    setError(null)
    setIsDone(false)

    exportBenchmarkRalphErrors(benchmarkSessionId, controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return
        saveBlob(blob, ralphErrorsArchiveName(benchmarkSessionId))
        setIsDone(true)
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted) return
        setError(toAppError(failure))
      })
      .finally(() => {
        controllerRef.current = null
        if (!controller.signal.aborted) setIsExporting(false)
      })
  }, [benchmarkSessionId])

  return { isExporting, error, isDone, start }
}
