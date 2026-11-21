// Deriva `(type, subtype)` de uma mensagem persistida (README, seção 3.5). A mensagem salva
// não carrega `subtype` — só o evento ao vivo do WebSocket tem esse campo — então a tela de
// histórico precisa reconstruí-lo a partir de `(phase, source, content)` para produzir a mesma
// linha do tempo que a execução ao vivo. Função pura: nunca lança, mesmo para uma combinação
// fora da tabela conhecida.

import { EVENT_SUBTYPE, type EventSubtype } from '../enums/eventSubtype'
import { EVENT_TYPE, type EventType } from '../enums/eventType'
import { FLOW_VERSION, type FlowVersion } from '../enums/flowVersion'
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
  /** Versão do fluxo da sessão; ausente, a sessão é antiga (versão 1, A.3 = aprendizados do enunciado). */
  flowVersion?: FlowVersion
}

// Fluxo versão 2 sem subtipo persistido (não ocorre em sessões gravadas pelo backend atual): A.2 é sempre
// um candidato — nunca tarefas confirmadas —, A.3 lê o marcador da decisão do plano e A.4 é a extração.
const PLAN_DECISION_RE = /\*\*Plan decision:\*\*\s*`(approved|rejected)`/

function deriveValidatedPlanningSubtype(message: SessionMessageDocument): EventSubtype | null {
  if (message.phase === THINKING_PHASE.A2) return EVENT_SUBTYPE.PLAN_CANDIDATE
  if (message.phase === THINKING_PHASE.A4) return EVENT_SUBTYPE.LEARN
  if (message.phase !== THINKING_PHASE.A3) return null
  const decision = PLAN_DECISION_RE.exec(message.content)?.[1]
  if (decision === 'approved') return EVENT_SUBTYPE.PLAN_APPROVED
  if (decision === 'rejected') return EVENT_SUBTYPE.PLAN_REJECTED
  // Sem marcador reconhecível, A.3 não pode ser lida como aprendizados (significado da versão 1) nem como
  // uma decisão adivinhada: degrada para o subtipo mais neutro.
  return EVENT_SUBTYPE.REASONING
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
 * passo de pensamento (a pergunta do usuário, uma mensagem do fluxo baseline `DIRECT` ou, na versão 2,
 * um registro sem evento, como a auditoria de uma saída recusada).
 *
 * Sessões novas persistem o subtipo do evento: ele é usado diretamente, para que o histórico reproduza o
 * fluxo ao vivo sem adivinhar pelo conteúdo. Sessões antigas não o têm e seguem a derivação histórica,
 * em que `A3` é a extração dos aprendizados do enunciado.
 */
export function deriveStepKind(
  message: SessionMessageDocument,
  context: DeriveStepKindContext,
): DerivedStepKind | null {
  if (message.phase === THINKING_PHASE.DIRECT) return null
  if (message.source === MESSAGE_SOURCE.USER) return null

  // O subtipo persistido e o descarte dos registros sem evento vêm antes da regra de C.3: a auditoria de uma
  // saída recusada continua armazenada, mas não é passo nem resposta.
  if (message.subtype) {
    return { type: EVENT_TYPE.THINKING, subtype: message.subtype }
  }

  if (context.flowVersion === FLOW_VERSION.VALIDATED_PLANNING && message.source === MESSAGE_SOURCE.SYSTEM) {
    return null
  }

  // C.3 só grava como etapa do sistema a auditoria de uma saída recusada, em qualquer versão. A mensagem
  // aceita é o `thinking/compile`; o evento terminal `result/compile`, que ao vivo vem depois dela, é
  // reconstruído por `sessionToThinkingRun` quando a sessão tem resposta final.
  if (message.phase === THINKING_PHASE.C3) {
    if (message.source === MESSAGE_SOURCE.SYSTEM) return null
    return { type: EVENT_TYPE.THINKING, subtype: EVENT_SUBTYPE.COMPILE }
  }

  if (context.flowVersion === FLOW_VERSION.VALIDATED_PLANNING) {
    const subtype = deriveValidatedPlanningSubtype(message)
    if (subtype) return { type: EVENT_TYPE.THINKING, subtype }
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
