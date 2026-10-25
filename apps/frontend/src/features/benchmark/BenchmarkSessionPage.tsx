import { Link, useParams } from 'react-router-dom'
import { HttpError } from '@/api/errors/HttpError'
import { PageContainer } from '@/components/layout/PageContainer'
import { Badge } from '@/components/primitives/Badge'
import { Card } from '@/components/primitives/Card'
import { EmptyState } from '@/components/primitives/EmptyState'
import { ErrorState } from '@/components/primitives/ErrorState'
import { Skeleton } from '@/components/primitives/Skeleton'
import {
  BENCHMARK_SESSION_STATUS_LABEL,
  BENCHMARK_SESSION_STATUS_TONE,
} from '@/domain/enums/benchmarkStatus'
import { providerLabel } from '@/domain/enums/modelProvider'
import { formatDateTime, formatTemperature, formatTokens } from '@/domain/services/formatters'
import type { BenchmarkSessionDocument } from '@/domain/types/benchmarkSession'
import { useBenchmarkSession } from '@/hooks/useBenchmarkData'
import { ROUTES } from '@/router/routes'
import { useBenchmarkRun } from '@/state/BenchmarkRunContext'
import { BenchmarkProgressStats } from './BenchmarkProgressStats'
import { BenchmarkQuestionsTable } from './BenchmarkQuestionsTable'
import { BenchmarkSummary } from './BenchmarkSummary'
import styles from './BenchmarkSessionPage.module.css'

const NOT_FOUND_ICON = (
  <svg
    width="32"
    height="32"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    aria-hidden="true"
  >
    <circle cx="11" cy="11" r="7" />
    <path d="m21 21-4.3-4.3" strokeLinecap="round" />
  </svg>
)

function BenchmarkSessionView({
  session,
  isLive,
}: {
  session: BenchmarkSessionDocument
  isLive: boolean
}): JSX.Element {
  return (
    <>
      <div className={styles.header}>
        <Link to={ROUTES.benchmark} className={styles.backLink}>
          ← BenchMark
        </Link>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>Bateria de {formatDateTime(session.created_at)}</h1>
          <Badge tone={BENCHMARK_SESSION_STATUS_TONE[session.status]}>
            {BENCHMARK_SESSION_STATUS_LABEL[session.status]}
          </Badge>
          {isLive ? <Badge tone="accent">Ao vivo</Badge> : null}
        </div>
        <p className={styles.meta}>
          <span>{session.model_name}</span>
          <span>{providerLabel(session.provider)}</span>
          <span>máx. {formatTokens(session.max_tokens)} tokens</span>
          <span>temperatura {formatTemperature(session.temperature)}</span>
          <span>{session.max_parallel} em paralelo</span>
          <span className={styles.id}>{session.id}</span>
        </p>
      </div>

      {session.error ? (
        <p className={styles.error} role="alert">
          {session.error}
        </p>
      ) : null}

      <Card padding="lg" className={styles.card}>
        <BenchmarkProgressStats session={session} />
      </Card>
      <Card padding="lg" className={styles.card}>
        <h2 className={styles.sectionTitle}>Simples × Ralph</h2>
        <BenchmarkSummary session={session} />
      </Card>
      <h2 className={styles.sectionTitle}>Questões e sessões</h2>
      <BenchmarkQuestionsTable session={session} />
    </>
  )
}

/**
 * Detalhe de uma `BenchmarkSession`: configuração, progresso, comparativo dos fluxos e as
 * sessões de cada questão. Se for a bateria em execução, mostra os frames ao vivo.
 */
export function BenchmarkSessionPage(): JSX.Element {
  const { benchmarkSessionId: rawId } = useParams<{ benchmarkSessionId: string }>()
  const benchmarkSessionId = rawId ? decodeURIComponent(rawId) : ''
  const run = useBenchmarkRun()
  const liveSession = run.session?.id === benchmarkSessionId && run.isActive ? run.session : null
  const stored = useBenchmarkSession(
    liveSession === null ? benchmarkSessionId : null,
    run.finishedCount,
  )

  if (liveSession !== null) {
    return (
      <PageContainer width="wide">
        <BenchmarkSessionView session={liveSession} isLive />
      </PageContainer>
    )
  }

  if (stored.status === 'error') {
    return (
      <PageContainer width="content">
        {stored.error instanceof HttpError && stored.error.status === 404 ? (
          <EmptyState
            icon={NOT_FOUND_ICON}
            title="Esta bateria não existe"
            action={<Link to={ROUTES.benchmark}>Voltar ao BenchMark</Link>}
          />
        ) : (
          <ErrorState error={stored.error} onRetry={stored.reload} />
        )}
      </PageContainer>
    )
  }

  if (stored.status !== 'success' || stored.data === null) {
    return (
      <PageContainer width="wide">
        <Skeleton height="1.5rem" width="45%" />
        <Skeleton lines={6} />
      </PageContainer>
    )
  }

  return (
    <PageContainer width="wide">
      <BenchmarkSessionView session={stored.data} isLive={false} />
    </PageContainer>
  )
}
