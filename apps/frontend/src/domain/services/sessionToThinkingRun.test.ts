import { describe, expect, it } from 'vitest'
import completedFixture from '@/test/fixtures/session-a1-completed-15msgs.json'
import withA3Fixture from '@/test/fixtures/session-a1-completed-with-a3.json'
import failed1MsgFixture from '@/test/fixtures/session-a1-failed-1msg.json'
import failed2MsgsFixture from '@/test/fixtures/session-a1-failed-2msgs.json'
import { EVENT_SUBTYPE } from '../enums/eventSubtype'
import type { SessionDocument } from '../types/sessionDocument'
import { sessionToThinkingRun } from './sessionToThinkingRun'

const completedDocument = completedFixture as unknown as SessionDocument
const withA3Document = withA3Fixture as unknown as SessionDocument
const failed1MsgDocument = failed1MsgFixture as unknown as SessionDocument
const failed2MsgsDocument = failed2MsgsFixture as unknown as SessionDocument

describe('sessionToThinkingRun', () => {
  it('reconstrói a sessão completa (2 tarefas, ambas aprovadas)', () => {
    const run = sessionToThinkingRun(completedDocument)

    expect(run.tasks).toHaveLength(2)
    expect(run.tasks.map((task) => task.id)).toEqual(['T1', 'T2'])
    for (const task of run.tasks) {
      expect(task.attempts).toHaveLength(1)
      expect(task.attempts[0]?.approved).toBe(true)
      expect(task.status).toBe('approved')
    }

    expect(run.finalAnswer).toBe(completedDocument.final_answer)
    expect(run.status).toBe('completed')
    expect(run.sessionId).toBe(completedDocument.id)
    expect(run.question).toBe(completedDocument.user_question)
  })

  it('sobrescreve os totais com os valores autoritativos do documento', () => {
    const run = sessionToThinkingRun(completedDocument)

    expect(run.totals.totalTokens).toBe(completedDocument.totals.total_tokens)
    expect(run.totals.inferenceTimeMs).toBe(completedDocument.totals.inference_time_ms)
    expect(run.totals.llmCalls).toBe(completedDocument.totals.total_llm_calls)
    expect(run.totals.wallTimeMs).toBe(completedDocument.totals.wall_time_ms)
  })

  it('total_tokens dos passos é monotônico não decrescente', () => {
    const run = sessionToThinkingRun(completedDocument)
    for (let i = 1; i < run.steps.length; i += 1) {
      expect(run.steps[i]!.totalTokens).toBeGreaterThanOrEqual(run.steps[i - 1]!.totalTokens)
    }
  })

  it('context_size reconstruído zera a cada troca de context_id', () => {
    const run = sessionToThinkingRun(completedDocument)
    const resetSteps = run.steps.filter((step) => step.subtype === EVENT_SUBTYPE.RESET)
    expect(resetSteps.length).toBeGreaterThan(0)
    for (const step of resetSteps) {
      expect(step.contextSize).toBe(0)
    }
  })

  it('sintetiza o passo execute logo após cada reset, com a mesma janela de contexto', () => {
    const run = sessionToThinkingRun(completedDocument)
    const t1Steps = run.tasks.find((task) => task.id === 'T1')?.steps ?? []
    const subtypes = t1Steps.map((step) => step.subtype)

    expect(subtypes).toEqual(['reset', 'execute', 'reasoning', 'verify_pass', 'store', 'learn'])

    const resetStep = t1Steps.find((step) => step.subtype === 'reset')
    const executeStep = t1Steps.find((step) => step.subtype === 'execute')
    expect(executeStep?.contextId).toBe(resetStep?.contextId)
    expect(executeStep?.contextSize).toBe(resetStep?.contextSize)
    expect(executeStep?.inferenceTimeMs).toBe(0)
    expect(executeStep?.content).toContain('T1')
  })

  it('contextCount reflete a mesma contagem de transições que a execução ao vivo produziria', () => {
    const run = sessionToThinkingRun(completedDocument)

    let expected = 0
    let lastContextId: string | null = null
    for (const step of run.steps) {
      if (step.contextId !== lastContextId) expected += 1
      lastContextId = step.contextId
    }
    expect(run.totals.contextCount).toBe(expected)
  })

  it('sessão failed com 1 mensagem não lança e produz um run parcial', () => {
    expect(() => sessionToThinkingRun(failed1MsgDocument)).not.toThrow()
    const run = sessionToThinkingRun(failed1MsgDocument)
    expect(run.status).toBe('failed')
    expect(run.steps).toHaveLength(0)
  })

  it('sessão failed com 2 mensagens não lança e produz um run parcial', () => {
    expect(() => sessionToThinkingRun(failed2MsgsDocument)).not.toThrow()
    const run = sessionToThinkingRun(failed2MsgsDocument)
    expect(run.status).toBe('failed')
  })

  it('mapeia running e degraded para o RunStatus correspondente, e um status desconhecido cai em failed', () => {
    expect(sessionToThinkingRun({ ...completedDocument, status: 'running' }).status).toBe('running')
    expect(sessionToThinkingRun({ ...completedDocument, status: 'degraded' }).status).toBe('degraded')
    expect(
      sessionToThinkingRun({ ...completedDocument, status: 'algo-inesperado' as SessionDocument['status'] }).status,
    ).toBe('failed')
  })

  it('reconstrói degradations do documento, preservando uma phase válida e caindo em A1 quando inválida', () => {
    const withDegradation: SessionDocument = {
      ...completedDocument,
      degradations: [
        {
          limit: 'task_attempts',
          phase: 'B2',
          task_id: 'T1',
          description: 'limite de tentativas atingido',
          occurred_at: '2026-09-11T23:18:07.000Z',
        },
        {
          limit: 'session_timeout',
          phase: 'não-é-uma-fase',
          task_id: null,
          description: 'tempo de parede esgotado',
          occurred_at: '2026-09-11T23:19:00.000Z',
        },
      ],
    }
    const run = sessionToThinkingRun(withDegradation)

    expect(run.degradations).toHaveLength(2)
    expect(run.degradations[0]).toMatchObject({ limit: 'task_attempts', phase: 'B2', taskId: 'T1' })
    expect(run.degradations[1]).toMatchObject({ limit: 'session_timeout', phase: 'A1', taskId: null })
  })

  it('mensagem persistida com context_id nulo (dado inesperado) cai para janela vazia, sem lançar', () => {
    const withNullContext: SessionDocument = {
      ...completedDocument,
      messages: completedDocument.messages.map((message) =>
        message.order === 1 ? { ...message, context_id: null } : message,
      ),
    }
    expect(() => sessionToThinkingRun(withNullContext)).not.toThrow()
    const run = sessionToThinkingRun(withNullContext)
    expect(run.steps[0]?.contextId).toBe('')
  })

  it('uma tarefa referenciada fora do markdown de A2/C2 sintetiza um bloco mínimo em vez de ficar em branco', () => {
    const orphanMessage = completedDocument.messages.find((message) => message.phase === 'B1' && message.source === 'system')
    if (!orphanMessage) throw new Error('fixture sem mensagem B1/system (reset)')

    const withOrphanTask: SessionDocument = {
      ...completedDocument,
      messages: [...completedDocument.messages, { ...orphanMessage, id: 'msg_orphan', order: 999, task_id: 'T99' }],
    }
    const run = sessionToThinkingRun(withOrphanTask)
    const orphanTask = run.tasks.find((task) => task.id === 'T99')
    const executeStep = orphanTask?.steps.find((step) => step.subtype === 'execute')

    expect(executeStep?.content).toBe('### T99')
  })
})

