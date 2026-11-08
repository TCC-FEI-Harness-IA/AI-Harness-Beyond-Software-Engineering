// Planejamento validado (fluxo versão 2): A.2 gera candidatos, A.3 os aprova ou reprova, a fila só recebe o
// plano aprovado (evento `tasks`, uma vez) e A.4 extrai os aprendizados. Cada fixture `capture-*.json` é uma
// captura real do backend (`tests/doubles/frontend_parity_capture.py`, conferida por
// `tests/infra/test_frontend_parity_fixtures.py`): os frames que o WebSocket enviou e a sessão persistida da
// MESMA execução, com modelo roteirizado. Os eventos ao vivo não são reconstruídos a partir das mensagens.
// Sessões antigas (versão 1) continuam com A.3 = aprendizados do enunciado.

import { describe, expect, it } from 'vitest'
import c3AuditCapture from '@/test/fixtures/capture-v2-plan-revision-c3-audit.json'
import c3ExhaustedCapture from '@/test/fixtures/capture-v2-c3-exhausted.json'
import exhaustedCapture from '@/test/fixtures/capture-v2-planning-exhausted.json'
import techRetryCapture from '@/test/fixtures/capture-v2-tech-retry.json'
import legacyWithA3Fixture from '@/test/fixtures/session-a1-completed-with-a3.json'
import { parseReasoningFrame } from '@/api/parsers/reasoningFrame'
import { parseSessionDocument } from '@/api/parsers/sessionDocument'
import { TASK_LABEL_SETUP } from '../enums/taskLabels'
import type { ReasoningEventDTO } from '../types/reasoningEvent'
import type { SessionDocument } from '../types/sessionDocument'
import type { ThinkingRun, ThinkingStep } from '../types/thinkingRun'
import { buildLoopArcs, buildMacroTrack, describeTaskProgress } from './graphLayout'
import { createEmptyRun, reasoningRunReducer } from './reasoningRunReducer'
import { sessionToThinkingRun } from './sessionToThinkingRun'

interface Capture {
  name: string
  events: ReasoningEventDTO[]
  session: SessionDocument
}

function load(name: string, raw: { events: unknown[]; session: unknown }): Capture {
  return {
    name,
    events: raw.events.map((frame) => parseReasoningFrame(frame) as ReasoningEventDTO),
    session: parseSessionDocument(raw.session),
  }
}

const c3Audit = load('plano revisado e auditoria de C.3 seguida da resposta aceita', c3AuditCapture)
const exhausted = load('planejamento esgotado antes de A.4', exhaustedCapture)
const c3Exhausted = load('C.3 esgotada sem resposta', c3ExhaustedCapture)
const techRetry = load('reprovação só pelo critério técnico seguida de retentativa aprovada', techRetryCapture)
const revision = c3Audit
const legacy = parseSessionDocument(legacyWithA3Fixture)

// O evento terminal `error` vai só pelo WebSocket: a sessão guarda a falha em `failure`, não como mensagem.
function persistedCounterpart(events: ReasoningEventDTO[]): ReasoningEventDTO[] {
  return events.filter((event) => event.type !== 'error')
}

function liveRun(capture: Capture, events: ReasoningEventDTO[] = capture.events): ThinkingRun {
  let run = createEmptyRun(capture.session.user_question, capture.session.model_name)
  for (const event of events) {
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
    const run = liveRun(revision, revision.events.slice(0, 5))

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
    const run = liveRun(exhausted, persistedCounterpart(exhausted.events))

    expect(run.tasks).toEqual([])
    expect(run.phases.find((phase) => phase.id === 'A4')?.status).toBe('pending')
    expect(run.phases.find((phase) => phase.id === 'B')?.status).toBe('pending')
    expect(run.phases.find((phase) => phase.id === 'A3')?.status).toBe('active')
  })
})

describe.each([c3Audit, exhausted, c3Exhausted, techRetry])('paridade com eventos capturados: $name', (capture) => {
  it('o histórico reproduz os passos, as tarefas, as fases e os loops da execução ao vivo', () => {
    const live = liveRun(capture, persistedCounterpart(capture.events))

    expect(comparable(sessionToThinkingRun(capture.session))).toEqual(comparable(live))
  })

  it('o arco de revisão do plano e o progresso coincidem nos dois caminhos', () => {
    const history = sessionToThinkingRun(capture.session)
    const live = liveRun(capture)
    expect(buildLoopArcs(history)).toEqual(buildLoopArcs(live))
    expect(describeTaskProgress(history)).toEqual(describeTaskProgress(live))
  })

  it('a resposta final só existe quando a sessão foi concluída, e é a mesma nos dois caminhos', () => {
    const history = sessionToThinkingRun(capture.session)
    const live = liveRun(capture)

    expect(history.finalAnswer).toBe(capture.session.final_answer)
    expect(live.finalAnswer).toBe(capture.session.final_answer)
    const results = (run: ThinkingRun) => run.steps.filter((step) => step.type === 'result').length
    expect(results(history)).toBe(capture.session.status === 'completed' ? 1 : 0)
    expect(results(live)).toBe(results(history))
  })
})

