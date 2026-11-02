import { describe, expect, it } from 'vitest'
import { ContractError } from '../errors/ContractError'
import { parseBackendLimits } from './backendLimits'

describe('parseBackendLimits', () => {
  it('lê o limite de tokens por sessão do backend', () => {
    expect(parseBackendLimits({ max_tokens_limit: 120000 })).toEqual({ max_tokens_limit: 120000 })
  })

  it.each([
    [null, 'backendLimits'],
    [{}, 'max_tokens_limit'],
    [{ max_tokens_limit: '120000' }, 'max_tokens_limit'],
    [{ max_tokens_limit: 0 }, 'inteiro positivo'],
    [{ max_tokens_limit: 1.5 }, 'inteiro positivo'],
  ])('recusa %j', (raw, message) => {
    expect(() => parseBackendLimits(raw)).toThrow(ContractError)
    expect(() => parseBackendLimits(raw)).toThrow(message)
  })
})
