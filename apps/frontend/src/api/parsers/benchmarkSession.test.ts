import { describe, expect, it } from 'vitest'
import {
  benchmarkSession,
  completedBenchmarkSession,
  questionRun,
} from '@/test/fixtures/benchmarkSession'
import { ContractError } from '../errors/ContractError'
import {
  parseBenchmarkDataset,
  parseBenchmarkFrame,
  parseBenchmarkSession,
  parseBenchmarkSessionList,
} from './benchmarkSession'

function withQuestion(overrides: Record<string, unknown>): unknown {
  return { ...benchmarkSession(), questions: [{ ...questionRun(), ...overrides }] }
}

describe('parseBenchmarkSession', () => {
  it('aceita o documento completo da API', () => {
    const document = completedBenchmarkSession()

    expect(parseBenchmarkSession(document)).toEqual(document)
  })

  it('aceita a questão em execução sem desfechos', () => {
    const parsed = parseBenchmarkSession(withQuestion({ status: 'running', current_mode: 'ralph' }))

    expect(parsed.questions[0]?.current_mode).toBe('ralph')
    expect(parsed.questions[0]?.simple).toBeNull()
  })

  it('trata desfechos ausentes como nulos', () => {
    const question: Record<string, unknown> = { ...questionRun() }
    delete question.simple
    delete question.ralph

    expect(
      parseBenchmarkSession({ ...benchmarkSession(), questions: [question] }).questions[0]?.ralph,
    ).toBeNull()
  })

  it.each([
    ['status da bateria', { ...benchmarkSession(), status: 'pausada' }, 'benchmark_session.status'],
    ['provedor', { ...benchmarkSession(), provider: 'outro' }, 'benchmark_session.provider'],
    ['progresso', { ...benchmarkSession(), progress: null }, 'benchmark_session.progress'],
    ['status da questão', withQuestion({ status: 'parada' }), 'questions[0].status'],
    ['fluxo em execução', withQuestion({ current_mode: 'outro' }), 'questions[0].current_mode'],
    ['sessões', { ...benchmarkSession(), session_ids: [1] }, 'session_ids[0]'],
    [
      'acerto do desfecho',
      withQuestion({
        simple: { ...completedBenchmarkSession().questions[0]?.simple, is_correct: 'sim' },
      }),
      'simple.is_correct',
    ],
  ])('recusa %s inválido', (_, raw, path) => {
    expect(() => parseBenchmarkSession(raw)).toThrow(ContractError)
    expect(() => parseBenchmarkSession(raw)).toThrow(path)
  })
})

describe('parseBenchmarkSessionList', () => {
  it('lê o envelope da listagem', () => {
    expect(parseBenchmarkSessionList({ benchmark_sessions: [benchmarkSession()] })).toHaveLength(1)
  })

  it('aponta o item inválido', () => {
    expect(() => parseBenchmarkSessionList({ benchmark_sessions: [{}] })).toThrow(
      'benchmark_sessions[0]',
    )
  })
})

describe('parseBenchmarkDataset', () => {
  it('lê as questões e o limite de paralelismo', () => {
    expect(parseBenchmarkDataset({ question_ids: ['Q1'], max_parallel_limit: 10 })).toEqual({
      question_ids: ['Q1'],
      max_parallel_limit: 10,
    })
  })

  it('recusa limite ausente', () => {
    expect(() => parseBenchmarkDataset({ question_ids: [] })).toThrow(ContractError)
  })
})

describe('parseBenchmarkFrame', () => {
  it('lê frames de progresso e de resultado', () => {
    expect(
      parseBenchmarkFrame({ type: 'progress', benchmark_session: benchmarkSession() }).type,
    ).toBe('progress')
    expect(
      parseBenchmarkFrame({ type: 'result', benchmark_session: completedBenchmarkSession() }).type,
    ).toBe('result')
  })

  it('lê o frame de erro', () => {
    expect(parseBenchmarkFrame({ type: 'error', content: 'recusado' })).toEqual({
      type: 'error',
      content: 'recusado',
    })
  })

  it('recusa tipo desconhecido', () => {
    expect(() => parseBenchmarkFrame({ type: 'thinking' })).toThrow('type')
  })
})
