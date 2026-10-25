// Espelha `BenchmarkSessionStatusEnum` e `BenchmarkQuestionStatusEnum` do backend.

import { TONE, type Tone } from './tone'

export const BENCHMARK_SESSION_STATUS = {
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  INTERRUPTED: 'interrupted',
} as const

export type BenchmarkSessionStatus = (typeof BENCHMARK_SESSION_STATUS)[keyof typeof BENCHMARK_SESSION_STATUS]

export const isBenchmarkSessionStatus = (value: unknown): value is BenchmarkSessionStatus =>
  typeof value === 'string' && (Object.values(BENCHMARK_SESSION_STATUS) as string[]).includes(value)

export const BENCHMARK_SESSION_STATUS_LABEL: Record<BenchmarkSessionStatus, string> = {
  running: 'Em execução',
  completed: 'Concluída',
  failed: 'Falhou',
  interrupted: 'Interrompida',
}

export const BENCHMARK_SESSION_STATUS_TONE: Record<BenchmarkSessionStatus, Tone> = {
  running: TONE.ACCENT,
  completed: TONE.SUCCESS,
  failed: TONE.DANGER,
  interrupted: TONE.WARNING,
}

export const BENCHMARK_QUESTION_STATUS = {
  PENDING: 'pending',
  RUNNING: 'running',
  FINISHED: 'finished',
  INTERRUPTED: 'interrupted',
} as const

export type BenchmarkQuestionStatus = (typeof BENCHMARK_QUESTION_STATUS)[keyof typeof BENCHMARK_QUESTION_STATUS]

export const isBenchmarkQuestionStatus = (value: unknown): value is BenchmarkQuestionStatus =>
  typeof value === 'string' && (Object.values(BENCHMARK_QUESTION_STATUS) as string[]).includes(value)

export const BENCHMARK_MODE_LABEL = {
  simple: 'Simples',
  ralph: 'Ralph',
} as const
