// `unknown` → `ReasoningFrame` (README, FASE 02, seção 5). O backend usa dois formatos na
// mesma conexão: o frame de 9 campos e o frame reduzido de erro — a forma é decidida antes de
// validar os campos.

import { EVENT_SUBTYPE, isEventSubtype, type EventSubtype } from '../../domain/enums/eventSubtype'
import { isEventType } from '../../domain/enums/eventType'
import { isThinkingPhase, THINKING_PHASE, type ThinkingPhase } from '../../domain/enums/thinkingPhase'
import type {
  ContextWindowDTO,
  ReasoningErrorFrame,
  ReasoningEventDTO,
  ReasoningFrame,
} from '../../domain/types/reasoningEvent'
import { ContractError } from '../errors/ContractError'
import { requireNumber, requireObject, requireString } from './primitives'

// Chaves exclusivas do frame de evento completo — presentes apenas nesse formato, nunca no
// frame reduzido de erro (README, seção 3.2).
const EVENT_ONLY_KEYS = ['subtype', 'phase', 'task', 'session_id', 'context_window'] as const

function isErrorFrameShape(obj: Record<string, unknown>): boolean {
  return obj.type === 'error' && !EVENT_ONLY_KEYS.some((key) => key in obj)
}

function parseContextWindow(source: Record<string, unknown>): ContextWindowDTO {
  const raw = requireObject(source.context_window, 'context_window')
  return {
    context_id: requireString(raw, 'context_id', 'context_window.context_id'),
    context_size: requireNumber(raw, 'context_size', 'context_window.context_size'),
  }
}

function fallbackSubtype(rawSubtype: string): EventSubtype {
  if (isEventSubtype(rawSubtype)) return rawSubtype
  console.warn(`[reasoningFrame] subtype desconhecido "${rawSubtype}", usando fallback`)
  return EVENT_SUBTYPE.REASONING
}

function fallbackPhase(rawPhase: string): ThinkingPhase {
  if (isThinkingPhase(rawPhase)) return rawPhase
  console.warn(`[reasoningFrame] phase desconhecida "${rawPhase}", usando fallback`)
  return THINKING_PHASE.B1
}

function parseReasoningEvent(obj: Record<string, unknown>): ReasoningEventDTO {
  const rawType = requireString(obj, 'type', 'type')
  if (!isEventType(rawType)) {
    throw new ContractError(`campo "type" tem valor fora do enum EventType: "${rawType}"`)
  }

  const subtype = fallbackSubtype(requireString(obj, 'subtype', 'subtype'))
  const phase = fallbackPhase(requireString(obj, 'phase', 'phase'))

  return {
    type: rawType,
    subtype,
    phase,
    task: requireString(obj, 'task', 'task'),
    session_id: requireString(obj, 'session_id', 'session_id'),
    content: requireString(obj, 'content', 'content'),
    total_tokens: requireNumber(obj, 'total_tokens', 'total_tokens'),
    context_window: parseContextWindow(obj),
    inference_time_ms: requireNumber(obj, 'inference_time_ms', 'inference_time_ms'),
  }
}

function parseReasoningErrorFrame(obj: Record<string, unknown>): ReasoningErrorFrame {
  return {
    type: 'error',
    content: requireString(obj, 'content', 'content'),
  }
}

export function parseReasoningFrame(raw: unknown): ReasoningFrame {
  const obj = requireObject(raw, 'frame')

  if (isErrorFrameShape(obj)) {
    return parseReasoningErrorFrame(obj)
  }

  // Não é o formato reduzido de erro — a única outra forma válida é o evento de 9 campos.
  // `parseReasoningEvent` valida campo a campo e nomeia o primeiro que faltar ou tiver tipo
  // errado, o que cobre tanto o evento incompleto quanto qualquer formato desconhecido.
  return parseReasoningEvent(obj)
}
