// Decide se os erros do Ralph Loop de uma bateria podem ser exportados. Função pura, sem React:
// a mesma regra que o backend aplica (`ExportBenchmarkRalphErrorsUseCase`), para o botão nunca
// oferecer um download que o servidor recusaria.

import { BENCHMARK_SESSION_STATUS } from '../enums/benchmarkStatus'
import type { BenchmarkSessionDocument } from '../types/benchmarkSession'

export type BenchmarkRalphErrorsExport =
  /** A bateria ainda executa: os resultados podem mudar. */
  | { kind: 'running' }
  /** Bateria encerrada em que nenhuma questão errou no Ralph Loop. */
  | { kind: 'empty' }
  /** Bateria encerrada com `count` questões erradas no Ralph Loop. */
  | { kind: 'ready'; count: number }

/** Erro no Ralph Loop: desfecho registrado e não correto — falha técnica conta como erro. */
export function benchmarkRalphErrorCount(session: BenchmarkSessionDocument): number {
  return session.questions.filter(
    (question) => question.ralph !== null && !question.ralph.is_correct,
  ).length
}

export function benchmarkRalphErrorsExport(
  session: BenchmarkSessionDocument,
): BenchmarkRalphErrorsExport {
  if (session.status === BENCHMARK_SESSION_STATUS.RUNNING) return { kind: 'running' }
  const count = benchmarkRalphErrorCount(session)
  return count === 0 ? { kind: 'empty' } : { kind: 'ready', count }
}
