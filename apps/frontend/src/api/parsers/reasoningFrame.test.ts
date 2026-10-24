import { describe, expect, it, vi } from 'vitest'
import { ContractError } from '../errors/ContractError'
import { parseReasoningFrame } from './reasoningFrame'

const VALID_EVENT = {
  type: 'thinking',
  subtype: 'reasoning',
  phase: 'B1',
  task: 'T1',
  session_id: 'sess_abc123',
  content: '## Resolução\n\nConteúdo em markdown.',
  total_tokens: 1234,
  context_window: { context_id: 'ctx_1', context_size: 512 },
  inference_time_ms: 980,
}

describe('parseReasoningFrame', () => {
  it('reconhece um frame de 9 campos como ReasoningEventDTO', () => {
    const frame = parseReasoningFrame(VALID_EVENT)
    expect(frame).toEqual(VALID_EVENT)
  })

  it('reconhece o frame reduzido {type: "error", content} como ReasoningErrorFrame', () => {
    const frame = parseReasoningFrame({ type: 'error', content: 'falha genérica' })
    expect(frame).toEqual({ type: 'error', content: 'falha genérica' })
  })

  it('lança ContractError nomeando o campo faltando', () => {
    const { session_id: _omitted, ...withoutSessionId } = VALID_EVENT
    expect(() => parseReasoningFrame(withoutSessionId)).toThrow(ContractError)
    expect(() => parseReasoningFrame(withoutSessionId)).toThrow(/session_id/)
  })

  it('usa fallback para subtype desconhecido, sem lançar', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const frame = parseReasoningFrame({ ...VALID_EVENT, subtype: 'algo_novo_do_backend' })
    expect(frame).toMatchObject({ subtype: 'reasoning' })
    expect(warnSpy).toHaveBeenCalled()
    warnSpy.mockRestore()
  })

  it('reconhece a fase A3 sem usar o fallback nem registrar aviso', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    const frame = parseReasoningFrame({ ...VALID_EVENT, phase: 'A3', subtype: 'learn', task: 'setup' })

    expect(frame).toMatchObject({ phase: 'A3', subtype: 'learn', task: 'setup' })
    expect(warn).not.toHaveBeenCalled()
    warn.mockRestore()
  })

  it('usa fallback para phase desconhecida, sem lançar', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const frame = parseReasoningFrame({ ...VALID_EVENT, phase: 'FASE_NOVA_DO_BACKEND' })
    expect(frame).toMatchObject({ phase: 'B1' })
    expect(warnSpy).toHaveBeenCalled()
    warnSpy.mockRestore()
  })

  it('lança ContractError quando type tem valor fora do enum EventType', () => {
    expect(() => parseReasoningFrame({ ...VALID_EVENT, type: 'tipo-inexistente' })).toThrow(ContractError)
  })

  it('lança ContractError quando context_window está ausente', () => {
    const { context_window: _omitted, ...withoutContextWindow } = VALID_EVENT
    expect(() => parseReasoningFrame(withoutContextWindow)).toThrow(ContractError)
  })

  it('lança ContractError para um formato de frame desconhecido', () => {
    expect(() => parseReasoningFrame({ foo: 'bar' })).toThrow(ContractError)
  })
})
