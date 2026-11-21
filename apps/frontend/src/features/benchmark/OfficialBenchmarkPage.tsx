import { Link, useParams } from 'react-router-dom'
import { HttpError } from '@/api/errors/HttpError'
import { PageContainer } from '@/components/layout/PageContainer'
import { EmptyState } from '@/components/primitives/EmptyState'
import { ErrorState } from '@/components/primitives/ErrorState'
import { Skeleton } from '@/components/primitives/Skeleton'
import { officialAsDocument } from '@/domain/services/officialBattery'
import { useOfficialPublication } from '@/hooks/useOfficialPublications'
import { ROUTES } from '@/router/routes'
import { BenchmarkSessionView } from './BenchmarkSessionPage'

/** Detalhe público de um resultado oficial: a cópia publicada da bateria, somente leitura e sem login. */
export function OfficialBenchmarkPage(): JSX.Element {
  const { publicationId: rawId } = useParams<{ publicationId: string }>()
  const publicationId = rawId ? decodeURIComponent(rawId) : ''
  const publication = useOfficialPublication(publicationId)

  if (publication.status === 'error') {
    return (
      <PageContainer width="content">
        {publication.error instanceof HttpError && publication.error.status === 404 ? (
          <EmptyState
            icon={<span>?</span>}
            title="Este resultado oficial não existe"
            action={<Link to={ROUTES.benchmark}>Voltar ao BenchMark</Link>}
          />
        ) : (
          <ErrorState error={publication.error} onRetry={publication.reload} />
        )}
      </PageContainer>
    )
  }

  if (publication.status !== 'success' || publication.data === null) {
    return (
      <PageContainer width="wide">
        <Skeleton height="1.5rem" width="45%" />
        <Skeleton lines={6} />
      </PageContainer>
    )
  }

  const data = publication.data
  return (
    <PageContainer width="wide">
      <BenchmarkSessionView
        session={officialAsDocument(data)}
        isLive={false}
        official={{
          publishedAt: data.publishedAt,
          textRedacted: data.textRedacted,
          sourceBenchmarkSessionId: data.sourceBenchmarkSessionId,
        }}
      />
    </PageContainer>
  )
}
