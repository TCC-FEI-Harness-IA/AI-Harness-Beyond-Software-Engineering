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
import { BenchmarkProgressStats } from './BenchmarkProgressStats'
import { BenchmarkQuestionsTable } from './BenchmarkQuestionsTable'
import { BenchmarkSummary } from './BenchmarkSummary'
import styles from './RunMonitor.module.css'

/**
 * Acompanhamento da bateria em execução, alimentado pelos frames do WebSocket guardados em
 * `BenchmarkRunContext`. Continua visível depois do fim, até ser dispensado, com o desfecho.
 */
export function RunMonitor(): JSX.Element | null {
  const { phase, session, rejection, isActive, cancel, dismiss } = useBenchmarkRun()
  if (phase === 'idle') return null

  return (
    <Card as="article" padding="lg" className={styles.card} aria-label="Bateria atual">
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h2 className={styles.title}>Bateria atual</h2>
          {session ? (
            <Badge
              tone={
                phase === 'cancelled' ? 'warning' : BENCHMARK_SESSION_STATUS_TONE[session.status]
              }
            >
              {phase === 'cancelled' ? 'Cancelada' : BENCHMARK_SESSION_STATUS_LABEL[session.status]}
            </Badge>
          ) : null}
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
          <Spinner size="sm" label="Conectando" /> Iniciando a bateria…
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
          <BenchmarkProgressStats session={session} />
          <BenchmarkSummary session={session} />
          <BenchmarkQuestionsTable session={session} />
        </>
      ) : null}
    </Card>
  )
}
