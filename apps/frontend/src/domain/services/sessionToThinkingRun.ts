// Reconstrói o view-model `ThinkingRun` a partir de uma sessão persistida (`flow !== 'DIRECT'`)
// (README, seção 6.2 e 3.5; FASE 07, seção 3.3). Função pura: não importa React nem nada de
// `src/api/`.
//
// Estratégia obrigatória (FASE 07): reconstrói a sequência de `ReasoningEventDTO` que a execução
// ao vivo teria emitido e a alimenta, na ordem, ao MESMO `reasoningRunReducer` usado pelo
// WebSocket — nunca uma segunda implementação da agregação de tarefas/tentativas/totais. Isso é
// o que garante, por construção, que histórico e execução ao vivo produzam o mesmo `ThinkingRun`.

import { EVENT_SUBTYPE } from '../enums/eventSubtype'
import { EVENT_TYPE } from '../enums/eventType'
import { RUN_STATUS, type RunStatus } from '../enums/runStatus'
import { SESSION_STATUS } from '../enums/sessionStatus'
import { TASK_LABEL_SETUP, TASK_LABEL_SYNTHESIS } from '../enums/taskLabels'
import { THINKING_PHASE, isThinkingPhase, type ThinkingPhase } from '../enums/thinkingPhase'
import type {
  SessionDegradationDocument,
  SessionDocument,
  SessionMessageDocument,
} from '../types/sessionDocument'
import type { ReasoningEventDTO } from '../types/reasoningEvent'
import type { RunDegradation, ThinkingRun } from '../types/thinkingRun'
import { deriveStepKind } from './deriveSubtype'
import { createEmptyRun, reasoningRunReducer } from './reasoningRunReducer'
import { parseTasksFromMarkdown, type ParsedTask } from './taskParser'

function taskLabelFor(phase: ThinkingPhase): string {
  return phase.startsWith('C') ? TASK_LABEL_SYNTHESIS : TASK_LABEL_SETUP
}

// Reconstrói um bloco de markdown de tarefa a partir do que `parseTasksFromMarkdown` extraiu de
// A.2/C.2 — é o texto que o passo `execute` sintetizado (seção 3.2) usa como conteúdo, já que o
// backend não persiste o evento `execute` em si.
function renderTaskBlock(task: ParsedTask): string {
  const lines = [`### ${task.id} — ${task.title ?? ''}`.trimEnd()]
  if (task.description) lines.push('', task.description)
  if (task.expectedInput) lines.push('', `**Entrada esperada:** ${task.expectedInput}`)
  if (task.expectedOutput) lines.push(`**Saída esperada:** ${task.expectedOutput}`)
  if (task.criteria.length > 0) {
    lines.push('', '**Critérios de aceite:**')
    for (const criterion of task.criteria) {
      lines.push(`- \`${criterion.id}\`: ${criterion.text}`)
    }
  }
  return lines.join('\n')
}

// Procura o bloco da tarefa `taskId` em qualquer mensagem A2/C2 já vista — a tarefa pode ter
// sido criada tanto no planejamento inicial quanto num replanejamento (C.2).
function findTaskBlock(planningMessages: readonly SessionMessageDocument[], taskId: string): string {
  for (const planningMessage of planningMessages) {
    const task = parseTasksFromMarkdown(planningMessage.content).find((candidate) => candidate.id === taskId)
    if (task) return renderTaskBlock(task)
  }
  // Tarefa não encontrada no markdown de planejamento (formato inesperado): conteúdo mínimo,
  // nunca um passo em branco (README, FASE 07, seção 3.2).
  return `### ${taskId}`
}

/** Mapeia `SessionStatus` (documento) para `RunStatus` (view-model) — reusado por
 * `sessionToSimpleRun.ts`, já que os dois fluxos compartilham o mesmo vocabulário de status. */
export function toRunStatus(status: SessionDocument['status']): RunStatus {
  switch (status) {
    case SESSION_STATUS.RUNNING:
      return RUN_STATUS.RUNNING
    case SESSION_STATUS.COMPLETED:
      return RUN_STATUS.COMPLETED
    case SESSION_STATUS.DEGRADED:
      return RUN_STATUS.DEGRADED
    case SESSION_STATUS.FAILED:
      return RUN_STATUS.FAILED
    default:
      return RUN_STATUS.FAILED
  }
}

function toDegradation(document: SessionDegradationDocument): RunDegradation {
  return {
    limit: document.limit,
    phase: isThinkingPhase(document.phase) ? document.phase : THINKING_PHASE.A1,
    taskId: document.task_id,
    description: document.description,
    occurredAt: document.occurred_at,
  }
}

