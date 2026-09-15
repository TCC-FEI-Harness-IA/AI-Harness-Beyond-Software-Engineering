import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EVENT_SUBTYPE } from '@/domain/enums/eventSubtype'
import { EVENT_TYPE } from '@/domain/enums/eventType'
import { RUN_STATUS } from '@/domain/enums/runStatus'
import { THINKING_PHASE } from '@/domain/enums/thinkingPhase'
import type { PhaseProgress, TaskTimeline, ThinkingRun, ThinkingStep } from '@/domain/types/thinkingRun'
import { ViewModeProvider } from '@/state/ViewModeContext'
import { RalphGraphMode } from './RalphGraphMode'

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

const PHASES: PhaseProgress[] = [
  { id: 'A1', label: 'Critérios de aceite gerais', status: 'done', stepCount: 1 },
  { id: 'A2', label: 'Quebra em tarefas', status: 'done', stepCount: 1 },
  { id: 'B', label: 'Execução em loop', status: 'active', stepCount: 2 },
  { id: 'C1', label: 'Verificação global', status: 'pending', stepCount: 0 },
  { id: 'C2', label: 'Planejamento adicional', status: 'pending', stepCount: 0 },
  { id: 'C3', label: 'Resposta final', status: 'pending', stepCount: 0 },
]

function buildTask(): TaskTimeline {
  const resetStep = buildStep({ id: 'reset', subtype: EVENT_SUBTYPE.RESET })
  const reasoningStep = buildStep({ id: 'reasoning', subtype: EVENT_SUBTYPE.REASONING })
  return {
    id: 'T1',
    title: 'Identificar primos',
    status: 'running',
    origin: 'A2',
    attempts: [{ index: 1, reasoning: reasoningStep, verification: null, approved: null }],
    steps: [resetStep, reasoningStep],
    contextIds: ['ctx_1'],
    tokens: 150,
    inferenceTimeMs: 500,
  }
}

function buildRun(overrides: Partial<ThinkingRun> = {}): ThinkingRun {
  const task = buildTask()
  return {
    sessionId: 'sess_test',
    question: 'Quais são todos os números primos entre 0 e 20?',
    modelName: 'openai/gpt-4o-mini',
    status: RUN_STATUS.RUNNING,
    steps: task.steps,
    tasks: [task],
    phases: PHASES,
    finalAnswer: null,
    totals: {
      totalTokens: 150,
      inferenceTimeMs: 500,
      llmCalls: 1,
      taskCount: 1,
      attemptCount: 1,
      contextCount: 1,
      wallTimeMs: null,
    },
    degradations: [],
    error: null,
    warning: null,
    ...overrides,
  }
}

function renderGraph(run: ThinkingRun, isLive = true): ReturnType<typeof render> {
  return render(
    <ViewModeProvider>
      <RalphGraphMode run={run} isLive={isLive} />
    </ViewModeProvider>,
  )
}

describe('RalphGraphMode', () => {
  it('com run vazio mostra o EmptyState', () => {
    renderGraph(buildRun({ steps: [], tasks: [], phases: [] }))
    expect(screen.getByText('Nenhum passo ainda')).toBeInTheDocument()
  })

  it('renderiza os quatro blocos: trilha macro, tarefas, janela de contexto e resumo', () => {
    renderGraph(buildRun())

    expect(screen.getByRole('region', { name: 'Trilha macro das fases' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Tarefas' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Janela de contexto' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Resumo da execução' })).toBeInTheDocument()
  })

  it('com isLive={false} nenhum elemento tem a classe de halo pulsante', () => {
    const { container } = renderGraph(buildRun(), false)
    expect(container.querySelector('[class*="pulse"]')).not.toBeInTheDocument()
  })

  it('com isLive={true} e uma fase ativa, o halo pulsante aparece', () => {
    const { container } = renderGraph(buildRun(), true)
    expect(container.querySelector('[class*="pulse"]')).toBeInTheDocument()
  })

  it('a resposta final aparece também no Modo Gráfico', () => {
    renderGraph(buildRun({ finalAnswer: 'A resposta é 2, 3, 5, 7.' }))
    expect(screen.getAllByText('Resposta final').length).toBeGreaterThan(0)
    expect(screen.getByText('A resposta é 2, 3, 5, 7.')).toBeInTheDocument()
  })
})
