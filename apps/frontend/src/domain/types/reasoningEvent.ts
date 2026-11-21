// Contrato do frame do WebSocket `/v1/message/reasoning` (README, seção 3.2).

import type { EventSubtype } from '../enums/eventSubtype'
import type { EventType } from '../enums/eventType'
import type { FlowVersion } from '../enums/flowVersion'
import type { ThinkingPhase } from '../enums/thinkingPhase'

export interface ContextWindowDTO {
  context_id: string
  context_size: number
}

// Exatamente estes 10 campos, sem extras (README, seção 3.2). `flow_version` vem em todo frame para que
// as fases ambíguas sejam lidas pela versão certa; um frame antigo sem o campo é lido como versão 1.
export interface ReasoningEventDTO {
  type: EventType
  subtype: EventSubtype
  phase: ThinkingPhase
  task: string
  session_id: string
  content: string
  total_tokens: number
  context_window: ContextWindowDTO
  inference_time_ms: number
  flow_version: FlowVersion
}

/** Frame reduzido de erro, fora do contrato de 9 campos (README, seção 3.2). */
export interface ReasoningErrorFrame {
  type: 'error'
  content: string
}

export type ReasoningFrame = ReasoningEventDTO | ReasoningErrorFrame
