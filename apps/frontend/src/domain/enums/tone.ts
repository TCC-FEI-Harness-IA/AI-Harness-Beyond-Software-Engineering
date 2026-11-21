// Tom semântico de cor (README, seção 8.3). Não é um valor do contrato do backend — é o
// vocabulário que traduz subtype/status em cor, para que nenhum componente compare string
// de domínio com hex ou nome de cor.

export const TONE = {
  NEUTRAL: 'neutral',
  ACCENT: 'accent',
  SUCCESS: 'success',
  WARNING: 'warning',
  DANGER: 'danger',
  CONTEXT: 'context',
} as const

export type Tone = (typeof TONE)[keyof typeof TONE]
