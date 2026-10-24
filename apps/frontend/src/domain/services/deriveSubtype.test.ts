import { describe, expect, it, vi } from 'vitest'
import { deriveStepKind } from './deriveSubtype'
import type { SessionMessageDocument } from '../types/sessionDocument'

function message(overrides: Partial<SessionMessageDocument>): SessionMessageDocument {
  return {
    id: 'msg_1',
    order: 0,
    timestamp: '2026-09-11T23:18:06.000000+00:00',
    phase: 'A1',
    source: 'llm_agent',
    content: '',
    task_id: null,
    context_id: 'ctx_1',
    tokens_input: 0,
    tokens_output: 0,
    total_tokens: 0,
    inference_time_ms: 0,
    model_name: null,
    ...overrides,
  }
}

describe('deriveStepKind', () => {
  it('mensagem DIRECT nunca vira passo', () => {
    expect(deriveStepKind(message({ phase: 'DIRECT', source: 'user' }), { laterMessages: [] })).toBeNull()
    expect(deriveStepKind(message({ phase: 'DIRECT', source: 'llm_agent' }), { laterMessages: [] })).toBeNull()
  })

  it('a pergunta do usuário nunca vira passo', () => {
    expect(deriveStepKind(message({ phase: 'A1', source: 'user' }), { laterMessages: [] })).toBeNull()
  })

  it.each([
    ['A1', 'setup'],
    ['A2', 'tasks'],
    ['A3', 'learn'],
    ['B3', 'store'],
    ['B4', 'learn'],
    ['C1', 'compile'],
    ['C2', 'replan'],
  ] as const)('%s/llm_agent ou system → subtype %s', (phase, subtype) => {
    const result = deriveStepKind(message({ phase, source: phase === 'B3' ? 'system' : 'llm_agent' }), {
      laterMessages: [],
    })
    expect(result).toEqual({ type: 'thinking', subtype })
  })

  it('B1/system → reset', () => {
    const result = deriveStepKind(message({ phase: 'B1', source: 'system' }), { laterMessages: [] })
    expect(result).toEqual({ type: 'thinking', subtype: 'reset' })
  })

  it('B1/llm_agent → reasoning', () => {
    const result = deriveStepKind(message({ phase: 'B1', source: 'llm_agent' }), { laterMessages: [] })
    expect(result).toEqual({ type: 'thinking', subtype: 'reasoning' })
  })

  it('C3 → result/compile', () => {
    const result = deriveStepKind(message({ phase: 'C3', source: 'llm_agent' }), { laterMessages: [] })
    expect(result).toEqual({ type: 'result', subtype: 'compile' })
  })

  describe('B2 — verify_pass vs verify_fail', () => {
    it('marcador "approved" → verify_pass', () => {
      const result = deriveStepKind(
        message({ phase: 'B2', source: 'llm_agent', content: '**Decisão:** `approved`\n...' }),
        { laterMessages: [] },
      )
      expect(result).toEqual({ type: 'thinking', subtype: 'verify_pass' })
    })

    it('marcador "reproved" → verify_fail', () => {
      const result = deriveStepKind(
        message({ phase: 'B2', source: 'llm_agent', content: '**Decisão:** `reproved`\n...' }),
        { laterMessages: [] },
      )
      expect(result).toEqual({ type: 'thinking', subtype: 'verify_fail' })
    })

    it('sem marcador e com outro B2 da mesma tarefa depois → verify_fail (fallback posicional)', () => {
      const current = message({ phase: 'B2', source: 'llm_agent', content: 'sem marcador', task_id: 'T1' })
      const later = message({ phase: 'B2', source: 'llm_agent', task_id: 'T1', order: 1 })
      const result = deriveStepKind(current, { laterMessages: [later] })
      expect(result).toEqual({ type: 'thinking', subtype: 'verify_fail' })
    })

    it('sem marcador e sem outro B2 depois → verify_pass (fallback posicional)', () => {
      const current = message({ phase: 'B2', source: 'llm_agent', content: 'sem marcador', task_id: 'T1' })
      const laterOtherTask = message({ phase: 'B2', source: 'llm_agent', task_id: 'T2', order: 1 })
      const result = deriveStepKind(current, { laterMessages: [laterOtherTask] })
      expect(result).toEqual({ type: 'thinking', subtype: 'verify_pass' })
    })
  })

  it('combinação desconhecida cai no fallback "reasoning" sem lançar', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    // O parser de fronteira já garante que `phase` pertence ao enum antes de qualquer mensagem
    // chegar aqui — este `as` simula um valor fora do universo conhecido só para provar que a
    // função degrada graciosamente em vez de lançar, como a regra 6 exige.
    const unknownPhase = 'Z9' as unknown as SessionMessageDocument['phase']
    const result = deriveStepKind(message({ phase: unknownPhase, source: 'llm_agent' }), {
      laterMessages: [],
    })
    expect(result).toEqual({ type: 'thinking', subtype: 'reasoning' })
    expect(warnSpy).toHaveBeenCalled()
    warnSpy.mockRestore()
  })
})
