// Contrato do frame do WebSocket `/v1/message/reasoning` (README, seção 3.2).

import type { EventSubtype } from '../enums/eventSubtype'
import type { EventType } from '../enums/eventType'
import type { ThinkingPhase } from '../enums/thinkingPhase'

export interface ContextWindowDTO {
  context_id: string
  context_size: number
}

// Exatamente estes 9 campos, sem extras — qualquer campo a mais ou a menos é violação de
// contrato (README, seção 3.2).
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
}

/** Frame reduzido de erro, fora do contrato de 9 campos (README, seção 3.2). */
export interface ReasoningErrorFrame {
  type: 'error'
  content: string
}

export type ReasoningFrame = ReasoningEventDTO | ReasoningErrorFrame
