import { describe, expect, it } from 'vitest'
import fixture from '@/test/fixtures/session-a1-completed-15msgs.json'
import { EVENT_SUBTYPE, type EventSubtype } from '../enums/eventSubtype'
import { EVENT_TYPE, type EventType } from '../enums/eventType'
import { TASK_LABEL_SETUP, TASK_LABEL_SYNTHESIS } from '../enums/taskLabels'
import { THINKING_PHASE, type ThinkingPhase } from '../enums/thinkingPhase'
import type { ReasoningEventDTO } from '../types/reasoningEvent'
import type { ThinkingRun } from '../types/thinkingRun'
import { createEmptyRun, reasoningRunReducer } from './reasoningRunReducer'
import { buildContextSeries, buildLoopArcs, buildMacroTrack, buildTaskLanes, findActiveStep } from './graphLayout'

const MODEL_NAME = 'deepseek/deepseek-v4-flash-0731'

// Mesma reconstrução usada por `reasoningRunReducer.test.ts` (FASE 05, seção 11) — o fixture
// real de `sess_c848291dc9d34eeea33872d4108e3295.json` tem 2 tarefas de 5 passos cada
// (reset, reasoning, verify_pass, store, learn), o caso canônico para o Modo Gráfico.
const EVENT_META: Array<{ order: number; subtype: EventSubtype; type: EventType; task: string }> = [
  { order: 1, subtype: EVENT_SUBTYPE.SETUP, type: EVENT_TYPE.THINKING, task: TASK_LABEL_SETUP },
  { order: 2, subtype: EVENT_SUBTYPE.TASKS, type: EVENT_TYPE.THINKING, task: TASK_LABEL_SETUP },
  { order: 3, subtype: EVENT_SUBTYPE.RESET, type: EVENT_TYPE.THINKING, task: 'T1' },
  { order: 4, subtype: EVENT_SUBTYPE.REASONING, type: EVENT_TYPE.THINKING, task: 'T1' },
  { order: 5, subtype: EVENT_SUBTYPE.VERIFY_PASS, type: EVENT_TYPE.THINKING, task: 'T1' },
  { order: 6, subtype: EVENT_SUBTYPE.STORE, type: EVENT_TYPE.THINKING, task: 'T1' },
  { order: 7, subtype: EVENT_SUBTYPE.LEARN, type: EVENT_TYPE.THINKING, task: 'T1' },
  { order: 8, subtype: EVENT_SUBTYPE.RESET, type: EVENT_TYPE.THINKING, task: 'T2' },
  { order: 9, subtype: EVENT_SUBTYPE.REASONING, type: EVENT_TYPE.THINKING, task: 'T2' },
  { order: 10, subtype: EVENT_SUBTYPE.VERIFY_PASS, type: EVENT_TYPE.THINKING, task: 'T2' },
  { order: 11, subtype: EVENT_SUBTYPE.STORE, type: EVENT_TYPE.THINKING, task: 'T2' },
  { order: 12, subtype: EVENT_SUBTYPE.LEARN, type: EVENT_TYPE.THINKING, task: 'T2' },
  { order: 13, subtype: EVENT_SUBTYPE.COMPILE, type: EVENT_TYPE.THINKING, task: TASK_LABEL_SYNTHESIS },
  { order: 14, subtype: EVENT_SUBTYPE.COMPILE, type: EVENT_TYPE.RESULT, task: TASK_LABEL_SYNTHESIS },
]

function buildFixtureEvents(): ReasoningEventDTO[] {
  let cumulative = 0
  return EVENT_META.map(({ order, subtype, type, task }) => {
    const message = fixture.messages.find((candidate) => candidate.order === order)
    if (!message) throw new Error(`fixture sem mensagem de order ${order}`)
    cumulative += message.total_tokens
    return {
      type,
      subtype,
      phase: message.phase as ThinkingPhase,
      task,
      session_id: fixture.id,
      content: message.content,
      total_tokens: cumulative,
      context_window: { context_id: message.context_id ?? '', context_size: message.total_tokens },
      inference_time_ms: message.inference_time_ms,
    }
  })
}

