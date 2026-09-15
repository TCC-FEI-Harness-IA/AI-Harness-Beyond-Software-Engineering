// Estado passado pela navegação da home para as telas de chat (README, FASE 04, seção 5.3).
// `useLocation().state` é `unknown` na prática — todo consumidor precisa validar antes de usar
// (regra 6 do README, validação na fronteira).

export interface InferenceNavigationState {
  question: string
  autoStart: boolean
}

export function isInferenceNavigationState(value: unknown): value is InferenceNavigationState {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as InferenceNavigationState).question === 'string' &&
    typeof (value as InferenceNavigationState).autoStart === 'boolean'
  )
}
