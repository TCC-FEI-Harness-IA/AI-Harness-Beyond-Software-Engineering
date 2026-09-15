// `unknown` → `SessionDocument` (README, FASE 02, seção 5) — `GET /v1/sessions/{session_id}`.
// Diferente de `parseReasoningFrame`, aqui não há stream ao vivo para proteger: uma mensagem
// inválida invalida o documento inteiro.

import { isBudgetLimit } from '../../domain/enums/budgetLimit'
import { isMessageSource } from '../../domain/enums/messageSource'
import { isSessionStatus } from '../../domain/enums/sessionStatus'
import { isThinkingPhase } from '../../domain/enums/thinkingPhase'
import type {
  SessionDegradationDocument,
  SessionDocument,
  SessionMessageDocument,
  SessionTotalsDocument,
} from '../../domain/types/sessionDocument'
import { ContractError } from '../errors/ContractError'
import { optionalString, requireArray, requireNumber, requireObject, requireString } from './primitives'

function parseTotals(source: Record<string, unknown>): SessionTotalsDocument {
  const raw = requireObject(source.totals, 'totals')
  return {
    total_messages: requireNumber(raw, 'total_messages', 'totals.total_messages'),
    total_llm_calls: requireNumber(raw, 'total_llm_calls', 'totals.total_llm_calls'),
    tokens_input: requireNumber(raw, 'tokens_input', 'totals.tokens_input'),
    tokens_output: requireNumber(raw, 'tokens_output', 'totals.tokens_output'),
    total_tokens: requireNumber(raw, 'total_tokens', 'totals.total_tokens'),
    inference_time_ms: requireNumber(raw, 'inference_time_ms', 'totals.inference_time_ms'),
    wall_time_ms: requireNumber(raw, 'wall_time_ms', 'totals.wall_time_ms'),
  }
}

function parseMessage(raw: unknown, index: number): SessionMessageDocument {
  const path = `messages[${index}]`
  const obj = requireObject(raw, path)

  const phase = requireString(obj, 'phase', `${path}.phase`)
  if (!isThinkingPhase(phase)) {
    throw new ContractError(`campo "${path}.phase" tem valor fora do enum ThinkingPhase: "${phase}"`)
  }

  const source = requireString(obj, 'source', `${path}.source`)
  if (!isMessageSource(source)) {
    throw new ContractError(`campo "${path}.source" tem valor fora do enum MessageSource: "${source}"`)
  }

  return {
    id: requireString(obj, 'id', `${path}.id`),
    order: requireNumber(obj, 'order', `${path}.order`),
    timestamp: requireString(obj, 'timestamp', `${path}.timestamp`),
    phase,
    source,
    content: requireString(obj, 'content', `${path}.content`),
    task_id: optionalString(obj, 'task_id', `${path}.task_id`),
    context_id: optionalString(obj, 'context_id', `${path}.context_id`),
    tokens_input: requireNumber(obj, 'tokens_input', `${path}.tokens_input`),
    tokens_output: requireNumber(obj, 'tokens_output', `${path}.tokens_output`),
    total_tokens: requireNumber(obj, 'total_tokens', `${path}.total_tokens`),
    inference_time_ms: requireNumber(obj, 'inference_time_ms', `${path}.inference_time_ms`),
    model_name: optionalString(obj, 'model_name', `${path}.model_name`),
  }
}

function parseDegradation(raw: unknown, index: number): SessionDegradationDocument {
  const path = `degradations[${index}]`
  const obj = requireObject(raw, path)

  const limit = requireString(obj, 'limit', `${path}.limit`)
  if (!isBudgetLimit(limit)) {
    throw new ContractError(`campo "${path}.limit" tem valor fora do enum BudgetLimit: "${limit}"`)
  }

  return {
    limit,
    phase: requireString(obj, 'phase', `${path}.phase`),
    task_id: optionalString(obj, 'task_id', `${path}.task_id`),
    description: requireString(obj, 'description', `${path}.description`),
    occurred_at: requireString(obj, 'occurred_at', `${path}.occurred_at`),
  }
}

export function parseSessionDocument(raw: unknown): SessionDocument {
  const obj = requireObject(raw, 'sessionDocument')

  const flow = requireString(obj, 'flow', 'flow')
  if (!isThinkingPhase(flow)) {
    throw new ContractError(`campo "flow" tem valor fora do enum ThinkingPhase: "${flow}"`)
  }

  const status = requireString(obj, 'status', 'status')
  if (!isSessionStatus(status)) {
    throw new ContractError(`campo "status" tem valor fora do enum SessionStatus: "${status}"`)
  }

  const messages = requireArray(obj, 'messages', 'messages').map((item, index) =>
    parseMessage(item, index),
  )
  const degradations = requireArray(obj, 'degradations', 'degradations').map((item, index) =>
    parseDegradation(item, index),
  )

  return {
    id: requireString(obj, 'id', 'id'),
    user_question: requireString(obj, 'user_question', 'user_question'),
    flow,
    model_name: requireString(obj, 'model_name', 'model_name'),
    max_tokens: requireNumber(obj, 'max_tokens', 'max_tokens'),
    temperature: requireNumber(obj, 'temperature', 'temperature'),
    status,
    created_at: requireString(obj, 'created_at', 'created_at'),
    updated_at: requireString(obj, 'updated_at', 'updated_at'),
    final_answer: optionalString(obj, 'final_answer', 'final_answer'),
    totals: parseTotals(obj),
    messages,
    degradations,
  }
}
