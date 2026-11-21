import { cx } from '@/components/cx'
import type { MacroNodeView } from '@/domain/services/graphLayout'
import styles from './PhaseNode.module.css'

export interface PhaseNodeProps {
  node: MacroNodeView
  onSelect?: () => void
  /** Halo pulsando — só ao vivo (README, seção 9): histórico nunca pulsa, mesmo num nó `active`. */
  pulsing?: boolean
}

const STATUS_LABEL: Record<MacroNodeView['status'], string> = {
  pending: 'próxima etapa',
  active: 'etapa atual',
  done: 'etapa concluída',
  skipped: 'não foi necessária',
}

const CHECK_PATH = 'M3 8.2l3 3 6.5-7.4'
const SKIP_PATH = 'M2 2l10 10M12 2 2 12'

/**
 * Um nó da trilha macro A→B→C (README, FASE 06, seção 4). O texto e a cor vêm inteiramente de
 * `MacroNodeView` — nada é decidido aqui além de qual ícone mostrar para cada `status`.
 */
export function PhaseNode({ node, onSelect, pulsing = false }: PhaseNodeProps): JSX.Element {
  const ariaLabel = `${node.subtitle} — ${STATUS_LABEL[node.status]}`

  return (
    <button
      type="button"
      className={cx(styles.node, styles[node.status], pulsing && styles.pulse)}
      onClick={onSelect}
      aria-label={ariaLabel}
      title={node.status === 'skipped' ? 'Não foi necessário' : undefined}
    >
      <span className={styles.badge} aria-hidden="true">
        {node.status === 'done' ? (
          <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d={CHECK_PATH} />
          </svg>
        ) : node.status === 'skipped' ? (
          <svg viewBox="0 0 16 16" width="11" height="11" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
            <path d={SKIP_PATH} />
          </svg>
        ) : (
          <span className={styles.shortLabel}>{node.shortLabel}</span>
        )}
      </span>

      <span className={styles.texts}>
        <span className={styles.shortLabelText}>{node.shortLabel}</span>
        <span className={styles.subtitle}>{node.subtitle}</span>
      </span>

      {node.progress ? (
        <span className={styles.progress}>
          <span className={styles.progressCount}>
            {node.progress.done}/{node.progress.total}
          </span>
          <span className={styles.progressBar}>
            <span
              className={styles.progressFill}
              style={{ width: node.progress.total > 0 ? `${(node.progress.done / node.progress.total) * 100}%` : '0%' }}
            />
          </span>
        </span>
      ) : null}
    </button>
  )
}
