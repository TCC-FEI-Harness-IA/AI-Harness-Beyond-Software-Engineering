// Planejamento validado (fluxo versão 2): A.2 gera candidatos, A.3 os aprova ou reprova, a fila só recebe o
// plano aprovado (evento `tasks`, uma vez) e A.4 extrai os aprendizados. Os documentos vêm do backend real
// (completions roteirizadas): a execução ao vivo é reconstruída deles de forma independente e comparada
// ao histórico. Sessões antigas (versão 1) continuam com A.3 = aprendizados do enunciado.

import { describe, expect, it } from 'vitest'
import legacyWithA3Fixture from '@/test/fixtures/session-a1-completed-with-a3.json'
import exhaustedFixture from '@/test/fixtures/session-a1-v2-planning-exhausted.json'
import revisionFixture from '@/test/fixtures/session-a1-v2-plan-revision.json'
import { parseSessionDocument } from '@/api/parsers/sessionDocument'
import { TASK_LABEL_SETUP, TASK_LABEL_SYNTHESIS } from '../enums/taskLabels'
import type { ReasoningEventDTO } from '../types/reasoningEvent'
import type { SessionDocument, SessionMessageDocument } from '../types/sessionDocument'
import type { ThinkingRun, ThinkingStep } from '../types/thinkingRun'
import { buildLoopArcs, buildMacroTrack, describeTaskProgress } from './graphLayout'
import { createEmptyRun, reasoningRunReducer } from './reasoningRunReducer'
import { sessionToThinkingRun } from './sessionToThinkingRun'
import { parseTasksFromMarkdown, type ParsedTask } from './taskParser'

const revision = parseSessionDocument(revisionFixture)
const exhausted = parseSessionDocument(exhaustedFixture)
const legacy = parseSessionDocument(legacyWithA3Fixture)

// Reconstrução independente dos eventos ao vivo: o subtipo vem do registro persistido, os registros sem
// evento (a pergunta e a auditoria de saída recusada) ficam de fora, e cada `reset` é seguido pelo `execute`
// com o bloco da tarefa confirmada — copiado da confirmação, nunca de um candidato.
function renderTaskBlock(task: ParsedTask): string {
  const lines = [`### ${task.id} — ${task.title ?? ''}`.trimEnd()]
  if (task.description) lines.push('', task.description)
  if (task.criteria.length > 0) {
    lines.push('', '**Critérios de aceite:**')
    for (const criterion of task.criteria) lines.push(`- \`${criterion.id}\`: ${criterion.text}`)
  }
  return lines.join('\n')
}

function confirmedBlock(document: SessionDocument, taskId: string): string {
  const confirmation = document.messages.find((message) => message.subtype === 'tasks')
  const task = parseTasksFromMarkdown(confirmation?.content ?? '').find((candidate) => candidate.id === taskId)
  return task ? renderTaskBlock(task) : `### ${taskId}`
}

function liveEvents(document: SessionDocument): ReasoningEventDTO[] {
  let total = 0
  const windows = new Map<string, number>()
  const events: ReasoningEventDTO[] = []
  for (const message of document.messages as SessionMessageDocument[]) {
    if (message.source === 'user' || !message.subtype) continue
    total += message.total_tokens
    const contextId = message.context_id ?? ''
    const size = (windows.get(contextId) ?? 0) + message.total_tokens
    windows.set(contextId, size)
    const event: ReasoningEventDTO = {
      type: message.phase === 'C3' ? 'result' : 'thinking',
      subtype: message.subtype,
      phase: message.phase,
      task: message.task_id ?? (message.phase.startsWith('C') ? TASK_LABEL_SYNTHESIS : TASK_LABEL_SETUP),
      session_id: document.id,
      content: message.content,
      total_tokens: total,
      context_window: { context_id: contextId, context_size: size },
      inference_time_ms: message.inference_time_ms,
      flow_version: 2,
    }
    events.push(event)
    if (message.subtype === 'reset' && message.task_id) {
      events.push({
        ...event,
        subtype: 'execute',
        content: confirmedBlock(document, message.task_id),
        inference_time_ms: 0,
      })
    }
  }
  return events
}

function liveRun(document: SessionDocument): ThinkingRun {
  let run = createEmptyRun(document.user_question, document.model_name)
  for (const event of liveEvents(document)) {
    run = reasoningRunReducer(run, { kind: 'event', event })
  }
  return run
}

function stripStep(step: ThinkingStep): Omit<ThinkingStep, 'timestamp'> {
  const { timestamp: _timestamp, ...rest } = step
  return rest
}

function comparable(run: ThinkingRun): unknown {
  return {
    flowVersion: run.flowVersion,
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
    phases: run.phases,
    taskCount: run.totals.taskCount,
    attemptCount: run.totals.attemptCount,
    contextCount: run.totals.contextCount,
  }
}

