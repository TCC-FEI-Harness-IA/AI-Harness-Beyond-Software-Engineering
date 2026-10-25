// Contrato de `BenchmarkSession` (backend: `BenchmarkSessionDocumentMapper`) — o mesmo documento
// vem de `GET /v1/benchmark/sessions*` e de cada frame de `WS /v1/benchmark/run`.

import type { BenchmarkQuestionStatus, BenchmarkSessionStatus } from '../enums/benchmarkStatus'
import type { ModelProvider } from '../enums/modelProvider'
import type { BenchmarkInferenceMode } from './benchmarkDetails'

export interface BenchmarkFlowOutcome {
  mode: BenchmarkInferenceMode
  session_id: string | null
  selected_alternative: string | null
  is_correct: boolean
  error: string | null
  duration_seconds: number
  total_tokens: number
}

export interface BenchmarkQuestionRun {
  question_id: string
  expected_alternative: string
  status: BenchmarkQuestionStatus
  current_mode: BenchmarkInferenceMode | null
  current_tokens: number
  total_tokens: number
  simple: BenchmarkFlowOutcome | null
  ralph: BenchmarkFlowOutcome | null
}

export interface BenchmarkModeSummary {
  executed: number
  correct: number
  wrong: number
  failures: number
  /** Fração de acertos entre as questões executadas pelo fluxo, de 0 a 1. */
  accuracy: number
  total_tokens: number
  duration_seconds: number
}

export interface BenchmarkProgress {
  total: number
  pending: number
  running: number
  finished: number
  interrupted: number
}

export interface BenchmarkSessionDocument {
  id: string
  status: BenchmarkSessionStatus
  model_name: string
  provider: ModelProvider
  max_tokens: number
  temperature: number
  max_parallel: number
  question_count: number
  created_at: string
  updated_at: string
  finished_at: string | null
  wall_time_ms: number
  error: string | null
  progress: BenchmarkProgress
  total_tokens: number
  session_ids: string[]
  summary: Record<BenchmarkInferenceMode, BenchmarkModeSummary>
  questions: BenchmarkQuestionRun[]
}

/** `GET /v1/benchmark/questions` — questões na ordem de execução e os limites aceitos numa bateria. */
export interface BenchmarkDataset {
  question_ids: string[]
  max_parallel_limit: number
  /** Maior `max_tokens` por chamada: acima disso o Ralph esgota o orçamento da sessão. */
  max_tokens_limit: number
}

/** Frames de `WS /v1/benchmark/run`: `progress` durante a bateria, `result` no fim, `error` na recusa. */
export type BenchmarkFrame =
  | { type: 'progress' | 'result'; benchmark_session: BenchmarkSessionDocument }
  | { type: 'error'; content: string }

/** Frame de abertura de `WS /v1/benchmark/run`. */
export interface BenchmarkRunInput {
  question_count: number
  max_parallel: number
  llm_model_config: {
    provider: ModelProvider
    provider_config: { model_name: string; endpoint: null }
    max_tokens: number
    temperature: number
  }
}
