import type { ContextSeries } from '@/domain/services/graphLayout'
import styles from './ContextSpark.module.css'

export interface ContextSparkProps {
  series: ContextSeries
}

const MIN_BAR_HEIGHT_PERCENT = 4

/**
 * Miniatura do total acumulado da sessão — "▁▂▃▄▅▆▇█" do requisito, em barras CSS (README,
 * FASE 06, seção 6). Puramente decorativo: a leitura acessível da série já é o `aria-label` do
 * `ContextMeter`, por isso este componente é `aria-hidden`.
 */
export function ContextSpark({ series }: ContextSparkProps): JSX.Element {
  const max = Math.max(series.maxTotalTokens, 1)

  return (
    <div className={styles.spark} aria-hidden="true">
      {series.points.map((point) => (
        <span
          key={point.stepId}
          className={styles.bar}
          style={{ height: `${Math.max((point.totalTokens / max) * 100, MIN_BAR_HEIGHT_PERCENT)}%` }}
        />
      ))}
    </div>
  )
}
