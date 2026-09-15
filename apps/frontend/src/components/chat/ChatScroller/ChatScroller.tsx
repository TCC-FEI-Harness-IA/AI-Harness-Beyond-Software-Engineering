import type { ReactNode } from 'react'
import { useAutoScroll } from '@/hooks/useAutoScroll'
import styles from './ChatScroller.module.css'

export interface ChatScrollerProps {
  children: ReactNode
  /** Muda quando chega conteúdo novo; dispara a avaliação de auto-scroll. */
  contentKey: string | number
  isLive?: boolean
}

/**
 * Container rolável de mensagens com o comportamento "grudar no fim": rola automaticamente
 * quando chega conteúdo novo e o usuário já estava perto do fim; se ele subiu para ler, não
 * puxa a tela — mostra um botão flutuante para voltar.
 */
export function ChatScroller({ children, contentKey, isLive = false }: ChatScrollerProps): JSX.Element {
  const { containerRef, hasNewContentBelow, scrollToBottom } = useAutoScroll(contentKey)

  return (
    <div
      ref={containerRef}
      className={styles.scroller}
      aria-live="polite"
      aria-label={isLive ? 'Execução em andamento' : 'Histórico de mensagens'}
    >
      {children}
      {hasNewContentBelow ? (
        <button type="button" className={styles.jumpButton} onClick={scrollToBottom}>
          Ir para o fim
        </button>
      ) : null}
    </div>
  )
}
