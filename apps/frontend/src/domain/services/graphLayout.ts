// Toda a matemática do Modo Gráfico (README, FASE 06, seção 8). Funções puras: não medem DOM,
// não importam React — recebem o `ThinkingRun` já pronto (FASE 05) e devolvem coordenadas num
// `viewBox` normalizado (0..100). O componente só posiciona o que já veio calculado.

import { EVENT_SUBTYPE } from '../enums/eventSubtype'
import { PHASE_LABEL, PHASE_SHORT_LABEL } from '../enums/thinkingPhase'
import type { PhaseNodeId, PhaseProgress, TaskTimeline, ThinkingRun, ThinkingStep } from '../types/thinkingRun'

// 'B' agrega B1–B4 (README, seção 6.3) e por isso não tem correspondente direto em
// `PHASE_LABEL`/`PHASE_SHORT_LABEL` (FASE 02, indexados por `ThinkingPhase`) — é o único texto
// novo desta função; os outros cinco nós reusam os mapas da FASE 02 (FASE 06, seção 4).
const B_NODE_SUBTITLE = 'Execução em Loop'
const B_NODE_SHORT_LABEL = 'B'

export interface MacroNodeView {
  id: PhaseNodeId
  shortLabel: string
  subtitle: string
  status: PhaseProgress['status']
  /** Só o nó 'B' carrega progresso — as demais fases são um passo único (FASE 06, seção 4). */
  progress: { done: number; total: number } | null
}

/** Tarefas concluídas (aprovadas, degradadas ou descartadas) sobre o total conhecido até agora. */
export function describeTaskProgress(run: ThinkingRun): { done: number; total: number } {
  const total = run.tasks.length
  const done = run.tasks.filter((task) => task.status !== 'pending' && task.status !== 'running').length
  return { done, total }
}

/** A trilha macro A→B→C — os sete nós do "caminho" pedido no requisito (FASE 06, seção 4). */
export function buildMacroTrack(run: ThinkingRun): MacroNodeView[] {
  const progress = describeTaskProgress(run)
  return run.phases.map((phase) => ({
    id: phase.id,
    shortLabel: phase.id === 'B' ? B_NODE_SHORT_LABEL : PHASE_SHORT_LABEL[phase.id],
    subtitle: phase.id === 'B' ? B_NODE_SUBTITLE : PHASE_LABEL[phase.id],
    status: phase.status,
    progress: phase.id === 'B' ? progress : null,
  }))
}

/** O passo mais recente da execução — o que a trilha e as faixas destacam como "atual". */
export function findActiveStep(run: ThinkingRun): ThinkingStep | null {
  return run.steps[run.steps.length - 1] ?? null
}

export interface TaskLaneStepView {
  step: ThinkingStep
  /** 0 fora de uma tentativa (`reset`/`execute`); 1-based para `reasoning`/`verify_*`/`store`/`learn`. */
  attemptIndex: number
}

export interface TaskLaneView {
  id: string
  title: string | null
  status: TaskTimeline['status']
  origin: TaskTimeline['origin']
  tokens: number
  inferenceTimeMs: number
  attemptCount: number
  contextIds: string[]
  steps: TaskLaneStepView[]
}

const PRE_ATTEMPT_SUBTYPES: ReadonlySet<string> = new Set([EVENT_SUBTYPE.RESET, EVENT_SUBTYPE.EXECUTE])

// Cada `reasoning` (B.1) abre uma nova tentativa; `verify_*`, `store` e `learn` pertencem à
// tentativa em curso. `reset`/`execute` são anteriores à primeira tentativa e não entram em
// nenhuma chave de agrupamento (FASE 06, seção 5).
function computeAttemptIndices(steps: ThinkingStep[]): number[] {
  let counter = 0
  return steps.map((step) => {
    if (PRE_ATTEMPT_SUBTYPES.has(step.subtype)) return 0
    if (step.subtype === EVENT_SUBTYPE.REASONING) counter += 1
    return Math.max(counter, 1)
  })
}

/** Uma `TaskLaneView` por `TaskTimeline` do `ThinkingRun` — o que a faixa ② desenha. */
export function buildTaskLanes(run: ThinkingRun): TaskLaneView[] {
  return run.tasks.map((task) => {
    const attemptIndices = computeAttemptIndices(task.steps)
    return {
      id: task.id,
      title: task.title,
      status: task.status,
      origin: task.origin,
      tokens: task.tokens,
      inferenceTimeMs: task.inferenceTimeMs,
      attemptCount: task.attempts.length,
      contextIds: task.contextIds,
      // `attemptIndices` sempre tem o mesmo tamanho de `task.steps` (mesmo `.map`); o `?? 0` é
      // só para satisfazer `noUncheckedIndexedAccess`, não um caso alcançável.
      steps: task.steps.map((step, index) => ({ step, attemptIndex: attemptIndices[index] ?? /* v8 ignore next */ 0 })),
    }
  })
}

export interface ContextSeriesPoint {
  index: number
  stepId: string
  taskId: string
  contextId: string
  contextSize: number
  totalTokens: number
  /** Coordenadas normalizadas 0..100 — o componente só faz `viewBox="0 0 100 100"`. */
  xPercent: number
  contextYPercent: number
  totalYPercent: number
}

export interface ContextSeries {
  points: ContextSeriesPoint[]
  /** Índices, em `points`, de cada `reset` — onde `context_size` despenca (a serra dentada). */
  resetIndices: number[]
  maxContextSize: number
  maxTotalTokens: number
}

/** A serra dentada do Fresh Context: `context_size` (zera a cada reset) e `total_tokens` (monotônico). */
export function buildContextSeries(steps: ThinkingStep[]): ContextSeries {
  const maxContextSize = steps.reduce((max, step) => Math.max(max, step.contextSize), 0)
  const maxTotalTokens = steps.reduce((max, step) => Math.max(max, step.totalTokens), 0)
  const scaleMax = Math.max(maxContextSize, maxTotalTokens, 1)
  const lastIndex = Math.max(steps.length - 1, 1)

  const points = steps.map(
    (step, index): ContextSeriesPoint => ({
      index,
      stepId: step.id,
      taskId: step.taskId,
      contextId: step.contextId,
      contextSize: step.contextSize,
      totalTokens: step.totalTokens,
      xPercent: (index / lastIndex) * 100,
      contextYPercent: (step.contextSize / scaleMax) * 100,
      totalYPercent: (step.totalTokens / scaleMax) * 100,
    }),
  )

  const resetIndices: number[] = []
  steps.forEach((step, index) => {
    if (step.subtype === EVENT_SUBTYPE.RESET) resetIndices.push(index)
  })

  return { points, resetIndices, maxContextSize, maxTotalTokens }
}

export type LoopArcId = 'verify-retry' | 'replan-return'

export interface LoopArcView {
  id: LoopArcId
  active: boolean
}

/** Os dois arcos de retorno do paper: B.2 → B.1 (retentativa) e C.2 → B (replanejamento). */
export function buildLoopArcs(run: ThinkingRun): LoopArcView[] {
  const hasRetry = run.tasks.some((task) => task.attempts.length > 1)
  const hasReplan = run.tasks.some((task) => task.origin === 'C2')
  return [
    { id: 'verify-retry', active: hasRetry },
    { id: 'replan-return', active: hasReplan },
  ]
}