// Um item da conversão mensagem → evento: o evento em si, e a mensagem de origem (`null` para o
// passo `execute` sintetizado, que não tem mensagem persistida correspondente) — usada só para
// recuperar o `timestamp` depois que o reducer processa tudo.
interface StepSource {
  event: ReasoningEventDTO
  timestamp: string | null
}

// Contadores de acumulação, mantidos ao longo da iteração cronológica das mensagens (seção 3.3
// da FASE 07): `total_tokens` é o acumulado da sessão inteira; `context_size` é o acumulado por
// `context_id`, e é isso que reproduz a serra dentada do *fresh context* no histórico.
class Accumulators {
  private totalTokens = 0
  private readonly contextTotals = new Map<string, number>()

  addMessage(message: SessionMessageDocument): { totalTokens: number; contextSize: number } {
    this.totalTokens += message.total_tokens
    const contextId = message.context_id ?? ''
    const contextSize = (this.contextTotals.get(contextId) ?? 0) + message.total_tokens
    this.contextTotals.set(contextId, contextSize)
    return { totalTokens: this.totalTokens, contextSize }
  }

  get currentTotalTokens(): number {
    return this.totalTokens
  }
}

function buildEvent(
  document: SessionDocument,
  message: SessionMessageDocument,
  kind: { type: ReasoningEventDTO['type']; subtype: ReasoningEventDTO['subtype'] },
  totals: { totalTokens: number; contextSize: number },
): ReasoningEventDTO {
  return {
    type: kind.type,
    subtype: kind.subtype,
    phase: message.phase,
    task: message.task_id ?? taskLabelFor(message.phase),
    session_id: document.id,
    content: message.content,
    total_tokens: totals.totalTokens,
    context_window: { context_id: message.context_id ?? '', context_size: totals.contextSize },
    inference_time_ms: message.inference_time_ms,
  }
}

// Constrói a sequência de eventos que a execução ao vivo teria emitido, incluindo o passo
// `execute` sintetizado logo após cada `reset` (README, seção 3.5; FASE 07, seção 3.2) — os dois
// únicos eventos ao vivo que não são persistidos (`execute` e o `error` fora do fluxo normal, que
// não se aplica aqui).
function buildStepSources(document: SessionDocument): StepSource[] {
  const messages = [...document.messages].sort((a, b) => a.order - b.order)
  const planningMessages = messages.filter(
    (message) =>
      (message.phase === THINKING_PHASE.A2 || message.phase === THINKING_PHASE.C2) &&
      message.source !== 'user',
  )
  const accumulators = new Accumulators()
  const sources: StepSource[] = []

  messages.forEach((message, index) => {
    const kind = deriveStepKind(message, { laterMessages: messages.slice(index + 1) })
    if (!kind) return

    const totals = accumulators.addMessage(message)
    sources.push({ event: buildEvent(document, message, kind, totals), timestamp: message.timestamp })

    if (kind.subtype === EVENT_SUBTYPE.RESET && message.task_id) {
      const executeContent = findTaskBlock(planningMessages, message.task_id)
      sources.push({
        event: buildEvent(
          document,
          { ...message, content: executeContent, inference_time_ms: 0 },
          { type: EVENT_TYPE.THINKING, subtype: EVENT_SUBTYPE.EXECUTE },
          totals,
        ),
        timestamp: null,
      })
    }
  })

  return sources
}

/** Reconstrói o `ThinkingRun` de uma sessão persistida do Ralph Loop Adaptado (`flow !== 'DIRECT'`). */
export function sessionToThinkingRun(document: SessionDocument): ThinkingRun {
  const sources = buildStepSources(document)

  let run = createEmptyRun(document.user_question, document.model_name)
  run = { ...run, status: RUN_STATUS.RUNNING }
  for (const source of sources) {
    run = reasoningRunReducer(run, { kind: 'event', event: source.event })
  }

  const stepsWithTimestamp = run.steps.map((step, index) => ({
    ...step,
    timestamp: sources[index]?.timestamp ?? null,
  }))

  return {
    ...run,
    sessionId: document.id,
    question: document.user_question,
    modelName: document.model_name,
    status: toRunStatus(document.status),
    steps: stepsWithTimestamp,
    finalAnswer: document.final_answer,
    totals: {
      ...run.totals,
      totalTokens: document.totals.total_tokens,
      inferenceTimeMs: document.totals.inference_time_ms,
      llmCalls: document.totals.total_llm_calls,
      wallTimeMs: document.totals.wall_time_ms,
    },
    degradations: document.degradations.map(toDegradation),
  }
}
