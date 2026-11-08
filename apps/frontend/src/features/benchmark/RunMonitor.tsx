import { Link } from 'react-router-dom'
import { Badge } from '@/components/primitives/Badge'
import { Button } from '@/components/primitives/Button'
import { Card } from '@/components/primitives/Card'
import { Spinner } from '@/components/primitives/Spinner'
import {
  BENCHMARK_SESSION_STATUS_LABEL,
  BENCHMARK_SESSION_STATUS_TONE,
} from '@/domain/enums/benchmarkStatus'
import { buildBenchmarkSessionPath } from '@/router/routes'
import { useBenchmarkRun } from '@/state/BenchmarkRunContext'
import { benchmarkLabel } from '@/domain/services/benchmarkDefinition'
import { BenchmarkProgressStats } from './BenchmarkProgressStats'
import { BenchmarkQuestionsTable } from './BenchmarkQuestionsTable'
import { BenchmarkSummary } from './BenchmarkSummary'
import styles from './RunMonitor.module.css'

/**
 * Acompanhamento da bateria em execução, alimentado pelos frames do WebSocket guardados em
 * `BenchmarkRunContext`. Continua visível depois do fim, até ser dispensado, com o desfecho.
 */
export function RunMonitor(): JSX.Element | null {
  const { phase, session, rejection, rerunQuestionIds, isActive, rerun, cancel, dismiss } =
    useBenchmarkRun()
  if (phase === 'idle') return null
  const rerunCount = rerunQuestionIds.length
  const title = rerunCount === 1
    ? `Reexecução de ${rerunQuestionIds[0]}`
    : rerunCount > 1 ? `Reexecução de ${rerunCount} questões` : 'Bateria atual'
  const statusTone = phase === 'cancelled' ? 'warning'
    : isActive && rerunCount > 0 ? 'accent'
      : session ? BENCHMARK_SESSION_STATUS_TONE[session.status] : 'neutral'
  const statusLabel = phase === 'cancelled' ? 'Cancelada'
    : isActive && rerunCount > 0 ? 'Reexecutando'
      : session ? BENCHMARK_SESSION_STATUS_LABEL[session.status] : ''

  return (
    <Card as="article" padding="lg" className={styles.card} aria-label="Bateria atual">
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h2 className={styles.title}>{title}</h2>
          {session ? <Badge tone={statusTone}>{statusLabel}</Badge> : null}
        </div>
        <div className={styles.actions}>
          {session ? (
            <Link to={buildBenchmarkSessionPath(session.id)} className={styles.detailLink}>
              Ver detalhes
            </Link>
          ) : null}
          {isActive ? (
            <Button variant="danger" size="sm" onClick={cancel}>
              Cancelar
            </Button>
          ) : (
            <Button variant="secondary" size="sm" onClick={dismiss}>
              Fechar
            </Button>
          )}
        </div>
      </header>

      {phase === 'connecting' ? (
        <p className={styles.notice} role="status">
          <Spinner size="sm" label="Conectando" />{' '}
          {rerunCount > 0 ? 'Iniciando a reexecução…' : 'Iniciando a bateria…'}
        </p>
      ) : null}
      {rejection ? (
        <p className={styles.error} role="alert">
          {rejection}
        </p>
      ) : null}
      {session?.error ? (
        <p className={styles.error} role="alert">
          {session.error}
        </p>
      ) : null}
      {phase === 'cancelled' ? (
        <p className={styles.notice} role="status">
          Bateria cancelada: as questões em execução foram interrompidas no servidor.
        </p>
      ) : null}

      {session ? (
        <>
          <p>{benchmarkLabel(session.benchmark)}</p>
          <BenchmarkProgressStats session={session} />
          <BenchmarkSummary session={session} />
          <BenchmarkQuestionsTable
            session={session}
            onRerun={(questionId) => rerun(session.id, questionId, session.benchmark.dataset)}
            onRerunMany={(questionIds) => rerun(session.id, questionIds, session.benchmark.dataset)}
            rerunDisabled={isActive}
          />
        </>
      ) : null}
    </Card>
  )
}
