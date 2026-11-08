// Sessão baseline (fluxo DIRECT) montada a partir da resposta de `POST /v1/message/default`
// (README, FASE 04, seção 6). Mesmo sendo uma única chamada, passa pela camada de domínio para
// que a FASE 07 consiga reconstruir a mesma tela a partir de uma sessão `DIRECT` persistida.

import { RUN_STATUS } from '../enums/runStatus'
import type { DefaultOutputDTO } from '../types/defaultOutput'
import type { MessageStatsView } from '../types/messageStatsView'
import type { SimpleMessage, SimpleRun } from '../types/simpleRun'

function createMessageId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `msg_${crypto.randomUUID()}`
  }
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2)}`
}

// O `DefaultOutputDTO` não devolve o modelo usado — o backend não ecoa essa informação na
// resposta simples — por isso o nome do modelo vem de fora (do `RunConfig` de quem chamou),
// nunca do próprio DTO.
export function simpleRunFromResponse(
  question: string,
  response: DefaultOutputDTO,
  modelName: string,
): SimpleRun {
  const userMessage: SimpleMessage = {
    id: createMessageId(),
    role: 'user',
    content: question,
    stats: null,
  }

  const stats: MessageStatsView = {
    modelName,
    tokensInput: response.tokens_input,
    tokensOutput: response.tokens_output,
    totalTokens: response.tokens_input + response.tokens_output,
    inferenceTimeMs: response.inference_time_ms,
    contextId: null,
    contextSize: null,
    timestamp: null,
    sessionId: response.session_id,
  }

  const assistantMessage: SimpleMessage = {
    id: createMessageId(),
    role: 'assistant',
    content: response.response,
    stats,
  }

  return {
    sessionId: response.session_id,
    status: RUN_STATUS.COMPLETED,
    messages: [userMessage, assistantMessage],
    totals: {
      totalMessages: 2,
      totalLlmCalls: 1,
      tokensInput: response.tokens_input,
      tokensOutput: response.tokens_output,
      totalTokens: response.tokens_input + response.tokens_output,
      inferenceTimeMs: response.inference_time_ms,
      wallTimeMs: response.inference_time_ms,
    },
    error: null,
  }
}
