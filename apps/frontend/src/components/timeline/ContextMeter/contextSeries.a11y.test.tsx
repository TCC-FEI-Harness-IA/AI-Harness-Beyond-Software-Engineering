import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EVENT_SUBTYPE } from '@/domain/enums/eventSubtype'
import { EVENT_TYPE } from '@/domain/enums/eventType'
import { THINKING_PHASE } from '@/domain/enums/thinkingPhase'
import type { ThinkingStep } from '@/domain/types/thinkingRun'
import { ContextMeter } from './ContextMeter'

function buildStep(overrides: Partial<ThinkingStep>): ThinkingStep {
  return {
    id: 'step',
    order: 0,
    type: EVENT_TYPE.THINKING,
    subtype: EVENT_SUBTYPE.REASONING,
    phase: THINKING_PHASE.B1,
    taskId: 'T1',
    content: 'conteúdo',
    totalTokens: 100,
    contextId: 'ctx_1234567',
    contextSize: 50,
    inferenceTimeMs: 500,
    timestamp: null,
    ...overrides,
  }
}

describe('ContextMeter — acessibilidade do gráfico de contexto', () => {
  it('o SVG tem role="img" e um aria-label textual descrevendo a série', () => {
    const steps = [
      buildStep({ id: '1', subtype: EVENT_SUBTYPE.RESET, contextSize: 0, totalTokens: 0 }),
      buildStep({ id: '2', subtype: EVENT_SUBTYPE.REASONING, contextSize: 400, totalTokens: 400 }),
      buildStep({ id: '3', subtype: EVENT_SUBTYPE.RESET, taskId: 'T2', contextSize: 0, totalTokens: 400 }),
      buildStep({ id: '4', subtype: EVENT_SUBTYPE.REASONING, taskId: 'T2', contextSize: 200, totalTokens: 600 }),
    ]

    render(<ContextMeter steps={steps} />)

    const chart = screen.getByRole('img')
    const label = chart.getAttribute('aria-label') ?? ''

    expect(label).toContain('2 reinicializações')
    expect(label).toContain('400')
    expect(label).toContain('600')
  })

  it('o painel colapsado não mostra o gráfico, mas o botão continua acessível', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    const user = userEvent.setup()
    const steps = [buildStep({ id: '1' })]

    render(<ContextMeter steps={steps} />)

    const toggle = screen.getByRole('button', { name: /Janela de contexto/ })
    expect(toggle).toHaveAttribute('aria-expanded', 'true')

    await user.click(toggle)

    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })
})
