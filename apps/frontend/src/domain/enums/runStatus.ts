// Status do view-model `ThinkingRun`/`SimpleRun` (README, seção 6.3). Usado a partir da
// FASE 05 — declarado aqui porque é um enum de domínio como os demais.

import { TONE, type Tone } from './tone'

export const RUN_STATUS = {
  IDLE: 'idle',
  RUNNING: 'running',
  COMPLETED: 'completed',
  DEGRADED: 'degraded',
  FAILED: 'failed',
} as const

export type RunStatus = (typeof RUN_STATUS)[keyof typeof RUN_STATUS]

export const isRunStatus = (value: unknown): value is RunStatus =>
  typeof value === 'string' && (Object.values(RUN_STATUS) as string[]).includes(value)

export const RUN_STATUS_LABEL: Record<RunStatus, string> = {
  idle: 'Aguardando',
  running: 'Em execução',
  completed: 'Concluída',
  degraded: 'Concluída com degradação',
  failed: 'Falhou',
}

export const RUN_STATUS_TONE: Record<RunStatus, Tone> = {
  idle: TONE.NEUTRAL,
  running: TONE.ACCENT,
  completed: TONE.SUCCESS,
  degraded: TONE.WARNING,
  failed: TONE.DANGER,
}
