// Complexidade observada no processo do Ralph Loop, extraída das mensagens persistidas da sessão:
// quantas tarefas o plano teve, quantas verificações (B.2) reprovaram e quantos planos (A.3) foram
// recusados. Serve de quebra de complexidade comum aos três benchmarks.

import type { SessionDocument } from '../types/sessionDocument'
import type { AnalysisGroup, AnalysisRecord, GroupKey } from './benchmarkAnalysis'
import { groupBy } from './benchmarkAnalysis'

export interface RalphProcessMetrics {
  /** Tarefas distintas executadas na fase B. */
  taskCount: number
  /** Resoluções (B.1) produzidas, somando as retentativas. */
  resolutionCount: number
  /** Verificações de tarefa reprovadas (B.2). */
  verificationFailures: number
  /** Planos candidatos reprovados pelo validador (A.3). */
  planRejections: number
  /** Planejamentos adicionais feitos na síntese (C.2). */
  replans: number
  llmCalls: number
}

const EXECUTION_PHASES = new Set(['B1', 'B2', 'B3', 'B4'])

export function ralphProcessMetrics(document: SessionDocument): RalphProcessMetrics {
  const tasks = new Set<string>()
  let resolutionCount = 0
  let verificationFailures = 0
  let planRejections = 0
  let replans = 0
  for (const message of document.messages) {
    if (message.task_id !== null && EXECUTION_PHASES.has(message.phase)) tasks.add(message.task_id)
    if (message.subtype === 'reasoning') resolutionCount += 1
    else if (message.subtype === 'verify_fail') verificationFailures += 1
    else if (message.subtype === 'plan_rejected') planRejections += 1
    else if (message.subtype === 'replan') replans += 1
  }
  return {
    taskCount: tasks.size,
    resolutionCount,
    verificationFailures,
    planRejections,
    replans,
    llmCalls: document.totals.total_llm_calls,
  }
}

export type ProcessDimension = 'taskCount' | 'verificationFailures' | 'planRejections'

export const PROCESS_DIMENSION_LABEL: Record<ProcessDimension, string> = {
  taskCount: 'Tarefas no plano do Ralph',
  verificationFailures: 'Verificações de tarefa reprovadas (B.2)',
  planRejections: 'Planos reprovados pelo validador (A.3)',
}

// Últimas faixas abertas ("4+", "2+"): poucas questões passam delas e faixas vazias só poluem.
const BUCKET_CAP: Record<ProcessDimension, number> = {
  taskCount: 4,
  verificationFailures: 2,
  planRejections: 1,
}

const UNIT: Record<ProcessDimension, [string, string]> = {
  taskCount: ['tarefa', 'tarefas'],
  verificationFailures: ['reprovação', 'reprovações'],
  planRejections: ['plano reprovado', 'planos reprovados'],
}

const MISSING: GroupKey = { key: 'missing', label: 'Sessão não carregada', order: 99 }

export function processBucket(dimension: ProcessDimension, metrics: RalphProcessMetrics | undefined): GroupKey {
  if (metrics === undefined) return MISSING
  const cap = BUCKET_CAP[dimension]
  const value = Math.min(metrics[dimension], cap)
  const [singular, plural] = UNIT[dimension]
  const suffix = value === cap ? '+' : ''
  return {
    key: `${dimension}:${value}`,
    label: `${value}${suffix} ${value === 1 && suffix === '' ? singular : plural}`,
    order: value,
  }
}

/** Agrupa pela métrica do processo da sessão Ralph de cada questão (indexada por `session_id`). */
export function groupByProcess(
  records: readonly AnalysisRecord[],
  dimension: ProcessDimension,
  metricsBySession: ReadonlyMap<string, RalphProcessMetrics>,
): AnalysisGroup[] {
  return groupBy(records, (record) =>
    processBucket(
      dimension,
      record.ralph.session_id === null ? undefined : metricsBySession.get(record.ralph.session_id),
    ),
  )
}
