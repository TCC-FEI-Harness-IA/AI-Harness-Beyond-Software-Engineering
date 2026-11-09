import { describe, expect, it } from 'vitest'
import type { SessionDocument, SessionMessageDocument } from '@/domain/types/sessionDocument'
import { benchmarkSession, outcome, questionRun } from '@/test/fixtures/benchmarkSession'
import { buildAnalysisRecords } from './benchmarkAnalysis'
import { groupByProcess, processBucket, ralphProcessMetrics } from './ralphProcessMetrics'

function message(overrides: Partial<SessionMessageDocument>): SessionMessageDocument {
  return {
    id: 'm',
    order: 0,
    timestamp: '2026-11-08T00:00:00+00:00',
    phase: 'A1',
    source: 'llm_agent',
    content: '',
    task_id: null,
    context_id: null,
    tokens_input: 0,
    tokens_output: 0,
    total_tokens: 0,
    inference_time_ms: 0,
    model_name: null,
    subtype: null,
    ...overrides,
  } as SessionMessageDocument
}

function document(messages: SessionMessageDocument[]): SessionDocument {
  return {
    id: 'sess_r',
    user_question: 'Q',
    flow: 'A1',
    flow_version: 2,
    model_name: 'm',
    max_tokens: 1,
    temperature: 0,
    status: 'completed',
    created_at: '',
    updated_at: '',
    final_answer: null,
    totals: {
      total_messages: messages.length,
      total_llm_calls: 7,
      tokens_input: 0,
      tokens_output: 0,
      total_tokens: 0,
      inference_time_ms: 0,
      wall_time_ms: 0,
    },
    messages,
    degradations: [],
  }
}

describe('ralphProcessMetrics', () => {
  it('conta tarefas da fase B, resoluções, reprovações e replanejamentos', () => {
    const metrics = ralphProcessMetrics(
      document([
        message({ phase: 'A2', subtype: 'plan_candidate', task_id: 'T9' }),
        message({ phase: 'A3', subtype: 'plan_rejected' }),
        message({ phase: 'B1', subtype: 'reasoning', task_id: 'T1' }),
        message({ phase: 'B2', subtype: 'verify_fail', task_id: 'T1' }),
        message({ phase: 'B1', subtype: 'reasoning', task_id: 'T1' }),
        message({ phase: 'B1', subtype: 'reasoning', task_id: 'T2' }),
        message({ phase: 'C2', subtype: 'replan' }),
        message({ phase: 'C3' }),
      ]),
    )
    expect(metrics).toEqual({
      taskCount: 2,
      resolutionCount: 3,
      verificationFailures: 1,
      planRejections: 1,
      replans: 1,
      llmCalls: 7,
    })
  })
})

const base = { resolutionCount: 0, replans: 0, llmCalls: 0 }

describe('processBucket', () => {
  it('rotula singular, plural e a faixa aberta', () => {
    expect(processBucket('taskCount', undefined).label).toBe('Sessão não carregada')
    expect(processBucket('taskCount', { ...base, taskCount: 1, verificationFailures: 0, planRejections: 0 }).label).toBe('1 tarefa')
    expect(processBucket('taskCount', { ...base, taskCount: 3, verificationFailures: 0, planRejections: 0 }).label).toBe('3 tarefas')
    expect(processBucket('taskCount', { ...base, taskCount: 9, verificationFailures: 0, planRejections: 0 })).toEqual({
      key: 'taskCount:4',
      label: '4+ tarefas',
      order: 4,
    })
    expect(processBucket('planRejections', { ...base, taskCount: 1, verificationFailures: 0, planRejections: 1 }).label).toBe(
      '1+ planos reprovados',
    )
    expect(processBucket('verificationFailures', { ...base, taskCount: 1, verificationFailures: 0, planRejections: 0 }).label).toBe(
      '0 reprovações',
    )
  })
})

describe('groupByProcess', () => {
  it('agrupa pela métrica da sessão Ralph e separa as não carregadas', () => {
    const { records } = buildAnalysisRecords([
      benchmarkSession({
        questions: [
          questionRun({ question_id: 'Q1', simple: outcome(), ralph: outcome({ mode: 'ralph', session_id: 'r1' }) }),
          questionRun({ question_id: 'Q2', simple: outcome(), ralph: outcome({ mode: 'ralph', session_id: 'r2' }) }),
          questionRun({ question_id: 'Q3', simple: outcome(), ralph: outcome({ mode: 'ralph', session_id: null }) }),
        ],
      }),
    ])
    const metrics = new Map([['r1', { ...base, taskCount: 2, verificationFailures: 0, planRejections: 0 }]])
    const groups = groupByProcess(records, 'taskCount', metrics)
    expect(groups.map((group) => [group.label, group.summary.n])).toEqual([
      ['2 tarefas', 1],
      ['Sessão não carregada', 2],
    ])
  })
})
