// "O teste que prova o requisito" (README, FASE 07, seção 7): monta, de forma independente da
// implementação de `sessionToThinkingRun`, a sequência de eventos que a execução ao vivo teria
// emitido para esta sessão real — incluindo os passos `execute` sintetizados — e roda os dois
// caminhos (reducer direto vs. `sessionToThinkingRun`) até o mesmo `ThinkingRun`, estruturalmente.

import { describe, expect, it } from 'vitest'
import fixture from '@/test/fixtures/session-a1-completed-15msgs.json'
import withA3Fixture from '@/test/fixtures/session-a1-completed-with-a3.json'
import { TASK_LABEL_SETUP, TASK_LABEL_SYNTHESIS } from '../enums/taskLabels'
import type { EventSubtype } from '../enums/eventSubtype'
import type { EventType } from '../enums/eventType'
import type { ThinkingPhase } from '../enums/thinkingPhase'
import type { ReasoningEventDTO } from '../types/reasoningEvent'
import type { SessionDocument } from '../types/sessionDocument'
import type { ThinkingRun, ThinkingStep } from '../types/thinkingRun'
import { createEmptyRun, reasoningRunReducer } from './reasoningRunReducer'
import { sessionToThinkingRun } from './sessionToThinkingRun'
import { parseTasksFromMarkdown, type ParsedTask } from './taskParser'

// Reconstrução independente do bloco de tarefa usado pelo passo `execute` sintetizado — mesma
// forma que `sessionToThinkingRun.ts` produz (README, FASE 07, seção 3.2), mas escrita aqui de
// novo, sem importar a função privada, para que a comparação não vire uma tautologia.
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

const legacyDocument = fixture as unknown as SessionDocument
const withA3Document = withA3Fixture as unknown as SessionDocument

interface EventMeta {
  order: number
  subtype: EventSubtype
  type: EventType
  task: string
  synthesizeExecute?: boolean
}

const LEGACY_EVENT_META: EventMeta[] = [
  { order: 1, subtype: 'setup', type: 'thinking', task: TASK_LABEL_SETUP },
  { order: 2, subtype: 'tasks', type: 'thinking', task: TASK_LABEL_SETUP },
  { order: 3, subtype: 'reset', type: 'thinking', task: 'T1', synthesizeExecute: true },
  { order: 4, subtype: 'reasoning', type: 'thinking', task: 'T1' },
  { order: 5, subtype: 'verify_pass', type: 'thinking', task: 'T1' },
  { order: 6, subtype: 'store', type: 'thinking', task: 'T1' },
  { order: 7, subtype: 'learn', type: 'thinking', task: 'T1' },
  { order: 8, subtype: 'reset', type: 'thinking', task: 'T2', synthesizeExecute: true },
  { order: 9, subtype: 'reasoning', type: 'thinking', task: 'T2' },
  { order: 10, subtype: 'verify_pass', type: 'thinking', task: 'T2' },
  { order: 11, subtype: 'store', type: 'thinking', task: 'T2' },
  { order: 12, subtype: 'learn', type: 'thinking', task: 'T2' },
  { order: 13, subtype: 'compile', type: 'thinking', task: TASK_LABEL_SYNTHESIS },
  { order: 14, subtype: 'compile', type: 'result', task: TASK_LABEL_SYNTHESIS },
]

// Mesma sessão com a etapa A.3: a mensagem de aprendizados do enunciado (order 3) entra entre A.2 e a
// primeira tarefa, e todas as seguintes avançam uma posição.
const A3_EVENT_META: EventMeta[] = [
  ...LEGACY_EVENT_META.slice(0, 2),
  { order: 3, subtype: 'learn', type: 'thinking', task: TASK_LABEL_SETUP },
  ...LEGACY_EVENT_META.slice(2).map((meta) => ({ ...meta, order: meta.order + 1 })),
]

