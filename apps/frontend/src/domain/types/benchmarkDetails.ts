export type BenchmarkInferenceMode = 'simple' | 'ralph'

/** Contrato persistido em Session; nomes preservados conforme a API. */
export interface BenchmarkDetails {
  is_banchmark: boolean
  question_name: string | null
  corret_answer: string | null
  providade_answer: string | null
  inference_mode: BenchmarkInferenceMode | null
  run_id: string | null
  expected_alternative: string | null
  selected_alternative: string | null
  is_correct: boolean | null
  duration_seconds: number | null
  error: string | null
}
