// Resume um `SessionDocument` completo no card de histórico (README, FASE 07, seção 4). Função
// pura, sem truncamento — o limite de caracteres vive em `env` (config, não domínio), então
// `sessionSummary` devolve `question` igual a `fullQuestion`; quem aplica o corte é a camada de
// hooks (`useSessionList`), que já lê `env`.

import { THINKING_PHASE } from '../enums/thinkingPhase'
import type { SessionDocument } from '../types/sessionDocument'
import type { SessionSummaryView } from '../types/sessionSummaryView'

export function sessionSummary(document: SessionDocument): SessionSummaryView {
  return {
    id: document.id,
    question: document.user_question,
    fullQuestion: document.user_question,
    flow: document.flow === THINKING_PHASE.DIRECT ? 'simple' : 'ralph',
    status: document.status,
    createdAt: document.created_at,
    totalTokens: document.totals.total_tokens,
    messageCount: document.totals.total_messages,
  }
}
