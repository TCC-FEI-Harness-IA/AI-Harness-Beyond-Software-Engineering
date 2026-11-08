import { useEffect } from 'react'
import { ChatScroller } from '@/components/chat/ChatScroller'
import { Composer } from '@/components/chat/Composer'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { MessageStats } from '@/components/chat/MessageStats'
import { TypingIndicator } from '@/components/chat/TypingIndicator'
import { PageContainer } from '@/components/layout/PageContainer'
import { EmptyState } from '@/components/primitives/EmptyState'
import { ErrorState } from '@/components/primitives/ErrorState'
import { RUN_STATUS } from '@/domain/enums/runStatus'
import type { SimpleRun } from '@/domain/types/simpleRun'
import styles from './SimpleChatView.module.css'

export interface SimpleChatViewProps {
  run: SimpleRun
  /** Detalhes de apresentação que só a execução ao vivo tem: cursor/Composer e a
   * possibilidade de reenviar. O histórico (FASE 07) reusa esta view com `isLive={false}`. */
  isLive: boolean
  composerValue?: string
  onComposerChange?: (value: string) => void
  onSend?: (question: string) => void
  onRetry?: () => void
}

const DOCUMENT_TITLE_MAX_CHARS = 40

/**
 * Apresentação pura do fluxo baseline (README, FASE 04, seção 8). Recebe um `SimpleRun` e o
 * booleano `isLive`; não conhece hook, rede nem rota — quem conecta é `SimpleChatPage`. A
 * FASE 07 reusa este componente sem alterações para o histórico de sessões `DIRECT`.
 */
export function SimpleChatView({
  run,
  isLive,
  composerValue = '',
  onComposerChange,
  onSend,
  onRetry,
}: SimpleChatViewProps): JSX.Element {
  const firstQuestion = run.messages.find((message) => message.role === 'user')?.content ?? null

  useEffect(() => {
    if (!isLive || firstQuestion === null) return

    const previousTitle = document.title
    document.title =
      firstQuestion.length > DOCUMENT_TITLE_MAX_CHARS
        ? `${firstQuestion.slice(0, DOCUMENT_TITLE_MAX_CHARS)}…`
        : firstQuestion

    return () => {
      document.title = previousTitle
    }
  }, [isLive, firstQuestion])

  const isBusy = run.status === RUN_STATUS.RUNNING

  function handleSubmit(): void {
    if (composerValue.trim() === '') return
    onSend?.(composerValue)
  }

  return (
    <PageContainer width="content">
      <div className={styles.layout}>
        {run.messages.length === 0 ? (
          <EmptyState
            icon={
              <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                aria-hidden="true"
              >
                <path d="M4 5h16v11H8l-4 4V5Z" />
              </svg>
            }
            title="Faça uma pergunta para começar"
          />
        ) : (
          <ChatScroller contentKey={run.messages.length} isLive={isLive}>
            {run.messages.map((message) => (
              <MessageBubble
                key={message.id}
                role={message.role}
                content={message.content}
                animateIn
                {...(message.stats ? { stats: message.stats } : {})}
              />
            ))}
            {isBusy ? <TypingIndicator /> : null}
            {run.error ? (
              <ErrorState error={run.error} {...(onRetry ? { onRetry } : {})} />
            ) : null}
          </ChatScroller>
        )}

        {run.totals && !isBusy && run.messages.length > 0 ? (
          <div className={styles.summary}>
            <MessageStats
              layout="panel"
              stats={{
                modelName: null,
                tokensInput: null,
                tokensOutput: null,
                totalTokens: run.totals.totalTokens,
                inferenceTimeMs: run.totals.inferenceTimeMs,
                contextId: null,
                contextSize: null,
                timestamp: null,
              }}
            />
          </div>
        ) : null}

        {isLive ? (
          <div className={styles.composer}>
            <Composer
              value={composerValue}
              onChange={(value) => onComposerChange?.(value)}
              onSubmit={handleSubmit}
              placeholder="Faça uma pergunta…"
              busy={isBusy}
              autoFocus
            />
          </div>
        ) : null}
      </div>
    </PageContainer>
  )
}
