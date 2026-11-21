import { afterEach, describe, expect, it, vi } from 'vitest'
import type { DefaultOutputDTO } from '../types/defaultOutput'
import { simpleRunFromResponse } from './buildSimpleRun'

const RESPONSE: DefaultOutputDTO = {
  message: 'Quais são todos os números primos entre 0 e 20?',
  response: 'Os números primos entre 0 e 20 são: 2, 3, 5, 7, 11, 13, 17, 19.',
  session_id: 'sess_ab12cd34ef56',
  tokens_input: 42,
  tokens_output: 118,
  inference_time_ms: 812,
}

describe('simpleRunFromResponse', () => {
  it('monta as duas mensagens, com o total de tokens somado e o modelo vindo do parâmetro', () => {
    const run = simpleRunFromResponse(RESPONSE.message, RESPONSE, 'openai/gpt-4o-mini')

    expect(run.messages).toHaveLength(2)
    expect(run.messages[0]).toMatchObject({ role: 'user', content: RESPONSE.message, stats: null })
    expect(run.messages[1]).toMatchObject({ role: 'assistant', content: RESPONSE.response })

    const assistantStats = run.messages[1]?.stats
    expect(assistantStats?.totalTokens).toBe(160)
    expect(assistantStats?.modelName).toBe('openai/gpt-4o-mini')
    expect(assistantStats?.contextId).toBeNull()
  })

  it('carrega o session_id da resposta no run e nas estatísticas da mensagem', () => {
    const run = simpleRunFromResponse(RESPONSE.message, RESPONSE, 'openai/gpt-4o-mini')

    expect(run.sessionId).toBe('sess_ab12cd34ef56')
    expect(run.messages[1]?.stats?.sessionId).toBe('sess_ab12cd34ef56')
    expect(run.status).toBe('completed')
    expect(run.error).toBeNull()
  })

  it('gera ids estáveis e distintos para as duas mensagens', () => {
    const run = simpleRunFromResponse(RESPONSE.message, RESPONSE, 'openai/gpt-4o-mini')

    expect(run.messages[0]?.id).not.toBe(run.messages[1]?.id)
    expect(run.messages[0]?.id).toBeTruthy()
  })

  it('sem crypto.randomUUID, cai para o gerador alternativo baseado em Date/Math.random', () => {
    const stub = { ...globalThis.crypto }
    // @ts-expect-error remove a chave por completo — `'randomUUID' in crypto` precisa dar `false`
    delete stub.randomUUID
    vi.stubGlobal('crypto', stub)

    const run = simpleRunFromResponse(RESPONSE.message, RESPONSE, 'openai/gpt-4o-mini')

    expect(run.messages[0]?.id).toMatch(/^msg_\d+_[a-z0-9]+$/)
    expect(run.messages[0]?.id).not.toBe(run.messages[1]?.id)
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
})
