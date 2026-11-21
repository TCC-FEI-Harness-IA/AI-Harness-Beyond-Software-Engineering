// Paridade para sessões ANTIGAS (fluxo versão 1), sem captura disponível: a sequência de eventos é uma
// reconstrução SINTÉTICA, montada aqui a partir das mensagens persistidas e de metadados escritos à mão
// (subtype/type/task), de forma independente da implementação de `sessionToThinkingRun` — inclusive os
// passos `execute`. Ela não é um registro do que o WebSocket enviou e por isso não prova, sozinha, que o
// histórico reproduz a execução real; para o fluxo atual, a paridade é verificada contra eventos
// realmente capturados do backend em `validatedPlanning.test.ts`.

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

// O `execute` ao vivo traz a tarefa como o backend a renderizou, o mesmo texto que ele gravou no markdown de
// planejamento. A fatia é feita aqui por busca de texto, sem importar `extractTaskBlock`, para que a
// comparação não vire uma tautologia.
function taskBlockOf(markdown: string, taskId: string): string | null {
  const start = markdown.indexOf(`### ${taskId} `)
  if (start === -1) return null
  const next = markdown.indexOf('\n### T', start + 1)
  return markdown.slice(start, next === -1 ? markdown.length : next).trimEnd()
}

const legacyDocument = fixture as unknown as SessionDocument
const withA3Document = withA3Fixture as unknown as SessionDocument

interface EventMeta {
  order: number
  subtype: EventSubtype
  type: EventType
  task: string
  synthesizeExecute?: boolean
  /** C.3 aceita: ao vivo, o backend emite em seguida o terminal `result/compile` com o mesmo conteúdo. */
  terminalResult?: boolean
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
  { order: 14, subtype: 'compile', type: 'thinking', task: TASK_LABEL_SYNTHESIS, terminalResult: true },
]

// Mesma sessão com a etapa A.3: a mensagem de aprendizados do enunciado (order 3) entra entre A.2 e a
// primeira tarefa, e todas as seguintes avançam uma posição.
const A3_EVENT_META: EventMeta[] = [
  ...LEGACY_EVENT_META.slice(0, 2),
  { order: 3, subtype: 'learn', type: 'thinking', task: TASK_LABEL_SETUP },
  ...LEGACY_EVENT_META.slice(2).map((meta) => ({ ...meta, order: meta.order + 1 })),
]

// Reconstrói sinteticamente, de forma independente, a sequência de eventos que este documento persistido
// representa — inclusive o passo `execute` logo após cada `reset` (o único, junto do `error`, que não é
// persistido). `context_size` acumula por `context_id`, como o README manda.
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
      flow_version: 1,
    }
    events.push(event)

    if (meta.terminalResult) {
      events.push({ ...event, type: 'result' })
    }

    if (meta.synthesizeExecute && message.task_id) {
      const planningMessage = document.messages.find((candidate) => candidate.phase === 'A2')
      const executeContent =
        (planningMessage && taskBlockOf(planningMessage.content, message.task_id)) || `### ${message.task_id}`

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
] as const)('parity (reconstrução sintética, fluxo versão 1): histórico vs. eventos equivalentes — %s', (_name, document, eventMeta) => {
  it('sessionToThinkingRun produz o mesmo ThinkingRun, estruturalmente, que a sequência reconstruída', () => {
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
