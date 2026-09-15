import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EVENT_SUBTYPE } from '@/domain/enums/eventSubtype'
import { EVENT_TYPE } from '@/domain/enums/eventType'
import { RUN_STATUS } from '@/domain/enums/runStatus'
import { THINKING_PHASE } from '@/domain/enums/thinkingPhase'
import type { ThinkingRun, ThinkingStep } from '@/domain/types/thinkingRun'
import { RalphChatMode } from './RalphChatMode'

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
    contextId: 'ctx_1',
    contextSize: 50,
    inferenceTimeMs: 500,
    timestamp: null,
    ...overrides,
  }
}

function buildRun(steps: ThinkingStep[], overrides: Partial<ThinkingRun> = {}): ThinkingRun {
  return {
    sessionId: 'sess_test',
    question: 'Quais são todos os números primos entre 0 e 20?',
    modelName: 'openai/gpt-4o-mini',
    status: RUN_STATUS.COMPLETED,
    steps,
    tasks: [],
    phases: [],
    finalAnswer: null,
    totals: {
      totalTokens: 100,
      inferenceTimeMs: 500,
      llmCalls: 1,
      taskCount: 1,
      attemptCount: 1,
      contextCount: 1,
      wallTimeMs: null,
    },
    degradations: [],
    error: null,
    ...overrides,
  }
}

describe('RalphChatMode', () => {
  it('cada passo do fluxo vira uma mensagem com estatísticas', () => {
    const steps = [
      buildStep({ id: 'reset', order: 0, subtype: EVENT_SUBTYPE.RESET, phase: THINKING_PHASE.B1, inferenceTimeMs: 0 }),
      buildStep({ id: 'reasoning', order: 1, subtype: EVENT_SUBTYPE.REASONING, phase: THINKING_PHASE.B1 }),
    ]
    render(<RalphChatMode run={buildRun(steps)} isLive={false} />)

    expect(screen.getByRole('group', { name: 'Mensagem do usuário' })).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Mensagem do modelo' })).toHaveTextContent('conteúdo')
    expect(screen.getByText('Total', { exact: false })).toBeInTheDocument()
  })

  it('reset e store viram separador, não bolha', () => {
    const steps = [
      buildStep({ id: 'reset', order: 0, subtype: EVENT_SUBTYPE.RESET, phase: THINKING_PHASE.B1, inferenceTimeMs: 0 }),
      buildStep({ id: 'store', order: 1, subtype: EVENT_SUBTYPE.STORE, phase: THINKING_PHASE.B3, inferenceTimeMs: 0 }),
    ]
    render(<RalphChatMode run={buildRun(steps)} isLive={false} />)

    expect(screen.getByText('Contexto reinicializado · T1')).toBeInTheDocument()
    expect(screen.getByText('conteúdo', { selector: 'span' })).toBeInTheDocument()
    // Só a mensagem do usuário usa `role="group"` — nenhum separador vira bolha.
    expect(screen.getAllByRole('group')).toHaveLength(1)
  })

  it('a resposta final aparece destacada no FinalAnswerCard', () => {
    const steps = [
      buildStep({
        id: 'final',
        order: 0,
        subtype: EVENT_SUBTYPE.COMPILE,
        phase: THINKING_PHASE.C3,
        type: EVENT_TYPE.RESULT,
        content: 'resposta final',
      }),
    ]
    render(<RalphChatMode run={buildRun(steps, { finalAnswer: 'resposta final' })} isLive={false} />)

    expect(screen.getByText('Resposta final')).toBeInTheDocument()
    expect(screen.getAllByText('resposta final')).toHaveLength(1)
  })

  it('com isLive={false} não há Composer nem halo pulsante', () => {
    const steps = [buildStep({ id: 'reasoning', order: 0 })]
    const { container } = render(<RalphChatMode run={buildRun(steps)} isLive={false} />)

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    expect(container.querySelector('[class*="animateIn"]')).not.toBeInTheDocument()
  })
})
