import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { RUN_STATUS } from '@/domain/enums/runStatus'
import type { SimpleRun } from '@/domain/types/simpleRun'
import { SimpleChatView } from './SimpleChatView'

const RUN_WITH_MESSAGES: SimpleRun = {
  sessionId: 'sess_ab12cd34ef56',
  status: RUN_STATUS.COMPLETED,
  messages: [
    { id: 'msg_1', role: 'user', content: 'Quais são os primos entre 0 e 20?', stats: null },
    {
      id: 'msg_2',
      role: 'assistant',
      content: 'Os primos são 2, 3, 5, 7, 11, 13, 17, 19.',
      stats: {
        modelName: 'openai/gpt-4o-mini',
        tokensInput: 42,
        tokensOutput: 118,
        totalTokens: 160,
        inferenceTimeMs: 812,
        contextId: null,
        contextSize: null,
        timestamp: null,
        sessionId: 'sess_ab12cd34ef56',
      },
    },
  ],
  totals: {
    totalMessages: 2,
    totalLlmCalls: 1,
    tokensInput: 42,
    tokensOutput: 118,
    totalTokens: 160,
    inferenceTimeMs: 812,
    wallTimeMs: 812,
  },
  error: null,
}

describe('SimpleChatView', () => {
  it('com isLive={false} não renderiza o Composer', () => {
    render(<SimpleChatView run={RUN_WITH_MESSAGES} isLive={false} />)
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })

  it('com isLive={true} renderiza o Composer', () => {
    render(<SimpleChatView run={RUN_WITH_MESSAGES} isLive />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('a mensagem do assistente mostra as estatísticas', () => {
    render(<SimpleChatView run={RUN_WITH_MESSAGES} isLive={false} />)

    expect(screen.getByText('openai/gpt-4o-mini')).toBeInTheDocument()
    expect(screen.getAllByText('812 ms').length).toBeGreaterThan(0)
  })

  it('o estado de erro mostra "Tentar de novo"', () => {
    const runWithError: SimpleRun = {
      ...RUN_WITH_MESSAGES,
      status: RUN_STATUS.FAILED,
      error: { message: 'HTTP 500', userMessage: 'Algo deu errado no servidor.' },
    }
    const onRetry = vi.fn()

    render(<SimpleChatView run={runWithError} isLive onRetry={onRetry} />)

    expect(screen.getByText('Algo deu errado no servidor.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tentar de novo' })).toBeInTheDocument()
  })

  it('sem mensagens mostra o estado vazio', () => {
    const emptyRun: SimpleRun = {
      sessionId: null,
      status: RUN_STATUS.IDLE,
      messages: [],
      totals: null,
      error: null,
    }

    render(<SimpleChatView run={emptyRun} isLive />)

    expect(screen.getByText('Faça uma pergunta para começar')).toBeInTheDocument()
  })
})
