import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { MessageStatsView } from '@/domain/types/messageStatsView'
import { MessageStats } from './MessageStats'

const FULL_STATS: MessageStatsView = {
  modelName: 'openai/gpt-4o-mini',
  tokensInput: 420,
  tokensOutput: 118,
  totalTokens: null,
  inferenceTimeMs: 812,
  contextId: 'ctx_ab12cd34ef56',
  contextSize: 1834,
  timestamp: null,
}

const NULL_STATS: MessageStatsView = {
  modelName: null,
  tokensInput: null,
  tokensOutput: null,
  totalTokens: null,
  inferenceTimeMs: null,
  contextId: null,
  contextSize: null,
  timestamp: null,
}

describe('MessageStats', () => {
  it('omite campos null', () => {
    const { container } = render(<MessageStats stats={NULL_STATS} />)
    expect(container.textContent).toBe('')
  })

  it('a ordem é modelo → tokens → tempo → contexto', () => {
    const { container } = render(<MessageStats stats={FULL_STATS} />)
    const text = container.textContent ?? ''

    const modelIndex = text.indexOf('openai/gpt-4o-mini')
    const tokensIndex = text.indexOf('Tokens')
    const timeIndex = text.indexOf('Tempo')
    const contextIndex = text.indexOf('Contexto')

    expect(modelIndex).toBeGreaterThanOrEqual(0)
    expect(modelIndex).toBeLessThan(tokensIndex)
    expect(tokensIndex).toBeLessThan(timeIndex)
    expect(timeIndex).toBeLessThan(contextIndex)
  })

  it('os números saem formatados em pt-BR', () => {
    render(<MessageStats stats={FULL_STATS} />)
    expect(screen.getByText('420 → 118')).toBeInTheDocument()
    expect(screen.getByText('1.834 tokens')).toBeInTheDocument()
  })
})
