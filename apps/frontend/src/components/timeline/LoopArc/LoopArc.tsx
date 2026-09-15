import { cx } from '@/components/cx'
import type { LoopArcView } from '@/domain/services/graphLayout'
import styles from './LoopArc.module.css'

export interface LoopArcProps {
  arc: LoopArcView
}

const RETRY_ICON_PATH = 'M8 1a7 7 0 1 0 6.9 8.1M13 1v4h-4'

/**
 * Os dois arcos de loop do paper (README, FASE 06, seção 4) — o que diferencia esta trilha de
 * uma barra de progresso comum: eles mostram que o fluxo *volta*. `verify-retry` é o pequeno
 * ⟳ do ciclo B.1 ⇄ B.2, ao lado do nó `B`; `replan-return` é o arco largo C.2 → B.
 */
export function LoopArc({ arc }: LoopArcProps): JSX.Element {
  if (arc.id === 'verify-retry') {
    return (
      <span
        className={cx(styles.retry, arc.active && styles.retryActive)}
        role="img"
        aria-label={
          arc.active
            ? 'Ciclo de retentativa B.1 ⇄ B.2: pelo menos uma verificação foi reprovada'
            : 'Ciclo de retentativa B.1 ⇄ B.2, ainda não acionado'
        }
        title="Ciclo B.1 ⇄ B.2 — retentativa dentro da mesma tarefa"
      >
        <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
          <path d={RETRY_ICON_PATH} />
        </svg>
      </span>
    )
  }

  return (
    <div className={styles.replanRow}>
      <svg
        className={cx(styles.replanArc, arc.active && styles.replanActive)}
        viewBox="0 0 100 24"
        preserveAspectRatio="none"
        role="img"
        aria-label={
          arc.active
            ? 'Arco de retorno C.2 para B: planejamento adicional foi acionado'
            : 'Arco de retorno C.2 para B, ainda não acionado'
        }
      >
        <path d="M75 2 C 75 20, 42 20, 42 2" />
      </svg>
      <span className={styles.replanLabel} aria-hidden="true">
        C.2 → B · planejamento adicional
      </span>
    </div>
  )
}