describe('fluxo versão 2 — ao vivo', () => {
  it('candidatos e reprovações não criam tarefas; só a confirmação, uma vez, entra no progresso', () => {
    const run = liveRun(revision)

    expect(run.flowVersion).toBe(2)
    expect(run.steps.slice(0, 7).map((step) => [step.phase, step.subtype])).toEqual([
      ['A1', 'setup'],
      ['A2', 'plan_candidate'],
      ['A3', 'plan_rejected'],
      ['A2', 'plan_candidate'],
      ['A3', 'plan_approved'],
      ['A3', 'tasks'],
      ['A4', 'learn'],
    ])
    expect(run.tasks.map((task) => [task.id, task.title, task.origin])).toEqual([
      ['T1', 'Testar as condições em cada número', 'A2'],
      ['T2', 'Escolher a alternativa sustentada', 'A2'],
    ])
    expect(run.tasks.some((task) => task.title === 'Mostrar que o 4 é a resposta')).toBe(false)
    expect(run.totals.taskCount).toBe(2)
    expect(describeTaskProgress(run)).toEqual({ done: 2, total: 2 })
  })

  it('o progresso não é inflado enquanto o plano ainda é candidato', () => {
    let run = createEmptyRun('q', 'm')
    for (const event of liveEvents(revision).slice(0, 5)) {
      run = reasoningRunReducer(run, { kind: 'event', event })
    }

    expect(run.tasks).toEqual([])
    expect(run.totals.taskCount).toBe(0)
    expect(describeTaskProgress(run)).toEqual({ done: 0, total: 0 })
  })

  it('a trilha tem A.3 (validação) e A.4 (aprendizados) e mostra o retorno A.3 → A.2', () => {
    const run = liveRun(revision)
    const track = buildMacroTrack(run)

    expect(track.map((node) => node.id)).toEqual(['A1', 'A2', 'A3', 'A4', 'B', 'C1', 'C2', 'C3'])
    expect(track.find((node) => node.id === 'A3')).toMatchObject({
      shortLabel: 'A.3',
      subtitle: 'Validação da decomposição',
      status: 'done',
    })
    expect(track.find((node) => node.id === 'A4')).toMatchObject({ subtitle: 'Aprendizados do enunciado' })
    expect(run.phases.find((phase) => phase.id === 'A3')?.stepCount).toBe(3)
    expect(buildLoopArcs(run).find((arc) => arc.id === 'plan-revision')).toEqual({
      id: 'plan-revision',
      active: true,
    })
  })

  it('sessão interrompida antes de A.4 não mostra tarefas e deixa A.4 e a execução pendentes', () => {
    const run = liveRun(exhausted)

    expect(run.tasks).toEqual([])
    expect(run.phases.find((phase) => phase.id === 'A4')?.status).toBe('pending')
    expect(run.phases.find((phase) => phase.id === 'B')?.status).toBe('pending')
    expect(run.phases.find((phase) => phase.id === 'A3')?.status).toBe('active')
  })
})

describe.each([
  ['plano revisado e concluído', revision],
  ['planejamento esgotado antes de A.4', exhausted],
] as const)('fluxo versão 2 — histórico reproduz a execução ao vivo: %s', (_name, document) => {
  it('sessionToThinkingRun produz as mesmas fases, passos, loops e tarefas', () => {
    expect(comparable(sessionToThinkingRun(document))).toEqual(comparable(liveRun(document)))
  })

  it('o arco de revisão do plano e o progresso coincidem nos dois caminhos', () => {
    const history = sessionToThinkingRun(document)
    expect(buildLoopArcs(history)).toEqual(buildLoopArcs(liveRun(document)))
    expect(describeTaskProgress(history)).toEqual(describeTaskProgress(liveRun(document)))
  })
})

describe('histórico — o passo execute usa o plano confirmado, nunca um candidato reprovado', () => {
  it('a primeira tarefa traz o título aprovado', () => {
    const run = sessionToThinkingRun(revision)
    const execute = run.steps.find((step) => step.subtype === 'execute' && step.taskId === 'T1')

    expect(execute?.content).toContain('Testar as condições em cada número')
    expect(execute?.content).not.toContain('Mostrar que o 4')
  })
})

describe('fluxo versão 1 — A.3 continua sendo a extração do enunciado', () => {
  it('a trilha antiga tem sete nós e o rótulo histórico de A.3, sem arco de revisão do plano', () => {
    const run = sessionToThinkingRun(legacy)

    expect(run.flowVersion).toBe(1)
    expect(buildMacroTrack(run).map((node) => node.id)).toEqual(['A1', 'A2', 'A3', 'B', 'C1', 'C2', 'C3'])
    expect(buildMacroTrack(run).find((node) => node.id === 'A3')?.subtitle).toBe('Aprendizados do enunciado')
    expect(run.steps.find((step) => step.phase === 'A3')?.subtype).toBe('learn')
    expect(buildLoopArcs(run).find((arc) => arc.id === 'plan-revision')).toEqual({
      id: 'plan-revision',
      active: false,
    })
  })

  it('um evento ao vivo da versão 1 mantém a trilha antiga', () => {
    const run = reasoningRunReducer(createEmptyRun('q', 'm'), {
      kind: 'event',
      event: {
        type: 'thinking',
        subtype: 'learn',
        phase: 'A3',
        task: TASK_LABEL_SETUP,
        session_id: 's',
        content: '## Extracted learnings',
        total_tokens: 1,
        context_window: { context_id: 'c', context_size: 1 },
        inference_time_ms: 1,
        flow_version: 1,
      },
    })

    expect(run.flowVersion).toBe(1)
    expect(run.phases.map((phase) => phase.id)).toEqual(['A1', 'A2', 'A3', 'B', 'C1', 'C2', 'C3'])
    expect(run.phases.find((phase) => phase.id === 'A3')?.label).toBe('Aprendizados do enunciado')
  })
})
