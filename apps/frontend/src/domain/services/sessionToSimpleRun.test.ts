import { describe, expect, it } from 'vitest'
import directCompletedFixture from '@/test/fixtures/session-direct-completed.json'
import directFailedFixture from '@/test/fixtures/session-direct-failed-1msg.json'
import type { SessionDocument } from '../types/sessionDocument'
import { sessionToSimpleRun } from './sessionToSimpleRun'

const completedDocument = directCompletedFixture as unknown as SessionDocument
const failedDocument = directFailedFixture as unknown as SessionDocument

describe('sessionToSimpleRun', () => {
  it('sessão DIRECT completa vira duas mensagens com estatísticas', () => {
    const run = sessionToSimpleRun(completedDocument)

    expect(run.status).toBe('completed')
    expect(run.messages).toHaveLength(2)
    expect(run.messages[0]).toMatchObject({ role: 'user', content: completedDocument.user_question })
    expect(run.messages[1]).toMatchObject({ role: 'assistant', content: completedDocument.final_answer })
    expect(run.messages[1]?.stats?.totalTokens).toBe(completedDocument.totals.total_tokens)
    expect(run.totals?.totalTokens).toBe(completedDocument.totals.total_tokens)
  })

  it('sessão DIRECT failed com 1 mensagem vira só a pergunta, status failed', () => {
    const run = sessionToSimpleRun(failedDocument)

    expect(run.status).toBe('failed')
    expect(run.messages).toHaveLength(1)
    expect(run.messages[0]?.role).toBe('user')
    expect(run.totals).toBeNull()
  })

  it('sem model_name na própria mensagem, usa o model_name do documento', () => {
    const withoutMessageModel: SessionDocument = {
      ...completedDocument,
      messages: completedDocument.messages.map((message) =>
        message.source === 'llm_agent' ? { ...message, model_name: null } : message,
      ),
    }
    const run = sessionToSimpleRun(withoutMessageModel)

    expect(run.messages[1]?.stats?.modelName).toBe(completedDocument.model_name)
  })

  it('não lança para nenhuma das fixtures', () => {
    expect(() => sessionToSimpleRun(completedDocument)).not.toThrow()
    expect(() => sessionToSimpleRun(failedDocument)).not.toThrow()
  })
})
