import { describe, expect, it } from 'vitest'
import { outcome, questionRun } from '@/test/fixtures/benchmarkSession'
import { benchmarkCompletion, benchmarkFlowCell, isQuestionRerunnable } from './benchmarkView'

describe('benchmarkFlowCell', () => {
  it('fluxo sem desfecho e fora de execução aguarda', () => {
    expect(benchmarkFlowCell(questionRun(), 'simple')).toEqual({
      kind: 'pending',
      label: 'Aguardando',
      tone: 'neutral',
      sessionId: null,
      detail: null,
    })
  })

  it('fluxo em execução mostra executando', () => {
    const cell = benchmarkFlowCell(
      questionRun({ status: 'running', current_mode: 'ralph' }),
      'ralph',
    )

    expect(cell.kind).toBe('running')
    expect(cell.tone).toBe('accent')
  })

  it('o outro fluxo da questão em execução continua aguardando', () => {
    expect(
      benchmarkFlowCell(questionRun({ status: 'running', current_mode: 'simple' }), 'ralph').kind,
    ).toBe('pending')
  })

  it('fluxo em execução numa questão interrompida mostra a interrupção', () => {
    const cell = benchmarkFlowCell(
      questionRun({ status: 'interrupted', current_mode: 'simple' }),
      'simple',
    )

    expect(cell).toMatchObject({ kind: 'interrupted', label: 'Interrompido', tone: 'warning' })
  })

  it('acerto traz a alternativa e a sessão', () => {
    const cell = benchmarkFlowCell(
      questionRun({ simple: outcome({ session_id: 'sess_a' }) }),
      'simple',
    )

    expect(cell).toEqual({
      kind: 'correct',
      label: 'Certo (A)',
      tone: 'success',
      sessionId: 'sess_a',
      detail: null,
    })
  })

  it('erro traz a alternativa escolhida', () => {
    const cell = benchmarkFlowCell(
      questionRun({
        ralph: outcome({ mode: 'ralph', selected_alternative: 'C', is_correct: false }),
      }),
      'ralph',
    )

    expect(cell).toMatchObject({ kind: 'wrong', label: 'Errado (C)', tone: 'warning' })
  })

  it('falha sem alternativa traz o diagnóstico', () => {
    const cell = benchmarkFlowCell(
      questionRun({
        simple: outcome({ selected_alternative: null, is_correct: false, error: 'timeout' }),
      }),
      'simple',
    )

    expect(cell).toMatchObject({
      kind: 'failed',
      label: 'Falha (—)',
      tone: 'danger',
      detail: 'timeout',
    })
  })
})

describe('benchmarkCompletion', () => {
  it('conta encerradas e interrompidas sobre o total', () => {
    expect(benchmarkCompletion({ total: 4, finished: 1, interrupted: 1 })).toBe(0.5)
  })

  it('bateria sem questões tem progresso zero', () => {
    expect(benchmarkCompletion({ total: 0, finished: 0, interrupted: 0 })).toBe(0)
  })
})

describe('reexecução de uma questão', () => {
  const wrong = outcome({ mode: 'ralph', is_correct: false, selected_alternative: 'C' })

  it('fluxo reexecutado numa questão encerrada mostra executando, mesmo com o desfecho anterior', () => {
    const question = questionRun({
      status: 'finished',
      current_mode: 'ralph',
      simple: outcome(),
      ralph: wrong,
    })

    expect(benchmarkFlowCell(question, 'ralph')).toMatchObject({ kind: 'running', sessionId: null })
    expect(benchmarkFlowCell(question, 'simple').kind).toBe('correct')
  })

  it.each([
    [
      'simples errado',
      { simple: outcome({ is_correct: false }), ralph: outcome({ mode: 'ralph' }) },
    ],
    ['ralph errado', { simple: outcome(), ralph: wrong }],
    [
      'falha técnica',
      { simple: outcome(), ralph: outcome({ mode: 'ralph', is_correct: false, error: 'timeout' }) },
    ],
  ] as const)('questão encerrada com %s pode ser reexecutada', (_name, outcomes) => {
    expect(isQuestionRerunnable(questionRun({ status: 'finished', ...outcomes }))).toBe(true)
  })

  it('questão que acertou os dois fluxos não pode ser reexecutada', () => {
    const question = questionRun({
      status: 'finished',
      simple: outcome(),
      ralph: outcome({ mode: 'ralph' }),
    })

    expect(isQuestionRerunnable(question)).toBe(false)
  })

  it.each(['pending', 'running', 'interrupted'] as const)(
    'questão %s não pode ser reexecutada',
    (status) => {
      expect(
        isQuestionRerunnable(questionRun({ status, simple: outcome({ is_correct: false }) })),
      ).toBe(false)
    },
  )

  it('questão já em reexecução não pode ser reexecutada de novo', () => {
    expect(
      isQuestionRerunnable(
        questionRun({ status: 'finished', current_mode: 'ralph', simple: wrong, ralph: wrong }),
      ),
    ).toBe(false)
  })
})
