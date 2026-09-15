import { describe, expect, it } from 'vitest'
import a1Completed from '../../test/fixtures/session-a1-completed-15msgs.json'
import a1Failed1Msg from '../../test/fixtures/session-a1-failed-1msg.json'
import a1Failed1MsgB from '../../test/fixtures/session-a1-failed-1msg-b.json'
import a1Failed2Msgs from '../../test/fixtures/session-a1-failed-2msgs.json'
import directCompleted from '../../test/fixtures/session-direct-completed.json'
import directFailed1Msg from '../../test/fixtures/session-direct-failed-1msg.json'
import directFailed1MsgB from '../../test/fixtures/session-direct-failed-1msg-b.json'
import { ContractError } from '../errors/ContractError'
import { parseSessionDocument } from './sessionDocument'

const ALL_FIXTURES = [
  a1Completed,
  a1Failed1Msg,
  a1Failed1MsgB,
  a1Failed2Msgs,
  directCompleted,
  directFailed1Msg,
  directFailed1MsgB,
]

describe('parseSessionDocument', () => {
  it('processa, sem erro, todos os documentos reais de apps/backend/data/sessions/', () => {
    for (const fixture of ALL_FIXTURES) {
      expect(() => parseSessionDocument(fixture)).not.toThrow()
    }
  })

  it('aceita a sessão A1 completa com 15 mensagens, preservando a ordem e os campos', () => {
    const document = parseSessionDocument(a1Completed)
    expect(document.flow).toBe('A1')
    expect(document.status).toBe('completed')
    expect(document.messages).toHaveLength(15)
    expect(document.messages[0]?.source).toBe('user')
    expect(document.final_answer).toContain('primos')
  })

  it('aceita sessões failed com uma única mensagem', () => {
    const document = parseSessionDocument(a1Failed1Msg)
    expect(document.status).toBe('failed')
    expect(document.messages).toHaveLength(1)
    expect(document.final_answer).toBeNull()
  })

  it('aceita sessões DIRECT', () => {
    const document = parseSessionDocument(directCompleted)
    expect(document.flow).toBe('DIRECT')
    expect(document.messages.every((message) => message.phase === 'DIRECT')).toBe(true)
  })

  it('aceita final_answer: null e degradations: []', () => {
    const document = parseSessionDocument(directFailed1Msg)
    expect(document.final_answer).toBeNull()
    expect(document.degradations).toEqual([])
  })

  it('lança ContractError quando messages não é array', () => {
    const invalid = { ...a1Failed1Msg, messages: 'não é um array' }
    expect(() => parseSessionDocument(invalid)).toThrow(ContractError)
  })

  it('lança ContractError quando uma mensagem tem phase inválida', () => {
    const invalid = structuredClone(a1Failed1Msg)
    const [firstMessage] = invalid.messages
    if (!firstMessage) throw new Error('fixture sem mensagens')
    firstMessage.phase = 'FASE_INEXISTENTE'
    expect(() => parseSessionDocument(invalid)).toThrow(ContractError)
  })
})
