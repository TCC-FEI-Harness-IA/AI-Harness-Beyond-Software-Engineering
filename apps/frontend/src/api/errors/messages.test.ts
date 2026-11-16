import { describe, expect, it } from 'vitest'
import { httpStatusMessage, wsCloseCodeMessage } from './messages'

describe('mensagens de autenticação e credencial', () => {
  it('explica os códigos de fechamento de autenticação, credencial, limite e origem', () => {
    expect(wsCloseCodeMessage(4401)).toMatch(/login/i)
    expect(wsCloseCodeMessage(4428)).toMatch(/chave OpenRouter/)
    expect(wsCloseCodeMessage(4429)).toMatch(/limite/i)
    expect(wsCloseCodeMessage(4503)).toMatch(/autenticação/i)
    expect(wsCloseCodeMessage(1008)).toMatch(/origem/i)
  })

  it('explica os status de autenticação, CSRF, credencial e limite', () => {
    expect(httpStatusMessage(401)).toMatch(/login/i)
    expect(httpStatusMessage(403)).toMatch(/recusada/i)
    expect(httpStatusMessage(428)).toMatch(/chave OpenRouter/)
    expect(httpStatusMessage(429)).toMatch(/Muitas/)
    expect(httpStatusMessage(503)).toMatch(/indisponível/)
  })
})
