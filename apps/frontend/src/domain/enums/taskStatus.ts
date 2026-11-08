// Status de tarefa do view-model `TaskTimeline` (README, seção 6.3). Não vem direto de um
// campo do backend — é derivado na camada de domínio a partir da sequência de eventos/mensagens
// de cada tarefa, a partir da FASE 05/06.

import { TONE, type Tone } from './tone'

export const TASK_STATUS = {
  PENDING: 'pending',
  RUNNING: 'running',
  APPROVED: 'approved',
  DEGRADED: 'degraded',
  DISCARDED: 'discarded',
} as const

export type TaskStatus = (typeof TASK_STATUS)[keyof typeof TASK_STATUS]

export const isTaskStatus = (value: unknown): value is TaskStatus =>
  typeof value === 'string' && (Object.values(TASK_STATUS) as string[]).includes(value)

export const TASK_STATUS_LABEL: Record<TaskStatus, string> = {
  pending: 'Pendente',
  running: 'Em execução',
  approved: 'Aprovada',
  degraded: 'Degradada',
  discarded: 'Descartada',
}

export const TASK_STATUS_TONE: Record<TaskStatus, Tone> = {
  pending: TONE.NEUTRAL,
  running: TONE.ACCENT,
  approved: TONE.SUCCESS,
  degraded: TONE.WARNING,
  discarded: TONE.NEUTRAL,
}
