import { describe, expect, it } from 'vitest'
import fixture from '@/test/fixtures/session-a1-completed-15msgs.json'
import { EVENT_SUBTYPE, type EventSubtype } from '../enums/eventSubtype'
import { EVENT_TYPE, type EventType } from '../enums/eventType'
import { RUN_STATUS } from '../enums/runStatus'
import { TASK_LABEL_SETUP, TASK_LABEL_SYNTHESIS } from '../enums/taskLabels'
import { THINKING_PHASE, type ThinkingPhase } from '../enums/thinkingPhase'
import type { ReasoningEventDTO } from '../types/reasoningEvent'
import type { ThinkingRun } from '../types/thinkingRun'
import { createEmptyRun, reasoningRunReducer, type RunAction } from './reasoningRunReducer'

const MODEL_NAME = 'deepseek/deepseek-v4-flash-0731'

// Metadados do evento ao vivo (subtype/type/task) que a mensagem persistida não carrega — o
// resto (conteúdo, tokens, contexto, tempo) vem direto do fixture real de
// `apps/backend/data/sessions/sess_c848291dc9d34eeea33872d4108e3295.json`, copiado para
// `src/test/fixtures/session-a1-completed-15msgs.json` (FASE 05, seção 11).
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

/** Deriva a sequência de eventos ao vivo a partir do documento persistido real (seção 11). */
function buildFixtureEvents(): ReasoningEventDTO[] {
  let cumulative = 0
  return EVENT_META.map(({ order, subtype, type, task }) => {
    const message = fixture.messages.find((candidate) => candidate.order === order)
    if (!message) throw new Error(`fixture sem mensagem de order ${order}`)

    // O documento persistido não guarda o total acumulado da sessão (só o custo da própria
    // mensagem) nem o tamanho da janela — o WS manda os dois. O acumulado é reconstruído
    // aqui; o tamanho da janela usa o custo da própria mensagem como um substituto plausível,
    // já que o documento salvo não preserva esse dado.
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
  return events.reduce<ThinkingRun>(
    (acc, event) => reasoningRunReducer(acc, { kind: 'event', event }),
    run,
  )
}

describe('reasoningRunReducer', () => {
  it('processa a execução real de sess_c848291dc9d34eeea33872d4108e3295 corretamente', () => {
    const events = buildFixtureEvents()
    const initial = createEmptyRun(fixture.user_question, MODEL_NAME)
    const run = reduceAll(initial, events)

    expect(run.tasks).toHaveLength(2)
    expect(run.tasks.map((task) => task.id)).toEqual(['T1', 'T2'])

    for (const task of run.tasks) {
      expect(task.attempts).toHaveLength(1)
      expect(task.attempts[0]?.approved).toBe(true)
      expect(task.status).toBe('approved')
    }

    expect(run.finalAnswer).toBe(fixture.final_answer)
    expect(run.status).toBe(RUN_STATUS.COMPLETED)

    const lastEvent = events[events.length - 1]
    expect(run.totals.totalTokens).toBe(lastEvent?.total_tokens)
    expect(run.totals.llmCalls).toBe(events.filter((event) => event.inference_time_ms > 0).length)
    expect(run.totals.inferenceTimeMs).toBe(events.reduce((sum, event) => sum + event.inference_time_ms, 0))

    // contexto muda de janela toda vez que o `context_id` do evento difere do último visto,
    // contando a própria primeira janela como uma abertura.
    let expectedContextCount = 0
    let lastContextId: string | null = null
    for (const event of events) {
      if (event.context_window.context_id !== lastContextId) expectedContextCount += 1
      lastContextId = event.context_window.context_id
    }
    expect(run.totals.contextCount).toBe(expectedContextCount)
  })

  it('não muta o run recebido (imutabilidade)', () => {
    const events = buildFixtureEvents()
    const initial = createEmptyRun(fixture.user_question, MODEL_NAME)
    const snapshot = structuredClone(initial)

    reduceAll(initial, events)

    expect(initial).toEqual(snapshot)
  })

  it('gera os mesmos ids processando a mesma sequência duas vezes', () => {
    const events = buildFixtureEvents()
    const runA = reduceAll(createEmptyRun(fixture.user_question, MODEL_NAME), events)
    const runB = reduceAll(createEmptyRun(fixture.user_question, MODEL_NAME), events)

    expect(runA.steps.map((step) => step.id)).toEqual(runB.steps.map((step) => step.id))
  })

  it('verify_fail abre uma segunda tentativa na mesma tarefa sem abrir contexto novo', () => {
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
    const task = run.tasks.find((candidate) => candidate.id === 'T1')

    expect(task?.attempts).toHaveLength(2)
    expect(task?.attempts[0]?.approved).toBe(false)
    expect(task?.attempts[1]?.approved).toBe(true)
    // Todos os eventos usam o mesmo `context_id` — nenhuma janela nova foi aberta.
    expect(run.totals.contextCount).toBe(1)
    expect(task?.contextIds).toEqual(['ctx_a'])
  })

  it('replan acrescenta tarefas com origin C2 e devolve B ao estado active', () => {
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

    expect(run.tasks.map((task) => task.origin)).toEqual(['A2', 'C2'])
    expect(run.tasks[1]?.id).toBe('T2')

    const bNode = run.phases.find((phase) => phase.id === 'B')
    const c1Node = run.phases.find((phase) => phase.id === 'C1')
    expect(bNode?.status).toBe('done')
    expect(c1Node?.status).toBe('done')
    const c2Node = run.phases.find((phase) => phase.id === 'C2')
    expect(c2Node?.status).toBe('active')
  })

  it('evento degraded marca status degraded sem interromper o processamento dos eventos seguintes', () => {
    const events = [
      buildEvent({ subtype: EVENT_SUBTYPE.RESET, task: 'T1' }),
      buildEvent({
        type: EVENT_TYPE.DEGRADED,
        subtype: EVENT_SUBTYPE.REASONING,
        task: 'T1',
        content: 'limite task_attempts atingido',
      }),
      buildEvent({ subtype: EVENT_SUBTYPE.STORE, task: 'T1' }),
      buildEvent({ subtype: EVENT_SUBTYPE.COMPILE, phase: THINKING_PHASE.C3, task: TASK_LABEL_SYNTHESIS, type: EVENT_TYPE.RESULT, content: 'resposta final' }),
    ]

    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), events)

    expect(run.status).toBe(RUN_STATUS.DEGRADED)
    expect(run.degradations).toHaveLength(1)
    expect(run.degradations[0]?.limit).toBe('task_attempts')
    expect(run.steps).toHaveLength(4)
    expect(run.finalAnswer).toBe('resposta final')
  })

  it('evento error marca failed e preserva os passos anteriores', () => {
    const events = [
      buildEvent({ subtype: EVENT_SUBTYPE.RESET, task: 'T1' }),
      buildEvent({ subtype: EVENT_SUBTYPE.REASONING, task: 'T1' }),
      buildEvent({ type: EVENT_TYPE.ERROR, task: 'T1', content: 'falha no provedor' }),
    ]

    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), events)

    expect(run.status).toBe(RUN_STATUS.FAILED)
    expect(run.error).toEqual({ message: 'falha no provedor', userMessage: 'falha no provedor' })
    expect(run.steps).toHaveLength(3)
  })

  it('robustez: evento de tarefa desconhecida cria a tarefa em vez de descartar o passo', () => {
    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), [
      buildEvent({ subtype: EVENT_SUBTYPE.LEARN, task: 'T9' }),
    ])

    expect(run.tasks.map((task) => task.id)).toEqual(['T9'])
    expect(run.steps).toHaveLength(1)
  })

  it('robustez: store de uma tarefa desconhecida ignora o efeito, mas o passo continua em run.steps', () => {
    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), [
      buildEvent({ subtype: EVENT_SUBTYPE.STORE, task: 'T9' }),
    ])

    expect(run.tasks).toHaveLength(0)
    expect(run.steps).toHaveLength(1)
  })

  it('robustez: verify_pass sem tentativa aberta não lança e cria uma tentativa fechada', () => {
    expect(() =>
      reduceAll(createEmptyRun('pergunta', MODEL_NAME), [
        buildEvent({ subtype: EVENT_SUBTYPE.VERIFY_PASS, task: 'T1', content: '**Decisão:** `approved`' }),
      ]),
    ).not.toThrow()

    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), [
      buildEvent({ subtype: EVENT_SUBTYPE.VERIFY_PASS, task: 'T1', content: '**Decisão:** `approved`' }),
    ])
    const task = run.tasks.find((candidate) => candidate.id === 'T1')
    expect(task?.attempts).toHaveLength(1)
    expect(task?.attempts[0]?.reasoning).toBeNull()
    expect(task?.attempts[0]?.approved).toBe(true)
  })

  it('robustez: subtype fora do enum entra como passo sem lançar', () => {
    const rogueEvent = buildEvent({ subtype: 'algo_novo' as unknown as EventSubtype, task: 'T1' })

    expect(() => reasoningRunReducer(createEmptyRun('pergunta', MODEL_NAME), { kind: 'event', event: rogueEvent })).not.toThrow()

    const run = reasoningRunReducer(createEmptyRun('pergunta', MODEL_NAME), { kind: 'event', event: rogueEvent })
    expect(run.steps).toHaveLength(1)
  })

  it('uma ação de tipo desconhecido devolve o run inalterado, sem lançar', () => {
    const started = reduceAll(createEmptyRun('pergunta', MODEL_NAME), [buildEvent({ subtype: EVENT_SUBTYPE.RESET, task: 'T1' })])
    const run = reasoningRunReducer(started, { kind: 'nonsense' } as unknown as RunAction)

    expect(run).toBe(started)
  })

  it('nunca lança, mesmo diante de uma ação malformada', () => {
    const run = createEmptyRun('pergunta', MODEL_NAME)
    const malformed = { kind: 'event', event: null } as unknown as RunAction

    expect(() => reasoningRunReducer(run, malformed)).not.toThrow()
  })

  it('fechamento 1000 com status ainda running vira completed mantendo finalAnswer nulo', () => {
    const running: ThinkingRun = { ...createEmptyRun('pergunta', MODEL_NAME), status: RUN_STATUS.RUNNING }
    const run = reasoningRunReducer(running, { kind: 'closed', code: 1000 })

    expect(run.status).toBe(RUN_STATUS.COMPLETED)
    expect(run.finalAnswer).toBeNull()
  })

  it('errorFrame preenche error e marca failed preservando os passos', () => {
    const started = reduceAll(createEmptyRun('pergunta', MODEL_NAME), [buildEvent({ subtype: EVENT_SUBTYPE.RESET, task: 'T1' })])
    const run = reasoningRunReducer(started, { kind: 'errorFrame', frame: { type: 'error', content: 'payload inválido' } })

    expect(run.status).toBe(RUN_STATUS.FAILED)
    expect(run.error?.userMessage).toBe('payload inválido')
    expect(run.steps).toHaveLength(1)
  })

  it('reset repetido com o mesmo context_id não duplica a entrada em contextIds', () => {
    const events = [
      buildEvent({ subtype: EVENT_SUBTYPE.RESET, task: 'T1', context_window: { context_id: 'ctx_1', context_size: 0 } }),
      buildEvent({ subtype: EVENT_SUBTYPE.RESET, task: 'T1', context_window: { context_id: 'ctx_1', context_size: 0 } }),
    ]
    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), events)

    expect(run.tasks[0]?.contextIds).toEqual(['ctx_1'])
  })

  it('execute como primeiro evento de uma tarefa nova cria a tarefa na hora (robustez)', () => {
    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), [
      buildEvent({ subtype: EVENT_SUBTYPE.EXECUTE, task: 'T9', content: '### T9 — Uma tarefa\n\ncorpo' }),
    ])

    expect(run.tasks).toHaveLength(1)
    expect(run.tasks[0]?.id).toBe('T9')
  })

  it('degraded com task global (setup/synthesis) não cria nem altera nenhuma tarefa', () => {
    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), [
      buildEvent({ type: EVENT_TYPE.DEGRADED, subtype: EVENT_SUBTYPE.SETUP, task: TASK_LABEL_SETUP, content: 'limite atingido' }),
    ])

    expect(run.status).toBe(RUN_STATUS.DEGRADED)
    expect(run.tasks).toHaveLength(0)
    expect(run.degradations[0]?.taskId).toBeNull()
  })

  it('compile fora do type "result" não altera o status do run', () => {
    const started = reduceAll(createEmptyRun('pergunta', MODEL_NAME), [
      buildEvent({ subtype: EVENT_SUBTYPE.RESET, task: 'T1' }),
    ])
    const run = reasoningRunReducer(started, {
      kind: 'event',
      event: buildEvent({ type: EVENT_TYPE.THINKING, subtype: EVENT_SUBTYPE.COMPILE, phase: THINKING_PHASE.C3, task: TASK_LABEL_SYNTHESIS, content: 'rascunho' }),
    })

    expect(run.status).toBe(started.status)
    expect(run.finalAnswer).toBe('rascunho')
  })

  it('warning registra o aviso sem alterar status nem descartar os passos (FASE 08, seção 4)', () => {
    const started = reduceAll(createEmptyRun('pergunta', MODEL_NAME), [buildEvent({ subtype: EVENT_SUBTYPE.RESET, task: 'T1' })])
    const warned = reasoningRunReducer(started, { kind: 'warning', message: 'frame ignorado' })

    expect(warned.warning).toBe('frame ignorado')
    expect(warned.status).toBe(started.status)
    expect(warned.steps).toHaveLength(1)

    // Um evento válido seguinte limpa o aviso — o stream se recuperou.
    const recovered = reasoningRunReducer(warned, { kind: 'event', event: buildEvent({ subtype: EVENT_SUBTYPE.REASONING, task: 'T1' }) })
    expect(recovered.warning).toBeNull()
    expect(recovered.steps).toHaveLength(2)
  })
})

