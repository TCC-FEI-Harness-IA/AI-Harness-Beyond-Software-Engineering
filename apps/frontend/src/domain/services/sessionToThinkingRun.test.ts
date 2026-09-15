import { describe, expect, it } from 'vitest'
import completedFixture from '@/test/fixtures/session-a1-completed-15msgs.json'
import failed1MsgFixture from '@/test/fixtures/session-a1-failed-1msg.json'
import failed2MsgsFixture from '@/test/fixtures/session-a1-failed-2msgs.json'
import { EVENT_SUBTYPE } from '../enums/eventSubtype'
import type { SessionDocument } from '../types/sessionDocument'
import { sessionToThinkingRun } from './sessionToThinkingRun'

const completedDocument = completedFixture as unknown as SessionDocument
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
})
