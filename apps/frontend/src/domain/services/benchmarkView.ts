// Traduz o estado de uma questão do benchmark no que a tabela mostra em cada célula de fluxo.
// Função pura, sem React — a cor vem do `Tone`, nunca de comparação de string em componente.

import { BENCHMARK_QUESTION_STATUS } from '../enums/benchmarkStatus'
import { TONE, type Tone } from '../enums/tone'
import type { BenchmarkInferenceMode } from '../types/benchmarkDetails'
import type { BenchmarkQuestionRun } from '../types/benchmarkSession'

export type BenchmarkFlowCellKind =
  'pending' | 'running' | 'interrupted' | 'correct' | 'wrong' | 'failed'

export interface BenchmarkFlowCell {
  kind: BenchmarkFlowCellKind
  label: string
  tone: Tone
  /** Sessão do fluxo, para abrir o chat — só existe depois que o fluxo terminou. */
  sessionId: string | null
  /** Diagnóstico de falha técnica ou resposta inválida. */
  detail: string | null
}

const NO_ALTERNATIVE = '—'

export function benchmarkFlowCell(
  question: BenchmarkQuestionRun,
  mode: BenchmarkInferenceMode,
): BenchmarkFlowCell {
  const outcome = question[mode]
  if (outcome !== null) {
    const alternative = outcome.selected_alternative ?? NO_ALTERNATIVE
    if (outcome.error !== null) {
      return {
        kind: 'failed',
        label: `Falha (${alternative})`,
        tone: TONE.DANGER,
        sessionId: outcome.session_id,
        detail: outcome.error,
      }
    }
    return outcome.is_correct
      ? {
          kind: 'correct',
          label: `Certo (${alternative})`,
          tone: TONE.SUCCESS,
          sessionId: outcome.session_id,
          detail: null,
        }
      : {
          kind: 'wrong',
          label: `Errado (${alternative})`,
          tone: TONE.WARNING,
          sessionId: outcome.session_id,
          detail: null,
        }
  }

  if (question.current_mode === mode) {
    return question.status === BENCHMARK_QUESTION_STATUS.INTERRUPTED
      ? {
          kind: 'interrupted',
          label: 'Interrompido',
          tone: TONE.WARNING,
          sessionId: null,
          detail: null,
        }
      : { kind: 'running', label: 'Executando', tone: TONE.ACCENT, sessionId: null, detail: null }
  }

  return { kind: 'pending', label: 'Aguardando', tone: TONE.NEUTRAL, sessionId: null, detail: null }
}

/** Fração (0–1) das questões que já saíram da fila — encerradas ou interrompidas. */
export function benchmarkCompletion(progress: {
  total: number
  finished: number
  interrupted: number
}): number {
  if (progress.total === 0) return 0
  return (progress.finished + progress.interrupted) / progress.total
}