describe('C.3 — auditoria e resposta aceita', () => {
  it('a auditoria fica armazenada, mas não vira passo nem resposta; a resposta aceita aparece uma vez', () => {
    const audit = c3Audit.session.messages.find((message) => message.phase === 'C3' && message.source === 'system')
    expect(audit?.content).toContain('resposta sem json')

    const history = sessionToThinkingRun(c3Audit.session)
    expect(history.steps.some((step) => step.content.includes('resposta sem json'))).toBe(false)
    expect(history.steps.filter((step) => step.phase === 'C3').map((step) => [step.type, step.subtype])).toEqual([
      ['thinking', 'compile'],
      ['result', 'compile'],
    ])
    expect(history.finalAnswer).toBe('D) Nenhuma das anteriores')
  })

  it('o evento terminal não soma de novo o consumo da chamada de C.3', () => {
    const live = liveRun(c3Audit)

    expect(live.totals.inferenceTimeMs).toBe(c3Audit.session.totals.inference_time_ms)
    expect(live.totals.llmCalls).toBe(
      c3Audit.events.filter((event) => event.type === 'thinking' && event.inference_time_ms > 0).length,
    )
  })

  it('C.3 esgotada: as auditorias ficam armazenadas e não há passo de C.3 nem resposta', () => {
    expect(c3Exhausted.session.messages.filter((message) => message.phase === 'C3')).toHaveLength(3)

    const history = sessionToThinkingRun(c3Exhausted.session)
    expect(history.steps.some((step) => step.phase === 'C3')).toBe(false)
    expect(history.finalAnswer).toBeNull()
    expect(history.status).toBe('failed')
  })
})

describe('histórico — o passo execute usa o plano confirmado, nunca um candidato reprovado', () => {
  it('cada execute do histórico é idêntico ao capturado ao vivo, com critérios e dependências', () => {
    const live = revision.events.filter((event) => event.subtype === 'execute').map((event) => event.content)
    const history = sessionToThinkingRun(revision.session)
      .steps.filter((step) => step.subtype === 'execute')
      .map((step) => step.content)

    expect(history).toEqual(live)
    expect(history[0]).toContain('**Acceptance criteria:**\n- `T1-AC1`')
    expect(history[0]).toContain('- `T1-AC2`: Explicar o teste de cada condição em 2, 4 e 6.')
    expect(history[1]).toContain('**Depends on:** `T1`')
    expect(history.join('\n')).not.toContain('Mostrar que o 4')
  })
})

// Nova fase de validação — 02: B.2 avalia também o critério técnico fixo `<task_id>-TECH`. O frontend não
// interpreta o identificador: o relatório é mostrado como qualquer outro, e o subtipo persistido decide a tentativa.
describe('validação técnica — reprovação só por `T1-TECH` e retentativa aprovada', () => {
  it('a tentativa reprovada por TECH e a aprovada são as mesmas ao vivo e no histórico', () => {
    for (const run of [liveRun(techRetry), sessionToThinkingRun(techRetry.session)]) {
      const [task] = run.tasks
      expect(run.tasks).toHaveLength(1)
      expect(task?.attempts.map((attempt) => [attempt.verification?.subtype, attempt.approved])).toEqual([
        ['verify_fail', false],
        ['verify_pass', true],
      ])
      const rejected = task?.attempts[0]?.verification?.content ?? ''
      expect(rejected).toContain('- `T1-AC1` — met:')
      expect(rejected).toContain("- `T1-TECH` — not met: A condição 'maior que 2' foi ignorada")
      expect(task?.attempts[1]?.verification?.content).toContain('- `T1-TECH` — met:')
      expect(run.finalAnswer).toBe('D) Nenhuma das anteriores')
    }
  })

  it('o execute mostra só os critérios planejados; TECH aparece apenas nos relatórios de B.2', () => {
    const history = sessionToThinkingRun(techRetry.session)
    const execute = history.steps.filter((step) => step.subtype === 'execute').map((step) => step.content)
    const live = techRetry.events.filter((event) => event.subtype === 'execute').map((event) => event.content)

    expect(execute).toEqual(live)
    expect(execute[0]).toContain('- `T1-AC1`: Explicar o teste de cada condição em 2, 4 e 6.')
    expect(execute[0]).not.toContain('T1-TECH')
    expect(describeTaskProgress(history)).toEqual({ done: 1, total: 1 })
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