describe('reasoningRunReducer — A.3, aprendizados pontuais do enunciado', () => {
  function planningEvents(): ReasoningEventDTO[] {
    return [
      buildEvent({ subtype: EVENT_SUBTYPE.SETUP, phase: THINKING_PHASE.A1, task: TASK_LABEL_SETUP, context_window: { context_id: 'ctx_a1', context_size: 10 } }),
      buildEvent({ subtype: EVENT_SUBTYPE.TASKS, phase: THINKING_PHASE.A2, task: TASK_LABEL_SETUP, content: '### T1 — Tarefa inicial\n\ncorpo', context_window: { context_id: 'ctx_a2', context_size: 10 } }),
      buildEvent({
        subtype: EVENT_SUBTYPE.LEARN,
        phase: THINKING_PHASE.A3,
        task: TASK_LABEL_SETUP,
        content: '## Aprendizados extraídos\n\n- Alternativas: A) 2; B) 4',
        context_window: { context_id: 'ctx_a3', context_size: 10 },
      }),
    ]
  }

  function phaseStatus(run: ThinkingRun, id: string): string | undefined {
    return run.phases.find((phase) => phase.id === id)?.status
  }

  it('a trilha macro nasce com A.3 entre A.2 e a execução em loop', () => {
    const run = createEmptyRun('pergunta', MODEL_NAME)

    expect(run.phases.map((phase) => phase.id)).toEqual(['A1', 'A2', 'A3', 'B', 'C1', 'C2', 'C3'])
    expect(run.phases.find((phase) => phase.id === 'A3')?.label).toBe('Aprendizados do enunciado')
  })

  it('o evento learn de A.3 entra como passo, mas não cria uma tarefa chamada "setup"', () => {
    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), planningEvents())

    expect(run.steps.map((step) => step.phase)).toEqual(['A1', 'A2', 'A3'])
    expect(run.tasks.map((task) => task.id)).toEqual(['T1'])
    expect(run.totals.taskCount).toBe(1)
  })

  it('A.3 fica ativa quando é o passo mais recente e concluída quando o loop começa', () => {
    const planned = reduceAll(createEmptyRun('pergunta', MODEL_NAME), planningEvents())
    expect(phaseStatus(planned, 'A2')).toBe('done')
    expect(phaseStatus(planned, 'A3')).toBe('active')
    expect(planned.phases.find((phase) => phase.id === 'A3')?.stepCount).toBe(1)

    const running = reduceAll(planned, [buildEvent({ subtype: EVENT_SUBTYPE.RESET, phase: THINKING_PHASE.B1, task: 'T1' })])
    expect(phaseStatus(running, 'A3')).toBe('done')
    expect(phaseStatus(running, 'B')).toBe('active')
  })

  it('A.3 aguardando: só A.1 e A.2 aconteceram', () => {
    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), planningEvents().slice(0, 2))

    expect(phaseStatus(run, 'A3')).toBe('pending')
  })

  it('sessão anterior à A.3 (sem passo A.3, mas com o loop em andamento) mostra A.3 como não necessária', () => {
    const legacy = [
      ...planningEvents().slice(0, 2),
      buildEvent({ subtype: EVENT_SUBTYPE.RESET, phase: THINKING_PHASE.B1, task: 'T1' }),
    ]
    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), legacy)

    expect(phaseStatus(run, 'A3')).toBe('skipped')
    expect(phaseStatus(run, 'B')).toBe('active')
  })

  it('o evento de A.3 conta como chamada ao modelo e abre a própria janela de contexto', () => {
    const run = reduceAll(createEmptyRun('pergunta', MODEL_NAME), planningEvents())

    expect(run.totals.llmCalls).toBe(3)
    expect(run.totals.contextCount).toBe(3)
  })
})
