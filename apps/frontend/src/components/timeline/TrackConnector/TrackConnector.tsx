import { cx } from '@/components/cx'
import styles from './TrackConnector.module.css'

export interface TrackConnectorProps {
  /** O trecho já percorrido (entre dois nós concluídos, ou chegando num nó `active`). */
  drawn: boolean
  /** Um ponto luminoso percorre o traço — sinal de "ainda em movimento" (README, seção 4). */
  animated: boolean
}

/**
 * O traço entre dois nós da trilha macro. É o conector, não os nós, que comunica continuidade
 * (README, FASE 06, seção 4): o trecho percorrido é desenhado (`stroke-dashoffset`), nunca só
 * recolorido.
 */
export function TrackConnector({ drawn, animated }: TrackConnectorProps): JSX.Element {
  return (
    <svg className={styles.connector} viewBox="0 0 100 4" preserveAspectRatio="none" aria-hidden="true">
      <path className={styles.track} d="M0 2 H100" />
      <path className={cx(styles.progress, drawn && styles.drawn)} d="M0 2 H100" />
      {animated ? <circle className={styles.pulse} cx="0" cy="2" r="2" /> : null}
    </svg>
  )
}
