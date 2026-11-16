import { describe, expect, it } from 'vitest'
import { clearCsrfToken, getCsrfToken, setCsrfToken } from './csrfToken'

describe('csrfToken', () => {
  it('guarda o token só em memória e o apaga no logout', () => {
    setCsrfToken('token-da-sessao')
    expect(getCsrfToken()).toBe('token-da-sessao')

    clearCsrfToken()
    expect(getCsrfToken()).toBeNull()
  })
})
