import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { EVENT_SUBTYPE } from '@/domain/enums/eventSubtype'
import { EVENT_TYPE } from '@/domain/enums/eventType'
import { THINKING_PHASE } from '@/domain/enums/thinkingPhase'
import type { ThinkingStep } from '@/domain/types/thinkingRun'
import { StepDetailPanel } from './StepDetailPanel'

function buildStep(overrides: Partial<ThinkingStep> = {}): ThinkingStep {
  return {
    id: 'step-1',
    order: 0,
    type: EVENT_TYPE.THINKING,
    subtype: EVENT_SUBTYPE.REASONING,
    phase: THINKING_PHASE.B1,
    taskId: 'T1',
    content: '## Resolução\n\nConteúdo do passo em markdown.',
    totalTokens: 100,
    contextId: 'ctx_1234567',
    contextSize: 50,
    inferenceTimeMs: 500,
    timestamp: null,
    ...overrides,
  }
}

describe('StepDetailPanel', () => {
  it('abre com o conteúdo do passo em Markdown', () => {
    render(<StepDetailPanel step={buildStep()} modelName="openai/gpt-4o-mini" sessionId={null} onClose={vi.fn()} onViewInChat={vi.fn()} />)

    expect(screen.getByRole('dialog', { name: 'Detalhe do passo' })).toBeInTheDocument()
    expect(screen.getByText('Conteúdo do passo em markdown.')).toBeInTheDocument()
  })

  it('não renderiza nada quando step é null', () => {
    render(<StepDetailPanel step={null} modelName={null} sessionId={null} onClose={vi.fn()} onViewInChat={vi.fn()} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('Esc fecha o painel', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<StepDetailPanel step={buildStep()} modelName={null} sessionId={null} onClose={onClose} onViewInChat={vi.fn()} />)

    await user.keyboard('{Escape}')

    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('o foco volta ao elemento de origem ao fechar', async () => {
    const trigger = document.createElement('button')
    trigger.textContent = 'abrir'
    document.body.appendChild(trigger)
    trigger.focus()
    expect(document.activeElement).toBe(trigger)

    const { rerender } = render(
      <StepDetailPanel step={buildStep()} modelName={null} sessionId={null} onClose={vi.fn()} onViewInChat={vi.fn()} />,
    )

    expect(document.activeElement).not.toBe(trigger)

    rerender(<StepDetailPanel step={null} modelName={null} sessionId={null} onClose={vi.fn()} onViewInChat={vi.fn()} />)

    expect(document.activeElement).toBe(trigger)
    document.body.removeChild(trigger)
  })

  it('"Ver no Modo Chat" chama o callback de troca de modo com o step.id', async () => {
    const user = userEvent.setup()
    const onViewInChat = vi.fn()
    render(<StepDetailPanel step={buildStep({ id: 'step-42' })} modelName={null} sessionId={null} onClose={vi.fn()} onViewInChat={onViewInChat} />)

    await user.click(screen.getByRole('button', { name: 'Ver no Modo Chat' }))

    expect(onViewInChat).toHaveBeenCalledWith('step-42')
  })
})
