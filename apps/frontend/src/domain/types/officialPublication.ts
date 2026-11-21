import type { BenchmarkDatasetId, BenchmarkSessionDocument } from './benchmarkSession'

export type PublicationStatus = 'active' | 'superseded'

/** Resultado oficial público: cópia preservada de uma bateria, publicada por um administrador. */
export interface OfficialPublication {
  id: string
  dataset: BenchmarkDatasetId
  status: PublicationStatus
  publishedAt: string
  supersedes: string | null
  supersededBy: string | null
  supersededAt: string | null
  sourceBenchmarkSessionId: string
  /** As sessões públicas omitem enunciados e respostas (termos de uso do dataset). */
  textRedacted: boolean
  /** Bateria publicada, no mesmo formato da API privada. */
  battery: BenchmarkSessionDocument
}
