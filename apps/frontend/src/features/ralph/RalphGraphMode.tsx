import type { ThinkingRun } from '@/domain/types/thinkingRun'
import styles from './RalphGraphMode.module.css'

export interface RalphGraphModeProps {
  run: ThinkingRun
  isLive: boolean
}

/**
 * Placeholder do Modo Gráfico — a linha do tempo animada entra na FASE 06. Já recebe o
 * `ThinkingRun` completo (README, FASE 05, seção 2) para que a fase seguinte não precise
 * reprocessar `steps` crus para reconstruir a estrutura de tarefas/fases.
 */
export function RalphGraphMode({ run }: RalphGraphModeProps): JSX.Element {
  return (
    <div className={styles.placeholder} role="status">
      <p className={styles.title}>Modo Gráfico chega na próxima fase.</p>
      <p className={styles.meta}>{run.steps.length} passos recebidos até agora.</p>
    </div>
  )
}
