import { useState } from 'react'
import { ContextMeter } from '@/components/timeline/ContextMeter'
import { ContextSpark } from '@/components/timeline/ContextSpark'
import { LegendBar } from '@/components/timeline/LegendBar'
import { PhaseTrack } from '@/components/timeline/PhaseTrack'
import { TaskLane } from '@/components/timeline/TaskLane'
import { EmptyState } from '@/components/primitives/EmptyState'
import { buildContextSeries, buildTaskLanes } from '@/domain/services/graphLayout'
import type { ThinkingRun, ThinkingStep } from '@/domain/types/thinkingRun'
import { useViewMode } from '@/state/ViewModeContext'
import { RunSummaryPanel } from './RunSummaryPanel'
import { StepDetailPanel } from './StepDetailPanel'
import styles from './RalphGraphMode.module.css'

export interface RalphGraphModeProps {
  run: ThinkingRun
  isLive: boolean
  /** Rola o Modo Chat até este passo depois de trocar de modo pelo botão do painel de detalhe. */
  onViewStepInChat?: (stepId: string) => void
}

const EMPTY_ICON = (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
    <path d="M4 12h4l2-6 4 12 2-6h4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

/**
 * Modo Gráfico do Ralph (README, FASE 06): a linha do tempo animada das fases do paper, com a
 * trilha macro A→B→C, as faixas por tarefa, o medidor de contexto e o painel de detalhe. Consome
 * o mesmo `ThinkingRun` da FASE 05, sem processar eventos crus — funciona identicamente ao vivo
 * e no histórico (a FASE 07 reusa este componente sem alteração nenhuma).
 */
export function RalphGraphMode({ run, isLive, onViewStepInChat }: RalphGraphModeProps): JSX.Element {
  const [selectedStep, setSelectedStep] = useState<ThinkingStep | null>(null)
  const { setViewMode } = useViewMode()

  if (run.steps.length === 0) {
    return (
      <div className={styles.emptyWrapper}>
        <EmptyState
          icon={EMPTY_ICON}
          title="Nenhum passo ainda"
          description="A linha do tempo aparece assim que a execução começar."
        />
      </div>
    )
  }

  const lanes = buildTaskLanes(run)
  const series = buildContextSeries(run.steps)

  function handleViewInChat(stepId: string): void {
    setSelectedStep(null)
    setViewMode('chat')
    onViewStepInChat?.(stepId)
  }

  return (
    <div className={styles.layout}>
      <section className={styles.section} aria-label="Trilha macro das fases">
        <PhaseTrack run={run} isLive={isLive} onStepSelect={setSelectedStep} />
      </section>

      <section className={styles.section} aria-label="Tarefas">
        <h2 className={styles.sectionTitle}>Tarefas</h2>
        <ul className={styles.lanes}>
          {lanes.map((lane) => (
            <TaskLane key={lane.id} lane={lane} isLive={isLive} onStepSelect={setSelectedStep} />
          ))}
        </ul>
        <LegendBar />
      </section>

      <section className={styles.section} aria-label="Janela de contexto">
        <div className={styles.contextRow}>
          <div className={styles.contextMeter}>
            <ContextMeter steps={run.steps} />
          </div>
          <ContextSpark series={series} />
        </div>
      </section>

      <section className={styles.section} aria-label="Resumo da execução">
        <RunSummaryPanel run={run} />
      </section>

      <StepDetailPanel
        step={selectedStep}
        modelName={run.modelName}
        onClose={() => setSelectedStep(null)}
        onViewInChat={handleViewInChat}
      />
    </div>
  )
}
