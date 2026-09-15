import { describe, expect, it } from 'vitest'
import { ContractError } from '../errors/ContractError'
import { optionalString, requireNumber, requireObject, requireString } from './primitives'

describe('optionalString', () => {
  it('null e undefined viram null', () => {
    expect(optionalString({ x: null }, 'x', 'x')).toBeNull()
    expect(optionalString({}, 'x', 'x')).toBeNull()
  })

  it('string passa direto', () => {
    expect(optionalString({ x: 'valor' }, 'x', 'x')).toBe('valor')
  })

  it('lança ContractError quando o valor não é string nem null/undefined', () => {
    expect(() => optionalString({ x: 42 }, 'x', 'x')).toThrow(ContractError)
  })
})

describe('mensagens de erro com valor não serializável', () => {
  it('requireString com um valor circular não lança um segundo erro ao montar a mensagem', () => {
    const circular: Record<string, unknown> = {}
    circular.self = circular

    expect(() => requireString({ x: circular }, 'x', 'x')).toThrow(ContractError)
  })

  it('requireNumber com undefined descreve o valor como "undefined" na mensagem', () => {
    expect(() => requireNumber({}, 'x', 'x')).toThrow(/undefined/)
  })

  it('requireObject com array lança ContractError descrevendo o valor', () => {
    expect(() => requireObject([1, 2, 3], 'raiz')).toThrow(ContractError)
  })
})
