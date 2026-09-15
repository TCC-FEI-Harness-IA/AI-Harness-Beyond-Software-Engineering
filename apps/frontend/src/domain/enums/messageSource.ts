// Espelha o campo `source` de SessionMessageDocument (README, seção 3.4).

export const MESSAGE_SOURCE = {
  USER: 'user',
  LLM_AGENT: 'llm_agent',
  SYSTEM: 'system',
} as const

export type MessageSource = (typeof MESSAGE_SOURCE)[keyof typeof MESSAGE_SOURCE]

export const isMessageSource = (value: unknown): value is MessageSource =>
  typeof value === 'string' && (Object.values(MESSAGE_SOURCE) as string[]).includes(value)
