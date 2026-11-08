import { describe, expect, it } from 'vitest'
import { ContractError } from '../errors/ContractError'
import { parseSessionList } from './sessionList'

describe('parseSessionList', () => {
  it('devolve os ids para um corpo válido', () => {
    expect(parseSessionList({ session_ids: ['sess_ab12', 'sess_9f8e'] })).toEqual({
      session_ids: ['sess_ab12', 'sess_9f8e'],
    })
  })

  it('lista vazia é válida', () => {
    expect(parseSessionList({ session_ids: [] })).toEqual({ session_ids: [] })
  })

  it('lança ContractError quando a raiz não é um objeto', () => {
    expect(() => parseSessionList('não é objeto')).toThrow(ContractError)
  })

  it('lança ContractError quando session_ids não é array', () => {
    expect(() => parseSessionList({ session_ids: 'sess_ab12' })).toThrow(ContractError)
  })

  it('lança ContractError quando um item da lista não é string', () => {
    expect(() => parseSessionList({ session_ids: ['sess_ab12', 42] })).toThrow(ContractError)
  })
})
