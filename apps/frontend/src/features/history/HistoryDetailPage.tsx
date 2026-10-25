import type { SessionSource } from '@/domain/types/sessionSource'
import { useMemo } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { HttpError } from '@/api/errors/HttpError'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/primitives/Button'
import { EmptyState } from '@/components/primitives/EmptyState'
import { ErrorState } from '@/components/primitives/ErrorState'
import { Skeleton } from '@/components/primitives/Skeleton'
import { BENCHMARK_MODE_LABEL } from '@/domain/enums/benchmarkStatus'
import { SESSION_STATUS } from '@/domain/enums/sessionStatus'
import { sessionToRun } from '@/domain/services/sessionToRun'
import { RalphView } from '@/features/ralph/RalphView'
import { SimpleChatView } from '@/features/simple-chat/SimpleChatView'
import { useBenchmarkSession } from '@/hooks/useBenchmarkData'
import { useSession } from '@/hooks/useSession'
import { useSessionList } from '@/hooks/useSessionList'
import { ROUTES, buildBenchmarkChildSessionPath, buildBenchmarkSessionPath, buildHistoryDetailPath } from '@/router/routes'
import { useBenchmarkRun } from '@/state/BenchmarkRunContext'
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
export function HistoryDetailPage({ source = 'history' }: { source?: SessionSource }): JSX.Element {
  const { sessionId: rawSessionId, benchmarkSessionId: rawBenchmarkSessionId } = useParams<{
    sessionId: string
    benchmarkSessionId: string
  }>()
  const sessionId = rawSessionId ? decodeURIComponent(rawSessionId) : ''
  const benchmarkSessionId =
    source === 'benchmark' && rawBenchmarkSessionId ? decodeURIComponent(rawBenchmarkSessionId) : null
  const navigate = useNavigate()
  const { state, reload } = useSession(sessionId, source)

  // Numa sessão de benchmark, a barra lateral lista só as sessões da mesma bateria — ao vivo,
  // quando é a bateria em execução, ou como foram persistidas.
  const benchmarkRun = useBenchmarkRun()
  const liveBattery = benchmarkRun.session?.id === benchmarkSessionId ? benchmarkRun.session : null
  const storedBattery = useBenchmarkSession(liveBattery === null ? benchmarkSessionId : null)
  const batterySessionIds =
    benchmarkSessionId === null
      ? null
      : (liveBattery?.session_ids ?? (storedBattery.status === 'success' ? storedBattery.data?.session_ids : null) ?? [])
  const { items: sidebarItems, isLoadingIds: isSidebarLoading } = useSessionList(source, batterySessionIds)
  const isBatteryLoading = benchmarkSessionId !== null && liveBattery === null && storedBattery.status === 'loading'
  const backPath = benchmarkSessionId === null ? ROUTES.history : buildBenchmarkSessionPath(benchmarkSessionId)
  const linkTo = useMemo(
    () =>
      benchmarkSessionId === null
        ? buildHistoryDetailPath
        : (id: string) => buildBenchmarkChildSessionPath(benchmarkSessionId, id),
    [benchmarkSessionId],
  )

  // Memoizado: um elemento JSX é um objeto novo a cada render, mesmo com as mesmas props. Sem
  // isto, `useRegisterSidebar` (cujo efeito depende deste nó) rodaria a cada render — inclusive
  // os que o próprio `setSidebar` dispara no provider acima — entrando em loop infinito.
  const sidebarNode = useMemo(
    () => (
      <HistorySidebar
        items={sidebarItems}
        activeSessionId={sessionId}
        isLoading={isSidebarLoading || isBatteryLoading}
        linkTo={linkTo}
      />
    ),
    [sidebarItems, sessionId, isSidebarLoading, isBatteryLoading, linkTo],
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
            action={
              <Button onClick={() => navigate(backPath)}>
                {benchmarkSessionId === null ? 'Voltar ao histórico' : 'Voltar à bateria'}
              </Button>
            }
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
      {benchmarkSessionId !== null && document.benchmark_details?.is_banchmark ? (
        <PageContainer width="content">
          <div className={styles.benchmarkHeader}>
            <Link to={backPath} className={styles.backLink}>
              ← Voltar à bateria
            </Link>
            <h2 className={styles.benchmarkTitle}>
              {document.benchmark_details.question_name}
              {document.benchmark_details.inference_mode
                ? ` · ${BENCHMARK_MODE_LABEL[document.benchmark_details.inference_mode]}`
                : null}
            </h2>
            <p className={styles.benchmarkMeta}>
              {document.benchmark_details.is_correct === null
                ? 'Avaliação pendente'
                : document.benchmark_details.is_correct
                  ? 'Certo'
                  : 'Errado'}
              {' · '}Gabarito: {document.benchmark_details.corret_answer ?? '—'}
              {' · '}Alternativa selecionada: {document.benchmark_details.selected_alternative ?? '—'}
            </p>
            {document.benchmark_details.error ? (
              <p className={styles.benchmarkMeta} role="status">
                {document.benchmark_details.error}
              </p>
            ) : null}
          </div>
        </PageContainer>
      ) : null}
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
