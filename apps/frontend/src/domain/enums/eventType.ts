// Espelha o campo `type` do ReasoningEventDTO (README, seção 3.2).

export const EVENT_TYPE = {
  THINKING: 'thinking',
  RESULT: 'result',
  DEGRADED: 'degraded',
  ERROR: 'error',
} as const

export type EventType = (typeof EVENT_TYPE)[keyof typeof EVENT_TYPE]

export const isEventType = (value: unknown): value is EventType =>
  typeof value === 'string' && (Object.values(EVENT_TYPE) as string[]).includes(value)
