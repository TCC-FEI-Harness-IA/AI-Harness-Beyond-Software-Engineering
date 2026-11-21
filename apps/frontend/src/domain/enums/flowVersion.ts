// Versão do fluxo Ralph (campo `flow_version` do frame e da sessão). Ela define o significado das fases
// ambíguas antes de qualquer interpretação: na versão 1 (sessões antigas, sem o campo), `A3` é a extração
// dos aprendizados do enunciado; na versão 2, `A3` é a validação da decomposição e `A4` a extração.

export const FLOW_VERSION = {
  LEGACY: 1,
  VALIDATED_PLANNING: 2,
} as const

export type FlowVersion = (typeof FLOW_VERSION)[keyof typeof FLOW_VERSION]

export const isFlowVersion = (value: unknown): value is FlowVersion =>
  typeof value === 'number' && (Object.values(FLOW_VERSION) as number[]).includes(value)
