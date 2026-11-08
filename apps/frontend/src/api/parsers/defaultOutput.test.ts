import { describe, expect, it } from 'vitest'
import { ContractError } from '../errors/ContractError'
import { parseDefaultOutput } from './defaultOutput'

const VALID = {
  message: 'Quais são todos os números primos entre 0 e 20?',
  response: 'Os números primos entre 0 e 20 são: 2, 3, 5, 7, 11, 13, 17, 19.',
  session_id: 'sess_ab12cd34ef56',
  tokens_input: 42,
  tokens_output: 118,
  inference_time_ms: 812,
}

describe('parseDefaultOutput', () => {
  it('devolve o DTO tipado para um corpo válido', () => {
    expect(parseDefaultOutput(VALID)).toEqual(VALID)
  })

  it('lança ContractError quando a raiz não é um objeto', () => {
    expect(() => parseDefaultOutput('não é objeto')).toThrow(ContractError)
    expect(() => parseDefaultOutput(null)).toThrow(ContractError)
    expect(() => parseDefaultOutput([])).toThrow(ContractError)
  })

  it('lança ContractError quando falta um campo string', () => {
    const { message: _message, ...rest } = VALID
    expect(() => parseDefaultOutput(rest)).toThrow(ContractError)
  })

  it('lança ContractError quando um campo numérico vem com o tipo errado', () => {
    expect(() => parseDefaultOutput({ ...VALID, tokens_input: '42' })).toThrow(ContractError)
    expect(() => parseDefaultOutput({ ...VALID, inference_time_ms: Number.NaN })).toThrow(ContractError)
  })
})
