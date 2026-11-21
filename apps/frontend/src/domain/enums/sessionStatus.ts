// Espelha o campo `status` do SessionDocument (README, seção 3.4).

import { TONE, type Tone } from './tone'

export const SESSION_STATUS = {
  RUNNING: 'running',
  COMPLETED: 'completed',
  DEGRADED: 'degraded',
  FAILED: 'failed',
} as const

export type SessionStatus = (typeof SESSION_STATUS)[keyof typeof SESSION_STATUS]

export const isSessionStatus = (value: unknown): value is SessionStatus =>
  typeof value === 'string' && (Object.values(SESSION_STATUS) as string[]).includes(value)

export const SESSION_STATUS_LABEL: Record<SessionStatus, string> = {
  running: 'Em execução',
  completed: 'Concluída',
  degraded: 'Concluída com degradação',
  failed: 'Falhou',
}

export const SESSION_STATUS_TONE: Record<SessionStatus, Tone> = {
  running: TONE.ACCENT,
  completed: TONE.SUCCESS,
  degraded: TONE.WARNING,
  failed: TONE.DANGER,
}
