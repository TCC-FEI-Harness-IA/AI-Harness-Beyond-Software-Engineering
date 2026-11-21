// Roteador de reconstrução (README, seção 6.2; FASE 07, seção 3.5): decide, pelo campo `flow`
// do documento, qual view-model reconstruir. É este tipo discriminado que a tela de detalhe do
// histórico consome para escolher entre `SimpleChatView` e `RalphView`, sem nenhum `if` extra
// além da própria checagem do `kind`.

import { THINKING_PHASE } from '../enums/thinkingPhase'
import type { SessionDocument } from '../types/sessionDocument'
import type { SimpleRun } from '../types/simpleRun'
import type { ThinkingRun } from '../types/thinkingRun'
import { sessionToSimpleRun } from './sessionToSimpleRun'
import { sessionToThinkingRun } from './sessionToThinkingRun'

export type SessionRun =
  | { kind: 'simple'; run: SimpleRun }
  | { kind: 'ralph'; run: ThinkingRun }

export function sessionToRun(document: SessionDocument): SessionRun {
  if (document.flow === THINKING_PHASE.DIRECT) {
    return { kind: 'simple', run: sessionToSimpleRun(document) }
  }
  return { kind: 'ralph', run: sessionToThinkingRun(document) }
}