// Reproduz, de forma independente, a sequência de eventos ao vivo que este documento persistido
// representa — inclusive o passo `execute` sintetizado logo após cada `reset` (o único, junto do
// `error`, que não é persistido). `context_size` acumula por `context_id`, como o README manda.
function buildLiveLikeEvents(document: SessionDocument, eventMeta: EventMeta[]): ReasoningEventDTO[] {
  let cumulativeTokens = 0
  const contextTotals = new Map<string, number>()
  const events: ReasoningEventDTO[] = []

  function contextSizeFor(contextId: string, tokens: number): number {
    const next = (contextTotals.get(contextId) ?? 0) + tokens
    contextTotals.set(contextId, next)
    return next
  }

  for (const meta of eventMeta) {
    const message = document.messages.find((candidate) => candidate.order === meta.order)
    if (!message) throw new Error(`fixture sem mensagem de order ${meta.order}`)

    cumulativeTokens += message.total_tokens
    const contextId = message.context_id ?? ''
    const contextSize = contextSizeFor(contextId, message.total_tokens)

    const event: ReasoningEventDTO = {
      type: meta.type,
      subtype: meta.subtype,
      phase: message.phase as ThinkingPhase,
      task: meta.task,
      session_id: document.id,
      content: message.content,
      total_tokens: cumulativeTokens,
      context_window: { context_id: contextId, context_size: contextSize },
      inference_time_ms: message.inference_time_ms,
    }
    events.push(event)

    if (meta.synthesizeExecute && message.task_id) {
      const planningMessage = document.messages.find((candidate) => candidate.phase === 'A2')
      const task = planningMessage
        ? parseTasksFromMarkdown(planningMessage.content).find((candidate) => candidate.id === message.task_id)
        : undefined
      const executeContent = task ? renderTaskBlock(task) : `### ${message.task_id}`

      events.push({
        ...event,
        subtype: 'execute',
        task: message.task_id,
        content: executeContent,
        inference_time_ms: 0,
      })
    }
  }

  return events
}

function stripStep(step: ThinkingStep): Omit<ThinkingStep, 'timestamp'> {
  const { timestamp: _timestamp, ...rest } = step
  return rest
}

// Ignora só os campos que existem de um único lado por natureza (README, FASE 07, seção 7):
// `timestamp` (só no histórico) e `wallTimeMs` (só no histórico). Todo o resto — ids de passo,
// ordem, tarefas, tentativas, totais — precisa ser estruturalmente idêntico.
function stripVolatile(run: ThinkingRun): unknown {
  return {
    ...run,
    steps: run.steps.map(stripStep),
    tasks: run.tasks.map((task) => ({
      ...task,
      steps: task.steps.map(stripStep),
      attempts: task.attempts.map((attempt) => ({
        ...attempt,
        reasoning: attempt.reasoning ? stripStep(attempt.reasoning) : null,
        verification: attempt.verification ? stripStep(attempt.verification) : null,
      })),
    })),
    totals: { ...run.totals, wallTimeMs: null },
  }
}

describe.each([
  ['sessão sem A.3 (anterior à etapa)', legacyDocument, LEGACY_EVENT_META],
  ['sessão com A.3', withA3Document, A3_EVENT_META],
] as const)('parity: histórico vs. execução ao vivo — %s', (_name, document, eventMeta) => {
  it('sessionToThinkingRun produz o mesmo ThinkingRun, estruturalmente, que a execução ao vivo equivalente', () => {
    const liveEvents = buildLiveLikeEvents(document, [...eventMeta])
    let liveRun = createEmptyRun(document.user_question, document.model_name)
    for (const event of liveEvents) {
      liveRun = reasoningRunReducer(liveRun, { kind: 'event', event })
    }
    liveRun = { ...liveRun, sessionId: document.id, status: 'completed', finalAnswer: document.final_answer }

    const historyRun = sessionToThinkingRun(document)

    expect(stripVolatile(historyRun)).toEqual(stripVolatile(liveRun))
  })
})
