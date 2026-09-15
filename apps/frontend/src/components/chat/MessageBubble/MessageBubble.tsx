import type { ReactNode } from 'react'
import type { Tone } from '@/domain/enums/tone'
import type { MessageStatsView } from '@/domain/types/messageStatsView'
import { Markdown } from '@/components/markdown/Markdown'
import { MessageStats } from '@/components/chat/MessageStats'
import { cx } from '@/components/cx'
import styles from './MessageBubble.module.css'

const ROLE_LABEL: Record<'user' | 'assistant', string> = {
  user: 'Mensagem do usuário',
  assistant: 'Mensagem do modelo',
}

const TONE_CLASS: Partial<Record<Tone, string | undefined>> = {
  accent: styles.toneAccent,
  success: styles.toneSuccess,
  warning: styles.toneWarning,
  danger: styles.toneDanger,
  context: styles.toneContext,
}

export interface MessageBubbleProps {
  role: 'user' | 'assistant' | 'system'
  content: string
  stats?: MessageStatsView
  /** PhaseTag, no fluxo Ralph. */
  header?: ReactNode
  /** Borda/realce lateral, usado por `verify_fail` e `degraded`. */
  tone?: Tone
  /** 'final' = resposta final destacada. */
  emphasis?: 'none' | 'final'
  animateIn?: boolean
}

/**
 * Bolha de mensagem — a unidade visual repetida em todo chat do app, simples ou Ralph, ao
 * vivo ou histórico. `role="system"` não usa bolha: é o separador com rótulo usado por `reset`
 * e `store`, para não competir com o conteúdo do modelo.
 */
export function MessageBubble({
  role,
  content,
  stats,
  header,
  tone = 'neutral',
  emphasis = 'none',
  animateIn = false,
}: MessageBubbleProps): JSX.Element {
  if (role === 'system') {
    return (
      <div className={cx(styles.row, styles.rowSystem, animateIn && styles.animateIn)}>
        <p className={styles.system}>{content}</p>
      </div>
    )
  }

  const rowClass = role === 'user' ? styles.rowUser : styles.rowAssistant
  const roleClass = role === 'user' ? styles.user : styles.assistant

  return (
    <div className={cx(styles.row, rowClass, animateIn && styles.animateIn)}>
      <div
        role="group"
        aria-label={ROLE_LABEL[role]}
        aria-roledescription={emphasis === 'final' ? 'Resposta final' : undefined}
        className={cx(
          styles.bubble,
          roleClass,
          TONE_CLASS[tone],
          emphasis === 'final' && styles.emphasisFinal,
        )}
      >
        {header ? <div className={styles.header}>{header}</div> : null}
        <Markdown content={content} variant={role === 'user' ? 'bubble' : 'block'} />
        {stats ? (
          <div className={styles.stats}>
            <MessageStats stats={stats} layout="inline" />
          </div>
        ) : null}
      </div>
    </div>
  )
}
