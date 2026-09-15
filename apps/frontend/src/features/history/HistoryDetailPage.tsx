import { useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { HttpError } from '@/api/errors/HttpError'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/primitives/Button'
import { EmptyState } from '@/components/primitives/EmptyState'
import { ErrorState } from '@/components/primitives/ErrorState'
import { Skeleton } from '@/components/primitives/Skeleton'
import { SESSION_STATUS } from '@/domain/enums/sessionStatus'
import { sessionToRun } from '@/domain/services/sessionToRun'
import { RalphView } from '@/features/ralph/RalphView'
import { SimpleChatView } from '@/features/simple-chat/SimpleChatView'
import { useSession } from '@/hooks/useSession'
import { useSessionList } from '@/hooks/useSessionList'
import { ROUTES } from '@/router/routes'
import { useRegisterSidebar } from '@/state/SidebarSlotContext'
import { HistorySidebar } from './HistorySidebar'
import styles from './HistoryDetailPage.module.css'

const NOT_FOUND_ICON = (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
    <circle cx="11" cy="11" r="7" />
    <path d="m21 21-4.3-4.3M8.5 8.5l5 5m0-5-5 5" strokeLinecap="round" />
  </svg>
)

/**
 * Detalhe de um chat do histórico (README, FASE 07, seção 6). Reconstrói a sessão persistida em
 * `ThinkingRun`/`SimpleRun` via `sessionToRun` e reusa `RalphView`/`SimpleChatView` sem nenhuma
 * modificação — se algo não coubesse aqui, o conserto seria generalizar aquelas telas, não criar
 * uma variante "de histórico" (regra de reuso 3 do README).
 */
export function HistoryDetailPage(): JSX.Element {
  const { sessionId: rawSessionId } = useParams<{ sessionId: string }>()
  const sessionId = rawSessionId ? decodeURIComponent(rawSessionId) : ''
  const navigate = useNavigate()
  const { state, reload } = useSession(sessionId)
  const { items: sidebarItems, isLoadingIds: isSidebarLoading } = useSessionList()

  // Memoizado: um elemento JSX é um objeto novo a cada render, mesmo com as mesmas props. Sem
  // isto, `useRegisterSidebar` (cujo efeito depende deste nó) rodaria a cada render — inclusive
  // os que o próprio `setSidebar` dispara no provider acima — entrando em loop infinito.
  const sidebarNode = useMemo(
    () => <HistorySidebar items={sidebarItems} activeSessionId={sessionId} isLoading={isSidebarLoading} />,
    [sidebarItems, sessionId, isSidebarLoading],
  )
  useRegisterSidebar(sidebarNode)

  if (state.status === 'loading') {
    return (
      <PageContainer width="content">
        <div className={styles.skeletonWrap}>
          <Skeleton height="1.5rem" width="55%" />
          <Skeleton lines={6} />
        </div>
      </PageContainer>
    )
  }

  if (state.status === 'error') {
    if (state.error instanceof HttpError && state.error.status === 404) {
      return (
        <PageContainer width="content">
          <EmptyState
            icon={NOT_FOUND_ICON}
            title="Esta conversa não existe mais"
            action={<Button onClick={() => navigate(ROUTES.history)}>Voltar ao histórico</Button>}
          />
        </PageContainer>
      )
    }

    if (state.error instanceof HttpError && state.error.status === 400) {
      return (
        <PageContainer width="content">
          <ErrorState
            error={{
              userMessage: 'O registro deste chat está corrompido.',
              message: `id: ${sessionId}`,
            }}
            onRetry={reload}
          />
        </PageContainer>
      )
    }

    return (
      <PageContainer width="content">
        <ErrorState error={state.error} onRetry={reload} />
      </PageContainer>
    )
  }

  const document = state.data
  const result = sessionToRun(document)

  return (
    <>
      {document.status === SESSION_STATUS.FAILED ? (
        <p className={styles.notice} role="status">
          Esta execução falhou antes de terminar.
        </p>
      ) : null}
      {document.status === SESSION_STATUS.RUNNING ? (
        <p className={styles.notice} role="status">
          Esta execução ainda está em andamento.
        </p>
      ) : null}

      {result.kind === 'ralph' ? (
        <RalphView run={result.run} isLive={false} />
      ) : (
        <SimpleChatView run={result.run} isLive={false} />
      )}
    </>
  )
}
