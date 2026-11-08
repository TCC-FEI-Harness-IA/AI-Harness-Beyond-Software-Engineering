import { useEffect, useRef } from 'react'
import { MessageStats } from '@/components/chat/MessageStats'
import { PhaseTag } from '@/components/chat/PhaseTag'
import { Markdown } from '@/components/markdown/Markdown'
import { Button } from '@/components/primitives/Button'
import { IconButton } from '@/components/primitives/IconButton'
import { TASK_LABEL_SETUP, TASK_LABEL_SYNTHESIS } from '@/domain/enums/taskLabels'
import type { MessageStatsView } from '@/domain/types/messageStatsView'
import type { ThinkingStep } from '@/domain/types/thinkingRun'
import styles from './StepDetailPanel.module.css'

export interface StepDetailPanelProps {
  /** `null` fecha o painel — controlado inteiramente pelo passo selecionado. */
  step: ThinkingStep | null
  modelName: string | null
  sessionId: string | null
  onClose: () => void
  /** "Ver no Modo Chat" (README, seção 7): troca de modo e rola até `step.id`. */
  onViewInChat: (stepId: string) => void
}

const CLOSE_ICON = (
  <svg
    viewBox="0 0 16 16"
    width="14"
    height="14"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.6"
    strokeLinecap="round"
    aria-hidden="true"
  >
    <path d="M3 3l10 10M13 3 3 13" />
  </svg>
)

const FOCUSABLE_SELECTOR = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'

function displayTaskId(taskId: string): string | null {
  return taskId === TASK_LABEL_SETUP || taskId === TASK_LABEL_SYNTHESIS ? null : taskId
}

function buildStats(step: ThinkingStep, modelName: string | null, sessionId: string | null): MessageStatsView {
  return {
    modelName,
    tokensInput: null,
    tokensOutput: null,
    totalTokens: step.totalTokens,
    inferenceTimeMs: step.inferenceTimeMs,
    contextId: step.contextId,
    contextSize: step.contextSize,
    timestamp: step.timestamp,
    sessionId,
  }
}

/**
 * ④ Painel de detalhe (README, FASE 06, seção 7). Abre com o Markdown completo de um passo
 * clicado em qualquer nó ou ponto do Modo Gráfico. Reusa `<Markdown />` e `<MessageStats />` —
 * o Modo Gráfico não tem renderização própria de conteúdo (regra de reuso 4/5).
 */
export function StepDetailPanel({
  step,
  modelName,
  sessionId,
  onClose,
  onViewInChat,
}: StepDetailPanelProps): JSX.Element | null {
  const panelRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const isOpen = step !== null

  useEffect(() => {
    if (!isOpen) return

    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    panelRef.current?.focus()

    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }

      if (event.key !== 'Tab' || !panelRef.current) return

      const focusable = Array.from(panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (!first || !last) return

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      previousFocusRef.current?.focus()
    }
  }, [isOpen, onClose])

  if (!isOpen || !step) return null

  return (
    <>
      <button type="button" className={styles.overlay} onClick={onClose} aria-label="Fechar painel de detalhe" />
      <div ref={panelRef} className={styles.panel} role="dialog" aria-modal="true" aria-label="Detalhe do passo" tabIndex={-1}>
        <div className={styles.header}>
          <div className={styles.headerTop}>
            <PhaseTag phase={step.phase} subtype={step.subtype} taskId={displayTaskId(step.taskId)} />
            <IconButton aria-label="Fechar" icon={CLOSE_ICON} variant="ghost" size="sm" onClick={onClose} />
          </div>
          <MessageStats stats={buildStats(step, modelName, sessionId)} layout="panel" />
        </div>

        <div className={styles.body}>
          <Markdown content={step.content} variant="block" />
        </div>

        <div className={styles.footer}>
          <Button variant="secondary" size="sm" onClick={() => onViewInChat(step.id)}>
            Ver no Modo Chat
          </Button>
        </div>
      </div>
    </>
  )
}
