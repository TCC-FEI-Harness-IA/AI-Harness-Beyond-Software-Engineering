// Baixa o ZIP padronizado com a bateria completa (bateria, enunciados, gabaritos e as execuções
// simples e Ralph Loop), expondo o estado do download para o botão da tela.

import { benchmarkSessionArchiveName, exportBenchmarkSession } from '../api/benchmarkApi'
import { type UseArchiveDownload, useArchiveDownload } from './useArchiveDownload'

export type UseBenchmarkSessionExport = UseArchiveDownload

export function useBenchmarkSessionExport(benchmarkSessionId: string): UseBenchmarkSessionExport {
  return useArchiveDownload(benchmarkSessionId, exportBenchmarkSession, benchmarkSessionArchiveName)
}
