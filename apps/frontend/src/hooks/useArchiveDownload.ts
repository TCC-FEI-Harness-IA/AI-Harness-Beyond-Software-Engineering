// Baixa um arquivo de uma bateria (ZIP), expondo o estado do download (gerando, erro, concluído)
// para o botão da tela. Base comum das exportações do BenchMark.

import { useCallback, useEffect, useRef, useState } from 'react'
import { AppError } from '../api/errors/AppError'
import { ContractError } from '../api/errors/ContractError'
import { saveBlob } from './saveBlob'

export interface UseArchiveDownload {
  isExporting: boolean
  /** Falha do último download; limpa ao tentar de novo. */
  error: AppError | null
  /** `true` depois que o último download foi entregue ao navegador. */
  isDone: boolean
  start: () => void
}

export function toAppError(error: unknown): AppError {
  return error instanceof AppError ? error : new ContractError(String(error))
}

/**
 * @param benchmarkSessionId Bateria exportada; trocá-la descarta o resultado anterior.
 * @param download Busca o arquivo da bateria — deve ser estável entre renderizações.
 * @param filenameFor Nome do arquivo entregue ao navegador — deve ser estável entre renderizações.
 */
export function useArchiveDownload(
  benchmarkSessionId: string,
  download: (benchmarkSessionId: string, signal: AbortSignal) => Promise<Blob>,
  filenameFor: (benchmarkSessionId: string) => string,
): UseArchiveDownload {
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

    download(benchmarkSessionId, controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return
        saveBlob(blob, filenameFor(benchmarkSessionId))
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
  }, [benchmarkSessionId, download, filenameFor])

  return { isExporting, error, isDone, start }
}
