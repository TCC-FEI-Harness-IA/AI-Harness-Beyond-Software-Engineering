import { describe, expect, it } from 'vitest'
import {
  benchmarkSession,
  completedBenchmarkSession,
  outcome,
  questionRun,
} from '@/test/fixtures/benchmarkSession'
import { benchmarkRalphErrorCount, benchmarkRalphErrorsExport } from './benchmarkExport'

const ralph = (overrides: Parameters<typeof outcome>[0]) => outcome({ mode: 'ralph', ...overrides })

describe('benchmarkRalphErrorCount', () => {
  it('conta só os desfechos incorretos do Ralph, incluindo falhas técnicas', () => {
    const session = benchmarkSession({
      status: 'completed',
      questions: [
        questionRun({ question_id: 'Q1', ralph: ralph({ is_correct: false }) }),
        questionRun({ question_id: 'Q2', ralph: ralph({ is_correct: true }) }),
        questionRun({
          question_id: 'Q3',
          ralph: ralph({
            is_correct: false,
            error: 'provedor fora do ar',
            selected_alternative: null,
          }),
        }),
        questionRun({ question_id: 'Q4', ralph: null }),
        // O fluxo simples errado não conta.
        questionRun({
          question_id: 'Q5',
          simple: outcome({ is_correct: false }),
          ralph: ralph({ is_correct: true }),
        }),
      ],
    })

    expect(benchmarkRalphErrorCount(session)).toBe(2)
  })
})

describe('benchmarkRalphErrorsExport', () => {
  it('bateria em execução não exporta, mesmo com erros já registrados', () => {
    const session = benchmarkSession({
      status: 'running',
      questions: [questionRun({ ralph: ralph({ is_correct: false }) })],
    })

    expect(benchmarkRalphErrorsExport(session)).toEqual({ kind: 'running' })
  })

  it('bateria encerrada sem erros no Ralph não tem o que exportar', () => {
    expect(benchmarkRalphErrorsExport(completedBenchmarkSession())).toEqual({ kind: 'empty' })
  })

  it.each(['completed', 'failed', 'interrupted'] as const)(
    'bateria %s com erros no Ralph está pronta para exportar',
    (status) => {
      const session = benchmarkSession({
        status,
        questions: [
          questionRun({ question_id: 'Q1', ralph: ralph({ is_correct: false }) }),
          questionRun({ question_id: 'Q2', ralph: ralph({ is_correct: false }) }),
        ],
      })

      expect(benchmarkRalphErrorsExport(session)).toEqual({ kind: 'ready', count: 2 })
    },
  )
})
