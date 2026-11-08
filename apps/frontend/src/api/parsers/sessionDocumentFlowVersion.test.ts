// Versão do fluxo e subtipo persistido (nova fase de validação — 01). Sessões Ralph antigas, sem
// `flow_version`, continuam lidas como versão 1 (A.3 = aprendizados do enunciado); sessões novas trazem a
// versão 2 (A.3 = validação da decomposição, A.4 = aprendizados). A inferência direta não tem versão Ralph.

import { describe, expect, it } from 'vitest'
import a1CompletedWithA3 from '@/test/fixtures/session-a1-completed-with-a3.json'
import v2PlanRevision from '@/test/fixtures/session-a1-v2-plan-revision.json'
import directCompleted from '@/test/fixtures/session-direct-completed.json'
import { ContractError } from '../errors/ContractError'
import { parseSessionDocument } from './sessionDocument'

describe('parseSessionDocument — versão do fluxo', () => {
  it('sessão Ralph antiga sem o campo é lida como versão 1, sem subtipos', () => {
    const document = parseSessionDocument(a1CompletedWithA3)

    expect(document.flow_version).toBe(1)
    expect(document.messages.every((message) => message.subtype === null)).toBe(true)
  })

  it('sessão nova traz a versão 2 e o subtipo de cada mensagem que emitiu evento', () => {
    const document = parseSessionDocument(v2PlanRevision)

    expect(document.flow_version).toBe(2)
    expect(document.messages.slice(2, 9).map((message) => [message.phase, message.subtype])).toEqual([
      ['A2', 'plan_candidate'],
      ['A3', null],
      ['A3', 'plan_rejected'],
      ['A2', 'plan_candidate'],
      ['A3', 'plan_approved'],
      ['A3', 'tasks'],
      ['A4', 'learn'],
    ])
  })

  it('inferência direta não adquire versão de fluxo Ralph', () => {
    expect(parseSessionDocument(directCompleted).flow_version).toBeNull()
    expect(parseSessionDocument({ ...directCompleted, flow_version: null }).flow_version).toBeNull()
  })

  it('versão explícita não é reinterpretada', () => {
    expect(parseSessionDocument({ ...a1CompletedWithA3, flow_version: 1 }).flow_version).toBe(1)
  })

  it('lança ContractError para uma versão ou um subtipo desconhecidos', () => {
    expect(() => parseSessionDocument({ ...v2PlanRevision, flow_version: 3 })).toThrow(ContractError)
    expect(() => parseSessionDocument({ ...v2PlanRevision, flow_version: '2' })).toThrow(/flow_version/)
    const messages = v2PlanRevision.messages.map((message, index) =>
      index === 2 ? { ...message, subtype: 'candidato' } : message,
    )
    expect(() => parseSessionDocument({ ...v2PlanRevision, messages })).toThrow(/subtype/)
  })
})