function buildEvent(overrides: Partial<ReasoningEventDTO> = {}): ReasoningEventDTO {
  return {
    type: EVENT_TYPE.THINKING,
    subtype: EVENT_SUBTYPE.REASONING,
    phase: THINKING_PHASE.B1,
    task: 'T1',
    session_id: 'sess_test',
    content: 'conteúdo',
    total_tokens: 100,
    context_window: { context_id: 'ctx_1', context_size: 100 },
    inference_time_ms: 500,
    ...overrides,
  }
}

function reduceAll(run: ThinkingRun, events: ReasoningEventDTO[]): ThinkingRun {
  return events.reduce<ThinkingRun>((acc, event) => reasoningRunReducer(acc, { kind: 'event', event }), run)
}

describe('graphLayout', () => {
  describe('com a execução real (fixture de sess_c848291dc9d34eeea33872d4108e3295)', () => {
    const run = reduceAll(createEmptyRun(fixture.user_question, MODEL_NAME), buildFixtureEvents())

    it('buildMacroTrack marca A1/A2/B/C1 como done, C2 como skipped e C3 como ativo/concluído', () => {
      const track = buildMacroTrack(run)
      const byId = Object.fromEntries(track.map((node) => [node.id, node]))

      expect(byId.A1?.status).toBe('done')
      expect(byId.A2?.status).toBe('done')
      // Sessão anterior à etapa A.3: o loop rodou sem ela, então o nó fica como "não foi necessária".
      expect(byId.A3?.status).toBe('skipped')
      expect(byId.B?.status).toBe('done')
      expect(byId.C1?.status).toBe('done')
      expect(byId.C2?.status).toBe('skipped')
      expect(['active', 'done']).toContain(byId.C3?.status)
      expect(byId.B?.progress).toEqual({ done: 2, total: 2 })
    })

    it('buildTaskLanes devolve 2 faixas com 5 passos cada', () => {
      const lanes = buildTaskLanes(run)
      expect(lanes).toHaveLength(2)
      for (const lane of lanes) {
        expect(lane.steps).toHaveLength(5)
      }
    })

    it('buildContextSeries tem um resetIndex por tarefa, com context_size zerado neles, e total_tokens monotônico', () => {
      const series = buildContextSeries(run.steps)
      expect(series.resetIndices).toHaveLength(2)

      for (const index of series.resetIndices) {
        expect(series.points[index]?.contextSize).toBe(0)
      }

      let previous = -Infinity
      for (const point of series.points) {
        expect(point.totalTokens).toBeGreaterThanOrEqual(previous)
        previous = point.totalTokens
      }
    })
  })

  it('verify_fail: a faixa tem 2 tentativas e o mesmo context_id nas duas', () => {
    const events = [
      buildEvent({ subtype: EVENT_SUBTYPE.RESET, task: 'T1', context_window: { context_id: 'ctx_a', context_size: 0 } }),
      buildEvent({ subtype: EVENT_SUBTYPE.REASONING, task: 'T1', context_window: { context_id: 'ctx_a', context_size: 50 } }),
      buildEvent({
        subtype: EVENT_SUBTYPE.VERIFY_FAIL,
        task: 'T1',
        content: '**Decisão:** `reproved`',
        context_window: { context_id: 'ctx_a', context_size: 80 },
      }),
      buildEvent({ subtype: EVENT_SUBTYPE.REASONING, task: 'T1', context_window: { context_id: 'ctx_a', context_size: 120 } }),
      buildEvent({
        subtype: EVENT_SUBTYPE.VERIFY_PASS,
        task: 'T1',
        content: '**Decisão:** `approved`',
        context_window: { context_id: 'ctx_a', context_size: 150 },
      }),
    ]

    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), events)
    const lanes = buildTaskLanes(run)
    const lane = lanes.find((candidate) => candidate.id === 'T1')

    expect(lane?.attemptCount).toBe(2)
    expect(new Set(lane?.steps.map((entry) => entry.step.contextId))).toEqual(new Set(['ctx_a']))
    expect(lane?.steps.map((entry) => entry.attemptIndex)).toEqual([0, 1, 1, 2, 2])
  })

  it('replan: buildLoopArcs devolve o arco C.2 → B ativo', () => {
    const events = [
      buildEvent({ subtype: EVENT_SUBTYPE.TASKS, phase: THINKING_PHASE.A2, task: TASK_LABEL_SETUP, content: '### T1 — Tarefa inicial\n\ncorpo' }),
      buildEvent({ subtype: EVENT_SUBTYPE.RESET, phase: THINKING_PHASE.B1, task: 'T1' }),
      buildEvent({ subtype: EVENT_SUBTYPE.REASONING, phase: THINKING_PHASE.B1, task: 'T1' }),
      buildEvent({ subtype: EVENT_SUBTYPE.VERIFY_PASS, phase: THINKING_PHASE.B2, task: 'T1', content: '**Decisão:** `approved`' }),
      buildEvent({ subtype: EVENT_SUBTYPE.STORE, phase: THINKING_PHASE.B3, task: 'T1' }),
      buildEvent({ subtype: EVENT_SUBTYPE.COMPILE, phase: THINKING_PHASE.C1, task: TASK_LABEL_SYNTHESIS, content: '**Decisão:** `reproved`' }),
      buildEvent({
        subtype: EVENT_SUBTYPE.REPLAN,
        phase: THINKING_PHASE.C2,
        task: TASK_LABEL_SYNTHESIS,
        content: '### T2 — Tarefa adicional\n\ncorpo',
      }),
    ]

    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), events)
    const arcs = buildLoopArcs(run)

    expect(arcs.find((arc) => arc.id === 'replan-return')?.active).toBe(true)
    expect(arcs.find((arc) => arc.id === 'verify-retry')?.active).toBe(false)
  })
})

