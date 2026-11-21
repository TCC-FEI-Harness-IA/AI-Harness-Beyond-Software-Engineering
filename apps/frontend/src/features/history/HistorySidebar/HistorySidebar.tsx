import { Link } from 'react-router-dom'
import { Skeleton } from '@/components/primitives/Skeleton'
import { env } from '@/config/env'
import { BENCHMARK_MODE_LABEL } from '@/domain/enums/benchmarkStatus'
import { truncate } from '@/domain/services/formatters'
import type { SessionSummaryView } from '@/domain/types/sessionSummaryView'
import { buildHistoryDetailPath } from '@/router/routes'
import { cx } from '@/components/cx'
import { RALPH_FLOW_ICON, SIMPLE_FLOW_ICON } from '../flowIcons'
import styles from './HistorySidebar.module.css'

export interface HistorySidebarProps {
  /** Destino de cada item; o padrão é o detalhe do histórico. */
  linkTo?: (sessionId: string) => string
  items: SessionSummaryView[]
  activeSessionId: string
  /** A lista ainda não chegou do cache/rede — mostra esqueletos no lugar dos itens. */
  isLoading: boolean
}

const SKELETON_COUNT = 6

// Sessões de benchmark compartilham o mesmo enunciado longo; o nome da questão e o fluxo as
// distinguem na barra lateral.
function sidebarLabel(item: SessionSummaryView): string {
  const details = item.benchmarkDetails
  if (details?.is_banchmark && details.question_name) {
    return details.inference_mode
      ? `${details.question_name} · ${BENCHMARK_MODE_LABEL[details.inference_mode]}`
      : details.question_name
  }
  return item.fullQuestion
}

/**
 * Barra lateral reduzida do histórico (README, FASE 07, seção 6). Reusa o cache de
 * `useSessionList`: quando o usuário chega pelo card, a lista já está em memória e a barra
 * aparece instantaneamente; ao entrar direto pela URL, ela mostra esqueletos enquanto
 * `HistoryListPage`/`HistoryDetailPage` hidratam em segundo plano.
 */
export function HistorySidebar({
  items,
  activeSessionId,
  isLoading,
  linkTo = buildHistoryDetailPath,
}: HistorySidebarProps): JSX.Element {
  return (
    <nav className={styles.nav} aria-label="Conversas">
      <ul className={styles.list}>
        {items.map((item) => {
          const isActive = item.id === activeSessionId
          return (
            <li key={item.id}>
              <Link
                to={linkTo(item.id)}
                className={cx(styles.item, isActive && styles.itemActive)}
                aria-current={isActive ? 'page' : undefined}
                title={item.fullQuestion}
              >
                <span className={styles.icon} aria-hidden="true">
                  {item.flow === 'ralph' ? RALPH_FLOW_ICON : SIMPLE_FLOW_ICON}
                </span>
                {truncate(sidebarLabel(item), env.historySidebarSummaryMaxChars)}
              </Link>
            </li>
          )
        })}

        {isLoading && items.length === 0
          ? Array.from({ length: SKELETON_COUNT }, (_, index) => (
              <li key={index} className={styles.skeletonItem}>
                <Skeleton height="0.9em" />
              </li>
            ))
          : null}
      </ul>
    </nav>
  )
}
