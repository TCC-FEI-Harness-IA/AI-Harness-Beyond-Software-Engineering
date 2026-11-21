import { describe, expect, it } from 'vitest'
import { HttpError } from './HttpError'
import { NetworkError } from './NetworkError'
import { WebSocketError } from './WebSocketError'

describe('HttpError', () => {
  it('um status mapeado usa a mensagem específica', () => {
    expect(new HttpError(404, null).userMessage).toBe('Chat não encontrado.')
  })

  it('um status fora do mapa usa a mensagem genérica', () => {
    expect(new HttpError(418, null).userMessage).toBe('O servidor respondeu com um erro inesperado.')
  })

  it('sem detail, a mensagem técnica registra "(sem detail)"', () => {
    expect(new HttpError(500, null).message).toContain('(sem detail)')
  })

  it('com detail, a mensagem técnica inclui o texto', () => {
    expect(new HttpError(500, 'falha no provedor').message).toContain('falha no provedor')
  })
})

describe('NetworkError', () => {
  it('carrega a mensagem genérica de falha de rede', () => {
    const error = new NetworkError(new TypeError('Failed to fetch'))
    expect(error.userMessage).toBe('Não foi possível falar com o servidor.')
    expect(error.message).toContain('Failed to fetch')
  })
})

describe('WebSocketError.fromCloseCode', () => {
  it('um código mapeado (1011) usa a mensagem de execução falhada', () => {
    expect(WebSocketError.fromCloseCode(1011).userMessage).toBe('A execução falhou no servidor.')
  })

  it('um código fora do mapa usa a mensagem genérica de encerramento inesperado', () => {
    expect(WebSocketError.fromCloseCode(1006).userMessage).toBe(
      'A conexão com o servidor foi encerrada de forma inesperada.',
    )
  })
})
