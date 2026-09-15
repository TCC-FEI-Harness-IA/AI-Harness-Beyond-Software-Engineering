import { useEffect } from 'react'
import { Composer } from '@/components/chat/Composer'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/primitives/Button'
import { EmptyState } from '@/components/primitives/EmptyState'
import { RUN_STATUS } from '@/domain/enums/runStatus'
import type { ThinkingRun } from '@/domain/types/thinkingRun'
import { useViewMode } from '@/state/ViewModeContext'
import { RalphChatMode } from './RalphChatMode'
import { RalphGraphMode } from './RalphGraphMode'
import { ViewModeSwitch } from './ViewModeSwitch'
import styles from './RalphView.module.css'

export interface RalphViewProps {
  run: ThinkingRun
  /** Detalhes de apresentação que só a execução ao vivo tem: cursor/Composer, auto-scroll e o
   * botão de cancelar. A FASE 07 reusa esta view com `isLive={false}` para o histórico. */
  isLive: boolean
  isStreaming?: boolean
  /** Cancelamento é um estado de apresentação separado do `ThinkingRun` — o domínio não tem
   * um `RunStatus` de "cancelado" (só quem cancelou sabe disso, não o reducer). */
  wasCancelled?: boolean
  composerValue?: string
  onComposerChange?: (value: string) => void
  onStart?: (question: string) => void
  onCancel?: () => void
  onRetry?: () => void
}

const DOCUMENT_TITLE_MAX_CHARS = 40

const EMPTY_ICON = (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
    <circle cx="12" cy="12" r="3" />
    <ellipse cx="12" cy="12" rx="9" ry="3.8" transform="rotate(30 12 12)" />
  </svg>
)

/**
 * Apresentação pura do Ralph Loop Adaptado (README, FASE 05, seção 7). Recebe um
 * `ThinkingRun` e o booleano `isLive`; não importa nada de `src/api/`, de hooks de rede, de
 * `src/config/` nem de `react-router-dom` — quem conecta é `RalphPage`.
 */
export function RalphView({
  run,
  isLive,
  isStreaming = false,
  wasCancelled = false,
  composerValue = '',
  onComposerChange,
  onStart,
  onCancel,
  onRetry,
}: RalphViewProps): JSX.Element {
  const { viewMode } = useViewMode()

  useEffect(() => {
    if (!isLive || run.question === '') return
    const previousTitle = document.title
    document.title =
      run.question.length > DOCUMENT_TITLE_MAX_CHARS
        ? `${run.question.slice(0, DOCUMENT_TITLE_MAX_CHARS)}…`
        : run.question
    return () => {
      document.title = previousTitle
    }
  }, [isLive, run.question])

  function handleSubmit(): void {
    if (composerValue.trim() === '') return
    onStart?.(composerValue)
  }

  const isEmpty = run.steps.length === 0 && run.status === RUN_STATUS.IDLE

  return (
    <PageContainer width="content">
      <div className={styles.layout}>
        {isEmpty ? (
          <EmptyState icon={EMPTY_ICON} title="Faça uma pergunta para começar" />
        ) : (
          <>
            <ViewModeSwitch />

            {viewMode === 'chat' ? (
              <RalphChatMode
                run={run}
                isLive={isLive}
                isStreaming={isStreaming}
                {...(onRetry ? { onRetry } : {})}
              />
            ) : (
              <RalphGraphMode run={run} isLive={isLive} />
            )}

            {isLive && isStreaming ? (
              <div className={styles.cancelBar}>
                <Button variant="secondary" size="sm" onClick={onCancel}>
                  Cancelar execução
                </Button>
              </div>
            ) : null}

            {isLive && !isStreaming && wasCancelled ? (
              <div className={styles.cancelledNotice} role="status">
                <p>Execução cancelada.</p>
                <Button variant="secondary" size="sm" onClick={onRetry}>
                  Executar de novo
                </Button>
              </div>
            ) : null}
          </>
        )}

        {isLive ? (
          <div className={styles.composer}>
            <Composer
              value={composerValue}
              onChange={(value) => onComposerChange?.(value)}
              onSubmit={handleSubmit}
              placeholder="Faça uma pergunta…"
              busy={isStreaming}
              autoFocus
            />
          </div>
        ) : null}
      </div>
    </PageContainer>
  )
}
