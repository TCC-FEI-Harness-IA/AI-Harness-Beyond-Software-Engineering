// Reconstrói o view-model `SimpleRun` a partir de uma sessão persistida do fluxo baseline
// (`flow === 'DIRECT'`) (README, FASE 07, seção 3.4). Função pura: não importa React nem nada
// de `src/api/`. Bem mais simples que `sessionToThinkingRun` — uma sessão `DIRECT` tem no
// máximo duas mensagens (pergunta e resposta).

import type { MessageStatsView } from '../types/messageStatsView'
import type { SessionDocument, SessionMessageDocument } from '../types/sessionDocument'
import type { SimpleMessage, SimpleRun } from '../types/simpleRun'
import { toRunStatus } from './sessionToThinkingRun'

function toUserMessage(message: SessionMessageDocument): SimpleMessage {
  return { id: message.id, role: 'user', content: message.content, stats: null }
}

function toAssistantMessage(message: SessionMessageDocument, document: SessionDocument): SimpleMessage {
  const stats: MessageStatsView = {
    modelName: message.model_name ?? document.model_name,
    tokensInput: message.tokens_input,
    tokensOutput: message.tokens_output,
    totalTokens: message.total_tokens,
    inferenceTimeMs: message.inference_time_ms,
    contextId: null,
    contextSize: null,
    timestamp: message.timestamp,
    sessionId: document.id,
  }
  return { id: message.id, role: 'assistant', content: message.content, stats }
}

/** Reconstrói o `SimpleRun` de uma sessão persistida do fluxo baseline (`flow === 'DIRECT'`). */
export function sessionToSimpleRun(document: SessionDocument): SimpleRun {
  const sorted = [...document.messages].sort((a, b) => a.order - b.order)
  const userMessage = sorted.find((message) => message.source === 'user')
  const assistantMessage = sorted.find((message) => message.source === 'llm_agent')

  const messages: SimpleMessage[] = []
  if (userMessage) messages.push(toUserMessage(userMessage))
  if (assistantMessage) messages.push(toAssistantMessage(assistantMessage, document))

  return {
    sessionId: document.id,
    status: toRunStatus(document.status),
    messages,
    totals: assistantMessage
      ? {
          totalMessages: document.totals.total_messages,
          totalLlmCalls: document.totals.total_llm_calls,
          tokensInput: document.totals.tokens_input,
          tokensOutput: document.totals.tokens_output,
          totalTokens: document.totals.total_tokens,
          inferenceTimeMs: document.totals.inference_time_ms,
          wallTimeMs: document.totals.wall_time_ms,
        }
      : null,
    error: null,
  }
}
