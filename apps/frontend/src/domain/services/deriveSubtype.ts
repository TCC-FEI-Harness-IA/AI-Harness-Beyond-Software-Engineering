// Deriva `(type, subtype)` de uma mensagem persistida (README, seção 3.5). A mensagem salva
// não carrega `subtype` — só o evento ao vivo do WebSocket tem esse campo — então a tela de
// histórico precisa reconstruí-lo a partir de `(phase, source, content)` para produzir a mesma
// linha do tempo que a execução ao vivo. Função pura: nunca lança, mesmo para uma combinação
// fora da tabela conhecida.

import { EVENT_SUBTYPE, type EventSubtype } from '../enums/eventSubtype'
import { EVENT_TYPE, type EventType } from '../enums/eventType'
import { MESSAGE_SOURCE } from '../enums/messageSource'
import { THINKING_PHASE, type ThinkingPhase } from '../enums/thinkingPhase'
import type { SessionMessageDocument } from '../types/sessionDocument'
import { parseDecision } from './taskParser'

export interface DerivedStepKind {
  type: EventType
  subtype: EventSubtype
}

export interface DeriveStepKindContext {
  /** Mensagens da mesma sessão que vêm depois desta na ordem cronológica — usadas só pelo
   * fallback posicional de `verify_pass`/`verify_fail`. */
  laterMessages: readonly SessionMessageDocument[]
}

// Combinações `(phase, source)` que mapeiam para um único `subtype` fixo (README, seção 3.5).
// B1 e B2 ficam fora desta tabela porque dependem de `source` (B1) ou de conteúdo (B2).
const PHASE_SUBTYPE: Partial<Record<ThinkingPhase, EventSubtype>> = {
  A1: EVENT_SUBTYPE.SETUP,
  A2: EVENT_SUBTYPE.TASKS,
  A3: EVENT_SUBTYPE.LEARN,
  B3: EVENT_SUBTYPE.STORE,
  B4: EVENT_SUBTYPE.LEARN,
  C1: EVENT_SUBTYPE.COMPILE,
  C2: EVENT_SUBTYPE.REPLAN,
}

// Regra de precedência da seção 3.5: o marcador fixo `**Decisão:** \`approved|reproved\`` vence;
// só cai no fallback posicional quando o template não foi reconhecido no conteúdo.
function deriveVerifySubtype(
  message: SessionMessageDocument,
  context: DeriveStepKindContext,
): EventSubtype {
  const decision = parseDecision(message.content)
  if (decision === 'approved') return EVENT_SUBTYPE.VERIFY_PASS
  if (decision === 'reproved') return EVENT_SUBTYPE.VERIFY_FAIL

  const hasLaterAttemptForSameTask = context.laterMessages.some(
    (later) => later.phase === THINKING_PHASE.B2 && later.task_id === message.task_id,
  )
  return hasLaterAttemptForSameTask ? EVENT_SUBTYPE.VERIFY_FAIL : EVENT_SUBTYPE.VERIFY_PASS
}

/**
 * Deriva `(type, subtype)` de uma mensagem persistida, ou `null` quando a mensagem não vira um
 * passo de pensamento (a pergunta do usuário, ou uma mensagem do fluxo baseline `DIRECT`).
 */
export function deriveStepKind(
  message: SessionMessageDocument,
  context: DeriveStepKindContext,
): DerivedStepKind | null {
  if (message.phase === THINKING_PHASE.DIRECT) return null
  if (message.source === MESSAGE_SOURCE.USER) return null

  if (message.phase === THINKING_PHASE.C3) {
    return { type: EVENT_TYPE.RESULT, subtype: EVENT_SUBTYPE.COMPILE }
  }

  if (message.phase === THINKING_PHASE.B1) {
    const subtype =
      message.source === MESSAGE_SOURCE.SYSTEM ? EVENT_SUBTYPE.RESET : EVENT_SUBTYPE.REASONING
    return { type: EVENT_TYPE.THINKING, subtype }
  }

  if (message.phase === THINKING_PHASE.B2) {
    return { type: EVENT_TYPE.THINKING, subtype: deriveVerifySubtype(message, context) }
  }

  const subtype = PHASE_SUBTYPE[message.phase]
  if (subtype) {
    return { type: EVENT_TYPE.THINKING, subtype }
  }

  // Combinação não prevista: nunca lança, nunca descarta a mensagem — degrada para o subtype
  // mais neutro (README, FASE 07, seção 3.1, regra 6).
  console.warn(
    `[deriveStepKind] combinação (phase="${message.phase}", source="${message.source}") não prevista — usando fallback "reasoning"`,
  )
  return { type: EVENT_TYPE.THINKING, subtype: EVENT_SUBTYPE.REASONING }
}
