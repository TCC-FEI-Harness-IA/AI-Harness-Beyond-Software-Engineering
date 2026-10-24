import { buildLoopArcs, buildMacroTrack } from '@/domain/services/graphLayout'
import type { PhaseNodeId, ThinkingRun, ThinkingStep } from '@/domain/types/thinkingRun'
import { PhaseNode } from '@/components/timeline/PhaseNode'
import { TrackConnector } from '@/components/timeline/TrackConnector'
import { LoopArc } from '@/components/timeline/LoopArc'
import styles from './PhaseTrack.module.css'

export interface PhaseTrackProps {
  run: ThinkingRun
  isLive: boolean
  onStepSelect: (step: ThinkingStep) => void
}

function nodeIdForPhase(phase: ThinkingStep['phase']): PhaseNodeId | null {
  switch (phase) {
    case 'A1':
      return 'A1'
    case 'A2':
      return 'A2'
    case 'A3':
      return 'A3'
    case 'B1':
    case 'B2':
    case 'B3':
    case 'B4':
      return 'B'
    case 'C1':
      return 'C1'
    case 'C2':
      return 'C2'
    case 'C3':
      return 'C3'
    default:
      return null
  }
}

// O passo mais recente de cada fase macro é o que faz mais sentido mostrar ao clicar num nó —
// é o que "chegou até ali" no momento da execução.
function representativeStep(run: ThinkingRun, nodeId: PhaseNodeId): ThinkingStep | null {
  let found: ThinkingStep | null = null
  for (const step of run.steps) {
    if (nodeIdForPhase(step.phase) === nodeId) found = step
  }
  return found
}

/**
 * ① Trilha macro — o "caminho" pedido no requisito (README, FASE 06, seção 4): os sete nós do
 * paper ligados por conectores desenhados, com os dois arcos de loop que mostram que o fluxo
 * volta. Cálculo de estado vem inteiramente de `graphLayout.ts` — este componente só posiciona.
 */
export function PhaseTrack({ run, isLive, onStepSelect }: PhaseTrackProps): JSX.Element {
  const track = buildMacroTrack(run)
  const arcs = buildLoopArcs(run)
  const retryArc = arcs.find((arc) => arc.id === 'verify-retry')
  const replanArc = arcs.find((arc) => arc.id === 'replan-return')

  function handleSelect(nodeId: PhaseNodeId): void {
    const step = representativeStep(run, nodeId)
    if (step) onStepSelect(step)
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.row}>
        {track.map((node, index) => {
          const next = track[index + 1]
          return (
            <div key={node.id} className={styles.item}>
              <div className={styles.nodeSlot}>
                <PhaseNode
                  node={node}
                  onSelect={() => handleSelect(node.id)}
                  pulsing={isLive && node.status === 'active'}
                />
                {node.id === 'B' && retryArc ? (
                  <div className={styles.retrySlot}>
                    <LoopArc arc={retryArc} />
                  </div>
                ) : null}
              </div>
              {next ? (
                <TrackConnector
                  drawn={next.status === 'done' || next.status === 'active'}
                  animated={isLive && next.status === 'active'}
                />
              ) : null}
            </div>
          )
        })}
      </div>

      {replanArc ? (
        <div className={styles.replanSlot}>
          <LoopArc arc={replanArc} />
        </div>
      ) : null}
    </div>
  )
}