describe('findActiveStep', () => {
  it('devolve o último passo da execução', () => {
    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), EVENT_META.map(buildEvent))
    expect(findActiveStep(run)?.order).toBe(run.steps.length - 1)
  })

  it('sem nenhum passo ainda, devolve null', () => {
    const run = createEmptyRun('pergunta', MODEL_NAME)
    expect(findActiveStep(run)).toBeNull()
  })
})

describe('buildMacroTrack — A.3', () => {
  const planning = [
    buildEvent({ subtype: EVENT_SUBTYPE.SETUP, phase: THINKING_PHASE.A1, task: TASK_LABEL_SETUP }),
    buildEvent({ subtype: EVENT_SUBTYPE.TASKS, phase: THINKING_PHASE.A2, task: TASK_LABEL_SETUP, content: '### T1 — Tarefa\n\ncorpo' }),
    buildEvent({ subtype: EVENT_SUBTYPE.LEARN, phase: THINKING_PHASE.A3, task: TASK_LABEL_SETUP }),
    buildEvent({ subtype: EVENT_SUBTYPE.RESET, phase: THINKING_PHASE.B1, task: 'T1' }),
  ]

  it('a trilha tem sete nós, com A.3 entre A.2 e a execução em loop', () => {
    const track = buildMacroTrack(reduceAll(createEmptyRun('pergunta', MODEL_NAME), planning))

    expect(track.map((node) => node.id)).toEqual(['A1', 'A2', 'A3', 'B', 'C1', 'C2', 'C3'])
  })

  it('o nó A.3 usa o rótulo curto e o título do domínio, sem progresso de tarefas', () => {
    const track = buildMacroTrack(reduceAll(createEmptyRun('pergunta', MODEL_NAME), planning))
    const node = track.find((candidate) => candidate.id === 'A3')

    expect(node).toEqual({
      id: 'A3',
      shortLabel: 'A.3',
      subtitle: 'Aprendizados do enunciado',
      status: 'done',
      progress: null,
    })
  })

  it('A.3 não gera faixa de tarefa', () => {
    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), planning)

    expect(buildTaskLanes(run).map((lane) => lane.id)).toEqual(['T1'])
  })
})
