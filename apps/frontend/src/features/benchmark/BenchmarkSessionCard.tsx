import { Link } from 'react-router-dom'
import { Badge } from '@/components/primitives/Badge'
import { Card } from '@/components/primitives/Card'
import {
  BENCHMARK_SESSION_STATUS_LABEL,
  BENCHMARK_SESSION_STATUS_TONE,
} from '@/domain/enums/benchmarkStatus'
import {
  formatDateTime,
  formatDuration,
  formatPercent,
  formatTokens,
} from '@/domain/services/formatters'
import type {
  BenchmarkModeSummary,
  BenchmarkSessionDocument,
} from '@/domain/types/benchmarkSession'
import { buildBenchmarkSessionPath } from '@/router/routes'
import styles from './BenchmarkSessionCard.module.css'

function scoreLabel(label: string, summary: BenchmarkModeSummary): string {
  return `${label} ${summary.correct}/${summary.executed} (${formatPercent(summary.accuracy)})`
}

/** Cartão de uma bateria na listagem: desfecho, acertos por fluxo, consumo e duração. */
export function BenchmarkSessionCard({
  session,
}: {
  session: BenchmarkSessionDocument
}): JSX.Element {
  return (
    <Card as="li" className={styles.card}>
      <Link to={buildBenchmarkSessionPath(session.id)} className={styles.link}>
        <div className={styles.header}>
          <span className={styles.date}>{formatDateTime(session.created_at)}</span>
          <Badge tone={BENCHMARK_SESSION_STATUS_TONE[session.status]}>
            {BENCHMARK_SESSION_STATUS_LABEL[session.status]}
          </Badge>
        </div>
        <p className={styles.scores}>
          <span>{scoreLabel('Simples', session.summary.simple)}</span>
          <span>{scoreLabel('Ralph', session.summary.ralph)}</span>
        </p>
        <p className={styles.meta}>
          <span>{session.model_name}</span>
          <span>
            {session.question_count} {session.question_count === 1 ? 'questão' : 'questões'}
          </span>
          <span>{session.max_parallel} em paralelo</span>
          <span>{formatTokens(session.total_tokens)} tokens</span>
          <span>{formatDuration(session.wall_time_ms)}</span>
        </p>
      </Link>
    </Card>
  )
}