describe('sessionToThinkingRun — sessão com a etapa A.3', () => {
  it('a mensagem A3 vira um passo learn global, sem criar tarefa', () => {
    const run = sessionToThinkingRun(withA3Document)

    const step = run.steps.find((candidate) => candidate.phase === 'A3')
    expect(step?.subtype).toBe(EVENT_SUBTYPE.LEARN)
    expect(step?.type).toBe('thinking')
    expect(step?.taskId).toBe('setup')
    expect(step?.content).toContain('Intervalo pedido')
    expect(run.tasks.map((task) => task.id)).toEqual(['T1', 'T2'])
  })

  it('o passo A.3 vem logo depois de A.2 e antes da primeira tarefa', () => {
    const run = sessionToThinkingRun(withA3Document)

    expect(run.steps.slice(0, 4).map((step) => step.phase)).toEqual(['A1', 'A2', 'A3', 'B1'])
  })

  it('a trilha macro mostra A.3 concluída e a janela do passo é própria', () => {
    const run = sessionToThinkingRun(withA3Document)

    expect(run.phases.find((phase) => phase.id === 'A3')).toMatchObject({ status: 'done', stepCount: 1 })
    const a3 = run.steps.find((step) => step.phase === 'A3')
    const a2 = run.steps.find((step) => step.phase === 'A2')
    expect(a3?.contextId).toBe('9d41e7c')
    expect(a3?.contextId).not.toBe(a2?.contextId)
    expect(a3?.contextSize).toBe(358)
  })

  it('preserva o timestamp persistido do passo A.3 e os totais do documento', () => {
    const run = sessionToThinkingRun(withA3Document)

    const step = run.steps.find((candidate) => candidate.phase === 'A3')
    expect(step?.timestamp).toBe(withA3Document.messages.find((message) => message.phase === 'A3')?.timestamp)
    expect(run.totals.llmCalls).toBe(withA3Document.totals.total_llm_calls)
    expect(run.totals.contextCount).toBe(run.steps.reduce((count, step, index, all) => count + (index === 0 || all[index - 1]?.contextId !== step.contextId ? 1 : 0), 0))
  })

  it('uma sessão anterior à A.3 continua abrindo, com a etapa marcada como não necessária', () => {
    const run = sessionToThinkingRun(completedDocument)

    expect(run.phases.find((phase) => phase.id === 'A3')).toMatchObject({ status: 'skipped', stepCount: 0 })
  })
})
