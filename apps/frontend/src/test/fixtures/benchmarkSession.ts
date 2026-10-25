// Fábrica de documentos de `BenchmarkSession` no formato da API, para testes.

import type {
  BenchmarkFlowOutcome,
  BenchmarkQuestionRun,
  BenchmarkSessionDocument,
} from '@/domain/types/benchmarkSession'

export function outcome(overrides: Partial<BenchmarkFlowOutcome> = {}): BenchmarkFlowOutcome {
  return {
    mode: 'simple',
    session_id: 'sess_q1_simple',
    selected_alternative: 'A',
    is_correct: true,
    error: null,
    duration_seconds: 1.5,
    total_tokens: 10,
    ...overrides,
  }
}

export function questionRun(overrides: Partial<BenchmarkQuestionRun> = {}): BenchmarkQuestionRun {
  return {
    question_id: 'Q1',
    expected_alternative: 'A',
    status: 'pending',
    current_mode: null,
    current_tokens: 0,
    total_tokens: 0,
    simple: null,
    ralph: null,
    ...overrides,
  }
}

const EMPTY_SUMMARY = {
  executed: 0,
  correct: 0,
  wrong: 0,
  failures: 0,
  accuracy: 0,
  total_tokens: 0,
  duration_seconds: 0,
}

export function benchmarkSession(
  overrides: Partial<BenchmarkSessionDocument> = {},
): BenchmarkSessionDocument {
  return {
    id: 'bench_1',
    status: 'running',
    model_name: 'openai/gpt-4o-mini',
    provider: 'open_router',
    max_tokens: 1200,
    temperature: 0.3,
    max_parallel: 1,
    question_count: 2,
    created_at: '2026-10-25T12:00:00+00:00',
    updated_at: '2026-10-25T12:00:00+00:00',
    finished_at: null,
    wall_time_ms: 0,
    error: null,
    progress: { total: 2, pending: 2, running: 0, finished: 0, interrupted: 0 },
    total_tokens: 0,
    session_ids: [],
    summary: { simple: { ...EMPTY_SUMMARY }, ralph: { ...EMPTY_SUMMARY } },
    questions: [
      questionRun({ question_id: 'Q1' }),
      questionRun({ question_id: 'Q2', expected_alternative: 'B' }),
    ],
    ...overrides,
  }
}

/** Bateria de duas questões já concluída: simples acerta Q1 e erra Q2; Ralph acerta as duas. */
export function completedBenchmarkSession(): BenchmarkSessionDocument {
  return benchmarkSession({
    status: 'completed',
    finished_at: '2026-10-25T12:05:00+00:00',
    wall_time_ms: 300000,
    progress: { total: 2, pending: 0, running: 0, finished: 2, interrupted: 0 },
    total_tokens: 220,
    session_ids: ['sess_q1_simple', 'sess_q1_ralph', 'sess_q2_simple', 'sess_q2_ralph'],
    summary: {
      simple: {
        executed: 2,
        correct: 1,
        wrong: 1,
        failures: 0,
        accuracy: 0.5,
        total_tokens: 20,
        duration_seconds: 3,
      },
      ralph: {
        executed: 2,
        correct: 2,
        wrong: 0,
        failures: 0,
        accuracy: 1,
        total_tokens: 200,
        duration_seconds: 30,
      },
    },
    questions: [
      questionRun({
        question_id: 'Q1',
        status: 'finished',
        total_tokens: 110,
        simple: outcome({ session_id: 'sess_q1_simple' }),
        ralph: outcome({ mode: 'ralph', session_id: 'sess_q1_ralph', total_tokens: 100 }),
      }),
      questionRun({
        question_id: 'Q2',
        expected_alternative: 'B',
        status: 'finished',
        total_tokens: 110,
        simple: outcome({
          session_id: 'sess_q2_simple',
          selected_alternative: 'C',
          is_correct: false,
        }),
        ralph: outcome({
          mode: 'ralph',
          session_id: 'sess_q2_ralph',
          selected_alternative: 'B',
          total_tokens: 100,
        }),
      }),
    ],
  })
}
