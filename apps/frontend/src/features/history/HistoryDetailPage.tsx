import { useParams } from 'react-router-dom'
import { PageContainer } from '@/components/layout/PageContainer'

export function HistoryDetailPage(): JSX.Element {
  const { sessionId } = useParams<{ sessionId: string }>()
  const decodedSessionId = sessionId ? decodeURIComponent(sessionId) : null

  return (
    <PageContainer>
      <h1>Histórico</h1>
      <p>Sessão: {decodedSessionId}</p>
    </PageContainer>
  )
}
