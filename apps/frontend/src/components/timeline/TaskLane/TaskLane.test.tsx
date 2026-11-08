import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { EVENT_SUBTYPE } from '@/domain/enums/eventSubtype'
import { EVENT_TYPE } from '@/domain/enums/eventType'
import { THINKING_PHASE } from '@/domain/enums/thinkingPhase'
import type { TaskLaneView } from '@/domain/services/graphLayout'
import type { ThinkingStep } from '@/domain/types/thinkingRun'
import { TaskLane } from './TaskLane'

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

function buildLane(overrides: Partial<TaskLaneView> = {}): TaskLaneView {
  return {
    id: 'T1',
    title: 'Identificar primos de 0 a 10',
    status: 'approved',
    origin: 'A2',
    tokens: 966,
    inferenceTimeMs: 1200,
    attemptCount: 1,
    contextIds: ['ctx_1'],
    steps: [
      { step: buildStep({ id: 'reset', subtype: EVENT_SUBTYPE.RESET }), attemptIndex: 0 },
      { step: buildStep({ id: 'reasoning', subtype: EVENT_SUBTYPE.REASONING }), attemptIndex: 1 },
      { step: buildStep({ id: 'verify', subtype: EVENT_SUBTYPE.VERIFY_PASS, phase: THINKING_PHASE.B2 }), attemptIndex: 1 },
      { step: buildStep({ id: 'store', subtype: EVENT_SUBTYPE.STORE, phase: THINKING_PHASE.B3 }), attemptIndex: 1 },
      { step: buildStep({ id: 'learn', subtype: EVENT_SUBTYPE.LEARN, phase: THINKING_PHASE.B4 }), attemptIndex: 1 },
    ],
    ...overrides,
  }
}

describe('TaskLane', () => {
  it('renderiza um botão por passo', () => {
    render(
      <ul>
        <TaskLane lane={buildLane()} isLive={false} onStepSelect={vi.fn()} />
      </ul>,
    )
    expect(screen.getAllByRole('button')).toHaveLength(5)
  })

  it('clicar num passo chama onStepSelect com o step correspondente', async () => {
    const onStepSelect = vi.fn()
    const lane = buildLane()
    render(
      <ul>
        <TaskLane lane={lane} isLive={false} onStepSelect={onStepSelect} />
      </ul>,
    )

    screen.getByRole('button', { name: /Resolução/ }).click()

    expect(onStepSelect).toHaveBeenCalledTimes(1)
    expect(onStepSelect.mock.calls[0]?.[0]?.id).toBe('reasoning')
  })

  it('tarefa discarded recebe tratamento visual e rótulo acessível', () => {
    render(
      <ul>
        <TaskLane lane={buildLane({ id: 'T3', status: 'discarded' })} isLive={false} onStepSelect={vi.fn()} />
      </ul>,
    )

    expect(screen.getByRole('listitem', { name: /T3.*descartada/ })).toBeInTheDocument()
  })
})
