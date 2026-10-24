// View-model único do Ralph Loop Adaptado (README, seção 6.3; FASE 05, seção 3). Produzido
// tanto pelo `reasoningRunReducer` (evento ao vivo) quanto por `sessionToThinkingRun` (FASE 07,
// a partir do histórico) — nenhuma tela sabe de onde ele veio.

import type { EventSubtype } from '../enums/eventSubtype'
import type { EventType } from '../enums/eventType'
import type { RunStatus } from '../enums/runStatus'
import type { TaskStatus } from '../enums/taskStatus'
import type { ThinkingPhase } from '../enums/thinkingPhase'
import type { RunError } from './runError'

// Um passo de pensamento — a unidade que o Modo Chat renderiza mensagem a mensagem.
export interface ThinkingStep {
  /** Estável e determinístico: `${order}:${phase}:${subtype}:${taskId}` (FASE 05, seção 3). */
  id: string
  order: number
  type: EventType
  subtype: EventSubtype
  phase: ThinkingPhase
  taskId: string
  content: string
  totalTokens: number
  contextId: string
  contextSize: number
  inferenceTimeMs: number
  /** Presente no histórico, ausente (`null`) ao vivo — o WebSocket não manda timestamp. */
  timestamp: string | null
}

// Uma tentativa de resolução de uma tarefa: resolução (B.1) + verificação (B.2) correspondente.
export interface TaskAttemptView {
  /** 1-based. */
  index: number
  reasoning: ThinkingStep | null
  verification: ThinkingStep | null
  /** `null` enquanto a verificação não chegou. */
  approved: boolean | null
}

// Agregação de uma tarefa por todos os seus passos e tentativas — o que o Modo Gráfico desenha.
export interface TaskTimeline {
  /** 'T1', 'T2', … */
  id: string
  /** Extraído do conteúdo de A2/C2 quando disponível. */
  title: string | null
  status: TaskStatus
  /** Planejamento inicial (A2) ou planejamento adicional (C2). */
  origin: 'A2' | 'C2'
  attempts: TaskAttemptView[]
  steps: ThinkingStep[]
  /** Quantas janelas de contexto (`context_id` distintos) esta tarefa consumiu. */
  contextIds: string[]
  tokens: number
  inferenceTimeMs: number
}

// Nó da trilha macro A → B → C. 'B' agrega B1–B4 (README, seção 6.3).
export type PhaseNodeId = 'A1' | 'A2' | 'A3' | 'B' | 'C1' | 'C2' | 'C3'

export interface PhaseProgress {
  id: PhaseNodeId
  label: string
  status: 'pending' | 'active' | 'done' | 'skipped'
  stepCount: number
}

// Totais agregados de uma execução do Ralph (FASE 05, seção 3). Distinto do `RunTotals` do
// fluxo simples (`domain/types/runTotals.ts`, FASE 04) — os dois fluxos medem coisas
// diferentes (tarefas/tentativas/janelas de contexto não existem no fluxo simples) e um nome
// compartilhado exigiria forçar os dois formatos num só tipo, o que a FASE 05 não pede.
export interface ThinkingRunTotals {
  totalTokens: number
  inferenceTimeMs: number
  llmCalls: number
  taskCount: number
  attemptCount: number
  /** Quantas janelas de contexto foram abertas — métrica central do paper (fresh context). */
  contextCount: number
  /** Só existe no histórico (FASE 07); `null` ao vivo. */
  wallTimeMs: number | null
}

export interface RunDegradation {
  limit: string
  phase: ThinkingPhase
  taskId: string | null
  description: string
  occurredAt: string | null
}

export interface ThinkingRun {
  sessionId: string | null
  question: string
  modelName: string | null
  status: RunStatus
  /** Ordem cronológica — o Modo Chat renderiza isto. */
  steps: ThinkingStep[]
  /** Agregação por tarefa — o Modo Gráfico renderiza isto. */
  tasks: TaskTimeline[]
  /** A1, A2, A3, B, C1, C2, C3 com estado — a trilha macro. */
  phases: PhaseProgress[]
  finalAnswer: string | null
  totals: ThinkingRunTotals
  degradations: RunDegradation[]
  error: RunError | null
  /**
   * Aviso não fatal do frame mais recente (ex.: um frame malformado no meio do stream —
   * FASE 08, seção 4). Nunca aparece no histórico (`sessionToThinkingRun` sempre entrega
   * `null`); ao vivo, o stream continua normalmente depois dele.
   */
  warning: string | null
}
