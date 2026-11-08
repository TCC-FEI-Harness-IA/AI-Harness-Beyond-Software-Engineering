// Baixa o ZIP com as questões erradas no Ralph Loop de uma bateria, expondo o estado do download
// (gerando, erro, concluído) para o botão da tela.

import { exportBenchmarkRalphErrors, ralphErrorsArchiveName } from '../api/benchmarkApi'
import { type UseArchiveDownload, useArchiveDownload } from './useArchiveDownload'

export type UseBenchmarkRalphErrorsExport = UseArchiveDownload

export function useBenchmarkRalphErrorsExport(
  benchmarkSessionId: string,
): UseBenchmarkRalphErrorsExport {
  return useArchiveDownload(benchmarkSessionId, exportBenchmarkRalphErrors, ralphErrorsArchiveName)
}
